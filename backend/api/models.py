from typing import Optional

from pydantic import BaseModel


class DataPoint(BaseModel):
    timestamp: str
    value: float


class DeviceCounts(BaseModel):
    solar: int
    wind: int = 0


class AddSourceRequest(BaseModel):
    source_type: str  # 'solar' or 'wind'
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


class HouseholdUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    solar_panels: Optional[int] = None
    building_type: Optional[str] = None
    num_people: Optional[int] = None
    num_evs: Optional[int] = None
    osm_feature_id: Optional[str] = None
    geometry: Optional[dict] = None


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


class TariffPeriod(BaseModel):
    day_type: str = "all"  # 'weekday', 'weekend', 'all'
    hour_start: int
    hour_end: int
    price_per_kwh: float


class TariffCreate(BaseModel):
    name: str
    tariff_type: str  # 'grid_import' or 'grid_export'
    currency: str = "EUR"
    periods: list[TariffPeriod]


class Tariff(BaseModel):
    tariff_id: str
    name: str
    tariff_type: str
    currency: str = "EUR"
    active: bool = False
    periods: list[TariffPeriod] = []


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
