import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
from .models import Base

load_dotenv()

# Determina URL do banco de dados
# Se DATABASE_URL estiver configurada para postgresql, adapta para driver asyncpg se necessário,
# ou usa SQLite por padrão caso seja local/não configurado.
raw_db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///coldchain.db")

if raw_db_url.startswith("postgresql://"):
    # Converte para driver async se for postgresql
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://")
elif raw_db_url.startswith("sqlite:///"):
    db_url = raw_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif not raw_db_url.startswith("sqlite+aiosqlite://") and not raw_db_url.startswith("postgresql+asyncpg://"):
    db_url = "sqlite+aiosqlite:///coldchain.db"
else:
    db_url = raw_db_url

from sqlalchemy import event

# Caso o usuário esteja em ambiente local sem PostgreSQL ativo, fallback automático para SQLite
try:
    engine = create_async_engine(db_url, echo=False)
except Exception:
    db_url = "sqlite+aiosqlite:///coldchain.db"
    engine = create_async_engine(db_url, echo=False)

if "sqlite" in db_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Inicializa as tabelas no banco de dados"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependência para injeção de sessão do banco"""
    async with AsyncSessionLocal() as session:
        yield session
