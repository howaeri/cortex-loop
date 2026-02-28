from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from .utils import _as_string_list


class RequirementAuditEvaluation(NamedTuple):
    report: dict[str, Any] | None
    details: dict[str, Any] | None
    gap: bool
    missing: bool
    warnings: list[str]


def evaluate_requirement_audit_payload(
    payload: Any,
    *,
    require_requirement_audit: bool,
    require_evidence_for_passed_requirement: bool,
    required_requirement_ids: list[str],
    root: Path,
    witness: Mapping[str, list[str]] | None = None,
) -> RequirementAuditEvaluation:
    if payload is None:
        if require_requirement_audit:
            return RequirementAuditEvaluation(
                report=None,
                details=None,
                gap=False,
                missing=True,
                warnings=[
                    "No requirement_audit provided in Stop payload. Include requirement_audit to prove "
                    "prompt requirement coverage with evidence."
                ],
            )
        return RequirementAuditEvaluation(report=None, details=None, gap=False, missing=False, warnings=[])

    details = validate_requirement_audit(
        payload,
        require_evidence_for_passed_requirement=require_evidence_for_passed_requirement,
        required_requirement_ids=required_requirement_ids,
        root=root,
        witness=witness,
    )
    warnings: list[str] = []
    gap = not details["ok"]
    if gap:
        warnings.append("Requirement audit reported gaps: " + "; ".join(details.get("errors", [])))
    warnings.extend(f"Requirement audit note: {note}" for note in details.get("warnings", []))
    return RequirementAuditEvaluation(
        report=minimal_requirement_audit_report(details),
        details=details,
        gap=gap,
        missing=False,
        warnings=warnings,
    )


def minimal_requirement_audit_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(report.get("ok")),
        "errors": [str(v) for v in _as_string_list(report.get("errors"))],
        "missing_required_ids": [str(v) for v in _as_string_list(report.get("missing_required_ids"))],
        "item_count": int(report.get("item_count") or 0),
        "pass_count": int(report.get("pass_count") or 0),
        "fail_count": int(report.get("fail_count") or 0),
    }


def validate_requirement_audit(
    payload: Any,
    *,
    require_evidence_for_passed_requirement: bool,
    required_requirement_ids: list[str],
    root: Path,
    witness: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    pass_count = 0
    fail_count = 0
    unique_ids: set[str] = set()
    missing_required_ids: list[str] = []
    observed_commands = [_normalize_command(v) for v in _as_string_list((witness or {}).get("commands"))]
    observed_tools = {v.lower() for v in _as_string_list((witness or {}).get("tools"))}

    if not isinstance(payload, Mapping):
        return {
            "ok": False,
            "item_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "missing_required_ids": list(required_requirement_ids),
            "warnings": [],
            "errors": ["Invalid requirement_audit format; expected an object."],
        }

    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    if not items:
        errors.append("requirement_audit.items must be a non-empty list.")

    for idx, item in enumerate(items):
        if not isinstance(item, Mapping):
            errors.append(f"requirement_audit.items[{idx}] must be an object.")
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            errors.append(f"requirement_audit.items[{idx}] is missing a non-empty id.")
            continue
        if item_id in unique_ids:
            errors.append(f"requirement_audit.items[{idx}] has duplicate id '{item_id}'.")
        unique_ids.add(item_id)

        status = str(item.get("status") or "").strip().lower()
        if status == "pass":
            pass_count += 1
            evidence = _as_string_list(item.get("evidence"))
            if require_evidence_for_passed_requirement and not evidence:
                errors.append(f"requirement '{item_id}' is pass but has no evidence.")
            for evidence_ref in evidence:
                check = _evaluate_evidence_reference(
                    evidence_ref,
                    root=root,
                    observed_commands=observed_commands,
                    observed_tools=observed_tools,
                )
                if check["status"] == "unverified":
                    errors.append(f"requirement '{item_id}' evidence is unverified: {check['reason']}")
                elif check["status"] == "uncheckable":
                    warnings.append(f"requirement '{item_id}' evidence is uncheckable: {check['reason']}")
        elif status == "fail":
            fail_count += 1
            if not str(item.get("gap") or "").strip():
                errors.append(f"requirement '{item_id}' is fail but has no gap description.")
        else:
            errors.append(f"requirement '{item_id}' has invalid status '{status}' (expected pass|fail).")

    if required_requirement_ids:
        missing_required_ids = [rid for rid in required_requirement_ids if rid not in unique_ids]
        if missing_required_ids:
            errors.append("requirement_audit missing required ids: " + ", ".join(missing_required_ids))

    expected_verdict = "pass" if (items and fail_count == 0 and not errors) else "fail"
    completeness_verdict = payload.get("completeness_verdict")
    if completeness_verdict is not None:
        normalized_verdict = str(completeness_verdict).strip().lower()
        if normalized_verdict not in {"pass", "fail"}:
            errors.append("requirement_audit.completeness_verdict must be 'pass' or 'fail'.")
        elif normalized_verdict != expected_verdict:
            errors.append(
                f"requirement_audit.completeness_verdict={normalized_verdict} "
                f"does not match computed verdict={expected_verdict}."
            )

    return {
        "ok": len(errors) == 0 and fail_count == 0,
        "item_count": len(items),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "missing_required_ids": missing_required_ids,
        "warnings": warnings,
        "errors": errors,
    }


def _evaluate_evidence_reference(
    reference: str,
    *,
    root: Path,
    observed_commands: list[str],
    observed_tools: set[str],
) -> dict[str, str]:
    kind, claim = _classify_evidence_reference(reference, root=root)
    if kind == "path":
        path = _evidence_reference_path(reference, root)
        if path is not None and path.exists():
            return {"kind": "path", "status": "verified", "reason": "path exists"}
        return {
            "kind": "path",
            "status": "unverified",
            "reason": f"path does not exist: {path}",
        }

    if kind == "tool":
        if not observed_tools:
            return {"kind": "tool", "status": "uncheckable", "reason": "no observed tool events in session"}
        if claim in observed_tools:
            return {"kind": "tool", "status": "verified", "reason": f"tool observed: {claim}"}
        return {"kind": "tool", "status": "unverified", "reason": f"tool not observed: {claim}"}

    if kind == "command":
        if not observed_commands:
            return {
                "kind": "command",
                "status": "uncheckable",
                "reason": "no observed command events in session",
            }
        if claim and any((claim in cmd) or (cmd in claim) for cmd in observed_commands):
            return {"kind": "command", "status": "verified", "reason": "command matched session witness"}
        return {
            "kind": "command",
            "status": "unverified",
            "reason": "command not witnessed in session events",
        }

    return {"kind": "note", "status": "uncheckable", "reason": "reference is non-verifiable note text"}


def _classify_evidence_reference(reference: str, *, root: Path) -> tuple[str, str]:
    text = str(reference).strip()
    lower = text.lower()
    if lower.startswith("tool:"):
        return "tool", lower.split(":", 1)[1].strip()
    if lower.startswith("cmd:"):
        return "command", _normalize_command(text.split(":", 1)[1].strip())
    if _looks_like_command(text):
        return "command", _normalize_command(text)
    if _evidence_reference_path(text, root) is not None:
        return "path", text
    return "note", ""


def _evidence_reference_path(reference: str, root: Path) -> Path | None:
    text = str(reference).strip()
    if not text or text.startswith(("http://", "https://")):
        return None

    path_text = text.split("#", 1)[0].strip()
    if " " in path_text:
        first_token = path_text.split(None, 1)[0].strip()
        if first_token and (
            any(sep in first_token for sep in ("/", "\\"))
            or first_token.startswith((".", "~"))
        ):
            path_text = first_token
    path_text = re.sub(r":\d+(?::\d+|-\d+)?$", "", path_text).strip()
    path_text = path_text.rstrip(".,;:")
    if not path_text:
        return None
    if not any(sep in path_text for sep in ("/", "\\")) and not path_text.startswith((".", "~")):
        return None

    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _looks_like_command(text: str) -> bool:
    return bool(
        re.search(
            r"\b(pytest|npm|pnpm|yarn|npx|ruff|mypy|go test|cargo test|python\s+-m)\b",
            text.lower(),
        )
    )


def _normalize_command(text: str) -> str:
    value = text.strip().strip("`").lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[:\-]\s*(ok|pass|passed|success|succeeded)$", "", value).strip()
    return value
