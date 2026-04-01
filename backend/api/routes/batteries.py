import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.api.models import Battery, BatteryCreate, BatteryOperation
from backend.src.dependencies import get_crud_manager

router = APIRouter()


def _assert_battery_ownership(crud, battery_id: str, user_id: str):
    """Raise 404 if the battery doesn't exist or doesn't belong to the user."""
    bat = crud.get_battery(battery_id)
    if not bat:
        raise HTTPException(404, "Battery not found")
    hh = crud.get_household(bat["household_id"], user_id=user_id)
    if not hh:
        raise HTTPException(404, "Battery not found")
    return bat


@router.get("/batteries", response_model=list[Battery])
def list_batteries(crud=Depends(get_crud_manager), current_user: dict = Depends(get_current_user)):
    return crud.get_all_batteries(user_id=current_user["user_id"])


@router.post("/batteries", response_model=Battery)
def create_battery(
    req: BatteryCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    hh = crud.get_household(req.household_id, user_id=current_user["user_id"])
    if not hh:
        raise HTTPException(404, "Household not found")
    battery_id = f"bat_{uuid.uuid4().hex[:8]}"
    crud.create_battery(
        battery_id, req.household_id, req.name, req.capacity_kwh,
        req.soc_kwh, req.max_charge_kw, req.max_discharge_kw, req.eta,
    )
    return crud.get_battery(battery_id)


@router.get("/batteries/{battery_id}", response_model=Battery)
def get_battery(
    battery_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return _assert_battery_ownership(crud, battery_id, current_user["user_id"])


@router.delete("/batteries/{battery_id}")
def delete_battery(
    battery_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    _assert_battery_ownership(crud, battery_id, current_user["user_id"])
    crud.delete_battery(battery_id)
    return {"message": "Battery deleted"}


@router.post("/batteries/{battery_id}/charge")
def charge_battery(
    battery_id: str,
    op: BatteryOperation,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    bat = _assert_battery_ownership(crud, battery_id, current_user["user_id"])
    max_charge = min(op.power_kw, bat["max_charge_kw"])
    new_soc = min(bat["soc_kwh"] + max_charge * op.duration_h * bat["eta"], bat["capacity_kwh"])
    crud.update_battery_soc(battery_id, new_soc)
    return {"battery_id": battery_id, "new_soc_kwh": new_soc, "actual_power_kw": max_charge}


@router.post("/batteries/{battery_id}/discharge")
def discharge_battery(
    battery_id: str,
    op: BatteryOperation,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    bat = _assert_battery_ownership(crud, battery_id, current_user["user_id"])
    max_discharge = min(op.power_kw, bat["max_discharge_kw"])
    new_soc = max(bat["soc_kwh"] - max_discharge * op.duration_h / bat["eta"], 0.0)
    crud.update_battery_soc(battery_id, new_soc)
    return {"battery_id": battery_id, "new_soc_kwh": new_soc, "actual_power_kw": max_discharge}
