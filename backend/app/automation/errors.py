"""Typed automation / portal errors."""

from __future__ import annotations


class PortalAuthError(Exception):
    """Raised when portal login / session verification fails."""

    def __init__(self, message: str, code: str = "AUTH_FAILED") -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:  # noqa: D105
        return f"[{self.code}] {self.message}"
