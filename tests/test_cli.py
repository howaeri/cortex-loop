from __future__ import annotations

import json
from pathlib import Path
import sys

from cortex import cli as cortex_cli
from cortex.store import SQLiteStore


def test_init_creates_turnkey_files(tmp_path: Path, capsys) -> None:
    root = tmp_path / "new-project"
    rc = cortex_cli.main(["init", "--root", str(root)])
    assert rc == 0

    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True
    assert (root / "cortex.toml").exists()
    assert (root / ".cortex" / "cortex.db").exists()
    assert (root / "tests" / "invariants" / "example_invariant_test.py").exists()
    assert (root / ".claude" / "settings.json").exists()
    assert (root / ".claude" / "CLAUDE.md").exists()

    # Claude settings are based on the repo template but pin the current interpreter
    # so hooks work from the target project root.
    repo_root = Path(__file__).resolve().parents[1]
    generated_settings = json.loads(
        (root / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    template_settings = json.loads(
        (repo_root / "claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert set(generated_settings["hooks"]) == set(template_settings["hooks"])
    python_path = sys.executable
    for event_name, entries in generated_settings["hooks"].items():
        assert event_name in template_settings["hooks"]
        commands = []
        for entry in entries:
            commands.extend(h["command"] for h in entry.get("hooks", []))
        assert any("cortex.hooks." in cmd for cmd in commands)
        assert any(python_path in cmd for cmd in commands)
    assert (root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8") == (
        repo_root / "claude" / "CLAUDE.md"
    ).read_text(encoding="utf-8")

    starter = (root / "tests" / "invariants" / "example_invariant_test.py").read_text(
        encoding="utf-8"
    )
    assert "external constraints the current agent did not author" in starter
    assert "def test_cortex_config_exists()" in starter
    assert "Example of a real invariant" in starter
    starter_cfg = (root / "cortex.toml").read_text(encoding="utf-8")
    assert "require_requirement_audit = false" in starter_cfg
    assert "fail_on_requirement_audit_gap = false" in starter_cfg
    assert "require_evidence_for_passed_requirement = true" in starter_cfg
    assert "require_structured_stop_payload = true" in starter_cfg
    assert "allow_message_stop_fallback = false" in starter_cfg
    assert 'execution_mode = "host"' in starter_cfg


def test_init_refuses_overwrite_without_force_and_overwrites_with_force(
    tmp_path: Path, capsys
) -> None:
    root = tmp_path / "project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    claude_md = root / ".claude" / "CLAUDE.md"
    claude_md.write_text("modified\n", encoding="utf-8")

    rc = cortex_cli.main(["init", "--root", str(root)])
    stderr = capsys.readouterr().err
    assert rc == 1
    assert "Use --force" in stderr

    rc = cortex_cli.main(["init", "--root", str(root), "--force"])
    out = capsys.readouterr().out
    assert rc == 0
    result = json.loads(out)
    assert str(claude_md) in result["overwritten"]
    assert "Cortex Governance Instructions" in claude_md.read_text(encoding="utf-8")


def test_check_reports_human_readable_summary(tmp_path: Path, capsys) -> None:
    root = tmp_path / "checked-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cortex Check:" in out
    assert "OK:" in out
    assert "Needs Attention:" in out
    assert "Missing / Errors:" in out
    assert "Config parsed:" in out
    assert "Database ready:" in out
    assert "Claude hook wiring found" in out
    assert "Repo-map is disabled in cortex.toml" in out


def test_check_warns_on_db_schema_version_mismatch(tmp_path: Path, capsys) -> None:
    root = tmp_path / "schema-mismatch-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    # Simulate older metadata version while tables are still present.
    store = SQLiteStore(root / ".cortex" / "cortex.db")
    with store.connection() as conn:
        conn.execute("PRAGMA user_version = 0")

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Database schema version mismatch: found 0, expected 1" in out


def test_check_json_and_status_artifact(tmp_path: Path, capsys) -> None:
    root = tmp_path / "checked-project-json"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    rc = cortex_cli.main(["check", "--root", str(root), "--json", "--write-status"])
    out = capsys.readouterr().out
    assert rc == 0
    report = json.loads(out)
    assert report["status"] == "ok"
    assert report["summary"]["errors"] == 0
    assert report["cortex_version"]
    assert report["config_schema_version"] == "cortex_toml_v1"
    assert report["db"]["expected_schema_version"] == 1
    assert report["hooks"]["valid"] is True
    assert report["status_artifact"] == str(root / ".cortex" / "status.json")
    status_data = json.loads((root / ".cortex" / "status.json").read_text(encoding="utf-8"))
    assert status_data["root"] == str(root)


def test_check_accepts_legacy_claude_settings_location(tmp_path: Path, capsys) -> None:
    root = tmp_path / "legacy-claude-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    preferred_dir = root / ".claude"
    legacy_dir = root / "claude"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "settings.json").write_text(
        (preferred_dir / "settings.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (legacy_dir / "CLAUDE.md").write_text(
        (preferred_dir / "CLAUDE.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (preferred_dir / "settings.json").unlink()
    (preferred_dir / "CLAUDE.md").unlink()
    preferred_dir.rmdir()

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"Claude hook wiring found in {legacy_dir / 'settings.json'}" in out


def test_check_warns_when_repomap_enabled_missing_deps(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    root = tmp_path / "repomap-check-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    cfg_path = root / "cortex.toml"
    text = cfg_path.read_text(encoding="utf-8")
    before, after = text.split("[repomap]\n", 1)
    after = after.replace("enabled = false", "enabled = true", 1)
    cfg_path.write_text(before + "[repomap]\n" + after, encoding="utf-8")

    monkeypatch.setattr(
        cortex_cli, "_repomap_dependency_status", lambda: ["networkx"]
    )

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Repo-map enabled; optional ranking dependencies missing" in out
    assert "AST graph + lightweight fallback remain available" in out
    assert "networkx" in out
    assert "Repo-map artifact missing (warning only): .cortex/artifacts/repomap/latest.json" in out


def test_check_warns_when_challenge_coverage_gate_is_non_blocking(tmp_path: Path, capsys) -> None:
    root = tmp_path / "advisory-coverage-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    cfg_path = root / "cortex.toml"
    text = cfg_path.read_text(encoding="utf-8")
    text = text.replace("fail_on_missing_challenge_coverage = false", "fail_on_missing_challenge_coverage = true", 1)
    cfg_path.write_text(text, encoding="utf-8")

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "hooks.fail_on_missing_challenge_coverage=true has no blocking effect while hooks.mode='advisory'" in out
    assert "set [hooks].mode='strict' to enforce missing challenge coverage as a real gate" in out


def test_check_warns_when_structured_stop_required_but_message_fallback_enabled(
    tmp_path: Path, capsys
) -> None:
    root = tmp_path / "structured-stop-warning-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    cfg_path = root / "cortex.toml"
    text = cfg_path.read_text(encoding="utf-8")
    text = text.replace("require_structured_stop_payload = false", "require_structured_stop_payload = true", 1)
    text = text.replace("allow_message_stop_fallback = false", "allow_message_stop_fallback = true", 1)
    cfg_path.write_text(text, encoding="utf-8")

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "hooks.require_structured_stop_payload=true while hooks.allow_message_stop_fallback=true" in out


def test_check_warns_when_container_mode_engine_missing(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    root = tmp_path / "container-mode-missing-engine"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    cfg_path = root / "cortex.toml"
    text = cfg_path.read_text(encoding="utf-8")
    text = text.replace('execution_mode = "host"', 'execution_mode = "container"', 1)
    cfg_path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(cortex_cli.shutil, "which", lambda _name: None)

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "invariants.execution_mode='container' but container engine 'docker' is not on PATH" in out
    assert "switch to execution_mode='host'" in out


def test_check_reports_container_mode_engine_available(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    root = tmp_path / "container-mode-engine-ok"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    cfg_path = root / "cortex.toml"
    text = cfg_path.read_text(encoding="utf-8")
    text = text.replace('execution_mode = "host"', 'execution_mode = "container"', 1)
    cfg_path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(cortex_cli.shutil, "which", lambda _name: "/usr/local/bin/docker")

    rc = cortex_cli.main(["check", "--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Invariant container engine available: docker" in out
    assert "container engine 'docker' is not on PATH" not in out


def test_repomap_cli_emits_artifact_json(tmp_path: Path, capsys) -> None:
    root = tmp_path / "repomap-cli-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")

    rc = cortex_cli.main(
        [
            "repomap",
            "--root",
            str(root),
            "--json",
            "--scope",
            "src",
            "--focus-file",
            "src/app.py",
            "--max-files",
            "7",
            "--max-text-bytes",
            "2048",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    result = json.loads(out)
    assert result["ok"] is True
    assert result["schema_version"] == "repomap_artifact_v1"
    assert "status" not in result
    assert "requested" not in result
    assert "repomap" not in result
    assert "artifact_path" not in result
    assert result["provenance"]["scope"] == ["src"]
    assert result["provenance"]["focus_files"] == ["src/app.py"]
    assert result["provenance"]["timeout_ms"] is None
    assert result["ranking"][0]["path"] == "src/app.py"


def test_repomap_cli_debug_json_emits_wrapper_metadata(tmp_path: Path, capsys) -> None:
    root = tmp_path / "repomap-cli-debug-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")

    rc = cortex_cli.main(
        [
            "repomap",
            "--root",
            str(root),
            "--debug-json",
            "--scope",
            "src",
            "--focus-file",
            "src/app.py",
            "--max-files",
            "7",
            "--max-text-bytes",
            "2048",
            "--timeout-ms",
            "0",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 1
    result = json.loads(out)
    assert result["ok"] is False
    assert result["status"] == "error"
    assert result["schema_version"] == "repomap_artifact_v1"
    assert result["repomap"]["enabled"] is False
    assert result["requested"]["scope"] == ["src"]
    assert result["requested"]["focus_files"] == ["src/app.py"]
    assert result["requested"]["max_files"] == 7
    assert result["requested"]["max_text_bytes"] == 2048
    assert result["requested"]["timeout_ms"] == 0
    assert result["error"]["code"] == "timeout"


def test_graveyard_lists_entries_human_readable(tmp_path: Path, capsys) -> None:
    root = tmp_path / "graveyard-project"
    assert cortex_cli.main(["init", "--root", str(root)]) == 0
    _ = capsys.readouterr()

    store = SQLiteStore(root / ".cortex" / "cortex.db")
    store.insert_graveyard(
        session_id="sess-1",
        summary="Tried virtualized list",
        reason="Sticky header regression",
        files=["src/list.py"],
        keywords=["virtualized", "sticky", "header"],
    )

    rc = cortex_cli.main(["graveyard", "--root", str(root), "--limit", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cortex Graveyard" in out
    assert "Tried virtualized list" in out
    assert "Sticky header regression" in out
    assert "src/list.py" in out


def test_fleet_status_reports_multiple_projects(tmp_path: Path, capsys) -> None:
    ok_root = tmp_path / "fleet-ok"
    err_root = tmp_path / "fleet-err"
    assert cortex_cli.main(["init", "--root", str(ok_root)]) == 0
    _ = capsys.readouterr()
    err_root.mkdir(parents=True)

    rc = cortex_cli.main(
        [
            "fleet",
            "status",
            "--roots",
            str(ok_root),
            str(err_root),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert payload["summary"]["projects"] == 2
    assert payload["summary"]["error_projects"] == 1
    assert len(payload["projects"]) == 2
    by_root = {item["root"]: item for item in payload["projects"]}
    assert by_root[str(ok_root)]["summary"]["errors"] == 0
    assert by_root[str(err_root)]["summary"]["errors"] > 0
