from backend.web.utils.helpers import extract_webhook_instance_id


def test_extract_webhook_instance_id_prefers_top_level_value() -> None:
    payload = {
        "session_id": "sess-top",
        "data": {"session_id": "sess-nested"},
    }

    assert extract_webhook_instance_id(payload) == "sess-top"


def test_extract_webhook_instance_id_falls_back_to_nested_data() -> None:
    payload = {
        "event": "sandbox.started",
        "data": {"sandbox_id": "sbx-123"},
    }

    assert extract_webhook_instance_id(payload) == "sbx-123"


def test_extract_webhook_instance_id_skips_empty_or_non_string_values() -> None:
    payload = {
        "session_id": "",
        "sandbox_id": None,
        "instance_id": 123,
        "data": {"id": "inst-777"},
    }

    assert extract_webhook_instance_id(payload) == "inst-777"
