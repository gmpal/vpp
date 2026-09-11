"""Real-time device simulator: emits one reading per second per source.

When the source has valid lat/lon coordinates (non-zero), the simulator uses
real weather data from Open-Meteo to drive solar and wind generation.
Market prices from ENTSO-E are attached to every message when available.
Synthetic fallbacks are used whenever real data is unavailable.
"""
import asyncio
import json
import math
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np


def _get_bootstrap_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")


# Panel efficiency used to convert irradiance → power
# 18 % is a realistic value for modern monocrystalline panels
_PV_EFFICIENCY = 0.18

# Simple cubic wind power curve parameters
# Cut-in: 3 m/s, rated: 12 m/s, cut-out: 25 m/s
_WIND_CUT_IN = 3.0
_WIND_RATED = 12.0
_WIND_CUT_OUT = 25.0


def _wind_power_factor(wind_speed_ms: float) -> float:
    """Return a 0–1 capacity factor using a simplified cubic power curve."""
    if wind_speed_ms < _WIND_CUT_IN or wind_speed_ms >= _WIND_CUT_OUT:
        return 0.0
    if wind_speed_ms >= _WIND_RATED:
        return 1.0
    return ((wind_speed_ms - _WIND_CUT_IN) / (_WIND_RATED - _WIND_CUT_IN)) ** 3


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

        # Real-data providers — created lazily on first use
        self._weather: Optional[object] = None
        self._market: Optional[object] = None
        self._use_real_data = bool(latitude and longitude)

    def _init_providers(self) -> None:
        """Initialise provider objects (import deferred to keep startup fast)."""
        if self._weather is None and self._use_real_data:
            from backend.src.streaming.providers.weather import WeatherProvider
            from backend.src.streaming.providers.market_prices import MarketPriceProvider
            self._weather = WeatherProvider(self.latitude, self.longitude)
            self._market = MarketPriceProvider()

    def _make_producer(self):
        from kafka import KafkaProducer

        return KafkaProducer(
            bootstrap_servers=_get_bootstrap_servers(),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    async def run(self):
        self.running = True
        self._init_providers()
        self._producer = self._make_producer()
        try:
            while self.running:
                value, extra = await self._generate_reading()
                message = {
                    "device_id": self.source_id,
                    "device_type": self.source_type,
                    "community_id": self.community_id,
                    "source_id": self.source_id,
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **extra,
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

    async def _generate_reading(self) -> tuple[float, dict]:
        """Return (power_kw, extra_fields) for the current tick.

        extra_fields may contain real-world context (irradiance, wind_speed,
        market_price_eur_mwh) attached to the message for downstream consumers.
        """
        extra: dict = {}

        if self.source_type == "solar":
            value, extra = await self._solar()
        elif self.source_type == "wind":
            value, extra = await self._wind()
        elif self.source_type == "load":
            value = self._load()
        else:
            value = 0.0

        # Attach market price when available
        if self._market is not None:
            price = await self._market.get_current_price()
            if price is not None:
                extra["market_price_eur_mwh"] = price

        return value, extra

    async def _solar(self) -> tuple[float, dict]:
        """PV generation in kW.

        With real data: irradiance (W/m²) × panel area equivalent × efficiency.
        Synthetic fallback: cosine bell centred at solar noon.
        """
        if self._weather is not None:
            weather = await self._weather.get_current()
            irradiance = weather["irradiance_w_m2"]
            temp_c = weather["temperature_c"]

            # Derate for temperature: panels lose ~0.45 %/°C above 25 °C STC
            temp_derate = 1.0 - max(0.0, (temp_c - 25.0)) * 0.0045

            # capacity_kw / (1 kW/m² reference) × efficiency gives effective area;
            # here we normalise so that 1 000 W/m² at STC → capacity_kw output
            power = self.capacity_kw * (irradiance / 1000.0) * temp_derate
            noise = float(np.random.normal(0, 0.02 * self.capacity_kw))
            return max(0.0, power + noise), {
                "irradiance_w_m2": irradiance,
                "temperature_c": temp_c,
                "data_source": "open-meteo",
            }

        # Synthetic: cosine bell 06:00–18:00
        hour = (self.tick % 86400) / 3600
        cos_val = math.cos((hour - 12) / 6 * math.pi / 2)
        factor = max(0.0, cos_val) ** 2
        noise = float(np.random.normal(0, 0.05))
        return max(0.0, self.capacity_kw * factor + noise), {"data_source": "synthetic"}

    async def _wind(self) -> tuple[float, dict]:
        """Wind generation in kW using a cubic power curve.

        With real data: wind speed at 100 m from Open-Meteo → cubic power curve.
        Synthetic fallback: slow sinusoid with noise.
        """
        if self._weather is not None:
            weather = await self._weather.get_current()
            wind_speed = weather["wind_speed_ms"]
            # Add sub-hourly turbulence noise (σ ≈ 10 % of speed)
            noisy_speed = max(0.0, wind_speed + float(np.random.normal(0, 0.1 * wind_speed)))
            factor = _wind_power_factor(noisy_speed)
            return self.capacity_kw * factor, {
                "wind_speed_ms": wind_speed,
                "data_source": "open-meteo",
            }

        # Synthetic
        factor = max(0.0, math.sin(self.tick / 100) + float(np.random.normal(0, 0.3)))
        return max(0.0, self.capacity_kw * min(1.0, factor)), {"data_source": "synthetic"}

    def _load(self) -> float:
        """Household load in kW — synthetic profile (no real-time load data API)."""
        hour = (self.tick % 86400) / 3600
        peak = max(0.0, 1 - abs(hour - 19) / 4)
        baseline = 0.5 * self.capacity_kw
        return baseline + peak * 0.5 * self.capacity_kw
