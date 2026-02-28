from __future__ import annotations

def compute_stop_outcome(
    *,
    mode: str,
    fail_on_missing_challenge_coverage: bool,
    fail_on_requirement_audit_gap: bool,
    require_requirement_audit: bool,
    challenge_ok: bool | None,
    invariant_ok: bool | None,
    invariant_recommend_revert: bool,
    missing_challenge_coverage: bool,
    requirement_audit_gap: bool,
    requirement_audit_missing: bool,
    structured_stop_violation: bool,
) -> tuple[str, bool]:
    strict_mode = mode == "strict"
    strict_challenge_gate = mode == "strict" and fail_on_missing_challenge_coverage
    challenge_gate_violation = strict_challenge_gate and (
        missing_challenge_coverage or challenge_ok is False
    )
    requirement_audit_violation = (
        strict_mode
        and fail_on_requirement_audit_gap
        and (requirement_audit_gap or (requirement_audit_missing and require_requirement_audit))
    )

    if invariant_ok is False:
        session_status = "failed_invariants"
    elif structured_stop_violation:
        session_status = "failed_stop_contract"
    elif requirement_audit_violation:
        session_status = "failed_requirements"
    elif challenge_ok is False:
        session_status = "failed_challenges"
    elif missing_challenge_coverage and strict_challenge_gate:
        session_status = "missing_challenge_coverage"
    else:
        session_status = "completed"

    recommend_revert = bool(
        invariant_recommend_revert
        or challenge_gate_violation
        or requirement_audit_violation
        or (strict_mode and structured_stop_violation)
    )
    return session_status, recommend_revert
