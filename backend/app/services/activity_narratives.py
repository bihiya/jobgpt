"""Human-readable activity copy: who did what, outcome, and next step."""

from __future__ import annotations

from typing import Any

# Default next actions shown under each activity row.
_NEXT_STEPS: dict[str, str] = {
    "auth.register": "Complete onboarding — add your profile, resume, and a job portal.",
    "auth.login": "You're signed in. Continue from Digest or Approvals.",
    "auth.logout": "Sign in again when you're ready to continue.",
    "profile.updated": "Your updated profile will be used on the next application.",
    "resume.uploaded": "Make sure this resume is set as default before auto-apply runs.",
    "resume.deleted": "Upload another resume if you still want to auto-apply.",
    "settings.updated": "New settings apply on the next fetch, match, or apply run.",
    "portal.connected": "Run Fetch from Automation (or sync the portal) to pull jobs.",
    "portal.synced": "New jobs are ready — run Match, or wait for automatic matching.",
    "portal.reauth": "Retry sync / fetch now that the portal session is refreshed.",
    "job.created": "Job was fetched — matching will score it next.",
    "job.matched": "Review the score in Approvals or Pipeline.",
    "job.tracked": "Find it under Jobs → Tracked when you're ready to apply.",
    "job.ignored": "No further action. It won't be auto-applied.",
    "job.updated": "Open the job to confirm the new status or notes.",
    "job.ingested": "Matching will score this job next.",
    "approval.needed": "Open Approvals — approve to apply, or reject to skip.",
    "approval.approved": "Passed — apply worker will start submitting this application.",
    "approval.rejected": "Stopped here — this job will not be applied to.",
    "application.queued": "Apply worker will pick this up shortly.",
    "application.started": "Watch Automation logs for each apply step.",
    "application.succeeded": "Passed — follow up from Calendar / Email if they reply.",
    "application.failed": "Failed — check Automation logs, then retry from Applications.",
    "application.needs_input": "Answer the questions, then resume the apply from Approvals.",
    "application.otp_required": "Enter the portal OTP to continue the application.",
    "application.retry": "Retry queued — watch Automation for progress.",
    "application.cancelled": "Cancelled — no further apply attempts for this job.",
    "automation.triggered": "Open Automation to see live progress and results.",
    "email.applied": "Pipeline / Calendar updated from this email event.",
}

_ACTION_VERBS: dict[str, str] = {
    "auth.register": "created an account",
    "auth.login": "signed in",
    "auth.logout": "signed out",
    "profile.updated": "updated their profile",
    "resume.uploaded": "uploaded a resume",
    "resume.deleted": "deleted a resume",
    "settings.updated": "updated settings",
    "portal.connected": "connected a job portal",
    "portal.synced": "synced a job portal",
    "portal.reauth": "re-authenticated a job portal",
    "job.created": "fetched a new job",
    "job.matched": "matched a job",
    "job.tracked": "tracked a job",
    "job.ignored": "ignored a job",
    "job.updated": "updated a job",
    "job.ingested": "added a job",
    "approval.needed": "flagged a job for approval",
    "approval.approved": "approved an application",
    "approval.rejected": "rejected an application",
    "application.queued": "queued an application",
    "application.started": "started applying",
    "application.succeeded": "successfully applied",
    "application.failed": "failed an application",
    "application.needs_input": "paused apply — answers needed",
    "application.otp_required": "paused apply — OTP required",
    "application.retry": "retried an application",
    "application.cancelled": "cancelled an application",
    "automation.triggered": "triggered automation",
    "email.applied": "applied an email event to the pipeline",
}


def outcome_label(severity: str, action: str = "") -> str:
    """Passed / Failed / Needs attention / Happened."""
    if action.endswith(".failed") or action.endswith(".rejected") or severity == "error":
        return "Failed" if severity == "error" or action.endswith(".failed") else "Stopped"
    if action.endswith(".succeeded") or action.endswith(".approved") or severity == "success":
        if action.endswith(".rejected"):
            return "Stopped"
        return "Passed"
    if severity == "warning" or "needs_input" in action or "otp" in action or action.endswith(".needed"):
        return "Needs attention"
    if action.endswith(".started") or action.endswith(".queued") or action.endswith(".triggered"):
        return "In progress"
    return "Happened"


def next_step_for(action: str, severity: str, metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    if meta.get("next_step"):
        return str(meta["next_step"])
    if action in _NEXT_STEPS:
        return _NEXT_STEPS[action]
    if severity == "error":
        return "Check Automation logs or Activity details, then retry the step."
    if severity == "warning":
        return "Open the related page and finish the pending action."
    return "No further action required."


def build_summary(
    *,
    actor_name: str,
    action: str,
    message: str,
    source: str,
    severity: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Build '{Who} did X — detail' style headline."""
    meta = metadata or {}
    who = (actor_name or "").strip()
    if source in {"worker", "system"}:
        who = who or "JobPilot"
    else:
        who = who or "You"

    detail = (message or "").strip()
    verb = _ACTION_VERBS.get(action)

    # Prefer concrete message as the detail clause.
    if verb and detail:
        # Avoid "Lav updated settings — Settings updated"
        if detail.lower().rstrip(".") == verb.lower() or detail.lower() in verb.lower():
            summary = f"{who} {verb}"
        elif detail[0:1].islower() or detail.startswith(who):
            summary = f"{who} {detail[0].lower() + detail[1:]}" if detail[0:1].isupper() else f"{who} {detail}"
        else:
            summary = f"{who} {verb} — {detail}"
    elif verb:
        summary = f"{who} {verb}"
    elif detail:
        if detail.lower().startswith(who.lower()):
            summary = detail
        else:
            summary = f"{who} — {detail}"
    else:
        summary = f"{who} performed {action.replace('.', ' ')}"

    # Append compact outcome for clear pass/fail scanning.
    outcome = meta.get("outcome") or outcome_label(severity, action)
    if outcome and outcome not in summary:
        summary = f"{summary} · {outcome}"
    return summary


def narrate_activity(
    *,
    actor_name: str,
    action: str,
    message: str,
    source: str,
    severity: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    meta = dict(metadata or {})
    outcome = str(meta.get("outcome") or outcome_label(severity, action))
    next_step = next_step_for(action, severity, meta)
    summary = build_summary(
        actor_name=actor_name,
        action=action,
        message=message,
        source=source,
        severity=severity,
        metadata={**meta, "outcome": outcome},
    )
    return {
        "summary": summary,
        "outcome": outcome,
        "next_step": next_step,
        "actor_name": actor_name or ("JobPilot" if source in {"worker", "system"} else "You"),
    }
