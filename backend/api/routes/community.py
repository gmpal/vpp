from fastapi import APIRouter, Depends
from backend.api.models import CommunitySummary
from backend.src.dependencies import get_crud_manager

router = APIRouter()


@router.get("/community/summary", response_model=CommunitySummary)
def community_summary(crud=Depends(get_crud_manager)):
    return crud.get_community_summary()
