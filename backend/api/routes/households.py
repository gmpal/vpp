from fastapi import APIRouter, HTTPException, Depends
import uuid
from datetime import datetime
from backend.api.models import Household, HouseholdCreate
from backend.src.dependencies import get_crud_manager
from backend.src.db import CrudManager
from backend.src.pipelines.generation import generate_synthetic_load_data

router = APIRouter()


@router.post("/households", response_model=Household)
def create_household(req: HouseholdCreate, crud: CrudManager = Depends(get_crud_manager)):
    household_id = f"hh_{uuid.uuid4().hex[:8]}"
    crud.create_household(
        household_id, req.name, req.latitude, req.longitude,
        solar_panels=req.solar_panels, building_type=req.building_type,
        num_people=req.num_people, num_evs=req.num_evs,
        osm_feature_id=req.osm_feature_id,
    )

    # Generate a 30-day synthetic load profile scaled by number of occupants.
    # generate_synthetic_load_data uses a hardcoded *10 multiplier internally,
    # so we normalise: divide by 10 for a single-person base, then scale by num_people.
    starting_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    raw_load = generate_synthetic_load_data(
        starting_date=starting_date,
        num_days=30,
        freq='h',
        output_path=None,
    )
    scaled_load = raw_load * (req.num_people / 10.0)
    crud.save_household_load(household_id, scaled_load)

    return {
        "household_id": household_id, "name": req.name,
        "latitude": req.latitude, "longitude": req.longitude,
        "solar_panels": req.solar_panels, "building_type": req.building_type,
        "num_people": req.num_people, "num_evs": req.num_evs,
        "osm_feature_id": req.osm_feature_id,
    }


@router.get("/households", response_model=list[Household])
def list_households(crud: CrudManager = Depends(get_crud_manager)):
    return crud.get_all_households()


@router.get("/households/by-osm/{osm_feature_id}", response_model=Household)
def get_household_by_osm(osm_feature_id: str, crud: CrudManager = Depends(get_crud_manager)):
    hh = crud.get_household_by_osm_id(osm_feature_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    return hh


@router.get("/households/{household_id}", response_model=Household)
def get_household(household_id: str, crud: CrudManager = Depends(get_crud_manager)):
    hh = crud.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    return hh


@router.delete("/households/{household_id}")
def delete_household(household_id: str, crud: CrudManager = Depends(get_crud_manager)):
    hh = crud.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    crud.delete_household(household_id)
    return {"message": "Household deleted"}


@router.get("/households/{household_id}/summary")
def household_summary(household_id: str, crud: CrudManager = Depends(get_crud_manager)):
    hh = crud.get_household(household_id)
    if not hh:
        raise HTTPException(404, "Household not found")
    evs = crud.get_evs_by_household(household_id)
    ev_soc = sum(e["soc_kwh"] for e in evs)
    ev_cap = sum(e["capacity_kwh"] for e in evs)
    return {
        "household_id": household_id,
        "ev_count": len(evs),
        "ev_soc_kwh": ev_soc,
        "ev_capacity_kwh": ev_cap,
        "ev_soc_pct": (ev_soc / ev_cap * 100) if ev_cap > 0 else 0,
    }
