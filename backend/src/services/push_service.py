import os
import json
import logging
from pywebpush import webpush, WebPushException

logger = logging.getLogger("coldchain.push")

def send_push_notification(subscription_info: dict, payload: dict):
    """
    Envia uma notificação Web Push usando pywebpush.
    O VAPID_PRIVATE_KEY deve estar configurado no servidor.
    """
    vapid_private_key = os.getenv("VAPID_PRIVATE_KEY", "")
    vapid_claims = {
        "sub": "mailto:admin@controlcold.com"
    }

    if not vapid_private_key:
        logger.warning("VAPID_PRIVATE_KEY não configurada. Push nativo desabilitado.")
        return False

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims
        )
        return True
    except WebPushException as ex:
        logger.error(f"Erro ao enviar Push: {repr(ex)}")
        # Se for um erro 410 Gone, a assinatura deve ser removida do DB
        if ex.response and ex.response.status_code == 410:
            return "EXPIRED"
        return False
