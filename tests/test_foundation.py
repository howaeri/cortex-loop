from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from cortex.foundation import FoundationAnalyzer
from cortex.genome import FoundationConfig


def test_analyze_without_git_repo_is_graceful(tmp_path: Path) -> None:
    analyzer = FoundationAnalyzer(tmp_path, FoundationConfig())
    report = analyzer.analyze()
    assert report.enabled is True
    assert report.git_available is False
    assert "Git repository not detected" in report.warnings[0]


def test_norm_path_and_ignored_helpers(tmp_path: Path) -> None:
    analyzer = FoundationAnalyzer(tmp_path, FoundationConfig(ignored_dirs=["dist", "node_modules"]))
    assert analyzer._norm_path("src/../src/app.py") == "src/../src/app.py"
    assert analyzer._ignored("src/dist/bundle.js") is True
    assert analyzer._ignored("src/app.py") is False


def test_collect_churn_counts_handles_subprocess_failure_gracefully(tmp_path: Path, monkeypatch) -> None:
    analyzer = FoundationAnalyzer(tmp_path, FoundationConfig())
    monkeypatch.setattr(FoundationAnalyzer, "_is_git_repo", lambda self: True)
    monkeypatch.setattr(
        "cortex.foundation.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="boom"),
    )
    report = analyzer.analyze()
    assert report.git_available is True
    assert report.findings == []
