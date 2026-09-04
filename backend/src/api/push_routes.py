import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, ConfigDict

from ..database.db import get_db
from ..database.models import User, PushSubscription
from .auth_routes import get_current_user

router = APIRouter()

# DTO para a subscription Web Push (Keys: p256dh, auth)
class PushKeys(BaseModel):
    model_config = ConfigDict(extra='forbid')
    p256dh: str
    auth: str

class PushSubscriptionDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    endpoint: str
    keys: PushKeys

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Retorna a chave pública VAPID para o frontend."""
    public_key = os.getenv("VAPID_PUBLIC_KEY", "")
    if not public_key:
        raise HTTPException(status_code=501, detail="VAPID_PUBLIC_KEY não configurada no servidor.")
    return {"public_key": public_key}

@router.post("/subscribe")
async def subscribe_push(sub: PushSubscriptionDTO, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Salva a assinatura Push do navegador do usuário no banco."""
    # Verifica se já existe para não duplicar
    query = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == sub.endpoint)
    )
    existing = query.scalars().first()

    if existing:
        # Se for do mesmo usuário, tudo certo. Se for outro, atualiza.
        if existing.user_id != current_user.id:
            existing.user_id = current_user.id
            existing.p256dh = sub.keys.p256dh
            existing.auth = sub.keys.auth
            await db.commit()
        return {"message": "Assinatura já registrada/atualizada."}

    # Cria nova
    new_sub = PushSubscription(
        user_id=current_user.id,
        endpoint=sub.endpoint,
        p256dh=sub.keys.p256dh,
        auth=sub.keys.auth
    )
    db.add(new_sub)
    await db.commit()
    
    return {"message": "Notificações Push ativadas com sucesso."}
