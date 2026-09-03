import datetime
import os
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.db import get_db
from ..database.models import User, TuyaIntegration, Device
from .auth_routes import get_current_user
from ..collectors.tuya_client import TuyaClient

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])
tuya_client = TuyaClient()

@router.get("/tuya/auth-url")
async def get_tuya_auth_url(request: Request, current_user: User = Depends(get_current_user)):
    """Gera a URL de login do usuário para vincular sua conta Tuya/Ekaza"""
    # A URL de callback deve ser pública (ngrok em dev)
    host_url = os.getenv("HOST_URL", str(request.base_url).rstrip('/'))
    redirect_uri = f"{host_url}/api/integrations/tuya/callback"
    
    # URL oficial de autorização OAuth da Tuya
    auth_url = f"{tuya_client.endpoint}/api/v1.0/oauth2/authorize?client_id={tuya_client.access_id}&redirect_uri={redirect_uri}&response_type=code&state={current_user.id}"
    
    return {"success": True, "auth_url": auth_url}

@router.get("/tuya/callback")
async def tuya_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Recebe o authorization_code e troca pelo token de usuário"""
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="State inválido (user_id).")
    
    token_data = tuya_client.get_user_token_from_ticket(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Falha ao trocar ticket pelo token na Tuya.")
    
    tuya_uid = token_data.get("uid")
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expire_time", 7200)
    
    if not tuya_uid or not access_token:
        raise HTTPException(status_code=400, detail="Dados de token inválidos da Tuya.")
    
    # Verifica se já existe integração para este usuário
    result = await db.execute(select(TuyaIntegration).where(TuyaIntegration.user_id == user_id))
    integration = result.scalar_one_or_none()
    
    if integration:
        integration.tuya_uid = tuya_uid
        integration.access_token = access_token
        integration.refresh_token = refresh_token
        integration.token_expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    else:
        integration = TuyaIntegration(
            user_id=user_id,
            tuya_uid=tuya_uid,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
        )
        db.add(integration)
        
    await db.commit()
    
    # Em produção, redirecionaria para o dashboard com uma mensagem de sucesso.
    # Ex: return RedirectResponse(url="/?tuya_linked=true")
    # Por enquanto, retornamos JSON para facilitar debug e uso com modais.
    return {"success": True, "message": "Conta Tuya/Ekaza vinculada com sucesso! Você pode fechar esta aba."}

@router.post("/tuya/sync")
async def sync_tuya_devices(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Puxa os dispositivos do usuário na Tuya e cadastra no ControlCold"""
    result = await db.execute(select(TuyaIntegration).where(TuyaIntegration.user_id == current_user.id))
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=400, detail="Conta Tuya não vinculada.")
    
    # Puxa dispositivos da Tuya
    devices_data = tuya_client.get_user_devices(integration.tuya_uid, integration.access_token)
    if not devices_data:
        return {"success": True, "message": "Nenhum dispositivo encontrado na conta Tuya.", "synced_count": 0}
        
    synced_count = 0
    for d_data in devices_data:
        device_id = d_data.get("id")
        name = d_data.get("name", "Sensor Tuya")
        
        # Ignora se não houver ID
        if not device_id:
            continue
            
        # Verifica se já existe no banco
        res = await db.execute(select(Device).where(Device.id == device_id))
        existing_device = res.scalar_one_or_none()
        
        if not existing_device:
            new_device = Device(
                id=device_id,
                user_id=current_user.id,
                name=name,
                category="congelados", # Padrão, usuário pode editar
                temp_min=-22.0,
                temp_max=-15.0
            )
            db.add(new_device)
            synced_count += 1
            
    if synced_count > 0:
        await db.commit()
        
    return {"success": True, "message": f"{synced_count} novos dispositivos sincronizados com sucesso!", "synced_count": synced_count}
