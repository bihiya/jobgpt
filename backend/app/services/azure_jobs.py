"""Start Azure Container Apps Jobs via ARM (managed identity)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

_ARM_API = "2024-03-01"
_JOB_NAME_MAP = {
    "fetch": lambda: settings.azure_job_fetch,
    "match": lambda: settings.azure_job_match,
    "apply": lambda: settings.azure_job_apply,
}


def azure_jobs_configured() -> bool:
    return bool(
        settings.azure_jobs_enabled
        and settings.azure_subscription_id
        and settings.azure_resource_group
        and settings.azure_job_fetch
    )


async def _access_token() -> str:
    try:
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover
        raise ServiceUnavailableError(
            "azure-identity is not installed; cannot start Container Apps Jobs",
            code="AZURE_SDK_MISSING",
        ) from exc

    credential = DefaultAzureCredential()
    try:
        token = await credential.get_token("https://management.azure.com/.default")
        return token.token
    finally:
        await credential.close()


async def start_container_app_job(
    job_type: str,
    *,
    user_id: str,
    job_id: str | None = None,
    portal: str | None = None,
) -> dict[str, Any]:
    """Start a manual ACA job execution with per-run env overrides."""
    if not azure_jobs_configured():
        raise ServiceUnavailableError(
            "Azure Container Apps Jobs are not configured",
            code="AZURE_JOBS_DISABLED",
        )

    name_factory = _JOB_NAME_MAP.get(job_type)
    job_name = name_factory() if name_factory else ""
    if not job_name:
        raise ServiceUnavailableError(
            f"No Azure job configured for type '{job_type}'",
            code="AZURE_JOB_UNKNOWN",
        )

    env = [
        {"name": "JOB_TYPE", "value": job_type},
        {"name": "JOB_USER_ID", "value": user_id},
    ]
    if job_id:
        env.append({"name": "JOB_ID", "value": job_id})
    if portal:
        env.append({"name": "JOB_PORTAL", "value": portal})

    url = (
        f"https://management.azure.com/subscriptions/{settings.azure_subscription_id}"
        f"/resourceGroups/{settings.azure_resource_group}"
        f"/providers/Microsoft.App/jobs/{job_name}/start"
        f"?api-version={_ARM_API}"
    )
    body = {
        "containers": [
            {
                "name": "worker",
                "env": env,
            }
        ]
    }

    token = await _access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    if response.status_code >= 400:
        logger.warning(
            "azure_job_start_failed",
            job_type=job_type,
            job_name=job_name,
            status=response.status_code,
            body=response.text[:500],
        )
        raise ServiceUnavailableError(
            f"Failed to start Azure job '{job_name}': HTTP {response.status_code}",
            code="AZURE_JOB_START_FAILED",
        )

    data = response.json() if response.content else {}
    logger.info(
        "azure_job_started",
        job_type=job_type,
        job_name=job_name,
        user_id=user_id,
        execution=data.get("name"),
    )
    return {
        "job_name": job_name,
        "execution": data.get("name"),
        "job_type": job_type,
    }
