"""Real-time device simulator: emits one reading per second per source."""
import asyncio
import json
import math
import os
from datetime import datetime, timezone

import numpy as np


def _get_bootstrap_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")


class DeviceSimulator:
    """Simulates an IoT device (inverter, smart meter) emitting readings every second."""

    TOPIC = "device_readings"

    def __init__(
        self,
        source_id: str,
        source_type: str,
        community_id: str,
        latitude: float,
        longitude: float,
        capacity_kw: float = 10.0,
    ):
        self.source_id = source_id
        self.source_type = source_type  # "solar", "wind", "load"
        self.community_id = community_id
        self.latitude = latitude
        self.longitude = longitude
        self.capacity_kw = capacity_kw
        self._producer = None
        self.running = False
        self.tick = 0  # increments every second

    def _make_producer(self):
        from kafka import KafkaProducer

        return KafkaProducer(
            bootstrap_servers=_get_bootstrap_servers(),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    async def run(self):
        self.running = True
        self._producer = self._make_producer()
        try:
            while self.running:
                value = self._generate_reading()
                message = {
                    "device_id": self.source_id,
                    "device_type": self.source_type,
                    "community_id": self.community_id,
                    "source_id": self.source_id,
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._producer.send(self.TOPIC, value=message)
                self.tick += 1
                await asyncio.sleep(1)
        finally:
            if self._producer:
                self._producer.close()
                self._producer = None

    def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    # Generation helpers
    # ------------------------------------------------------------------

    def _generate_reading(self) -> float:
        if self.source_type == "solar":
            return self._solar()
        if self.source_type == "wind":
            return self._wind()
        if self.source_type == "load":
            return self._load()
        return 0.0

    def _solar(self) -> float:
        hour = (self.tick % 86400) / 3600  # 0–24
        # Clip cosine before squaring so nighttime hours (outside 6–18) → 0
        cos_val = math.cos((hour - 12) / 6 * math.pi / 2)
        factor = max(0.0, cos_val) ** 2
        noise = float(np.random.normal(0, 0.05))
        return max(0.0, self.capacity_kw * factor + noise)

    def _wind(self) -> float:
        factor = max(0.0, math.sin(self.tick / 100) + float(np.random.normal(0, 0.3)))
        return max(0.0, self.capacity_kw * min(1.0, factor))

    def _load(self) -> float:
        hour = (self.tick % 86400) / 3600
        # Evening peak 17–21 h
        peak = max(0.0, 1 - abs(hour - 19) / 4)
        baseline = 0.5 * self.capacity_kw
        return baseline + peak * 0.5 * self.capacity_kw
