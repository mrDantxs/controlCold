import time
import logging
import math
from collections import deque
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("coldchain.rules")

class RulesEngine:
    """
    Motor de regras de negócio térmicas com Inteligência Preditiva para prevenção de perdas.
    """

    def __init__(self):
        # Armazena estado dos alarmes ativos em memória para evitar floods: {device_id: {alarm_type: active_alarm_data}}
        self.active_alarms: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Histórico de timestamps das violações para tolerância de degelo (histerese no tempo)
        self.breach_tracker: Dict[str, float] = {}
        
        # Histórico de leituras para aprendizado de linha de base (IA/Machine Learning leve)
        # Mantém as últimas 60 leituras (~5 horas considerando ingestão a cada 5 mins)
        self.temp_history: Dict[str, deque] = {}
        
        # Configurações do Motor Preditivo
        self.DEFROST_TOLERANCE_SECONDS = 20 * 60  # 20 minutos de tolerância para degelo/porta aberta

    def _calculate_baseline(self, history: deque) -> Tuple[float, float]:
        """Calcula a Média e o Desvio Padrão do histórico de temperaturas (Linha de base)."""
        if not history:
            return 0.0, 0.0
        
        mean = sum(history) / len(history)
        if len(history) < 2:
            return mean, 0.0
            
        variance = sum((x - mean) ** 2 for x in history) / (len(history) - 1)
        std_dev = math.sqrt(variance)
        return mean, std_dev

    def _calculate_trend(self, history: deque) -> float:
        """Calcula a taxa de variação (slope) das últimas leituras."""
        if len(history) < 3:
            return 0.0
        
        # Pega as últimas 3 leituras para ver a tendência curtíssima
        recent = list(history)[-3:]
        slope = (recent[-1] - recent[0]) / len(recent)
        return slope

    def evaluate(
        self,
        device_id: str,
        device_name: str,
        temp: float,
        temp_min: float,
        temp_max: float,
        battery: Optional[int] = None,
        humidity: Optional[float] = None
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """
        Avalia os dados telemétricos utilizando inteligência preditiva e retorna:
        (status_do_dispositivo, lista_de_novos_alarmes_para_disparo, lista_de_tipos_de_alarme_resolvidos)
        """
        now = time.time()
        new_alarms = []
        resolved_alarms = []
        status = "NORMAL"

        if device_id not in self.active_alarms:
            self.active_alarms[device_id] = {}
            
        if device_id not in self.temp_history:
            self.temp_history[device_id] = deque(maxlen=60)
            
        # 0. Atualiza Memória e Calcula Padrões
        history = self.temp_history[device_id]
        history.append(temp)
        
        baseline_mean, baseline_std = self.calculate_baseline(history)
        trend = self.calculate_trend(history)
        
        # Anomaly Detection (Z-Score > 2.5 indica desvio forte do padrão normal)
        is_anomaly = False
        if baseline_std > 0 and len(history) >= 5:
            z_score = abs(temp - baseline_mean) / baseline_std
            if z_score > 2.5:
                is_anomaly = True

        # 1. Verificação de Limite Superior com Tolerância (Prevenção de Falsos Positivos)
        if temp > temp_max:
            if device_id not in self.breach_tracker:
                self.breach_tracker[device_id] = now
            
            time_in_breach = now - self.breach_tracker[device_id]
            
            # Se a violação dura mais que a tolerância (ex: 20 min), é CRÍTICO (Falha de Compressor/Porta esquecida)
            if time_in_breach > self.DEFROST_TOLERANCE_SECONDS:
                status = "CRITICO"
                alarm_type = "TEMP_HIGH_CRITICAL"
                severity = "CRITICAL"
                msg = f"🚨 FALHA CRÍTICA em {device_name}! Temperatura acima de {temp_max}°C por mais de 20 minutos. Ação imediata necessária (Medido: {temp}°C)."
            else:
                # Dentro da janela de tolerância. É um degelo ou porta aberta rápida.
                status = "ALERTA"
                alarm_type = "TEMP_HIGH_WARNING"
                severity = "WARNING"
                msg = f"⚠️ Pico de temperatura em {device_name} (Medido: {temp}°C). Monitorando ciclo de degelo/porta..."

            # Limpa o alarme Warning se for evoluir para Critical
            if alarm_type == "TEMP_HIGH_CRITICAL" and "TEMP_HIGH_WARNING" in self.active_alarms[device_id]:
                del self.active_alarms[device_id]["TEMP_HIGH_WARNING"]
                resolved_alarms.append("TEMP_HIGH_WARNING")

            if alarm_type not in self.active_alarms[device_id]:
                alarm_data = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "alarm_type": alarm_type,
                    "severity": severity,
                    "value": temp,
                    "threshold": temp_max,
                    "message": msg,
                    "triggered_at": now
                }
                self.active_alarms[device_id][alarm_type] = alarm_data
                new_alarms.append(alarm_data)
        else:
            # Temperatura estabilizou abaixo do máximo, resolve todos os alarmes de alta
            if "TEMP_HIGH_WARNING" in self.active_alarms[device_id]:
                del self.active_alarms[device_id]["TEMP_HIGH_WARNING"]
                resolved_alarms.append("TEMP_HIGH_WARNING")
            if "TEMP_HIGH_CRITICAL" in self.active_alarms[device_id]:
                del self.active_alarms[device_id]["TEMP_HIGH_CRITICAL"]
                resolved_alarms.append("TEMP_HIGH_CRITICAL")
                
            if device_id in self.breach_tracker:
                del self.breach_tracker[device_id]
                
            # Disparo Preditivo: Temperatura normal, mas a tendência é de alta rápida e já é uma anomalia
            if status == "NORMAL" and is_anomaly and trend > 0.3:
                status = "ALERTA"
                alarm_type = "ANOMALY_TREND_UP"
                if alarm_type not in self.active_alarms[device_id]:
                    alarm_data = {
                        "device_id": device_id,
                        "device_name": device_name,
                        "alarm_type": alarm_type,
                        "severity": "WARNING",
                        "value": temp,
                        "threshold": temp_max,
                        "message": f"🤖 IA Preditiva: Padrão anormal detectado em {device_name}. A temperatura está subindo rápido e deve romper o limite em breve.",
                        "triggered_at": now
                    }
                    self.active_alarms[device_id][alarm_type] = alarm_data
                    new_alarms.append(alarm_data)
            else:
                if "ANOMALY_TREND_UP" in self.active_alarms[device_id]:
                    del self.active_alarms[device_id]["ANOMALY_TREND_UP"]
                    resolved_alarms.append("ANOMALY_TREND_UP")

        # 2. Verificação de Limite Inferior (Subresfriamento)
        if temp < temp_min:
            if status != "CRITICO":
                status = "ALERTA"

            alarm_type = "TEMP_LOW"
            if alarm_type not in self.active_alarms[device_id]:
                diff = round(temp_min - temp, 1)
                alarm_data = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "alarm_type": alarm_type,
                    "severity": "WARNING",
                    "value": temp,
                    "threshold": temp_min,
                    "message": f"❄️ Subresfriamento em {device_name}! (Medido: {temp}°C, -{diff}°C abaixo).",
                    "triggered_at": now
                }
                self.active_alarms[device_id][alarm_type] = alarm_data
                new_alarms.append(alarm_data)
        else:
            if "TEMP_LOW" in self.active_alarms[device_id]:
                del self.active_alarms[device_id]["TEMP_LOW"]
                resolved_alarms.append("TEMP_LOW")

        # 3. Alerta de Bateria Fraca (< 20%)
        if battery is not None and battery <= 20:
            if status != "CRITICO":
                status = "CRITICO"
            alarm_type = "BATTERY_LOW"
            if alarm_type not in self.active_alarms[device_id]:
                alarm_data = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "alarm_type": alarm_type,
                    "severity": "CRITICAL",
                    "value": float(battery),
                    "threshold": 20.0,
                    "message": f"🚨 Bateria Crítica no sensor {device_name}: {battery}% restante! Risco iminente de desligamento. Troque as pilhas imediatamente.",
                    "triggered_at": now
                }
                self.active_alarms[device_id][alarm_type] = alarm_data
                new_alarms.append(alarm_data)
        elif battery is not None and battery > 20:
            if "BATTERY_LOW" in self.active_alarms[device_id]:
                del self.active_alarms[device_id]["BATTERY_LOW"]
                resolved_alarms.append("BATTERY_LOW")

        return status, new_alarms, resolved_alarms
