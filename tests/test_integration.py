from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from cortex import cli as cortex_cli
from cortex.core import CortexKernel


def test_full_cortex_session_lifecycle(tmp_path: Path, capsys) -> None:
    project_root = tmp_path / "testing-project"

    rc = cortex_cli.main(["init", "--root", str(project_root)])
    assert rc == 0
    init_out = capsys.readouterr().out
    init_result = json.loads(init_out)
    assert init_result["ok"] is True
    assert (project_root / "cortex.toml").exists()
    assert (project_root / ".cortex" / "cortex.db").exists()
    assert (project_root / "tests" / "invariants").is_dir()

    pytest_bin = shutil.which("pytest") or str(Path(sys.executable).with_name("pytest"))
    config_path = project_root / "cortex.toml"
    config_text = config_path.read_text(encoding="utf-8")
    config_text = config_text.replace('pytest_bin = "pytest"', f'pytest_bin = "{pytest_bin}"')
    config_path.write_text(config_text, encoding="utf-8")

    invariant_test = project_root / "tests" / "invariants" / "test_invariant_smoke.py"
    invariant_test.write_text("def test_invariant_smoke():\n    assert 2 + 2 == 4\n", encoding="utf-8")

    kernel = CortexKernel(root=project_root, config_path=config_path, db_path=project_root / ".cortex" / "cortex.db")

    start_1 = kernel.on_session_start(
        {
            "session_id": "sess-1",
            "objective": "Add input validation to parser",
            "target_files": ["src/parser.py"],
        }
    )
    assert start_1["ok"] is True
    assert "foundation" in start_1
    assert "graveyard_matches" in start_1

    pre = kernel.on_pre_tool_use(
        {
            "session_id": "sess-1",
            "tool_name": "Write",
            "target_files": ["src/parser.py"],
        }
    )
    assert pre["ok"] is True
    assert pre["proceed"] is True

    post = kernel.on_post_tool_use(
        {
            "session_id": "sess-1",
            "tool_name": "Write",
            "status": "ok",
        }
    )
    assert post["ok"] is True
    assert post["proceed"] is True

    stop_1 = kernel.on_stop(
        {
            "session_id": "sess-1",
            "run_invariants": True,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "pytest_args": ["-q"],
        }
    )
    assert stop_1["ok"] is True
    assert stop_1["challenge_report"]["ok"] is True
    assert stop_1["invariant_report"]["ok"] is True
    assert stop_1["recommend_revert"] is False

    start_2 = kernel.on_session_start(
        {
            "session_id": "sess-2",
            "objective": "Optimize parser branch",
            "target_files": ["src/parser.py"],
        }
    )
    assert start_2["ok"] is True

    stop_2 = kernel.on_stop(
        {
            "session_id": "sess-2",
            "run_invariants": False,
            "challenge_coverage": {
                "null_inputs": True,
                "boundary_values": True,
                "error_handling": True,
                "graveyard_regression": True,
            },
            "failed_approach": {
                "summary": "Removed null guard in parser refactor",
                "reason": "Null payload caused parser crash during validation",
                "files": ["src/parser.py"],
            },
        }
    )
    assert stop_2["ok"] is True
    assert stop_2["challenge_report"]["ok"] is True

    start_3 = kernel.on_session_start(
        {
            "session_id": "sess-3",
            "objective": "Fix parser null payload validation crash",
            "target_files": ["src/parser.py"],
        }
    )
    assert start_3["ok"] is True
    assert start_3["graveyard_matches"], "expected graveyard match to surface in third session"

    with kernel.ctx.store.connection() as conn:
        sessions = conn.execute("SELECT session_id, status FROM sessions ORDER BY session_id").fetchall()
        graveyard_count = conn.execute("SELECT COUNT(*) AS n FROM graveyard").fetchone()["n"]
        event_count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        stop_events = conn.execute("SELECT COUNT(*) AS n FROM events WHERE hook = 'Stop'").fetchone()["n"]

    assert {row["session_id"] for row in sessions} == {"sess-1", "sess-2", "sess-3"}
    statuses = {row["session_id"]: row["status"] for row in sessions}
    assert statuses["sess-1"] == "completed"
    assert statuses["sess-2"] == "completed"
    assert statuses["sess-3"] == "running"
    assert graveyard_count == 1
    assert stop_events == 2
    assert event_count == 7
