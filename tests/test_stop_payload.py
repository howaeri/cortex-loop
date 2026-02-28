from __future__ import annotations

from cortex.stop_payload import extract_stop_fields, parse_cortex_stop_json


def test_extract_stop_fields_prefers_structured_payload() -> None:
    fields, source, warnings = extract_stop_fields(
        {
            "cortex_stop": {
                "challenge_coverage": {
                    "null_inputs": True,
                }
            },
            "last_assistant_message": 'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":false}}',
        }
    )
    assert source == "payload.cortex_stop"
    assert fields is not None
    assert fields["challenge_coverage"]["null_inputs"] is True
    assert warnings == []


def test_extract_stop_fields_can_disable_message_fallback() -> None:
    fields, source, warnings = extract_stop_fields(
        {"last_assistant_message": 'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true}}'},
        allow_message_fallback=False,
    )
    assert fields is None
    assert source is None
    assert warnings == []


def test_parse_cortex_stop_json_reports_invalid_trailer() -> None:
    parsed, marker_found, error = parse_cortex_stop_json('CORTEX_STOP_JSON: {"challenge_coverage":')
    assert parsed is None
    assert marker_found is True
    assert error
