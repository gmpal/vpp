"""Weather API routes — backed by Open-Meteo (free, no API key required).

Falls back to a synthetic response when the upstream call fails so that the
frontend always receives a valid payload.
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"


@router.get("/weather/current")
async def current_weather(lat: float, lon: float):
    """Return current-hour weather for the given coordinates."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                OPEN_METEO_FORECAST,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "hourly": "shortwave_radiation,temperature_2m,cloudcover",
                    "forecast_days": 1,
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Open-Meteo error: {exc.response.text}") from exc
    except Exception as exc:
        logger.warning("Open-Meteo current weather failed: %s — returning synthetic", exc)
        return _synthetic_current()

    data = resp.json()
    cw = data.get("current_weather", {})

    # Match the current hour's irradiance from hourly data
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    irradiances = hourly.get("shortwave_radiation", [])
    cloudcovers = hourly.get("cloudcover", [])
    temps = hourly.get("temperature_2m", [])

    irradiance = 0.0
    cloudcover = cw.get("cloudcover", 0)
    temperature = cw.get("temperature", 15.0)

    if times:
        # current_weather.time is in local time; just take the first hourly bucket
        irradiance = float(irradiances[0]) if irradiances else 0.0
        cloudcover = int(cloudcovers[0]) if cloudcovers else cloudcover
        temperature = float(temps[0]) if temps else temperature

    return {
        "temperature": temperature,
        "clouds": cloudcover,
        "windspeed_kmh": cw.get("windspeed", 0.0),
        "winddirection_deg": cw.get("winddirection", 0),
        "irradiance_w_m2": irradiance,
        "description": "Open-Meteo",
        "is_day": bool(cw.get("is_day", 1)),
        "source": "open-meteo",
    }


@router.get("/weather/forecast")
async def weather_forecast(lat: float, lon: float):
    """Return 24-hour hourly forecast for the given coordinates."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                OPEN_METEO_FORECAST,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "shortwave_radiation,windspeed_10m,windspeed_100m,temperature_2m,cloudcover",
                    "forecast_days": 2,
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Open-Meteo error: {exc.response.text}") from exc
    except Exception as exc:
        logger.warning("Open-Meteo forecast failed: %s — returning empty", exc)
        return {"forecasts": [], "source": "error", "note": str(exc)}

    data = resp.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    irradiances = hourly.get("shortwave_radiation", [])
    wind_10 = hourly.get("windspeed_10m", [])
    wind_100 = hourly.get("windspeed_100m") or wind_10
    temps = hourly.get("temperature_2m", [])
    clouds = hourly.get("cloudcover", [])

    forecasts = [
        {
            "time": times[i],
            "irradiance_w_m2": float(irradiances[i]) if i < len(irradiances) else 0.0,
            "windspeed_10m_ms": float(wind_10[i]) if i < len(wind_10) else 0.0,
            "windspeed_100m_ms": float(wind_100[i]) if i < len(wind_100) else 0.0,
            "temperature_c": float(temps[i]) if i < len(temps) else 15.0,
            "cloudcover_pct": int(clouds[i]) if i < len(clouds) else 0,
        }
        for i in range(min(48, len(times)))
    ]

    return {"forecasts": forecasts, "source": "open-meteo"}


def _synthetic_current() -> dict:
    return {
        "temperature": 15.0,
        "clouds": 30,
        "windspeed_kmh": 10.0,
        "winddirection_deg": 180,
        "irradiance_w_m2": 0.0,
        "description": "synthetic (Open-Meteo unavailable)",
        "is_day": True,
        "source": "synthetic",
    }
