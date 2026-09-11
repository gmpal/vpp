"""Open-Meteo weather provider — free, no API key required.

Fetches hourly forecasts for a given location and caches them in memory.
The cache is refreshed at most once per hour to avoid hammering the API.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherProvider:
    """Hourly weather data from Open-Meteo for a fixed lat/lon.

    Usage::

        provider = WeatherProvider(50.85, 4.35)
        data = await provider.get_current()
        # {"irradiance_w_m2": 450.0, "wind_speed_ms": 6.2, "temperature_c": 14.0}
    """

    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        # hour_key (e.g. "2025-04-16T14:00") -> dict
        self._cache: dict[str, dict] = {}
        self._last_fetch_hour: Optional[str] = None

    async def get_current(self) -> dict:
        """Return weather data for the current UTC hour.

        Returns a dict with keys:
            irradiance_w_m2  – shortwave radiation (W/m²), 0 at night
            wind_speed_ms    – wind speed at 100 m height (m/s)
            temperature_c    – air temperature at 2 m (°C)
        Falls back to zeros on any network error.
        """
        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y-%m-%dT%H:00")

        if hour_key not in self._cache:
            await self._refresh()

        return self._cache.get(
            hour_key,
            {"irradiance_w_m2": 0.0, "wind_speed_ms": 0.0, "temperature_c": 15.0},
        )

    async def _refresh(self) -> None:
        """Fetch a 2-day hourly forecast and populate the cache."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    OPEN_METEO_URL,
                    params={
                        "latitude": self.latitude,
                        "longitude": self.longitude,
                        "hourly": "shortwave_radiation,windspeed_10m,windspeed_100m,temperature_2m",
                        "forecast_days": 2,
                        "timezone": "UTC",
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("Open-Meteo fetch failed: %s — using synthetic fallback", exc)
            return

        data = resp.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        irradiances = hourly.get("shortwave_radiation", [])
        wind_100 = hourly.get("windspeed_100m") or hourly.get("windspeed_10m", [])
        temps = hourly.get("temperature_2m", [])

        for i, time_str in enumerate(times):
            self._cache[time_str] = {
                "irradiance_w_m2": float(irradiances[i] or 0.0) if i < len(irradiances) else 0.0,
                "wind_speed_ms": float(wind_100[i] or 0.0) if i < len(wind_100) else 0.0,
                "temperature_c": float(temps[i] or 15.0) if i < len(temps) else 15.0,
            }

        now_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        self._last_fetch_hour = now_key
        logger.info(
            "Open-Meteo cache refreshed for (%.2f, %.2f) — %d hours loaded",
            self.latitude,
            self.longitude,
            len(times),
        )
