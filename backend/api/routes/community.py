from fastapi import APIRouter, Depends

from backend.api.auth import get_current_user
from backend.api.models import CommunitySummary
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.get("/community/summary", response_model=CommunitySummary)
def community_summary(
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.get_community_summary(user_id=current_user["user_id"])
