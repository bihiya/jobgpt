"""Azure Container Apps job trigger helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.services.azure_jobs import (
    _merge_env,
    azure_jobs_configured,
    start_container_app_job,
)


def test_azure_jobs_configured_false_by_default():
    with patch("app.services.azure_jobs.settings") as settings:
        settings.azure_jobs_enabled = False
        settings.azure_subscription_id = ""
        settings.azure_resource_group = ""
        settings.azure_job_fetch = ""
        assert azure_jobs_configured() is False


def test_azure_jobs_configured_true_when_set():
    with patch("app.services.azure_jobs.settings") as settings:
        settings.azure_jobs_enabled = True
        settings.azure_subscription_id = "sub"
        settings.azure_resource_group = "rg"
        settings.azure_job_fetch = "job-fetch"
        assert azure_jobs_configured() is True


def test_merge_env_preserves_secret_refs_and_overrides():
    template = [
        {"name": "MONGODB_URL", "secretRef": "mongodb-url", "value": ""},
        {"name": "JOB_TYPE", "value": "fetch"},
        {"name": "APP_ENV", "value": "production"},
    ]
    merged = _merge_env(
        template,
        [
            {"name": "JOB_TYPE", "value": "fetch"},
            {"name": "JOB_USER_ID", "value": "u1"},
        ],
    )
    by_name = {item["name"]: item for item in merged}
    assert by_name["MONGODB_URL"]["secretRef"] == "mongodb-url"
    assert by_name["JOB_TYPE"]["value"] == "fetch"
    assert by_name["JOB_USER_ID"]["value"] == "u1"
    assert by_name["APP_ENV"]["value"] == "production"


def _mock_client(*, post_status=200, template_container=None):
    container = template_container or {
        "name": "job-fetch",
        "image": "example.azurecr.io/jobpilot-api:latest",
        "command": ["python"],
        "args": ["-m", "app.workers.run_job"],
        "env": [
            {"name": "JOB_TYPE", "value": "fetch"},
            {"name": "MONGODB_URL", "secretRef": "mongodb-url", "value": ""},
        ],
        "resources": {"cpu": 1.0, "memory": "2Gi"},
    }
    get_response = AsyncMock()
    get_response.status_code = 200
    get_response.text = ""
    get_response.json = lambda: {
        "properties": {"template": {"containers": [container]}}
    }

    post_response = AsyncMock()
    post_response.status_code = post_status
    post_response.content = b'{"name":"exec-1"}'
    post_response.text = "forbidden" if post_status >= 400 else ""
    post_response.json = lambda: {"name": "exec-1"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = get_response
    mock_client.post.return_value = post_response
    return mock_client


@pytest.mark.asyncio
async def test_start_container_app_job_posts_arm():
    mock_client = _mock_client()

    with (
        patch("app.services.azure_jobs.settings") as settings,
        patch("app.services.azure_jobs._access_token", new=AsyncMock(return_value="tok")),
        patch("app.services.azure_jobs.httpx.AsyncClient", return_value=mock_client),
    ):
        settings.azure_jobs_enabled = True
        settings.azure_subscription_id = "sub"
        settings.azure_resource_group = "rg"
        settings.azure_job_fetch = "job-fetch"
        settings.azure_job_match = "job-match"
        settings.azure_job_apply = "job-apply"

        result = await start_container_app_job("fetch", user_id="u1", portal="linkedin")
        assert result["job_name"] == "job-fetch"
        assert result["execution"] == "exec-1"
        mock_client.get.assert_called_once()
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert "jobs/job-fetch/start" in args[0]
        container = kwargs["json"]["containers"][0]
        assert container["name"] == "job-fetch"
        assert container["image"] == "example.azurecr.io/jobpilot-api:latest"
        assert container["command"] == ["python"]
        assert container["args"] == ["-m", "app.workers.run_job"]
        assert container["resources"] == {"cpu": 1.0, "memory": "2Gi"}
        env = {item["name"]: item for item in container["env"]}
        assert env["MONGODB_URL"]["secretRef"] == "mongodb-url"
        assert env["JOB_USER_ID"]["value"] == "u1"
        assert env["JOB_PORTAL"]["value"] == "linkedin"


@pytest.mark.asyncio
async def test_start_container_app_job_raises_on_http_error():
    mock_client = _mock_client(post_status=403)

    with (
        patch("app.services.azure_jobs.settings") as settings,
        patch("app.services.azure_jobs._access_token", new=AsyncMock(return_value="tok")),
        patch("app.services.azure_jobs.httpx.AsyncClient", return_value=mock_client),
    ):
        settings.azure_jobs_enabled = True
        settings.azure_subscription_id = "sub"
        settings.azure_resource_group = "rg"
        settings.azure_job_fetch = "job-fetch"
        settings.azure_job_match = ""
        settings.azure_job_apply = ""

        with pytest.raises(ServiceUnavailableError) as exc:
            await start_container_app_job("fetch", user_id="u1")
        assert exc.value.code == "AZURE_JOB_START_FAILED"


@pytest.mark.asyncio
async def test_start_container_app_job_raises_when_image_missing():
    mock_client = _mock_client(
        template_container={"name": "job-fetch", "env": [], "command": ["python"]}
    )

    with (
        patch("app.services.azure_jobs.settings") as settings,
        patch("app.services.azure_jobs._access_token", new=AsyncMock(return_value="tok")),
        patch("app.services.azure_jobs.httpx.AsyncClient", return_value=mock_client),
    ):
        settings.azure_jobs_enabled = True
        settings.azure_subscription_id = "sub"
        settings.azure_resource_group = "rg"
        settings.azure_job_fetch = "job-fetch"

        with pytest.raises(ServiceUnavailableError) as exc:
            await start_container_app_job("fetch", user_id="u1")
        assert exc.value.code == "AZURE_JOB_IMAGE_MISSING"
