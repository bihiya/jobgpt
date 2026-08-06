"""Auth endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserProfileSchema
from app.dependencies.services import get_auth_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        profile=UserProfileSchema(**user.profile.model_dump()),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    user = await service.register(payload)
    return _user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return await service.refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    await service.logout(payload.refresh_token)
    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return _user_response(user)
