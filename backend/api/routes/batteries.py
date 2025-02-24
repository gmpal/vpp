from fastapi import APIRouter, HTTPException
from typing import List, Dict
from backend.api.models import BatteryStatus, BatteryOperation, BatteryAddRequest
from backend.src.storage.battery import Battery

router = APIRouter()

# In-memory store for batteries (consider moving to a separate module if it grows)
batteries: Dict[str, Battery] = {}


@router.get("/batteries", response_model=List[BatteryStatus])
def get_all_batteries():
    """Returns list and current state of all batteries."""
    return [
        BatteryStatus(
            battery_id=battery_id,
            capacity_kWh=battery.capacity_kWh,
            soc_kWh=battery.current_soc_kWh,
            max_charge_kW=battery.max_charge_kW,
            max_discharge_kW=battery.max_discharge_kW,
            eta=battery.round_trip_efficiency,
        )
        for battery_id, battery in batteries.items()
    ]


@router.post("/batteries", response_model=BatteryStatus)
def add_battery(battery: BatteryAddRequest):
    """Adds a new battery."""
    battery_id = f"battery_{len(batteries) + 1}"
    new_battery = Battery(
        battery_id=battery_id,
        capacity_kWh=battery.capacity_kWh,
        current_soc_kWh=battery.current_soc_kWh,
        max_charge_kW=battery.max_charge_kW,
        max_discharge_kW=battery.max_discharge_kW,
        round_trip_efficiency=battery.eta,
    )
    batteries[battery_id] = new_battery
    # TODO: save_battery_state(new_battery) if desired
    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=new_battery.capacity_kWh,
        soc_kWh=new_battery.current_soc_kWh,
        max_charge_kW=new_battery.max_charge_kW,
        max_discharge_kW=new_battery.max_discharge_kW,
        eta=new_battery.round_trip_efficiency,
    )


@router.delete("/batteries/{battery_id}", response_model=None)
def remove_battery(battery_id: str):
    """Removes a battery from the in-memory store."""
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")
    del batteries[battery_id]
    # TODO: remove_battery_state(battery_id) if desired
    return {"detail": "Battery removed successfully"}


@router.post("/batteries/{battery_id}/charge", response_model=BatteryStatus)
def charge_battery(battery_id: str, operation: BatteryOperation):
    """Triggers a charge operation on a specific battery."""
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")
    battery = batteries[battery_id]
    battery.charge(power_kW=operation.power_kW, duration_h=operation.duration_h)
    # TODO: save_battery_state(battery) if desired
    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=battery.capacity_kWh,
        soc_kWh=battery.current_soc_kWh,
        max_charge_kW=battery.max_charge_kW,
        max_discharge_kW=battery.max_discharge_kW,
        eta=battery.round_trip_efficiency,
    )


@router.post("/batteries/{battery_id}/discharge", response_model=BatteryStatus)
def discharge_battery(battery_id: str, operation: BatteryOperation):
    """Triggers a discharge operation on a specific battery."""
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")
    battery = batteries[battery_id]
    battery.discharge(power_kW=operation.power_kW, duration_h=operation.duration_h)
    # TODO: save_battery_state(battery) if desired
    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=battery.capacity_kWh,
        soc_kWh=battery.current_soc_kWh,
        max_charge_kW=battery.max_charge_kW,
        max_discharge_kW=battery.max_discharge_kW,
        eta=battery.round_trip_efficiency,
    )
