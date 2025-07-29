from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user,
    UserCreate,
)
from schemas.requests import RegisterUserRequest
from schemas.responses import TokenResponse
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

## TODO 
# [ ] - Retornar o ID do cliente na API para autenticar no dashboard


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate token for authentication."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")
async def register_user(form_data: RegisterUserRequest):
    """Register a new user."""
    user = UserCreate(
        username=form_data.username,
        password=form_data.password,
        email=form_data.email,
        full_name=form_data.full_name,
        disabled=False,
        phone=form_data.phone
    )
    create_user(user)
    if not user.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing username")
    if not user.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing password")
    return {
        "message": "User registered successfully",
        "user": form_data
    }
