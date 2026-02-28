from __future__ import annotations

import json
from pathlib import Path

from cortex.core import CortexKernel
from cortex.repomap import RepoMapArtifact, RepoMapRunResult


def test_on_session_start_returns_structure_and_records_session(kernel: CortexKernel) -> None:
    result = kernel.on_session_start(
        {"session_id": "sess-core", "objective": "Add validation", "target_files": ["src/api.py"]}
    )
    assert result["ok"] is True
    assert result["hook"] == "SessionStart"
    assert result["session_id"] == "sess-core"
    assert "foundation" in result
    assert "graveyard_matches" in result
    assert "repomap" in result
    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT status, genome_path FROM sessions WHERE session_id = ?",
            ("sess-core",),
        ).fetchone()
    assert row["status"] == "running"
    assert row["genome_path"].endswith("cortex.toml")


def test_on_session_start_includes_graveyard_explainability_warning(kernel: CortexKernel) -> None:
    kernel.graveyard.record_failure(
        session_id="sess-prev",
        summary="Removed null guard in parser",
        reason="Null payload crashed parser",
        files=["src/parser.py"],
    )

    result = kernel.on_session_start(
        {
            "session_id": "sess-with-graveyard-match",
            "objective": "Fix parser null payload crash",
            "target_files": ["src/parser.py"],
        }
    )

    assert result["graveyard_matches"]
    assert any("Top graveyard match" in warning for warning in result["warnings"])


def test_on_session_start_persists_requirement_contract_ids(kernel: CortexKernel) -> None:
    result = kernel.on_session_start(
        {
            "session_id": "sess-contract",
            "objective": "Validate contract storage",
            "required_requirement_ids": ["R1", "R1", "R2"],
        }
    )
    assert result["required_requirement_ids"] == ["R1", "R2"]
    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT metadata_json FROM sessions WHERE session_id = ?",
            ("sess-contract",),
        ).fetchone()
    metadata = json.loads(row["metadata_json"])
    assert metadata["required_requirement_ids"] == ["R1", "R2"]


def test_on_session_start_includes_repomap_metadata_and_records_event(
    kernel: CortexKernel, tmp_project: Path
) -> None:
    (tmp_project / "src" / "api.py").write_text("class API:\n    pass\n", encoding="utf-8")

    result = kernel.on_session_start(
        {"session_id": "sess-repomap", "objective": "Add validation", "target_files": ["src/api.py"]}
    )

    assert result["ok"] is True
    assert result["hook"] == "SessionStart"
    assert result["repomap"]["ok"] is True
    assert "text" not in result["repomap"]
    assert result["repomap"]["top_ranked_files"]
    assert "src/api.py" in result["repomap"]["top_ranked_files"]
    assert result["repomap"]["artifact_path"]
    assert Path(result["repomap"]["artifact_path"]).exists()

    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT status, payload_json FROM events WHERE session_id = ? AND hook = ? ORDER BY id DESC LIMIT 1",
            ("sess-repomap", "RepoMap"),
        ).fetchone()
    assert row["status"] == "ok"
    payload = json.loads(row["payload_json"])
    assert payload["trigger"] == "SessionStart"
    assert payload["ok"] is True
    assert "text" not in payload


def test_on_session_start_repomap_failure_is_non_blocking(
    kernel: CortexKernel, monkeypatch
) -> None:
    import cortex.repomap as repomap_module

    def _fake_run_repomap(**_: object) -> RepoMapRunResult:
        artifact = RepoMapArtifact(
            ok=False,
            generated_at="2026-02-26T00:00:00Z",
            provenance={
                "method": "none",
                "source_root": str(kernel.ctx.root),
                "scope": ["src"],
                "focus_files": [],
                "duration_ms": 1,
                "timeout_ms": 1800,
            },
            stats={"files_parsed": 0, "symbols_found": 0, "graph_edges": 0, "byte_count": 0},
            ranking=[],
            text="",
            error={
                "code": "deps_missing",
                "message": "Missing optional repo-map deps",
                "retryable": True,
                "failed_stage": "dependency_check",
            },
        )
        return RepoMapRunResult(artifact=artifact)

    monkeypatch.setattr(repomap_module, "run_repomap", _fake_run_repomap)

    result = kernel.on_session_start({"session_id": "sess-repomap-fail", "objective": "Start"})

    assert result["ok"] is True
    assert "foundation" in result
    assert "graveyard_matches" in result
    assert result["repomap"]["ok"] is False
    assert result["repomap"]["error"]["code"] == "deps_missing"
    assert "text" not in result["repomap"]
    assert any("Repo-map warning:" in warning for warning in result["warnings"])

    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT status, payload_json FROM events WHERE session_id = ? AND hook = ? ORDER BY id DESC LIMIT 1",
            ("sess-repomap-fail", "RepoMap"),
        ).fetchone()
    assert row["status"] == "error"
    payload = json.loads(row["payload_json"])
    assert payload["trigger"] == "SessionStart"
    assert payload["error"]["code"] == "deps_missing"


def test_on_session_start_repomap_timeout_is_non_blocking(
    kernel: CortexKernel, tmp_project: Path
) -> None:
    (tmp_project / "src" / "api.py").write_text("class API:\n    pass\n", encoding="utf-8")
    kernel.ctx.genome.repomap.session_start_timeout_ms = 0

    result = kernel.on_session_start({"session_id": "sess-repomap-timeout", "objective": "Start"})

    assert result["ok"] is True
    assert "foundation" in result
    assert "graveyard_matches" in result
    assert result["repomap"]["ok"] is False
    assert result["repomap"]["error"]["code"] == "timeout"
    assert any("Repo-map warning:" in warning for warning in result["warnings"])


def test_on_stop_records_graveyard_and_challenge_results(kernel: CortexKernel) -> None:
    kernel.on_session_start({"session_id": "sess-stop", "objective": "Handle bad input"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": False,
            },
            "failed_approach": {
                "summary": "Accepted missing body",
                "reason": "Parser crashed on empty payload",
                "files": ["src/api.py"],
            },
        }
    )
    assert stop["hook"] == "Stop"
    assert stop["recommend_revert"] is False
    assert stop["challenge_report"]["ok"] is False
    assert stop["challenge_report"]["missing_categories"] == ["graveyard_regression"]
    with kernel.ctx.store.connection() as conn:
        graveyard_row = conn.execute("SELECT * FROM graveyard WHERE session_id = ?", ("sess-stop",)).fetchone()
        session_row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", ("sess-stop",)).fetchone()
        challenge_rows = conn.execute(
            "SELECT COUNT(*) AS n FROM challenge_results WHERE session_id = ?",
            ("sess-stop",),
        ).fetchone()
    assert graveyard_row["summary"] == "Accepted missing body"
    assert json.loads(graveyard_row["files_json"]) == ["src/api.py"]
    assert session_row["status"] == "failed_challenges"
    assert session_row["ended_at"]
    assert challenge_rows["n"] == 4


def test_pre_tool_use_backfills_session_row_when_session_start_missing(kernel: CortexKernel) -> None:
    result = kernel.on_pre_tool_use(
        {
            "session_id": "sess-backfill",
            "tool_name": "Read",
            "target_files": ["src/api.py"],
        }
    )
    assert result["ok"] is True
    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT status, genome_path, metadata_json FROM sessions WHERE session_id = ?",
            ("sess-backfill",),
        ).fetchone()
        events = conn.execute(
            "SELECT COUNT(*) AS n FROM events WHERE session_id = ? AND hook = ?",
            ("sess-backfill", "PreToolUse"),
        ).fetchone()
    assert row["status"] == "running"
    assert row["genome_path"].endswith("cortex.toml")
    assert json.loads(row["metadata_json"])["auto_started"] is True
    assert events["n"] == 1


def test_on_pre_tool_use_normalizes_tool_alias_via_adapter(kernel: CortexKernel) -> None:
    kernel.on_pre_tool_use(
        {
            "session_id": "sess-tool-alias",
            "tool": "Edit",
            "target_files": ["src/api.py"],
        }
    )
    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT tool_name, payload_json FROM events WHERE session_id = ? AND hook = ? ORDER BY id DESC LIMIT 1",
            ("sess-tool-alias", "PreToolUse"),
        ).fetchone()
    assert row["tool_name"] == "Edit"
    payload = json.loads(row["payload_json"])
    assert payload["tool_name"] == "Edit"


def test_post_tool_use_includes_graveyard_explainability_warning(kernel: CortexKernel) -> None:
    kernel.graveyard.record_failure(
        session_id="sess-prev",
        summary="Write path update broke parser",
        reason="Unhandled empty payload branch",
        files=["src/parser.py"],
    )
    kernel.on_session_start({"session_id": "sess-post-graveyard", "objective": "Patch parser"})
    result = kernel.on_post_tool_use(
        {
            "session_id": "sess-post-graveyard",
            "tool_name": "Write",
            "status": "error",
            "error": "Unhandled empty payload branch in parser",
            "target_files": ["src/parser.py"],
        }
    )

    assert result["hook"] == "PostToolUse"
    assert any("Top graveyard match" in warning for warning in result["warnings"])


def test_on_stop_without_challenge_coverage_skips_recording_not_false_zeros(kernel: CortexKernel) -> None:
    kernel.on_session_start({"session_id": "sess-stop-missing-coverage", "objective": "Do work"})
    stop = kernel.on_stop({"session_id": "sess-stop-missing-coverage", "run_invariants": False})

    assert stop["hook"] == "Stop"
    assert stop["challenge_report"] is None
    assert stop["challenge_coverage_missing"] is True
    assert any("No challenge_coverage provided" in warning for warning in stop["warnings"])

    with kernel.ctx.store.connection() as conn:
        challenge_rows = conn.execute(
            "SELECT COUNT(*) AS n FROM challenge_results WHERE session_id = ?",
            ("sess-stop-missing-coverage",),
        ).fetchone()
        session_row = conn.execute(
            "SELECT status, metadata_json FROM sessions WHERE session_id = ?",
            ("sess-stop-missing-coverage",),
        ).fetchone()

    assert challenge_rows["n"] == 0
    assert session_row["status"] == "completed"
    assert json.loads(session_row["metadata_json"])["challenge_coverage_missing"] is True


def test_on_stop_warns_when_builtin_challenge_categories_are_not_active(kernel: CortexKernel) -> None:
    kernel.ctx.genome.challenges.active_categories = ["null_inputs", "error_handling"]
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-builtin-audit",
            "run_invariants": False,
            "challenge_coverage": {"null_inputs": True, "error_handling": True},
        }
    )

    assert stop["hook"] == "Stop"
    assert stop["challenge_report"]["ok"] is True
    assert any("Built-in challenge categories missing" in warning for warning in stop["warnings"])


def test_on_stop_parses_cortex_stop_json_from_last_assistant_message(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.allow_message_stop_fallback = True
    kernel.on_session_start({"session_id": "sess-stop-embedded", "objective": "Validate payloads"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-embedded",
            "run_invariants": False,
            "last_assistant_message": (
                "Done.\n"
                'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,'
                '"error_handling":true,"graveyard_regression":true},"failed_approach":{"summary":"Tried '
                'single-pass parser","reason":"Missed malformed branch","files":["src/parser.py"]}}'
            ),
        }
    )

    assert stop["hook"] == "Stop"
    assert stop["challenge_coverage_missing"] is False
    assert stop["challenge_report"]["ok"] is True
    assert any("CORTEX_STOP_JSON" in warning for warning in stop["warnings"])

    with kernel.ctx.store.connection() as conn:
        graveyard_row = conn.execute(
            "SELECT summary, reason, files_json FROM graveyard WHERE session_id = ?",
            ("sess-stop-embedded",),
        ).fetchone()
        challenge_rows = conn.execute(
            "SELECT COUNT(*) AS n FROM challenge_results WHERE session_id = ?",
            ("sess-stop-embedded",),
        ).fetchone()

    assert graveyard_row["summary"] == "Tried single-pass parser"
    assert json.loads(graveyard_row["files_json"]) == ["src/parser.py"]
    assert challenge_rows["n"] == 4


def test_on_stop_trailer_only_blocked_when_structured_stop_required_in_strict_mode(
    kernel: CortexKernel,
) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_missing_challenge_coverage = True
    kernel.ctx.genome.hooks.require_structured_stop_payload = True
    kernel.ctx.genome.hooks.allow_message_stop_fallback = True
    kernel.on_session_start({"session_id": "sess-stop-structured-required", "objective": "Validate contract"})

    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-structured-required",
            "run_invariants": False,
            "last_assistant_message": (
                "Done.\n"
                'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,'
                '"error_handling":true,"graveyard_regression":true}}'
            ),
        }
    )

    assert stop["structured_stop_violation"] is True
    assert stop["recommend_revert"] is True
    assert stop["proceed"] is False
    assert any("Structured stop payload is required" in w for w in stop["warnings"])

    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT status, metadata_json FROM sessions WHERE session_id = ?",
            ("sess-stop-structured-required",),
        ).fetchone()
    assert row["status"] == "failed_stop_contract"
    metadata = json.loads(row["metadata_json"])
    assert metadata["structured_stop_violation"] is True


def test_on_stop_ignores_message_fallback_when_disabled(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.allow_message_stop_fallback = False
    kernel.on_session_start({"session_id": "sess-stop-fallback-off", "objective": "Validate fallback policy"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-fallback-off",
            "run_invariants": False,
            "last_assistant_message": (
                'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,'
                '"error_handling":true,"graveyard_regression":true}}'
            ),
        }
    )

    assert stop["challenge_report"] is None
    assert stop["challenge_coverage_missing"] is True
    assert stop["structured_stop_violation"] is False
    assert not any("Using challenge_coverage parsed from last assistant message" in w for w in stop["warnings"])


def test_on_stop_requires_structured_payload_when_configured(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.require_structured_stop_payload = True
    kernel.on_session_start({"session_id": "sess-stop-structured-missing", "objective": "Contract check"})
    stop = kernel.on_stop({"session_id": "sess-stop-structured-missing", "run_invariants": False})

    assert stop["structured_stop_violation"] is True
    assert stop["recommend_revert"] is True
    assert any("Structured stop payload is required" in w for w in stop["warnings"])


def test_on_stop_records_graveyard_from_top_level_failure_fields(kernel: CortexKernel) -> None:
    kernel.on_session_start({"session_id": "sess-stop-top-level-failure", "objective": "Implement parser"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-top-level-failure",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "what_was_tried": "Used single-pass regex parser",
            "why_failed": "Edge cases with nested blocks were skipped",
            "failed_files": ["src/parser.py", "src/tokenizer.py"],
        }
    )

    assert stop["hook"] == "Stop"
    with kernel.ctx.store.connection() as conn:
        row = conn.execute(
            "SELECT summary, reason, files_json FROM graveyard WHERE session_id = ?",
            ("sess-stop-top-level-failure",),
        ).fetchone()
    assert row is not None
    assert row["summary"] == "Used single-pass regex parser"
    assert row["reason"] == "Edge cases with nested blocks were skipped"
    assert json.loads(row["files_json"]) == ["src/parser.py", "src/tokenizer.py"]


def test_on_stop_requirement_audit_gap_blocks_in_strict_mode(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True
    kernel.ctx.genome.hooks.require_evidence_for_passed_requirement = True

    kernel.on_session_start({"session_id": "sess-stop-req-gap", "objective": "Validate contract"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-gap",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": []}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["hook"] == "Stop"
    assert stop["requirement_audit_gap"] is True
    assert stop["requirement_audit_missing"] is False
    assert stop["requirement_audit_report"]["ok"] is False
    assert any("no evidence" in err for err in stop["requirement_audit_report"]["errors"])
    assert stop["recommend_revert"] is True
    assert stop["proceed"] is False

    with kernel.ctx.store.connection() as conn:
        session_row = conn.execute(
            "SELECT status, metadata_json FROM sessions WHERE session_id = ?",
            ("sess-stop-req-gap",),
        ).fetchone()
    assert session_row["status"] == "failed_requirements"
    metadata = json.loads(session_row["metadata_json"])
    assert metadata["requirement_audit_ok"] is False
    assert metadata["requirement_audit_gap"] is True


def test_on_stop_missing_requirement_audit_blocks_when_required(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.require_requirement_audit = True
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True

    kernel.on_session_start({"session_id": "sess-stop-req-missing", "objective": "Validate contract"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-missing",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
        }
    )

    assert stop["requirement_audit_report"] is None
    assert stop["requirement_audit_missing"] is True
    assert stop["requirement_audit_gap"] is False
    assert stop["recommend_revert"] is True
    assert stop["proceed"] is False
    assert any("No requirement_audit provided" in warning for warning in stop["warnings"])

    with kernel.ctx.store.connection() as conn:
        session_row = conn.execute(
            "SELECT status, metadata_json FROM sessions WHERE session_id = ?",
            ("sess-stop-req-missing",),
        ).fetchone()
    assert session_row["status"] == "failed_requirements"
    metadata = json.loads(session_row["metadata_json"])
    assert metadata["requirement_audit_ok"] is None
    assert metadata["requirement_audit_missing"] is True


def test_on_stop_parses_requirement_audit_from_cortex_stop_json(kernel: CortexKernel) -> None:
    (kernel.ctx.root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    kernel.ctx.genome.hooks.allow_message_stop_fallback = True
    kernel.on_session_start({"session_id": "sess-stop-req-embedded", "objective": "Validate payloads"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-embedded",
            "run_invariants": False,
            "last_assistant_message": (
                "Done.\n"
                'CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,'
                '"error_handling":true,"graveyard_regression":true},"required_requirement_ids":["R1"],'
                '"requirement_audit":{"items":[{"id":"R1",'
                '"status":"pass","evidence":["src/app.py:10"]}],"completeness_verdict":"pass"}}'
            ),
        }
    )

    assert stop["hook"] == "Stop"
    assert stop["challenge_report"]["ok"] is True
    assert stop["requirement_audit_missing"] is False
    assert stop["requirement_audit_gap"] is False
    assert stop["required_requirement_ids"] == ["R1"]
    assert stop["requirement_audit_report"]["ok"] is True
    assert set(stop["requirement_audit_report"].keys()) == {
        "ok",
        "errors",
        "missing_required_ids",
        "item_count",
        "pass_count",
        "fail_count",
    }
    assert any("requirement_audit parsed from last assistant message" in w for w in stop["warnings"])


def test_on_stop_requirement_audit_enforces_required_ids(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True
    (kernel.ctx.root / "src" / "api.py").write_text("print('ok')\n", encoding="utf-8")

    kernel.on_session_start(
        {
            "session_id": "sess-stop-req-ids",
            "objective": "Validate contract",
            "required_requirement_ids": ["R1", "R2"],
        }
    )
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-ids",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": ["src/api.py:1"]}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_gap"] is True
    assert stop["recommend_revert"] is True
    assert stop["required_requirement_ids"] == ["R1", "R2"]
    assert stop["requirement_audit_report"]["missing_required_ids"] == ["R2"]
    assert any("missing required ids" in err for err in stop["requirement_audit_report"]["errors"])


def test_on_stop_ignores_conflicting_stop_requirement_ids_when_session_contract_exists(
    kernel: CortexKernel,
) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True
    (kernel.ctx.root / "src" / "api.py").write_text("print('ok')\n", encoding="utf-8")

    kernel.on_session_start(
        {
            "session_id": "sess-stop-req-conflict",
            "objective": "Validate contract",
            "required_requirement_ids": ["R1", "R2"],
        }
    )
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-conflict",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "required_requirement_ids": ["R1"],
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": ["src/api.py:1"]}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["required_requirement_ids"] == ["R1", "R2"]
    assert stop["requirement_audit_gap"] is True
    assert stop["recommend_revert"] is True
    assert any(
        "Ignoring required_requirement_ids from Stop payload" in warning
        for warning in stop["warnings"]
    )


def test_on_stop_requirement_gap_warns_but_does_not_block_in_advisory_mode(
    kernel: CortexKernel,
) -> None:
    kernel.ctx.genome.hooks.mode = "advisory"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True
    (kernel.ctx.root / "src" / "api.py").write_text("print('ok')\n", encoding="utf-8")

    kernel.on_session_start(
        {
            "session_id": "sess-stop-req-advisory",
            "objective": "Validate contract",
            "required_requirement_ids": ["R1", "R2"],
        }
    )
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-advisory",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": ["src/api.py:1"]}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_gap"] is True
    assert stop["recommend_revert"] is False
    assert stop["proceed"] is True
    assert any("Requirement audit reported gaps:" in warning for warning in stop["warnings"])
    with kernel.ctx.store.connection() as conn:
        session_row = conn.execute(
            "SELECT status FROM sessions WHERE session_id = ?",
            ("sess-stop-req-advisory",),
        ).fetchone()
    assert session_row["status"] == "completed"


def test_on_stop_requirement_audit_validates_evidence_paths(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True

    kernel.on_session_start({"session_id": "sess-stop-req-evidence", "objective": "Validate evidence"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-evidence",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [
                    {"id": "R1", "status": "pass", "evidence": ["src/does-not-exist.py:7"]},
                    {"id": "R2", "status": "pass", "evidence": ["npm run build: ok"]},
                ],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_gap"] is True
    assert stop["recommend_revert"] is True
    assert any(
        "path does not exist" in err for err in stop["requirement_audit_report"]["errors"]
    )


def test_on_stop_requirement_audit_accepts_common_path_evidence_formats(kernel: CortexKernel) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True
    (kernel.ctx.root / "src").mkdir(parents=True, exist_ok=True)
    (kernel.ctx.root / "src" / "ok.py").write_text("print('ok')\n", encoding="utf-8")

    kernel.on_session_start(
        {"session_id": "sess-stop-req-evidence-fmt", "objective": "Validate evidence formats"}
    )
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-evidence-fmt",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [
                    {
                        "id": "R1",
                        "status": "pass",
                        "evidence": [
                            "src/ok.py:1-2",
                            "src/ok.py updated import ordering",
                        ],
                    }
                ],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_gap"] is False
    assert stop["requirement_audit_report"]["ok"] is True


def test_on_stop_requirement_audit_unverified_command_blocks_in_strict_mode(
    kernel: CortexKernel,
) -> None:
    kernel.ctx.genome.hooks.mode = "strict"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True

    kernel.on_session_start({"session_id": "sess-stop-req-cmd-strict", "objective": "Validate commands"})
    kernel.on_pre_tool_use(
        {
            "session_id": "sess-stop-req-cmd-strict",
            "tool_name": "Bash",
            "command": "npm run build",
        }
    )
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-cmd-strict",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": ["cmd:pytest -q"]}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_gap"] is True
    assert stop["recommend_revert"] is True
    assert any(
        "command not witnessed in session events" in err for err in stop["requirement_audit_report"]["errors"]
    )


def test_on_stop_requirement_audit_uncheckable_command_warns_in_advisory_mode(
    kernel: CortexKernel,
) -> None:
    kernel.ctx.genome.hooks.mode = "advisory"
    kernel.ctx.genome.hooks.fail_on_requirement_audit_gap = True

    kernel.on_session_start({"session_id": "sess-stop-req-cmd-advisory", "objective": "Validate commands"})
    stop = kernel.on_stop(
        {
            "session_id": "sess-stop-req-cmd-advisory",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "requirement_audit": {
                "items": [{"id": "R1", "status": "pass", "evidence": ["cmd:pytest -q"]}],
                "completeness_verdict": "pass",
            },
        }
    )

    assert stop["requirement_audit_report"]["ok"] is True
    assert stop["requirement_audit_gap"] is False
    assert stop["recommend_revert"] is False
    assert any("Requirement audit note:" in warning for warning in stop["warnings"])


def test_dispatch_normalizes_event_names(kernel: CortexKernel) -> None:
    result = kernel.dispatch("pre-tool-use", {"session_id": "sess-dispatch"})
    assert result["hook"] == "PreToolUse"
    assert result["session_id"] == "sess-dispatch"
