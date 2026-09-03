import os
import asyncio
import datetime
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, func

from src.database.db import init_db, AsyncSessionLocal
from src.database.models import Device, TelemetryLog, AlarmEvent, User, PushSubscription
from src.collectors.simulator import TelemetrySimulator
from src.api.routes import router as api_router, simulator, tuya_client, telegram_notifier
from src.api.auth_routes import router as auth_router
from src.api.integration_routes import router as integration_router
from src.api.report_routes import router as report_router
from src.api.push_routes import router as push_router
from src.api.websocket import ws_manager
from src.rules_engine.evaluator import RulesEngine
from src.security.auth import hash_password
from src.services.push_service import send_push_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("coldchain.main")

rules_engine = RulesEngine()
background_collector_running = True

async def seed_initial_devices_if_empty():
    """Garante que haja freezers cadastrados na primeira inicialização"""
    async with AsyncSessionLocal() as db:
        count_q = await db.execute(select(func.count(Device.id)))
        count = count_q.scalar() or 0
        if count == 0:
            logger.info("Banco inicial vazio. Cadastrando freezers padrão para monitoramento (Admin)...")
            admin_q = await db.execute(select(User).where(User.email == "willian.dantas@admin.com"))
            admin = admin_q.scalar_one_or_none()
            admin_id = admin.id if admin else None

            for sim_dev in TelemetrySimulator.DEFAULT_SIMULATED_DEVICES:
                device = Device(
                    id=sim_dev["id"],
                    user_id=admin_id,
                    name=sim_dev["name"],
                    category=sim_dev["category"],
                    location=sim_dev["location"],
                    temp_min=sim_dev["temp_min"],
                    temp_max=sim_dev["temp_max"],
                    current_temp=sim_dev["target_temp"],
                    current_humidity=sim_dev["target_humidity"],
                    battery_level=sim_dev["battery_level"],
                    status="NORMAL"
                )
                db.add(device)
            await db.commit()
            logger.info("Freezers padrão cadastrados com sucesso.")

async def seed_admin_user():
    """Garante que o administrador principal willian.dantas@admin.com esteja cadastrado"""
    async with AsyncSessionLocal() as db:
        admin_email = "willian.dantas@admin.com"
        result = await db.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()
        if not user:
            admin = User(
                email=admin_email,
                phone="(11) 99999-9999",
                password_hash=hash_password("98765432"),
                is_verified=True,
                role="admin"
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Administrador mestre criado com sucesso: {admin_email}")
        else:
            # Garante que a senha e status de verificação estejam em conformidade
            user.is_verified = True
            user.password_hash = hash_password("98765432")
            user.role = "admin"
            await db.commit()

async def telemetry_collection_loop():
    """
    Loop em segundo plano responsável pela coleta periódica de telemetria
    (via Tuya Cloud / TinyTuya LAN ou simulador termodinâmico).
    """
    logger.info("Iniciando loop de coleta de telemetria em segundo plano...")
    
    # Aguarda inicialização do banco
    await asyncio.sleep(2)

    while background_collector_running:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.is_active == True))
                devices = result.scalars().all()

                for dev in devices:
                    temp = None
                    hum = None
                    bat = dev.battery_level or 95

                    # 1. Tentativa de Leitura Real Tuya (se configurado)
                    if tuya_client.is_configured():
                        # Se possui IP e chave local configurados, tenta TinyTuya direto na rede local (LAN)
                        if dev.local_ip and dev.local_key:
                            local_data = tuya_client.read_device_local(dev.id, dev.local_ip, dev.local_key)
                            if local_data and local_data.get("temperature") is not None:
                                temp = local_data["temperature"]
                                hum = local_data.get("humidity")
                                bat = local_data.get("battery") or bat

                        # Se não obteve via LAN, consulta Tuya Cloud OpenAPI
                        if temp is None:
                            cloud_data = tuya_client.get_device_status(dev.id)
                            if cloud_data and cloud_data.get("temperature") is not None:
                                temp = cloud_data["temperature"]
                                hum = cloud_data.get("humidity")
                                bat = cloud_data.get("battery") or bat

                    # 2. Fallback para Simulador (quando em modo simulação ou sem sensor físico respondendo)
                    if temp is None:
                        sim_data = simulator.generate_reading({
                            "id": dev.id,
                            "target_temp": (dev.temp_min + dev.temp_max) / 2.0,
                            "target_humidity": 65.0,
                            "temp_min": dev.temp_min,
                            "temp_max": dev.temp_max,
                            "battery_level": bat
                        })
                        temp = sim_data["temperature"]
                        hum = sim_data["humidity"]
                        bat = sim_data["battery"]

                    # 2.5 Aplicar Calibração (Offset Farmacêutico)
                    if temp is not None and getattr(dev, 'temp_offset', None) is not None:
                        temp = round(temp + dev.temp_offset, 2)

                    # 3. Avaliação no Motor de Regras
                    status, new_alarms, resolved_alarms = rules_engine.evaluate(
                        device_id=dev.id,
                        device_name=dev.name,
                        temp=temp,
                        temp_min=dev.temp_min,
                        temp_max=dev.temp_max,
                        battery=bat,
                        humidity=hum
                    )

                    # 4. Atualiza estado do dispositivo
                    dev.current_temp = temp
                    dev.current_humidity = hum
                    dev.battery_level = bat
                    dev.status = status
                    dev.last_seen = datetime.datetime.utcnow()

                    # 5. Salva histórico de telemetria
                    telemetry_entry = TelemetryLog(
                        device_id=dev.id,
                        temperature=temp,
                        humidity=hum,
                        battery=bat
                    )
                    db.add(telemetry_entry)

                    # 6. Processa novos alarmes
                    for alarm_data in new_alarms:
                        alarm_rec = AlarmEvent(
                            device_id=dev.id,
                            alarm_type=alarm_data["alarm_type"],
                            severity=alarm_data["severity"],
                            value=alarm_data["value"],
                            threshold=alarm_data["threshold"],
                            message=alarm_data["message"],
                            status="ACTIVE"
                        )
                        db.add(alarm_rec)
                        # Dispara Telegram se configurado
                        telegram_notifier.send_alarm(alarm_data)
                        
                        # Notifica via WebSocket e Web Push
                        if dev.user_id:
                            await ws_manager.broadcast_to_user(dev.user_id, "NEW_ALARM", alarm_data)
                            
                            # Web Push
                            sub_q = await db.execute(select(PushSubscription).where(PushSubscription.user_id == dev.user_id))
                            subs = sub_q.scalars().all()
                            for sub in subs:
                                push_payload = {
                                    "title": "🚨 ControlCold: " + ("CRÍTICO" if alarm_data["severity"] == "CRITICAL" else "ALERTA"),
                                    "body": alarm_data["message"],
                                    "url": "/"
                                }
                                sub_info = {
                                    "endpoint": sub.endpoint,
                                    "keys": {
                                        "p256dh": sub.p256dh,
                                        "auth": sub.auth
                                    }
                                }
                                res = send_push_notification(sub_info, push_payload)
                                if res == "EXPIRED":
                                    await db.delete(sub)
                                    
                    # 7. Processa alarmes resolvidos
                    for res_type in resolved_alarms:
                        res_q = await db.execute(
                            select(AlarmEvent)
                            .where(AlarmEvent.device_id == dev.id)
                            .where(AlarmEvent.alarm_type == res_type)
                            .where(AlarmEvent.status == "ACTIVE")
                        )
                        active_records = res_q.scalars().all()
                        for rec in active_records:
                            rec.status = "RESOLVED"
                            rec.resolved_at = datetime.datetime.utcnow()

                        telegram_notifier.send_resolution(dev.name, res_type, temp)
                        if dev.user_id:
                            await ws_manager.broadcast_to_user(dev.user_id, "ALARM_RESOLVED", {
                                "device_id": dev.id,
                                "alarm_type": res_type,
                                "current_temp": temp
                            })

                    await db.commit()

                    # Transmite telemetria em tempo real via WebSocket
                    if dev.user_id:
                        await ws_manager.broadcast_to_user(dev.user_id, "TELEMETRY_UPDATE", {
                            "device_id": dev.id,
                            "name": dev.name,
                            "temperature": temp,
                            "humidity": hum,
                            "battery": bat,
                            "status": status,
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        })

        except Exception as e:
            logger.error(f"Erro no loop de telemetria: {e}", exc_info=True)

        # Intervalo de coleta (5 minutos para conservar bateria dos sensores IoT)
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização
    await init_db()
    await seed_admin_user()
    await seed_initial_devices_if_empty()
    # Inicia o coletor em background
    collector_task = asyncio.create_task(telemetry_collection_loop())
    yield
    # Finalização
    global background_collector_running
    background_collector_running = False
    collector_task.cancel()

app = FastAPI(
    title="ControlCold - Monitor de Freezers IoT",
    description="Sistema centralizado para monitoramento térmico em tempo real integrado a sensores Tuya/Ekaza com autenticação e prevenção de perdas",
    version="1.0.0",
    lifespan=lifespan
)

# CORS liberado para permitir conexões de qualquer app mobile ou rede interna
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas da API REST (Autenticação e Telemetria)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(integration_router)
app.include_router(report_router)
app.include_router(push_router, prefix="/api/push")

from src.security.auth import decode_auth_token

# Endpoint WebSocket para streaming de telemetria ao vivo
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket, token: str):
    payload = decode_auth_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
        
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008, reason="User ID missing")
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Mantém a conexão aberta escutando mensagens do cliente (ex: ping/pong)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception:
        ws_manager.disconnect(websocket, user_id)

# Servir Frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
