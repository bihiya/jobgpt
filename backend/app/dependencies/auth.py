"""Auth and RBAC dependencies."""

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

    user = await UserRepository().get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    request.state.user = user
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
