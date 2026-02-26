from backend.web.utils.serializers import extract_text_content, serialize_message


class _DummyMessage:
    content = "hello"
    tool_calls = [{"name": "calc"}]
    tool_call_id = "call-1"


def test_extract_text_content_joins_text_blocks_and_plain_strings() -> None:
    raw_content = [
        {"type": "text", "text": "alpha"},
        {"type": "image", "url": "x"},
        "beta",
        {"type": "text", "text": "gamma"},
        123,
    ]

    assert extract_text_content(raw_content) == "alphabetagamma"


def test_extract_text_content_falls_back_to_string_conversion() -> None:
    assert extract_text_content({"k": "v"}) == "{'k': 'v'}"


def test_serialize_message_includes_expected_fields() -> None:
    out = serialize_message(_DummyMessage())

    assert out == {
        "type": "_DummyMessage",
        "id": None,
        "content": "hello",
        "tool_calls": [{"name": "calc"}],
        "tool_call_id": "call-1",
    }
