from __future__ import annotations

from pathlib import Path

from cortex.genome import load_genome


def test_loads_valid_toml(tmp_project: Path) -> None:
    genome = load_genome(tmp_project / "cortex.toml")
    assert genome.parse_error is None
    assert genome.project.name == "test-app"
    assert genome.project.type == "python"
    assert genome.invariants.suite_paths == ["tests/invariants/sample_test.py"]
    assert genome.invariants.run_on_stop is False
    assert genome.invariants.execution_mode == "host"
    assert genome.invariants.graduation.target_dir == "tests/invariants/graduated"
    assert genome.challenges.active_categories == [
        "null_inputs",
        "boundary_values",
        "error_handling",
        "graveyard_regression",
    ]
    assert genome.challenges.custom_paths == [".cortex/challenges/custom.toml"]
    assert genome.graveyard.max_matches == 3
    assert genome.graveyard.similarity_threshold == 0.2
    assert genome.foundation.watch_paths == ["src", "pkg"]
    assert genome.foundation.stability_thresholds.warn_churn_count == 2
    assert genome.foundation.stability_thresholds.high_churn_count == 4
    assert genome.repomap.enabled is True
    assert genome.repomap.run_on_session_start is True
    assert genome.repomap.prefer_ast_graph is True
    assert genome.repomap.watch_paths == ["src", "pkg"]
    assert genome.repomap.max_ranked_files == 12
    assert genome.repomap.max_text_bytes == 4096
    assert genome.repomap.session_start_timeout_ms == 1800
    assert genome.hooks.mode == "advisory"
    assert genome.hooks.require_requirement_audit is False
    assert genome.hooks.fail_on_requirement_audit_gap is False
    assert genome.hooks.require_evidence_for_passed_requirement is True
    assert genome.hooks.require_structured_stop_payload is False
    assert genome.hooks.allow_message_stop_fallback is False
    assert genome.metrics.track[-1] == "foundation_quality"


def test_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    genome = load_genome(missing)
    assert genome.parse_error is None
    assert genome.source_path == str(missing)
    assert genome.project.name == "unknown-project"
    assert genome.foundation.watch_paths == ["src"]
    assert genome.repomap.enabled is False
    assert genome.repomap.prefer_ast_graph is True
    assert genome.repomap.artifact_path == ".cortex/artifacts/repomap/latest.json"


def test_returns_defaults_with_parse_error_on_invalid_toml(tmp_path: Path) -> None:
    bad = tmp_path / "cortex.toml"
    bad.write_text("[project]\nname = 'ok'\ninvalid = [\n", encoding="utf-8")
    genome = load_genome(bad)
    assert genome.project.name == "unknown-project"
    assert genome.parse_error
    assert genome.source_path == str(bad)


def test_section_type_mismatches_fall_back_to_defaults(tmp_path: Path) -> None:
    cfg = tmp_path / "cortex.toml"
    cfg.write_text(
        """
        [project]
        name = "demo"

        [invariants]
        execution_mode = "invalid"

        [foundation]
        watch_paths = "not-a-list"
        churn_window_commits = "bad"

        [graveyard]
        similarity_threshold = "bad"

        [repomap]
        enabled = "not-bool"
        watch_paths = "not-a-list"
        max_ranked_files = "bad"
        max_text_bytes = "bad"
        """,
        encoding="utf-8",
    )
    genome = load_genome(cfg)
    assert genome.project.name == "demo"
    assert genome.invariants.execution_mode == "host"
    assert genome.foundation.watch_paths == ["src"]
    assert genome.foundation.churn_window_commits == 200
    assert genome.graveyard.similarity_threshold == 0.35
    assert genome.repomap.enabled is False
    assert genome.repomap.prefer_ast_graph is True
    assert genome.repomap.watch_paths == ["src"]
    assert genome.repomap.max_ranked_files == 20
    assert genome.repomap.max_text_bytes == 8192


def test_loads_hooks_requirement_audit_fields(tmp_path: Path) -> None:
    cfg = tmp_path / "cortex.toml"
    cfg.write_text(
        """
        [hooks]
        mode = "strict"
        require_requirement_audit = true
        fail_on_requirement_audit_gap = true
        require_evidence_for_passed_requirement = false
        require_structured_stop_payload = true
        allow_message_stop_fallback = false
        """,
        encoding="utf-8",
    )
    genome = load_genome(cfg)
    assert genome.hooks.mode == "strict"
    assert genome.hooks.require_requirement_audit is True
    assert genome.hooks.fail_on_requirement_audit_gap is True
    assert genome.hooks.require_evidence_for_passed_requirement is False
    assert genome.hooks.require_structured_stop_payload is True
    assert genome.hooks.allow_message_stop_fallback is False
