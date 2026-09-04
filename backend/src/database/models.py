import datetime
import hashlib
import hmac
import os
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from cryptography.fernet import Fernet

# Chave de criptografia simétrica para PIIs
ENCRYPTION_KEY = os.getenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

def get_blind_index(value: str) -> str:
    """Gera um hash determinístico (Blind Index) para permitir buscas exatas no banco."""
    if not value:
        return value
    return hmac.new(ENCRYPTION_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # email_hash armazena o Blind Index para buscas de login
    email = Column(String(120), unique=True, nullable=False, index=True)
    # email_encrypted armazena o dado real reversível
    email_encrypted = Column(Text, nullable=True)
    phone_encrypted = Column(Text, nullable=True)
    
    password_hash = Column(String(256), nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(6), nullable=True)
    code_expires_at = Column(DateTime, nullable=True)
    role = Column(String(20), default="operator")  # admin, operator
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def raw_email(self) -> str:
        if not self.email_encrypted:
            return ""
        return fernet.decrypt(self.email_encrypted.encode()).decode()

    @raw_email.setter
    def raw_email(self, value: str):
        if value:
            self.email = get_blind_index(value.lower().strip())
            self.email_encrypted = fernet.encrypt(value.lower().strip().encode()).decode()

    @property
    def phone(self) -> str:
        if not self.phone_encrypted:
            return ""
        return fernet.decrypt(self.phone_encrypted.encode()).decode()

    @phone.setter
    def phone(self, value: str):
        if value:
            self.phone_encrypted = fernet.encrypt(value.encode()).decode()
        else:
            self.phone_encrypted = None

    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "email_blind_index": self.email,  # Não expor o e-mail real no to_dict
            "is_verified": self.is_verified,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="push_subscriptions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(64), primary_key=True, index=True)  # Tuya Device ID ou Identificador Único
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) # Dono do dispositivo
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="congelados")  # congelados, resfriados, carnes, sorvetes
    location = Column(String(100), default="Setor Principal")
    temp_min = Column(Float, default=-22.0)
    temp_max = Column(Float, default=-15.0)
    current_temp = Column(Float, nullable=True)
    current_humidity = Column(Float, nullable=True)
    battery_level = Column(Integer, default=100)
    status = Column(String(20), default="NORMAL")  # NORMAL, ALERTA, CRITICO, OFFLINE
    temp_offset = Column(Float, default=0.0)
    calibration_cert = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    local_ip = Column(String(45), nullable=True)
    local_key = Column(String(64), nullable=True)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    telemetry = relationship("TelemetryLog", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    alarms = relationship("AlarmEvent", back_populates="device", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "category": self.category,
            "location": self.location,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "temp_offset": self.temp_offset,
            "calibration_cert": self.calibration_cert,
            "current_temp": self.current_temp,
            "current_humidity": self.current_humidity,
            "battery_level": self.battery_level,
            "status": self.status,
            "is_active": self.is_active,
            "local_ip": self.local_ip,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id"), index=True, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=True)
    battery = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    device = relationship("Device", back_populates="telemetry", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class AlarmEvent(Base):
    __tablename__ = "alarm_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id"), index=True, nullable=False)
    alarm_type = Column(String(30), nullable=False)  # TEMP_HIGH, TEMP_LOW, BATTERY_LOW, OFFLINE, RAPID_RISE
    severity = Column(String(20), default="WARNING")  # WARNING, CRITICAL
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, RESOLVED, ACKNOWLEDGED
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="alarms", lazy="selectin")

    def to_dict(self):
        # Trata com segurança caso o objeto device ainda não esteja carregado
        dev_name = self.device_id
        try:
            if self.device:
                dev_name = self.device.name
        except Exception:
            pass

        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_name": dev_name,
            "alarm_type": self.alarm_type,
            "severity": self.severity,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "status": self.status,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", backref="refresh_tokens")


class TuyaIntegration(Base):
    __tablename__ = "tuya_integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    tuya_uid = Column(String(100), nullable=False)
    access_token = Column(String(200), nullable=False)
    refresh_token = Column(String(200), nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", backref="tuya_integration")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=True)
    action_type = Column(String(50), nullable=False)  # Ex: ALARM_ACKNOWLEDGED, DEVICE_LIMITS_CHANGED
    reason = Column(String(255), nullable=True)       # Motivo digitado pelo usuário
    details = Column(Text, nullable=True)             # JSON string extra
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    device = relationship("Device")
