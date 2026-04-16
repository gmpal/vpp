from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CommunityCreate(BaseModel):
    name: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None


class Community(BaseModel):
    community_id: str
    manager_user_id: str
    name: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    created_at: datetime


class DataPoint(BaseModel):
    timestamp: str
    value: float


class DeviceCounts(BaseModel):
    solar: int


class AddSourceRequest(BaseModel):
    source_type: str  # 'solar' or 'wind'
    latitude: float
    longitude: float
    name: str | None = None
    household_id: str | None = None
    community_id: str | None = None


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
    building_type: str = "household"
    num_people: int = 1
    num_evs: int = 0
    osm_feature_id: Optional[str] = None
    geometry: Optional[dict] = None


class HouseholdCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    solar_panels: int = 0
    building_type: str = "household"
    num_people: int = 1
    num_evs: int = 0
    osm_feature_id: Optional[str] = None
    geometry: Optional[dict] = None
    community_id: Optional[str] = None


class ElectricVehicle(BaseModel):
    vehicle_id: str
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float
    status: str = "home"
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
    status: str = "home"


class EVOperation(BaseModel):
    power_kw: float
    duration_h: float = 1.0


class Battery(BaseModel):
    battery_id: str
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float = 0.95


class BatteryCreate(BaseModel):
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float = 0.95


class BatteryOperation(BaseModel):
    power_kw: float
    duration_h: float = 1.0


class CommunitySummary(BaseModel):
    total_production: float
    total_consumption: float
    net: float
    ev_soc_total: float
    ev_soc_capacity: float
    battery_soc_total: float = 0.0
    battery_soc_capacity: float = 0.0
    action: str
    household_count: int
    ev_count: int
    battery_count: int = 0
