from __future__ import annotations

import json

from cortex.challenges import ChallengeEnforcer
from cortex.genome import ChallengesConfig


def _coverage_all_true() -> dict[str, bool]:
    return {
        "null_inputs": True,
        "boundary_values": True,
        "error_handling": True,
        "graveyard_regression": True,
    }


def test_all_categories_covered_is_ok(store) -> None:
    enforcer = ChallengeEnforcer(store, ChallengesConfig())
    report = enforcer.evaluate("sess-1", _coverage_all_true())
    assert report.ok is True
    assert report.missing_categories == []
    assert all(r.covered for r in report.results)


def test_missing_category_returns_missing_list(store) -> None:
    enforcer = ChallengeEnforcer(store, ChallengesConfig())
    coverage = _coverage_all_true()
    coverage["graveyard_regression"] = False
    report = enforcer.evaluate("sess-1", coverage)
    assert report.ok is False
    assert report.missing_categories == ["graveyard_regression"]


def test_coerce_coverage_variants() -> None:
    covered, evidence = ChallengeEnforcer._coerce_coverage(True)
    assert covered is True and evidence == {}
    covered, evidence = ChallengeEnforcer._coerce_coverage({"covered": True, "tests": ["x"]})
    assert covered is True and evidence == {"tests": ["x"]}
    covered, evidence = ChallengeEnforcer._coerce_coverage(None)
    assert covered is False and evidence == {}


def test_store_records_results(store) -> None:
    enforcer = ChallengeEnforcer(store, ChallengesConfig())
    enforcer.evaluate("sess-1", _coverage_all_true())
    with store.connection() as conn:
        rows = conn.execute(
            "SELECT category, covered, evidence_json FROM challenge_results WHERE session_id = ?",
            ("sess-1",),
        ).fetchall()
    assert len(rows) == 4
    assert {row["category"] for row in rows} == {
        "null_inputs",
        "boundary_values",
        "error_handling",
        "graveyard_regression",
    }
    assert all(row["covered"] == 1 for row in rows)
    assert all(isinstance(json.loads(row["evidence_json"]), dict) for row in rows)


def test_config_audit_warns_when_builtin_categories_missing(store) -> None:
    cfg = ChallengesConfig(active_categories=["null_inputs", "error_handling"], require_coverage=True)
    enforcer = ChallengeEnforcer(store, cfg)

    report = enforcer.evaluate("sess-2", {"null_inputs": True, "error_handling": True})

    assert report.ok is True
    assert report.config_warnings
    assert "boundary_values" in report.config_warnings[0]
    assert "graveyard_regression" in report.config_warnings[0]
