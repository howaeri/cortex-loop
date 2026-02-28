from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cortex.adapters import AiderAdapter, ClaudeCodeAdapter, NormalizedEvent
from cortex.core import CortexKernel


def test_claude_adapter_normalizes_event_and_tool_alias() -> None:
    adapter = ClaudeCodeAdapter()
    event = adapter.normalize("PreToolUse", {"session_id": "sess-1", "tool": "Write"})
    assert event.name == "pre_tool_use"
    assert event.payload["tool_name"] == "Write"


def test_aider_adapter_normalizes_event_and_tool_alias() -> None:
    adapter = AiderAdapter()
    event = adapter.normalize("before_tool", {"session_id": "sess-1", "action": "Write"})
    assert event.name == "pre_tool_use"
    assert event.payload["tool_name"] == "Write"


def test_kernel_uses_aider_adapter_name(tmp_project) -> None:
    kernel = CortexKernel(
        root=tmp_project,
        config_path=tmp_project / "cortex.toml",
        db_path=tmp_project / ".cortex" / "cortex.db",
        adapter_name="aider",
    )
    result = kernel.dispatch(
        "before_tool",
        {
            "session_id": "sess-aider",
            "action": "Edit",
            "target_files": ["src/app.py"],
        },
    )
    assert result["hook"] == "PreToolUse"
    assert result["session_id"] == "sess-aider"
    assert result["ok"] is True


def test_kernel_dispatch_uses_injected_adapter(tmp_project) -> None:
    @dataclass(slots=True)
    class TestAdapter:
        def normalize(self, event_name: str, payload: dict[str, Any] | None = None) -> NormalizedEvent:
            _ = event_name
            _ = payload
            return NormalizedEvent(
                name="stop",
                payload={
                    "session_id": "sess-adapter",
                    "run_invariants": False,
                    "challenge_coverage": {
                        "null_inputs": True,
                        "boundary_values": True,
                        "error_handling": True,
                        "graveyard_regression": True,
                    },
                },
            )

    kernel = CortexKernel(
        root=tmp_project,
        config_path=tmp_project / "cortex.toml",
        db_path=tmp_project / ".cortex" / "cortex.db",
        adapter=TestAdapter(),
    )
    result = kernel.dispatch("IGNORED")
    assert result["hook"] == "Stop"
    assert result["session_id"] == "sess-adapter"
    assert result["challenge_report"]["ok"] is True
