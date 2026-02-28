from __future__ import annotations

from pathlib import Path


def test_agents_contract_contains_required_philosophy_markers() -> None:
    text = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")
    for token in ("PHI_MINIFY", "PHI_MISSION", "PHI_NICHE", "CUT_LIST", "todos.md"):
        assert token in text


def test_claude_guidance_declares_repo_scope_and_philosophy_loop() -> None:
    text = (Path(__file__).resolve().parents[1] / "claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "agents editing Cortex itself" in text
    for token in ("PHI_MINIFY", "PHI_MISSION", "PHI_NICHE"):
        assert token in text
