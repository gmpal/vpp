import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.models import Community, CommunityCreate, CommunitySummary
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.post("/communities", response_model=Community)
def create_community(
    req: CommunityCreate,
    crud=Depends(get_crud_manager),
):
    community_id = str(uuid.uuid4())
    return crud.create_community(
        community_id=community_id,
        name=req.name,
        location_lat=req.location_lat,
        location_lon=req.location_lon,
    )


@router.get("/communities", response_model=list[Community])
def list_communities(
    crud=Depends(get_crud_manager),
):
    return crud.list_communities()


@router.get("/communities/{community_id}", response_model=Community)
def get_community(
    community_id: str,
    crud=Depends(get_crud_manager),
):
    community = crud.get_community(community_id)
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return community


@router.get("/community/summary", response_model=CommunitySummary)
def community_summary(
    crud=Depends(get_crud_manager),
):
    return crud.get_community_summary()
