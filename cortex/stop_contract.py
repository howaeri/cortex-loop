from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .stop_payload import extract_stop_fields, resolve_stop_value
from .utils import _as_string_list

STOP_PAYLOAD_KEYS = (
    "challenge_coverage",
    "requirement_audit",
    "required_requirement_ids",
    "failed_approach",
)


@dataclass(slots=True)
class StopContract:
    warnings: list[str]
    challenge_coverage: Any
    requirement_audit: Any
    required_requirement_ids: list[str]
    failed_approach: dict[str, Any] | None
    structured_stop_violation: bool


def resolve_stop_contract(
    payload: Mapping[str, Any],
    *,
    allow_message_fallback: bool,
    require_structured_stop_payload: bool,
) -> StopContract:
    stop_fields, stop_fields_source, warnings = extract_stop_fields(
        payload, allow_message_fallback=allow_message_fallback
    )
    values = {
        key: resolve_stop_value(
            key=key,
            payload=payload,
            stop_fields=stop_fields,
            stop_fields_source=stop_fields_source,
            warnings=warnings,
            value_label=key,
        )
        for key in STOP_PAYLOAD_KEYS
    }

    used_message_stop_fallback = bool(
        stop_fields_source == "last_assistant_message"
        and stop_fields
        and any(payload.get(key) is None and key in stop_fields for key in STOP_PAYLOAD_KEYS)
    )
    has_structured_stop_source = (
        any(payload.get(key) is not None for key in STOP_PAYLOAD_KEYS)
        or stop_fields_source == "payload.cortex_stop"
    )
    structured_stop_violation = bool(require_structured_stop_payload and not has_structured_stop_source)
    if structured_stop_violation:
        if used_message_stop_fallback:
            warnings.append(
                "Structured stop payload is required; trailer-only CORTEX_STOP_JSON fallback is rejected."
            )
        else:
            warnings.append(
                "Structured stop payload is required; include stop fields directly or via payload.cortex_stop."
            )

    return StopContract(
        warnings=warnings,
        challenge_coverage=values["challenge_coverage"],
        requirement_audit=values["requirement_audit"],
        required_requirement_ids=_as_string_list(values["required_requirement_ids"]),
        failed_approach=_resolve_failed_approach(payload, values["failed_approach"], stop_fields=stop_fields),
        structured_stop_violation=structured_stop_violation,
    )


def _resolve_failed_approach(
    payload: Mapping[str, Any],
    failed_approach: Any,
    *,
    stop_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    summary = ""
    reason = ""
    files: list[str] = []

    if isinstance(failed_approach, Mapping):
        summary = str(
            failed_approach.get("summary")
            or failed_approach.get("what_was_tried")
            or failed_approach.get("approach")
            or ""
        ).strip()
        reason = str(failed_approach.get("reason") or failed_approach.get("why_failed") or "").strip()
        files = _as_string_list(failed_approach.get("files"))
    elif isinstance(failed_approach, str):
        summary = failed_approach.strip()

    if not summary:
        for key in ("what_was_tried", "failed_summary", "approach", "failed_approach_summary"):
            candidate = str(payload.get(key) or (stop_fields or {}).get(key) or "").strip()
            if candidate:
                summary = candidate
                break
    if not reason:
        for key in ("why_failed", "failure_reason", "reason"):
            candidate = str(payload.get(key) or (stop_fields or {}).get(key) or "").strip()
            if candidate:
                reason = candidate
                break
    if not files:
        files = (
            _as_string_list(payload.get("failed_files"))
            or _as_string_list(payload.get("files"))
            or _as_string_list(payload.get("target_files"))
            or _as_string_list((stop_fields or {}).get("failed_files"))
            or _as_string_list((stop_fields or {}).get("files"))
            or _as_string_list((stop_fields or {}).get("target_files"))
        )

    if not summary or not reason:
        return None
    return {"summary": summary, "reason": reason, "files": files}


def reconcile_required_requirement_ids(
    session_required_ids: list[str], stop_required_ids: list[str]
) -> tuple[list[str], str, str | None]:
    if session_required_ids:
        warning = (
            "Ignoring required_requirement_ids from Stop payload; using SessionStart contract."
            if stop_required_ids and set(stop_required_ids) != set(session_required_ids)
            else None
        )
        return list(session_required_ids), "session", warning
    if stop_required_ids:
        return (
            list(stop_required_ids),
            "stop_payload",
            "No SessionStart requirement contract found; using Stop-provided required_requirement_ids.",
        )
    return [], "none", None
