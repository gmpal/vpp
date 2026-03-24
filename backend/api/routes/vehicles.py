from fastapi import APIRouter, HTTPException, Depends
import uuid
from backend.api.models import ElectricVehicle, EVCreate, EVOperation
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.get("/vehicles", response_model=list[ElectricVehicle])
def list_vehicles(crud=Depends(get_crud_manager)):
    return crud.get_all_evs()


@router.post("/vehicles", response_model=ElectricVehicle)
def create_vehicle(req: EVCreate, crud=Depends(get_crud_manager)):
    vehicle_id = f"ev_{uuid.uuid4().hex[:8]}"
    crud.create_ev(vehicle_id, req.household_id, req.name, req.capacity_kwh,
                   req.soc_kwh, req.max_charge_kw, req.max_discharge_kw,
                   req.eta, req.status)
    ev = crud.get_ev(vehicle_id)
    return ev


@router.get("/vehicles/{vehicle_id}", response_model=ElectricVehicle)
def get_vehicle(vehicle_id: str, crud=Depends(get_crud_manager)):
    ev = crud.get_ev(vehicle_id)
    if not ev:
        raise HTTPException(404, "Vehicle not found")
    return ev


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: str, crud=Depends(get_crud_manager)):
    ev = crud.get_ev(vehicle_id)
    if not ev:
        raise HTTPException(404, "Vehicle not found")
    crud.delete_ev(vehicle_id)
    return {"message": "Vehicle deleted"}


@router.post("/vehicles/{vehicle_id}/charge")
def charge_vehicle(vehicle_id: str, op: EVOperation, crud=Depends(get_crud_manager)):
    ev = crud.get_ev(vehicle_id)
    if not ev:
        raise HTTPException(404, "Vehicle not found")
    max_charge = min(op.power_kw, ev["max_charge_kw"])
    energy_in = max_charge * op.duration_h * ev["eta"]
    new_soc = min(ev["soc_kwh"] + energy_in, ev["capacity_kwh"])
    crud.update_ev_soc(vehicle_id, new_soc)
    return {"vehicle_id": vehicle_id, "new_soc_kwh": new_soc, "actual_power_kw": max_charge}


@router.post("/vehicles/{vehicle_id}/discharge")
def discharge_vehicle(vehicle_id: str, op: EVOperation, crud=Depends(get_crud_manager)):
    ev = crud.get_ev(vehicle_id)
    if not ev:
        raise HTTPException(404, "Vehicle not found")
    max_discharge = min(op.power_kw, ev["max_discharge_kw"])
    energy_out = max_discharge * op.duration_h
    new_soc = max(ev["soc_kwh"] - energy_out / ev["eta"], 0.0)
    crud.update_ev_soc(vehicle_id, new_soc)
    return {"vehicle_id": vehicle_id, "new_soc_kwh": new_soc, "actual_power_kw": max_discharge}


@router.post("/vehicles/{vehicle_id}/location")
def update_location(vehicle_id: str, status: str, lat: float = None, lon: float = None,
                    crud=Depends(get_crud_manager)):
    ev = crud.get_ev(vehicle_id)
    if not ev:
        raise HTTPException(404, "Vehicle not found")
    crud.update_ev_status(vehicle_id, status, lat, lon)
    return {"message": "Location updated"}
