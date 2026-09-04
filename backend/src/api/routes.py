import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from ..database.db import get_db
from ..database.models import Device, TelemetryLog, AlarmEvent, User
from ..collectors.tuya_client import TuyaClient
from ..collectors.simulator import TelemetrySimulator
from ..alerts.telegram_bot import TelegramNotifier
from .auth_routes import get_current_user

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])

# Schemas Pydantic
class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    category: Optional[str] = "congelados"
    location: Optional[str] = "Setor Principal"
    temp_min: float = -22.0
    temp_max: float = -15.0
    local_ip: Optional[str] = None
    local_key: Optional[str] = None

class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    is_active: Optional[bool] = None
    local_ip: Optional[str] = None
    local_key: Optional[str] = None

class AnomalyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_id: str
    anomaly_type: str = "DOOR_OPEN"  # DOOR_OPEN, DEFROST, SPIKE

class TelegramTestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chat_id: Optional[str] = None

# Instâncias compartilhadas
tuya_client = TuyaClient()
simulator = TelemetrySimulator()
telegram_notifier = TelegramNotifier()

@router.get("/overview")
async def get_overview(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Retorna métricas consolidadas da câmara fria / loja"""
    devices_query = await db.execute(select(Device).where(Device.is_active == True, Device.user_id == current_user.id))
    devices = devices_query.scalars().all()

    total = len(devices)
    normal = sum(1 for d in devices if d.status == "NORMAL")
    alerta = sum(1 for d in devices if d.status == "ALERTA")
    critico = sum(1 for d in devices if d.status == "CRITICO")
    offline = sum(1 for d in devices if d.status == "OFFLINE")

    temps = [d.current_temp for d in devices if d.current_temp is not None]
    avg_temp = round(sum(temps) / len(temps), 1) if temps else 0.0

    # Contagem de alarmes ativos
    active_alarms_q = await db.execute(
        select(func.count(AlarmEvent.id)).where(AlarmEvent.status == "ACTIVE")
    )
    active_alarms_count = active_alarms_q.scalar() or 0

    return {
        "total_devices": total,
        "normal_count": normal,
        "alert_count": alerta,
        "critical_count": critico,
        "offline_count": offline,
        "average_temp": avg_temp,
        "active_alarms_count": active_alarms_count,
        "system_mode": "LIVE_TUYA" if tuya_client.is_configured() else "SIMULATOR",
        "tuya_configured": tuya_client.is_configured(),
        "telegram_configured": telegram_notifier.is_configured()
    }

@router.get("/devices")
async def list_devices(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Lista todos os freezers monitorados com status atual"""
    result = await db.execute(select(Device).where(Device.user_id == current_user.id).order_by(Device.name))
    devices = result.scalars().all()
    return [d.to_dict() for d in devices]

@router.post("/devices")
async def create_device(payload: DeviceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Cadastra um novo freezer / sensor Tuya no sistema"""
    existing = await db.get(Device, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail="Dispositivo com este ID já cadastrado")

    device = Device(
        id=payload.id,
        user_id=current_user.id,
        name=payload.name,
        category=payload.category,
        location=payload.location,
        temp_min=payload.temp_min,
        temp_max=payload.temp_max,
        local_ip=payload.local_ip,
        local_key=payload.local_key,
        status="NORMAL"
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device.to_dict()

@router.put("/devices/{device_id}")
async def update_device(device_id: str, payload: DeviceUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Atualiza limites térmicos ou configurações de um freezer"""
    device = await db.get(Device, device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou sem permissão")

    dump_fn = getattr(payload, "model_dump", None) or getattr(payload, "dict")
    for field, val in dump_fn(exclude_unset=True).items():
        setattr(device, field, val)

    await db.commit()
    await db.refresh(device)
    return device.to_dict()

@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Remove um freezer do monitoramento"""
    device = await db.get(Device, device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou sem permissão")

    await db.delete(device)
    await db.commit()
    return {"message": "Dispositivo removido com sucesso"}

@router.get("/devices/{device_id}/history")
async def get_device_history(
    device_id: str,
    limit: int = Query(60, ge=10, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retorna o histórico de leituras de temperatura e umidade para renderização de gráficos"""
    device = await db.get(Device, device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou sem permissão")

    result = await db.execute(
        select(TelemetryLog)
        .where(TelemetryLog.device_id == device_id)
        .order_by(desc(TelemetryLog.timestamp))
        .limit(limit)
    )
    logs = result.scalars().all()
    # Retorna em ordem cronológica (mais antigo para o mais recente)
    logs_ordered = list(reversed(logs))
    return [log.to_dict() for log in logs_ordered]

@router.get("/alarms")
async def list_alarms(limit: int = 50, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Retorna lista de alarmes e incidentes recentes"""
    result = await db.execute(
        select(AlarmEvent)
        .join(Device, AlarmEvent.device_id == Device.id)
        .where(Device.user_id == current_user.id)
        .order_by(desc(AlarmEvent.triggered_at))
        .limit(limit)
    )
    alarms = result.scalars().all()
    return [a.to_dict() for a in alarms]

@router.post("/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Reconhece/silencia um alarme ativo"""
    result = await db.execute(
        select(AlarmEvent)
        .join(Device, AlarmEvent.device_id == Device.id)
        .where(AlarmEvent.id == alarm_id, Device.user_id == current_user.id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarme não encontrado ou sem permissão")

    alarm.status = "ACKNOWLEDGED"
    await db.commit()
    return {"message": "Alarme reconhecido com sucesso", "alarm": alarm.to_dict()}

@router.post("/system/simulate-incident")
async def simulate_incident(payload: AnomalyRequest):
    """Dispara uma anomalia simulada (porta aberta/elevação) para teste visual e sonoro do alarme"""
    simulator.trigger_anomaly(payload.device_id, payload.anomaly_type)
    return {"message": f"Anomalia '{payload.anomaly_type}' ativada para {payload.device_id}. Observe a curva e o alarme no painel!"}

@router.post("/system/clear-incident")
async def clear_incident(payload: AnomalyRequest):
    """Finaliza a anomalia e restabelece a temperatura segura"""
    simulator.clear_anomaly(payload.device_id)
    return {"message": f"Anomalia encerrada para {payload.device_id}. A temperatura irá normalizar."}

@router.post("/system/test-telegram")
async def test_telegram(payload: TelegramTestRequest):
    """Envia mensagem de teste para o bot do Telegram configurado"""
    if not telegram_notifier.is_configured():
        return {
            "success": False,
            "message": "TELEGRAM_BOT_TOKEN não está configurado no arquivo .env"
        }

    test_text = (
        "❄️ <b>AntiGravity ColdChain - Teste de Conexão</b>\n\n"
        "Se você recebeu esta mensagem, suas notificações do Telegram estão operando perfeitamente! 🚀"
    )
    success = telegram_notifier.send_message(test_text, payload.chat_id)
    return {
        "success": success,
        "message": "Mensagem de teste enviada com sucesso!" if success else "Falha ao enviar mensagem no Telegram. Verifique seu token e chat_id."
    }
