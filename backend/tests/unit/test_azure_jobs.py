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


def _mock_client(*, post_status=200, post_body=None):
    get_response = AsyncMock()
    get_response.status_code = 200
    get_response.json = lambda: {
        "properties": {
            "template": {
                "containers": [
                    {
                        "name": "job-fetch",
                        "image": "example.azurecr.io/jobpilot-api:latest",
                    }
                ]
            }
        }
    }

    post_response = AsyncMock()
    post_response.status_code = post_status
    post_response.content = b'{"name":"exec-1"}' if post_body is None else post_body
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
        env = container["env"]
        assert {"name": "JOB_USER_ID", "value": "u1"} in env
        assert {"name": "JOB_PORTAL", "value": "linkedin"} in env


@pytest.mark.asyncio
async def test_start_container_app_job_raises_on_http_error():
    mock_client = _mock_client(post_status=403, post_body=b"forbidden")

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
    get_response = AsyncMock()
    get_response.status_code = 200
    get_response.json = lambda: {"properties": {"template": {"containers": [{"name": "job-fetch"}]}}}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = get_response

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
