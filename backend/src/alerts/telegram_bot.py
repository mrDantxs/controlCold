import os
import logging
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("coldchain.telegram")

class TelegramNotifier:
    """
    Despachador de notificações e alertas em tempo real via Telegram Bot API
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = (bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
        self.chat_id = (chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip()

    def is_configured(self) -> bool:
        if not self.bot_token or "seu_bot_token" in self.bot_token:
            return False
        return True

    def send_message(self, text: str, target_chat_id: Optional[str] = None) -> bool:
        """Envia mensagem formatada para o chat configurado ou destinatário específico"""
        if not self.is_configured():
            logger.debug("Telegram Bot não configurado ou com token de exemplo. Mensagem não enviada.")
            return False

        cid = target_chat_id or self.chat_id
        if not cid or "seu_chat_id" in cid:
            logger.warning("Telegram Bot Token existe, mas TELEGRAM_CHAT_ID não está preenchido.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": cid,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            result = resp.json()
            if result.get("ok"):
                logger.info(f"Notificação Telegram enviada com sucesso para chat {cid}")
                return True
            else:
                logger.error(f"Erro ao enviar Telegram: {result.get('description')}")
                return False
        except Exception as e:
            logger.error(f"Falha na requisição ao Telegram: {e}")
            return False

    def send_alarm(self, alarm_data: dict, target_chat_id: Optional[str] = None) -> bool:
        """Formata e envia um alerta de violação térmica ou equipamento"""
        sev_icon = "🚨 <b>[CRÍTICO]</b>" if alarm_data.get("severity") == "CRITICAL" else "⚠️ <b>[ALERTA]</b>"
        device_name = alarm_data.get("device_name", alarm_data.get("device_id", "Freezer"))
        message = alarm_data.get("message", "")
        value = alarm_data.get("value")
        threshold = alarm_data.get("threshold")
        
        text = (
            f"{sev_icon}\n"
            f"<b>Equipamento:</b> {device_name}\n"
            f"<b>Detalhes:</b> {message}\n"
            f"<b>Valor Atual:</b> <code>{value}</code> | <b>Limite:</b> <code>{threshold}</code>\n"
            f"<i>AntiGravity ColdChain - Monitoramento IoT</i>"
        )
        return self.send_message(text, target_chat_id)

    def send_resolution(self, device_name: str, alarm_type: str, current_temp: float, target_chat_id: Optional[str] = None) -> bool:
        """Notifica retorno à normalidade térmica"""
        text = (
            f"✅ <b>[RESOLVIDO] Temperatura Normalizada</b>\n"
            f"<b>Equipamento:</b> {device_name}\n"
            f"<b>Temperatura Atual:</b> <code>{current_temp}°C</code>\n"
            f"A temperatura retornou à faixa segura de operação."
        )
        return self.send_message(text, target_chat_id)
