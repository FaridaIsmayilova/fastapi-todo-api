# app/security.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# Read from env (with safe fallbacks for local dev)
SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-change-me"
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def create_access_token(subject: int | str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    # Raises jose.JWTError on invalid/expired tokens
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "JWTError",
]
