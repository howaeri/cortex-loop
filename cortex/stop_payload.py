from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


def extract_stop_fields(
    payload: Mapping[str, Any], *, allow_message_fallback: bool = True
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    warnings: list[str] = []

    raw = payload.get("cortex_stop")
    if isinstance(raw, Mapping):
        return {str(k): v for k, v in raw.items()}, "payload.cortex_stop", warnings
    if raw is not None:
        warnings.append("Ignoring invalid cortex_stop field; expected an object.")

    if not allow_message_fallback:
        return None, None, warnings

    last_message = payload.get("last_assistant_message")
    if isinstance(last_message, str):
        parsed, marker_found, error = parse_cortex_stop_json(last_message)
        if parsed is not None:
            return parsed, "last_assistant_message", warnings
        if marker_found and error:
            warnings.append(f"Ignoring invalid CORTEX_STOP_JSON trailer: {error}")

    return None, None, warnings


def resolve_stop_value(
    *,
    key: str,
    payload: Mapping[str, Any],
    stop_fields: dict[str, Any] | None,
    stop_fields_source: str | None,
    warnings: list[str],
    value_label: str,
) -> Any:
    value = payload.get(key)
    if value is not None or not (stop_fields and key in stop_fields):
        return value
    value = stop_fields[key]
    if stop_fields_source == "last_assistant_message":
        warnings.append(f"Using {value_label} parsed from last assistant message (CORTEX_STOP_JSON).")
    elif stop_fields_source == "payload.cortex_stop":
        warnings.append(f"Using {value_label} from payload.cortex_stop.")
    return value


def parse_cortex_stop_json(text: str) -> tuple[dict[str, Any] | None, bool, str | None]:
    for pattern in (
        r"```(?:cortex-stop|cortex_stop)\s*(\{.*?\})\s*```",
        r"```json\s*(\{.*?\"challenge_coverage\".*?\})\s*```",
    ):
        match = re.search(pattern, text, flags=re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            return None, True, str(exc)
        if not isinstance(parsed, dict):
            return None, True, "expected a JSON object"
        return parsed, True, None

    marker = "CORTEX_STOP_JSON:"
    idx = text.rfind(marker)
    if idx == -1:
        return None, False, None
    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(text[idx + len(marker) :].lstrip())
    except json.JSONDecodeError as exc:
        return None, True, str(exc)
    if not isinstance(parsed, dict):
        return None, True, "expected a JSON object"
    return parsed, True, None
