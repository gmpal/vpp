from pydantic import BaseModel
from typing import List, Dict, Any


class DataPoint(BaseModel):
    timestamp: str
    value: float


class DeviceCounts(BaseModel):
    solar: int
    wind: int


class Source(BaseModel):
    source_type: str
    source_id: str


class BatteryStatus(BaseModel):
    battery_id: str
    capacity_kWh: float
    soc_kWh: float
    max_charge_kW: float
    max_discharge_kW: float
    eta: float


class BatteryOperation(BaseModel):
    power_kW: float
    duration_h: float = 1.0  # default duration


class BatteryAddRequest(BaseModel):
    capacity_kWh: float
    current_soc_kWh: float
    max_charge_kW: float
    max_discharge_kW: float
    eta: float
