"""Kafka-disabled worker dispatch (Azure Jobs / inline)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.producers.events import publish_job_apply, publish_job_match
from app.workers.apply_worker import _otp_code_from_payload


def _kafka_disabled():
    return AsyncMock(
        side_effect=ServiceUnavailableError("Kafka is disabled (KAFKA_ENABLED=false)", code="KAFKA_DISABLED")
    )


@pytest.mark.asyncio
async def test_publish_job_apply_uses_azure_when_kafka_off():
    start = AsyncMock(return_value={"job_name": "job-apply", "execution": "exec-1"})
    with (
        patch("app.producers.events.publish", new=_kafka_disabled()),
        patch("app.producers.events.settings") as settings_mock,
        patch("app.services.azure_jobs.azure_job_available", return_value=True),
        patch("app.services.azure_jobs.start_container_app_job", new=start),
    ):
        settings_mock.app_env = "production"
        settings_mock.kafka_enabled = False

        mode = await publish_job_apply("u1", "j1", application_id="a1")

    assert mode == "azure-job"
    start.assert_awaited_once()
    kwargs = start.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["job_id"] == "j1"
    assert kwargs["application_id"] == "a1"


@pytest.mark.asyncio
async def test_publish_job_apply_inline_when_playwright_available():
    create_task = MagicMock()
    with (
        patch("app.producers.events.publish", new=_kafka_disabled()),
        patch("app.producers.events.settings") as settings_mock,
        patch("app.services.azure_jobs.azure_job_available", return_value=False),
        patch("app.automation.playwright_runtime.playwright_available", return_value=True),
        patch("app.producers.events.asyncio.create_task", create_task),
    ):
        settings_mock.app_env = "development"
        settings_mock.kafka_enabled = False

        mode = await publish_job_apply("u1", "j1", application_id="a1")

    assert mode == "inline"
    create_task.assert_called_once()
    create_task.call_args[0][0].close()


@pytest.mark.asyncio
async def test_publish_job_apply_fails_without_runtime():
    with (
        patch("app.producers.events.publish", new=_kafka_disabled()),
        patch("app.producers.events.settings") as settings_mock,
        patch("app.services.azure_jobs.azure_job_available", return_value=False),
        patch("app.automation.playwright_runtime.playwright_available", return_value=False),
        patch(
            "app.automation.playwright_runtime.playwright_unavailable_message",
            return_value="Playwright is unavailable",
        ),
    ):
        settings_mock.app_env = "production"
        settings_mock.kafka_enabled = False

        with pytest.raises(ServiceUnavailableError) as exc:
            await publish_job_apply("u1", "j1")
        assert exc.value.code == "PLAYWRIGHT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_publish_job_match_runs_inline_when_kafka_off():
    with (
        patch("app.producers.events.publish", new=_kafka_disabled()),
        patch("app.producers.events.settings") as settings_mock,
        patch("app.producers.events._inline_match", new=AsyncMock()) as inline,
    ):
        settings_mock.app_env = "production"
        settings_mock.kafka_enabled = False

        mode = await publish_job_match("u1", "j1", wait=True)

    assert mode == "inline"
    inline.assert_awaited_once()


def test_otp_code_reads_session_step_and_clears_it():
    app = MagicMock()
    app.session_steps = [
        {"key": "otp_provided", "metadata": {"otp_code": "123456", "code_len": 6}},
    ]
    assert _otp_code_from_payload({}, app) == "123456"
    assert "otp_code" not in app.session_steps[0]["metadata"]
    assert _otp_code_from_payload({"otp_code": "999"}, app) == "999"
