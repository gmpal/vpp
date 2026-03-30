"""
Authentication utilities: JWT creation/verification, password hashing, and
the get_current_user FastAPI dependency injected into every protected route.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.src.db import DatabaseManager
from backend.src.dependencies import get_db_manager

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "vpp_dev_secret_change_in_production_32ch")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_user_by_username(db: DatabaseManager, username: str) -> dict | None:
    rows = db.execute(
        "SELECT user_id, username, hashed_password FROM users WHERE username = %s",
        (username,), fetch=True,
    )
    if not rows:
        return None
    r = rows[0]
    return {"user_id": r[0], "username": r[1], "hashed_password": r[2]}


def get_user_by_id(db: DatabaseManager, user_id: str) -> dict | None:
    rows = db.execute(
        "SELECT user_id, username FROM users WHERE user_id = %s",
        (user_id,), fetch=True,
    )
    if not rows:
        return None
    r = rows[0]
    return {"user_id": r[0], "username": r[1]}


def create_user_in_db(db: DatabaseManager, username: str, plain_password: str) -> dict:
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    db.execute(
        "INSERT INTO users (user_id, username, hashed_password) VALUES (%s, %s, %s)",
        (user_id, username, hash_password(plain_password)),
    )
    return {"user_id": user_id, "username": username}


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Decode the Bearer JWT and return the user dict. Raises 401 on any failure."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    user = get_user_by_id(db, user_id)
    if not user:
        raise exc
    return user
