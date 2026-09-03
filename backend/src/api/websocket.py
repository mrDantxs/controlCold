import json
import logging
from typing import List, Dict
from fastapi import WebSocket

logger = logging.getLogger("coldchain.ws")

class ConnectionManager:
    """
    Gerenciador de conexões WebSocket para atualização em tempo real
    isolado por usuário (Multi-Tenant).
    """

    def __init__(self):
        # Mapeia user_id -> lista de WebSockets ativos desse usuário
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"Cliente WS conectado (User {user_id}). Total do user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                logger.info(f"Cliente WS desconectado (User {user_id}). Restantes: {len(self.active_connections[user_id])}")
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: int, message_type: str, data: dict):
        """Envia mensagem JSON apenas para os clientes conectados do usuário específico"""
        if user_id not in self.active_connections or not self.active_connections[user_id]:
            return

        payload = json.dumps({"type": message_type, "data": data})
        stale_connections = []

        for conn in self.active_connections[user_id]:
            try:
                await conn.send_text(payload)
            except Exception:
                stale_connections.append(conn)

        for stale in stale_connections:
            if stale in self.active_connections.get(user_id, []):
                self.active_connections[user_id].remove(stale)

ws_manager = ConnectionManager()
