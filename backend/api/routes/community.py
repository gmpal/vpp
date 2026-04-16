import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.api.models import Community, CommunitySummary, CommunityCreate
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.post("/communities", response_model=Community)
def create_community(
    req: CommunityCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community_id = str(uuid.uuid4())
    return crud.create_community(
        community_id=community_id,
        manager_user_id=current_user["user_id"],
        name=req.name,
        location_lat=req.location_lat,
        location_lon=req.location_lon,
    )


@router.get("/communities", response_model=list[Community])
def list_communities(
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.list_communities(manager_user_id=current_user["user_id"])


@router.get("/communities/{community_id}", response_model=Community)
def get_community(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(
        community_id=community_id,
        manager_user_id=current_user["user_id"],
    )
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return community


@router.get("/community/summary", response_model=CommunitySummary)
def community_summary(
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.get_community_summary(user_id=current_user["user_id"])
