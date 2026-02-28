from __future__ import annotations

from cortex.stop_policy import compute_stop_outcome


def test_compute_stop_outcome_blocks_on_strict_structured_violation() -> None:
    session_status, recommend_revert = compute_stop_outcome(
        mode="strict",
        fail_on_missing_challenge_coverage=False,
        fail_on_requirement_audit_gap=False,
        require_requirement_audit=False,
        challenge_ok=True,
        invariant_ok=True,
        invariant_recommend_revert=False,
        missing_challenge_coverage=False,
        requirement_audit_gap=False,
        requirement_audit_missing=False,
        structured_stop_violation=True,
    )
    assert session_status == "failed_stop_contract"
    assert recommend_revert is True


def test_compute_stop_outcome_respects_advisory_mode_for_structured_violation() -> None:
    session_status, recommend_revert = compute_stop_outcome(
        mode="advisory",
        fail_on_missing_challenge_coverage=False,
        fail_on_requirement_audit_gap=False,
        require_requirement_audit=False,
        challenge_ok=True,
        invariant_ok=True,
        invariant_recommend_revert=False,
        missing_challenge_coverage=False,
        requirement_audit_gap=False,
        requirement_audit_missing=False,
        structured_stop_violation=True,
    )
    assert session_status == "failed_stop_contract"
    assert recommend_revert is False
