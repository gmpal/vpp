import os

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

OWM_BASE = "https://api.openweathermap.org/data/2.5"


def _get_api_key():
    key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    return key


@router.get("/weather/current")
async def current_weather(lat: float, lon: float):
    api_key = _get_api_key()
    if not api_key:
        # Return synthetic fallback
        return {
            "temperature": 15.0,
            "clouds": 30,
            "description": "synthetic (no API key)",
            "sunrise": None,
            "sunset": None,
        }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/weather",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Weather API error: {resp.text}")
    d = resp.json()
    return {
        "temperature": d["main"]["temp"],
        "clouds": d["clouds"]["all"],
        "description": d["weather"][0]["description"],
        "sunrise": d["sys"].get("sunrise"),
        "sunset": d["sys"].get("sunset"),
    }


@router.get("/weather/forecast")
async def weather_forecast(lat: float, lon: float):
    api_key = _get_api_key()
    if not api_key:
        return {"forecasts": [], "note": "No API key configured"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/forecast",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=5.0,
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Weather API error: {resp.text}")
    d = resp.json()
    forecasts = [
        {
            "time": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "clouds": item["clouds"]["all"],
            "description": item["weather"][0]["description"],
        }
        for item in d.get("list", [])[:8]  # next 24h (3-hour intervals)
    ]
    return {"forecasts": forecasts}
