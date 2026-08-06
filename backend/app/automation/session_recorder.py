"""Apply session step timeline recorder."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class SessionStep:
    key: str
    label: str
    status: str = "ok"  # ok|warn|error|pending|skipped
    detail: str = ""
    at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApplySessionRecorder:
    """In-memory step log for one apply attempt; persisted on Application."""

    def __init__(self, *, correlation_id: str | None = None) -> None:
        self.correlation_id = correlation_id or uuid4().hex
        self.steps: list[SessionStep] = []

    def add(
        self,
        key: str,
        label: str,
        *,
        status: str = "ok",
        detail: str = "",
        **metadata: Any,
    ) -> SessionStep:
        step = SessionStep(key=key, label=label, status=status, detail=detail, metadata=metadata)
        self.steps.append(step)
        return step

    def opened_jd(self, url: str = "") -> None:
        self.add("opened_jd", "Opened job description", detail=url[:300])

    def clicked_apply(self, selector: str = "") -> None:
        self.add("clicked_apply", "Clicked Easy Apply / Apply", detail=selector)

    def uploaded_resume(self) -> None:
        self.add("uploaded_resume", "Uploaded resume")

    def filled_fields(self, count: int) -> None:
        self.add("filled_fields", f"Filled {count} field{'s' if count != 1 else ''}", count=count)

    def captcha(self, solved: bool, detail: str = "") -> None:
        self.add(
            "captcha",
            "Captcha challenge",
            status="ok" if solved else "warn",
            detail=detail or ("solved" if solved else "unsolved"),
        )

    def otp(self, handled: bool, detail: str = "") -> None:
        self.add(
            "otp",
            "2FA / OTP",
            status="ok" if handled else "warn",
            detail=detail or ("filled" if handled else "needs user OTP"),
        )

    def submitted(self) -> None:
        self.add("submitted", "Submitted application")

    def verified(self, success: bool, detail: str = "") -> None:
        self.add(
            "verified",
            "Verified apply result",
            status="ok" if success else "error",
            detail=detail,
        )

    def needs_input(self, questions: list[str]) -> None:
        self.add(
            "needs_input",
            "Paused for unknown questions",
            status="pending",
            detail=f"{len(questions)} question(s)",
            questions=questions[:20],
        )

    def failed(self, message: str) -> None:
        self.add("failed", "Apply failed", status="error", detail=message[:500])

    def to_list(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.steps]
