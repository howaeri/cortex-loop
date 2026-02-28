from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from cortex.hooks import post_tool_use, pre_tool_use, session_start, stop


@pytest.mark.parametrize(
    ("module", "payload", "expected_hook"),
    [
        (session_start, {"session_id": "sess-hook", "objective": "Start"}, "SessionStart"),
        (pre_tool_use, {"session_id": "sess-hook", "tool": "Edit"}, "PreToolUse"),
        (post_tool_use, {"session_id": "sess-hook", "tool": "Edit", "status": "ok"}, "PostToolUse"),
        (
            stop,
            {
                "session_id": "sess-hook",
                "run_invariants": False,
                "challenge_coverage": {
                    "null_inputs": True,
                    "boundary_values": True,
                    "error_handling": True,
                    "graveyard_regression": True,
                },
            },
            "Stop",
        ),
    ],
)
def test_hook_main_functions_end_to_end(tmp_project: Path, monkeypatch, capsys, module, payload, expected_hook) -> None:
    monkeypatch.chdir(tmp_project)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = module.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["ok"] is True
    assert data["hook"] == expected_hook
    assert data["session_id"] == "sess-hook"
    if expected_hook == "SessionStart":
        assert "repomap" in data
        assert isinstance(data["repomap"], dict)
        assert "text" not in data["repomap"]
    if expected_hook == "Stop":
        assert "requirement_audit_report" in data
        assert data["requirement_audit_report"] is None
        assert data["requirement_audit_missing"] is False
        assert data["requirement_audit_gap"] is False


def test_hook_main_supports_root_and_config_args(tmp_project: Path, monkeypatch, capsys) -> None:
    payload = {"session_id": "sess-hook-args", "objective": "Start with args"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    rc = session_start.main(["--root", str(tmp_project), "--config", str(tmp_project / "cortex.toml")])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 0
    assert data["ok"] is True
    assert data["hook"] == "SessionStart"
    assert data["session_id"] == "sess-hook-args"


@pytest.mark.parametrize(
    ("module", "expected_hook"),
    [
        (session_start, "SessionStart"),
        (pre_tool_use, "PreToolUse"),
        (post_tool_use, "PostToolUse"),
        (stop, "Stop"),
    ],
)
def test_hook_main_returns_json_error_on_malformed_payload(
    tmp_project: Path, monkeypatch, capsys, module, expected_hook
) -> None:
    monkeypatch.chdir(tmp_project)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{invalid-json"))

    rc = module.main()
    out = capsys.readouterr().out
    data = json.loads(out)

    assert rc == 1
    assert data["ok"] is False
    assert data["hook"] == expected_hook
    assert "error" in data
