"""Domain and HTTP exception hierarchy."""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 400,
        errors: list[Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(message=message, code=code, status_code=404)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED") -> None:
        super().__init__(message=message, code=code, status_code=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN") -> None:
        super().__init__(message=message, code=code, status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict", code: str = "CONFLICT") -> None:
        super().__init__(message=message, code=code, status_code=409)


class ValidationAppError(AppException):
    def __init__(
        self,
        message: str = "Validation error",
        errors: list[Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            errors=errors,
        )


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, code="RATE_LIMIT", status_code=429)


class ServiceUnavailableError(AppException):
    def __init__(
        self,
        message: str = "Service unavailable",
        code: str = "SERVICE_UNAVAILABLE",
    ) -> None:
        super().__init__(message=message, code=code, status_code=503)
