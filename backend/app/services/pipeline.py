"""Kanban column mapping for the job pipeline.

Fetched → Queued (auto-apply) → Applied → Interview → Shortlisted
"""

from __future__ import annotations

from app.models.enums import JobStatus

PIPELINE_COLUMN_KEYS = ("fetched", "queued", "applied", "interview", "shortlisted")

PIPELINE_COLUMNS: list[tuple[str, list[JobStatus]]] = [
    (
        "fetched",
        [
            JobStatus.NEW,
            JobStatus.MATCHED,
            JobStatus.AWAITING_APPROVAL,
            JobStatus.TRACKED,
            JobStatus.FAILED,
        ],
    ),
    ("queued", [JobStatus.APPROVED, JobStatus.APPLYING]),
    ("applied", [JobStatus.APPLIED]),
    ("interview", [JobStatus.INTERVIEW]),
    ("shortlisted", [JobStatus.SHORTLISTED, JobStatus.OFFER]),
]

_STATUS_TO_COLUMN: dict[JobStatus, str] = {
    status: key for key, statuses in PIPELINE_COLUMNS for status in statuses
}

_COLUMN_TARGET_STATUS: dict[str, JobStatus] = {
    "fetched": JobStatus.MATCHED,
    "queued": JobStatus.APPLYING,
    "applied": JobStatus.APPLIED,
    "interview": JobStatus.INTERVIEW,
    "shortlisted": JobStatus.SHORTLISTED,
}


def column_for_status(status: JobStatus | str | None) -> str | None:
    if status is None:
        return None
    try:
        parsed = status if isinstance(status, JobStatus) else JobStatus(str(status))
    except ValueError:
        return None
    return _STATUS_TO_COLUMN.get(parsed)


def target_status_for_column(column: str) -> JobStatus:
    try:
        return _COLUMN_TARGET_STATUS[column]
    except KeyError as exc:
        raise ValueError(f"Unknown pipeline column: {column}") from exc


def should_queue_apply(from_column: str | None, to_column: str) -> bool:
    """Dropping onto Queued from any other stage starts (or restarts) auto-apply."""
    return to_column == "queued" and from_column != "queued"
