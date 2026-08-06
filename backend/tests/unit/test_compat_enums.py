"""Compat helpers for older Python runtimes."""

from app.compat import StrEnum
from app.models.enums import ApplicationStatus, UserRole


def test_strenum_values_are_strings():
    assert UserRole.USER == "user"
    assert str(UserRole.ADMIN) == "admin"
    assert ApplicationStatus.PENDING.value == "pending"


def test_local_strenum_subclass():
    class Color(StrEnum):
        RED = "red"

    assert Color.RED == "red"
    assert isinstance(Color.RED, str)
