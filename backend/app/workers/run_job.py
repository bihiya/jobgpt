"""One-shot Azure Container Apps Job entrypoint (no Kafka).

Env:
  JOB_TYPE            fetch | match | apply
  JOB_USER_ID         required user id
  JOB_ID              required for apply; optional for match (matches all NEW if omitted)
  JOB_APPLICATION_ID  optional existing application for apply
  JOB_PORTAL          optional portal filter for fetch
"""

from __future__ import annotations

import os
import sys

from app.core.logging import get_logger
from app.workers.bootstrap import main

logger = get_logger(__name__)


async def _run_once() -> None:
    job_type = (os.getenv("JOB_TYPE") or "").strip().lower()
    user_id = (os.getenv("JOB_USER_ID") or "").strip()
    job_id = (os.getenv("JOB_ID") or "").strip()
    application_id = (os.getenv("JOB_APPLICATION_ID") or "").strip()
    portal = (os.getenv("JOB_PORTAL") or "").strip()

    if not job_type or not user_id:
        logger.error("azure_job_missing_env", job_type=job_type, user_id=bool(user_id))
        raise SystemExit("JOB_TYPE and JOB_USER_ID are required")

    if job_type == "fetch":
        from app.workers.fetch_worker import FetchWorker

        payload: dict = {"user_id": user_id, "source": "azure-job"}
        if portal:
            payload["portal"] = portal
        await FetchWorker().handle("job.fetch", payload)
    elif job_type == "match":
        from app.models.enums import JobStatus
        from app.models.job import Job
        from app.workers.match_worker import MatchWorker

        worker = MatchWorker()
        if job_id:
            await worker.handle("job.match", {"user_id": user_id, "job_id": job_id})
        else:
            jobs = await Job.find({"user_id": user_id, "status": JobStatus.NEW}).limit(50).to_list()
            for job in jobs:
                await worker.handle("job.match", {"user_id": user_id, "job_id": str(job.id)})
    elif job_type == "apply":
        if not job_id:
            raise SystemExit("JOB_ID is required for apply jobs")
        from app.workers.apply_worker import ApplyWorker

        payload = {"user_id": user_id, "job_id": job_id, "source": "azure-job"}
        if application_id:
            payload["application_id"] = application_id
        await ApplyWorker().handle("job.apply", payload)
    else:
        raise SystemExit(f"Unsupported JOB_TYPE: {job_type}")

    logger.info("azure_job_finished", job_type=job_type, user_id=user_id)


if __name__ == "__main__":
    try:
        main(_run_once)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
