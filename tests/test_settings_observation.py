import json

import pytest

from backend.web.routers import settings as settings_router
from backend.web.routers.settings import ObservationRequest, update_observation_settings


@pytest.mark.asyncio
async def test_update_observation_settings_replaces_provider_payload_for_field_clears(tmp_path, monkeypatch):
    observation_file = tmp_path / "observation.json"
    monkeypatch.setattr(settings_router, "OBSERVATION_FILE", observation_file)

    await update_observation_settings(
        ObservationRequest(
            active="langfuse",
            langfuse={
                "secret_key": "sk-live-1",
                "public_key": "pk-live-1",
                "host": "https://cloud.langfuse.com",
            },
        )
    )

    await update_observation_settings(
        ObservationRequest(
            active="langfuse",
            langfuse={
                "public_key": "pk-live-1",
            },
        )
    )

    payload = json.loads(observation_file.read_text(encoding="utf-8"))
    assert payload["active"] == "langfuse"
    assert payload["langfuse"] == {"public_key": "pk-live-1"}
