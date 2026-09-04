import sqlite3
import os
import hashlib
import hmac
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

db_path = os.path.join(os.path.dirname(__file__), "coldchain.db")
ENCRYPTION_KEY = os.getenv("PII_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    with open(os.path.join(os.path.dirname(__file__), ".env"), "a") as f:
        f.write(f"\nPII_ENCRYPTION_KEY={ENCRYPTION_KEY}\n")

fernet = Fernet(ENCRYPTION_KEY.encode())

def get_blind_index(value: str) -> str:
    if not value:
        return value
    return hmac.new(ENCRYPTION_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        if "email_encrypted" not in columns:
            print("Adicionando colunas de criptografia na tabela users...")
            cursor.execute("ALTER TABLE users ADD COLUMN email_encrypted TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN phone_encrypted TEXT")
            
            print("Migrando dados existentes para criptografia...")
            cursor.execute("SELECT id, email, phone FROM users")
            rows = cursor.fetchall()
            for row in rows:
                uid = row[0]
                email_real = row[1]
                phone_real = row[2]
                
                blind_email = get_blind_index(email_real)
                enc_email = fernet.encrypt(email_real.encode()).decode() if email_real else None
                enc_phone = fernet.encrypt(phone_real.encode()).decode() if phone_real else None
                
                cursor.execute(
                    "UPDATE users SET email = ?, email_encrypted = ?, phone_encrypted = ?, phone = NULL WHERE id = ?",
                    (blind_email, enc_email, enc_phone, uid)
                )
            
            conn.commit()
            print("Migração de criptografia concluída com sucesso.")
        else:
            print("As colunas de criptografia já existem na tabela users.")
    except Exception as e:
        print(f"Erro durante a migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
