from typing import Optional

from pydantic import BaseModel


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


class CommunitySummary(BaseModel):
    total_production: float
    total_consumption: float
    net: float
    ev_soc_total: float
    ev_soc_capacity: float
    action: str
    household_count: int
    ev_count: int


# ---------------------------------------------------------------------------
# Community / membership
# ---------------------------------------------------------------------------

class CommunityCreate(BaseModel):
    name: str
    export_limit_kw: float = 100.0
    import_limit_kw: float = 100.0


class Community(BaseModel):
    community_id: str
    name: str
    export_limit_kw: float
    import_limit_kw: float
    created_at: Optional[str] = None


class MemberCreate(BaseModel):
    household_id: str
    role: str = "member"


class Member(BaseModel):
    member_id: str
    community_id: str
    household_id: str
    role: str
    joined_at: Optional[str] = None


class ParticipationRuleCreate(BaseModel):
    policy: str  # equal_share | proportional | priority
    priority_order: Optional[list] = None


class ParticipationRule(BaseModel):
    rule_id: str
    community_id: str
    policy: str
    priority_order: Optional[list] = None
    effective_from: Optional[str] = None


# ---------------------------------------------------------------------------
# Allocation ledger
# ---------------------------------------------------------------------------

class AllocationLedgerEntry(BaseModel):
    ledger_id: str
    community_id: str
    interval_start: str
    from_household_id: str
    to_household_id: str
    amount_kwh: float
    policy: str


# ---------------------------------------------------------------------------
# Tariffs & settlement
# ---------------------------------------------------------------------------

class TariffCreate(BaseModel):
    name: str
    import_rate: float
    export_rate: float
    feed_in_rate: float = 0.0


class Tariff(BaseModel):
    tariff_id: str
    community_id: str
    name: str
    import_rate: float
    export_rate: float
    feed_in_rate: float


class SettlementRunCreate(BaseModel):
    period_start: str
    period_end: str


class SettlementRun(BaseModel):
    run_id: str
    community_id: str
    period_start: str
    period_end: str
    status: str
    created_at: Optional[str] = None


class SettlementLine(BaseModel):
    line_id: str
    run_id: str
    household_id: str
    net_kwh: float
    cost: float
    savings: float


# ---------------------------------------------------------------------------
# Stationary battery assets
# ---------------------------------------------------------------------------

class BatteryAssetCreate(BaseModel):
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float = 0.95


class BatteryAsset(BaseModel):
    battery_id: str
    household_id: str
    name: str
    capacity_kwh: float
    soc_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    eta: float


# ---------------------------------------------------------------------------
# Grid connection limits
# ---------------------------------------------------------------------------

class GridConnectionLimitCreate(BaseModel):
    export_limit_kw: float
    import_limit_kw: float


class GridConnectionLimit(BaseModel):
    limit_id: str
    community_id: str
    export_limit_kw: float
    import_limit_kw: float
    effective_from: Optional[str] = None
