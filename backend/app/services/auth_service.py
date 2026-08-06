"""Authentication service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repository.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(
        self,
        users: UserRepository | None = None,
        refresh_tokens: RefreshTokenRepository | None = None,
    ) -> None:
        self.users = users or UserRepository()
        self.refresh_tokens = refresh_tokens or RefreshTokenRepository()

    async def register(self, payload: RegisterRequest) -> User:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise ConflictError("Email already registered", code="AUTH_EMAIL_EXISTS")
        return await self.users.create_user(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials", code="AUTH_INVALID_CREDENTIALS")
        if not user.is_active:
            raise UnauthorizedError("Account disabled", code="AUTH_DISABLED")
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            data = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc
        if data.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        token_hash = self._hash_token(refresh_token)
        stored = await self.refresh_tokens.get_valid(token_hash)
        if not stored:
            raise UnauthorizedError("Refresh token revoked or expired")

        user = await self.users.get_by_id(data["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("User not found")

        await self.refresh_tokens.revoke(token_hash)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str, access_jti: str | None = None) -> None:
        await self.refresh_tokens.revoke(self._hash_token(refresh_token))
        if access_jti:
            try:
                from app.core.redis_features import blacklist_token

                await blacklist_token(
                    access_jti,
                    ttl_seconds=settings.access_token_expire_minutes * 60,
                )
            except Exception:  # noqa: BLE001
                pass

    async def _issue_tokens(self, user: User) -> TokenResponse:
        roles = [r.value for r in user.roles]
        access = create_access_token(str(user.id), {"roles": roles, "email": user.email})
        refresh = create_refresh_token(str(user.id))
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            days=settings.refresh_token_expire_days
        )
        await self.refresh_tokens.store(str(user.id), self._hash_token(refresh), expires_at)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
