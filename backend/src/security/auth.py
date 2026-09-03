import os
import secrets
import hashlib
import hmac
import json
import base64
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logger = logging.getLogger("controlcold.security")

# Chave secreta para assinatura dos tokens de autenticação
SECRET_KEY = os.getenv("APP_SECRET_KEY", "controlcold-super-secure-key-2026-iot-coldchain")

def hash_password(password: str) -> str:
    """Gera hash PBKDF2-HMAC-SHA256 com salt aleatório"""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Valida a senha contra o hash armazenado"""
    try:
        salt_hex, key_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(expected_key, key)
    except Exception:
        return False

def generate_verification_code() -> str:
    """Gera código numérico de 6 dígitos para verificação de email/SMS"""
    return f"{secrets.randbelow(900000) + 100000}"

def create_auth_token(user_id: int, email: str, role: str, expires_in_seconds: int = 900) -> str:
    """Gera token assinado com payload do usuário (válido por 15 minutos)"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time())
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{header_b64}.{payload_b64}.{signature}"

def decode_auth_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida assinatura e expiração do token"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature = parts
        
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature):
            return None
            
        # Adiciona padding base64 se necessário
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
            
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception as e:
        logger.warning(f"Falha na validação de token: {e}")
        return None

def generate_refresh_token_string() -> str:
    """Gera uma string segura e única de 64 caracteres hex para usar como refresh token."""
    return secrets.token_hex(32)

def send_email_verification(to_email: str, code: str, purpose: str = "verificação") -> Tuple[bool, str]:
    """
    Envia código de 6 dígitos via SMTP (Gmail, Google Workspace, Outlook, etc.).
    Mantém o código estritamente confidencial.
    """
    # Recarrega o .env dinamicamente caso o usuário tenha acabado de salvar credenciais
    load_dotenv(find_dotenv(), override=True)

    subject = f"❄️ ControlCold - Código de {purpose.capitalize()}"

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    # Remove espaços comuns em senhas de app do Google (ex: "abcd efgh ijkl mnop" -> "abcdefghijklmnop")
    smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
    from_addr = os.getenv("SMTP_FROM", smtp_user or "nao-responda@controlcold.io").strip()

    if not smtp_user or not smtp_pass or "seu_email" in smtp_user or "senha_de_app" in smtp_pass:
        error_msg = (
            "Servidor de e-mail não configurado no arquivo .env!\n"
            "Preencha SMTP_USER com seu e-mail do Gmail e SMTP_PASSWORD com sua Senha de App de 16 caracteres gerada no Google."
        )
        logger.warning(error_msg)
        return False, error_msg

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 20px; font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b1120; color: #f8fafc;">
            <div style="max-width: 520px; margin: 0 auto; background-color: #131d31; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <span style="font-size: 42px;">❄️</span>
                    <h1 style="color: #38bdf8; font-size: 26px; margin: 8px 0 4px 0; font-weight: 800; letter-spacing: -0.5px;">ControlCold <span style="font-size: 14px; background: rgba(56,189,248,0.2); padding: 2px 8px; border-radius: 6px;">IoT</span></h1>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0;">Monitoramento de Freezers e Prevenção de Perdas</p>
                </div>
                
                <div style="background-color: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; text-align: center;">
                    <p style="font-size: 15px; color: #cbd5e1; margin-top: 0;">Seu código de segurança para <b>{purpose}</b> é:</p>
                    <div style="font-size: 38px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; font-family: monospace; padding: 12px; background: #0b1120; border: 1px dashed #38bdf8; border-radius: 8px; margin: 16px 0;">
                        {code}
                    </div>
                    <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">⏱️ Válido por 15 minutos. Não compartilhe com ninguém.</p>
                </div>

                <p style="font-size: 12px; color: #64748b; text-align: center; line-height: 1.5; margin: 0;">
                    Se você não solicitou este código no ControlCold, desconsidere esta mensagem com segurança.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_email], msg.as_string())

        logger.info(f"✅ E-mail com código enviado com sucesso para {to_email}")
        return True, "E-mail enviado com sucesso."
    except smtplib.SMTPAuthenticationError as auth_err:
        err = f"Falha de autenticação no servidor de e-mail: {auth_err}"
        logger.error(err)
        return False, "Usuário ou senha de app do e-mail incorretos."
    except Exception as e:
        err = f"Erro no envio de e-mail via SMTP ({e})"
        logger.error(err)
        return False, f"Falha ao enviar e-mail: {str(e)}"
