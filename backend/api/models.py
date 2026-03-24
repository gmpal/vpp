from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class DataPoint(BaseModel):
    timestamp: str
    value: float


class DeviceCounts(BaseModel):
    solar: int


class AddSourceRequest(BaseModel):
    source_type: str  # 'solar'
    latitude: float
    longitude: float
    name: str | None = None
    household_id: str | None = None


class EnergySourceWithData(BaseModel):
    source_id: str
    source_type: str
    latitude: float
    longitude: float
    name: str | None
    household_id: str | None = None
    current_value: float | None = None
    status: str = "active"


class Household(BaseModel):
    household_id: str
    name: str
    latitude: float
    longitude: float
    solar_panels: int = 0
    building_type: str = 'household'
    num_people: int = 1
    num_evs: int = 0
    osm_feature_id: Optional[str] = None


class HouseholdCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    solar_panels: int = 0
    building_type: str = 'household'
    num_people: int = 1
    num_evs: int = 0
    osm_feature_id: Optional[str] = None


class ElectricVehicle(BaseModel):
    vehicle_id: str
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float
    status: str = 'home'
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class EVCreate(BaseModel):
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float = 0.9
    status: str = 'home'


class EVOperation(BaseModel):
    power_kw: float
    duration_h: float = 1.0


class CommunitySummary(BaseModel):
    total_production: float
    total_consumption: float
    net: float
    ev_soc_total: float
    ev_soc_capacity: float
    action: str
    household_count: int
    ev_count: int
