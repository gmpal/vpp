from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.api.auth import (
    get_user_by_username, create_user_in_db,
    verify_password, create_access_token, get_current_user,
)
from backend.src.db import DatabaseManager
from backend.src.dependencies import get_db_manager

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    user_id: str
    username: str


@router.post("/auth/register", response_model=UserResponse)
def register(req: RegisterRequest, db: DatabaseManager = Depends(get_db_manager)):
    if len(req.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if get_user_by_username(db, req.username):
        raise HTTPException(400, "Username already taken")
    return create_user_in_db(db, req.username, req.password)


@router.post("/auth/token", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DatabaseManager = Depends(get_db_manager),
):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user["user_id"]), "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return current_user
