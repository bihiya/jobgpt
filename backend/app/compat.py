"""Python version compatibility helpers (3.9+)."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum as StrEnum
else:

    class StrEnum(str, Enum):
        """Minimal backport of enum.StrEnum for Python < 3.11."""

        def __str__(self) -> str:  # pragma: no cover - trivial
            return str(self.value)
