import random
import math
import time
from typing import Dict, Any, List

class TelemetrySimulator:
    """
    Simulador realista de telemetria para câmaras frias e freezers industriais/comerciais.
    Simula ciclos termodinâmicos (compressor ligando e desligando), oscilações suaves,
    umidade relativa e consumo gradual de bateria.
    """

    DEFAULT_SIMULATED_DEVICES = [
        {
            "id": "FRZ-01-SORVETES",
            "name": "Freezer 01 - Sorvetes Artesanais",
            "category": "congelados",
            "location": "Câmara Fria A - Corredor 1",
            "temp_min": -24.0,
            "temp_max": -16.0,
            "target_temp": -20.0,
            "target_humidity": 65.0,
            "battery_level": 94,
        },
        {
            "id": "FRZ-02-CARNES",
            "name": "Freezer 02 - Carnes e Peixes Nobres",
            "category": "carnes",
            "location": "Câmara Fria A - Corredor 2",
            "temp_min": -22.0,
            "temp_max": -15.0,
            "target_temp": -18.5,
            "target_humidity": 70.0,
            "battery_level": 88,
        },
        {
            "id": "FRZ-03-LATICINIOS",
            "name": "Freezer 03 - Laticínios e Frios",
            "category": "resfriados",
            "location": "Expositor Salão Principal",
            "temp_min": 1.0,
            "temp_max": 6.0,
            "target_temp": 3.8,
            "target_humidity": 78.0,
            "battery_level": 99,
        },
        {
            "id": "FRZ-04-VACINAS",
            "name": "Câmara 04 - Termolábeis e Vacinas",
            "category": "vacinas",
            "location": "Ambulatório / Controle",
            "temp_min": 2.0,
            "temp_max": 8.0,
            "target_temp": 4.5,
            "target_humidity": 55.0,
            "battery_level": 91,
        }
    ]

    def __init__(self):
        self.cycle_time = 0.0
        # Permite disparar anomalia para demonstração e testes do usuário
        self.injected_anomalies: Dict[str, str] = {}

    def trigger_anomaly(self, device_id: str, anomaly_type: str = "DOOR_OPEN"):
        """Permite forçar um evento de anomalia (ex: porta aberta ou degelo) para testar alarmes"""
        self.injected_anomalies[device_id] = anomaly_type

    def clear_anomaly(self, device_id: str):
        if device_id in self.injected_anomalies:
            del self.injected_anomalies[device_id]

    def generate_reading(self, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """Gera uma leitura de telemetria coerente com o histórico e física do equipamento"""
        self.cycle_time += 0.05
        dev_id = device_config["id"]
        target = device_config.get("target_temp", -18.0)
        
        # Simula ciclo de histerese do compressor (onda senoidal com ruído suave)
        oscillation = math.sin(self.cycle_time + hash(dev_id) % 10) * 1.6
        jitter = (random.random() - 0.5) * 0.4
        current_temp = target + oscillation + jitter

        # Se houver anomalia injetada para teste (porta aberta)
        anomaly = self.injected_anomalies.get(dev_id)
        if anomaly == "DOOR_OPEN":
            # Temperatura sobe consideravelmente acima do limite máximo
            current_temp = device_config.get("temp_max", -15.0) + random.uniform(2.5, 6.0)

        current_humidity = device_config.get("target_humidity", 65.0) + (random.random() - 0.5) * 4.0
        battery = max(10, device_config.get("battery_level", 90))

        return {
            "device_id": dev_id,
            "temperature": round(current_temp, 1),
            "humidity": round(max(10.0, min(100.0, current_humidity)), 1),
            "battery": battery,
            "timestamp": time.time(),
            "simulated": True
        }
