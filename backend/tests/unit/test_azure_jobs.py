"""Azure Container Apps job trigger helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.services.azure_jobs import azure_jobs_configured, start_container_app_job


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


@pytest.mark.asyncio
async def test_start_container_app_job_posts_arm():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b'{"name":"exec-1"}'
    mock_response.json = lambda: {"name": "exec-1"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

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
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert "jobs/job-fetch/start" in args[0]
        env = kwargs["json"]["containers"][0]["env"]
        assert {"name": "JOB_USER_ID", "value": "u1"} in env
        assert {"name": "JOB_PORTAL", "value": "linkedin"} in env


@pytest.mark.asyncio
async def test_start_container_app_job_raises_on_http_error():
    mock_response = AsyncMock()
    mock_response.status_code = 403
    mock_response.content = b"forbidden"
    mock_response.text = "forbidden"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

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
