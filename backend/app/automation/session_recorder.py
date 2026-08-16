"""Apply session step timeline recorder."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.times import iso_utc


@dataclass
class SessionStep:
    key: str
    label: str
    status: str = "ok"  # ok|warn|error|pending|skipped
    detail: str = ""
    at: str = field(default_factory=lambda: iso_utc(datetime.utcnow()) or "")
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApplySessionRecorder:
    """In-memory step log for one apply attempt; persisted on Application."""

    def __init__(self, *, correlation_id: str | None = None, on_step: Any = None) -> None:
        self.correlation_id = correlation_id or uuid4().hex
        self.steps: list[SessionStep] = []
        self.on_step = on_step
        self._pending_tasks: list[asyncio.Task] = []

    def seed(self, steps: list[dict[str, Any]] | None) -> None:
        """Restore prior steps without firing on_step (queue + earlier attempts)."""
        for raw in steps or []:
            if not isinstance(raw, dict):
                continue
            meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
            extra = {
                key: value
                for key, value in raw.items()
                if key not in {"key", "label", "status", "detail", "at", "metadata"}
            }
            self.steps.append(
                SessionStep(
                    key=str(raw.get("key") or "step"),
                    label=str(raw.get("label") or raw.get("key") or "step"),
                    status=str(raw.get("status") or "ok"),
                    detail=str(raw.get("detail") or ""),
                    at=str(raw.get("at") or iso_utc(datetime.utcnow()) or ""),
                    metadata={**extra, **meta},
                )
            )

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
        self._emit(step)
        return step

    def complete_pending(
        self,
        key: str,
        *,
        label: str | None = None,
        detail: str | None = None,
    ) -> SessionStep | None:
        """Mark the latest pending step with this key as done (queued → worker picked up)."""
        for step in reversed(self.steps):
            if step.key != key or step.status != "pending":
                continue
            step.status = "ok"
            if label is not None:
                step.label = label
            if detail is not None:
                step.detail = detail
            step.at = iso_utc(datetime.utcnow()) or step.at
            self._emit(step)
            return step
        return None

    def _emit(self, step: SessionStep) -> None:
        callback = self.on_step
        if not callback:
            return
        try:
            result = callback(step)
        except Exception:  # noqa: BLE001 — live UI must never break apply
            return
        if not inspect.isawaitable(result):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            close = getattr(result, "close", None)
            if callable(close):
                close()
            return
        self._pending_tasks.append(loop.create_task(result))

    async def flush(self) -> None:
        """Wait until live UI publishes for steps already recorded.

        Call this before blocking work (blob download, Chromium launch) so the
        pipeline does not sit on “Worker started applying” with no next step.
        """
        if not self._pending_tasks:
            return
        pending = self._pending_tasks
        self._pending_tasks = []
        await asyncio.gather(*pending, return_exceptions=True)

    def opened_jd(self, url: str = "") -> None:
        self.add("opened_jd", "Opened job description", detail=url[:300])

    def apply_channel(self, label: str, *, kind: str = "", ats: str = "", url: str = "") -> None:
        self.add("apply_channel", label, kind=kind, ats=ats, url=url)

    def clicked_apply(self, selector: str = "", *, kind: str = "easy") -> None:
        if kind == "external":
            label = "Clicked External Apply"
        elif kind in {"easy", "linkedin"}:
            label = "Clicked LinkedIn Easy Apply"
        elif kind == "indeed":
            label = "Clicked Indeed Apply"
        else:
            label = "Clicked Apply"
        self.add("clicked_apply", label, detail=selector, kind=kind)

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

    def needs_account(self, detail: str = "") -> None:
        self.add(
            "needs_account",
            "Paused — candidate account required",
            status="pending",
            detail=detail[:500],
        )

    def failed(self, message: str) -> None:
        self.add("failed", "Apply failed", status="error", detail=message[:500])

    def to_list(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.steps]


def compact_sync_steps(steps: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Trim recorder steps for audit metadata (no huge blobs)."""
    out: list[dict[str, Any]] = []
    for step in (steps or [])[:50]:
        if not isinstance(step, dict):
            continue
        out.append(
            {
                "key": str(step.get("key") or "step")[:40],
                "label": str(step.get("label") or step.get("message") or "")[:240],
                "status": str(step.get("status") or "ok")[:20],
                "detail": str(step.get("detail") or "")[:400],
                "at": str(step.get("at") or "")[:40],
            }
        )
    return out
