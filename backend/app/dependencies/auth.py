"""Auth and RBAC dependencies with token blacklist check."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User
from app.repository.user_repository import UserRepository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authorization token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    jti = payload.get("jti")
    if jti:
        try:
            from app.core.redis_features import is_token_blacklisted

            if await is_token_blacklisted(jti):
                raise UnauthorizedError("Token revoked", code="AUTH_TOKEN_REVOKED")
        except UnauthorizedError:
            raise
        except Exception:  # noqa: BLE001
            pass

    user = await UserRepository().get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    request.state.user = user
    request.state.token_jti = jti
    return user


def require_roles(*roles: UserRole):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        user_roles = set(user.roles)
        if UserRole.ADMIN in user_roles:
            return user
        if not user_roles.intersection(set(roles)):
            raise ForbiddenError("Insufficient permissions")
        return user

    return _checker
