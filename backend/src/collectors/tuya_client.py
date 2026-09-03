import os
import time
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("coldchain.tuya")

class TuyaClient:
    """
    Cliente para integração com a plataforma Tuya / Ekaza via Tuya Cloud OpenAPI v2.0
    e suporte a conexão local com TinyTuya.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_id: Optional[str] = None,
        access_secret: Optional[str] = None
    ):
        self.endpoint = (endpoint or os.getenv("TUYA_ENDPOINT", "https://openapi.tuyaus.com")).strip().rstrip("/")
        # Trata caso a URL venha encapsulada em markdown ou com espaços
        if "[" in self.endpoint:
            import re
            m = re.search(r"https?://[^\s\]]+", self.endpoint)
            if m:
                self.endpoint = m.group(0)

        self.access_id = (access_id or os.getenv("TUYA_ACCESS_ID", "")).strip()
        self.access_secret = (access_secret or os.getenv("TUYA_ACCESS_SECRET", "")).strip()
        self.token: Optional[str] = None
        self.token_expire_time: float = 0

    def is_configured(self) -> bool:
        """Verifica se as credenciais reais foram informadas e não são placeholders"""
        if not self.access_id or not self.access_secret:
            return False
        if "seu_access_id" in self.access_id or "seu_access_secret" in self.access_secret:
            return False
        return True

    def _calc_sign(self, msg: str, secret: str) -> str:
        """Calcula a assinatura HMAC-SHA256 exigida pela Tuya Cloud"""
        return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    def get_token(self) -> Optional[str]:
        """Obtém ou renova o access_token na Tuya Cloud API"""
        if not self.is_configured():
            return None

        now = time.time()
        if self.token and now < (self.token_expire_time - 60):
            return self.token

        t = str(int(now * 1000))
        # Para obtenção de token: sign = HMAC-SHA256(client_id + t, secret)
        sign_str = self.access_id + t
        sign = self._calc_sign(sign_str, self.access_secret)

        url = f"{self.endpoint}/v1.0/token?grant_type=1"
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            if data.get("success"):
                result = data.get("result", {})
                self.token = result.get("access_token")
                expires_in = result.get("expire_time", 7200)
                self.token_expire_time = now + expires_in
                logger.info("Tuya access token obtido com sucesso.")
                return self.token
            else:
                logger.error(f"Erro ao obter Tuya token: {data.get('msg')} (code: {data.get('code')})")
                return None
        except Exception as e:
            logger.error(f"Falha na requisição de token Tuya: {e}")
            return None

    def get_user_token_from_ticket(self, ticket: str) -> Optional[Dict[str, Any]]:
        """Troca o Ticket OAuth2 pelo Token de Usuário (App-to-App)"""
        if not self.is_configured():
            return None
        t = str(int(time.time() * 1000))
        sign_str = self.access_id + t
        sign = self._calc_sign(sign_str, self.access_secret)
        
        url = f"{self.endpoint}/v1.0/token?code={ticket}&grant_type=2"
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            if data.get("success"):
                return data.get("result")
            else:
                logger.error(f"Erro ao trocar ticket Tuya: {data}")
                return None
        except Exception as e:
            logger.error(f"Falha na troca de ticket Tuya: {e}")
            return None

    def get_user_devices(self, uid: str, user_token: str) -> List[Dict[str, Any]]:
        """Busca a lista de dispositivos pareados na conta do usuário (Ekaza)"""
        path = f"/v1.0/users/{uid}/devices"
        res = self.request("GET", path, user_token=user_token)
        if res and res.get("success"):
            return res.get("result", [])
        return []

    def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None, user_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Realiza uma chamada autenticada à Tuya Cloud API"""
        token = user_token or self.get_token()
        if not token:
            return None

        now = str(int(time.time() * 1000))
        # Hash do payload
        content_hash = hashlib.sha256((json.dumps(body) if body else "").encode("utf-8")).hexdigest()
        
        # String para assinar na API v1.0 / v2.0
        string_to_sign = f"{method.upper()}\n{content_hash}\n\n{path}"
        sign_str = self.access_id + token + now + string_to_sign
        sign = self._calc_sign(sign_str, self.access_secret)

        headers = {
            "client_id": self.access_id,
            "access_token": token,
            "sign": sign,
            "t": now,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json"
        }

        url = f"{self.endpoint}{path}"
        try:
            resp = requests.request(method, url, headers=headers, params=params, json=body, timeout=12)
            return resp.json()
        except Exception as e:
            logger.error(f"Erro na requisição Tuya ({path}): {e}")
            return None

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Consulta o status em tempo real de um dispositivo via Tuya Cloud"""
        path = f"/v1.0/devices/{device_id}/status"
        res = self.request("GET", path)
        if res and res.get("success"):
            return self.parse_status_properties(res.get("result", []))
        return None

    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações cadastrais do dispositivo (nome, online/offline, categoria)"""
        path = f"/v1.0/devices/{device_id}"
        res = self.request("GET", path)
        if res and res.get("success"):
            return res.get("result")
        return None

    def parse_status_properties(self, status_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Interpreta a lista de Data Points (DPS) retornados pelo sensor Tuya/Ekaza
        e normaliza para temperatura (°C), umidade (%) e bateria (%).
        """
        data = {
            "temperature": None,
            "humidity": None,
            "battery": None,
            "raw_dps": {}
        }

        for item in status_list:
            code = item.get("code", "")
            val = item.get("value")
            data["raw_dps"][code] = val

            # Mapeamento de Temperatura (Ekaza/Tuya: va_temperature, temp_current, temp_indoor)
            if code in ["va_temperature", "temp_current", "temperature", "temp_indoor"]:
                try:
                    num_val = float(val)
                    # Sensores Tuya geralmente reportam com fator x10 ou x100
                    if abs(num_val) > 100:
                        num_val = num_val / 10.0
                        if abs(num_val) > 100:  # Se ainda for maior que 100, veio em x100
                            num_val = num_val / 10.0
                    data["temperature"] = round(num_val, 1)
                except (ValueError, TypeError):
                    pass

            # Mapeamento de Umidade (Ekaza/Tuya: va_humidity, humidity_value, humidity)
            elif code in ["va_humidity", "humidity_value", "humidity"]:
                try:
                    num_val = float(val)
                    if num_val > 100:
                        num_val = num_val / 10.0
                    data["humidity"] = round(num_val, 1)
                except (ValueError, TypeError):
                    pass

            # Mapeamento de Nível de Bateria
            elif code in ["battery_percentage", "battery_value", "battery", "battery_state"]:
                if isinstance(val, (int, float)):
                    data["battery"] = int(val)
                elif isinstance(val, str):
                    mapping = {"high": 100, "middle": 60, "low": 20}
                    data["battery"] = mapping.get(val.lower(), 50)

        return data

    def read_device_local(self, device_id: str, ip: str, local_key: str, version: float = 3.3) -> Optional[Dict[str, Any]]:
        """
        Leitura de telemetria diretamente via rede local (LAN) usando TinyTuya
        Sem dependência de internet ou Tuya Cloud!
        """
        try:
            import tinytuya
            d = tinytuya.OutletDevice(device_id, ip, local_key)
            d.set_version(version)
            d.set_socketTimeout(3)
            status = d.status()
            if status and "dps" in status:
                dps = status["dps"]
                # Formata dps para o interpretador
                prop_list = [{"code": k, "value": v} for k, v in dps.items()]
                parsed = self.parse_status_properties(prop_list)
                return parsed
        except Exception as e:
            logger.warning(f"Leitura TinyTuya local falhou para {device_id} ({ip}): {e}")
        return None
