from fastapi import APIRouter, Depends, HTTPException, status 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from jose import JWTError

from ..database import get_db
from .. import models, schemas
from ..security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Swagger "Authorize" support (OAuth2 Password flow)
# In Swagger, click Authorize and enter username/password; Swagger will call /auth/login
# with form data and store the returned bearer token automatically.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="Bearer")


@router.post("/register", response_model=schemas.UserOut, summary="Register a new user")
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # Extra guard (schema already enforces min_length=6 -> 422)
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = models.User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        password=hash_password(payload.password),  # hash before storing
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")


@router.post("/login", response_model=schemas.Token, summary="Login and get JWT")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Swagger's Authorize popup posts form data (username/password) here
    user = db.execute(
        select(models.User).where(models.User.username == form.username)
    ).scalar_one_or_none()

    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return schemas.Token(access_token=create_access_token(subject=user.id))


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> models.User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        user_id = int(sub) if sub is not None else None
    except (JWTError, ValueError):
        raise cred_exc

    user = db.get(models.User, user_id) if user_id else None
    if not user:
        raise cred_exc
    return user


# A protected endpoint so Swagger shows the "Authorize" button,
# and to quickly verify your token works.
@router.get(
    "/me",
    response_model=schemas.UserOut,
    summary="Get current user (requires Bearer token)",
    description="Returns the authenticated user's profile. Use the Authorize button to sign in.",
)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
