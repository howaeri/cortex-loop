from __future__ import annotations

import json
from pathlib import Path

from cortex.repomap import (
    MAX_DISCOVER_FILE_BYTES,
    RepoMapFileAnalysis,
    RepoMapRankingEntry,
    _build_dependency_edges,
    _discover_files,
    _pagerank_scores,
    _rank_files,
    _render_text,
    run_repomap,
)


def test_run_repomap_writes_valid_artifact_and_applies_ignores(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "src" / "nested").mkdir(parents=True)
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "dist").mkdir()
    (root / ".cortex").mkdir()

    (root / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (root / "src" / "util.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (root / "src" / "nested" / "data.json").write_text('{"ok": true}\n', encoding="utf-8")
    (root / "src" / "bundle.min.js").write_text("minified\n", encoding="utf-8")
    (root / "src" / "bundle.js.map").write_text("{}\n", encoding="utf-8")
    (root / "node_modules" / "pkg" / "index.js").write_text("module.exports={}\n", encoding="utf-8")
    (root / "dist" / "out.js").write_text("console.log(1)\n", encoding="utf-8")
    (root / ".cortex" / "ignore.txt").write_text("ignore me\n", encoding="utf-8")
    (root / "src" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    result = run_repomap(
        root=root,
        scope=["src", "node_modules", "dist", ".cortex"],
        focus_files=["src/app.py"],
        max_files=10,
        max_text_bytes=2048,
    )

    assert result.ok is True
    assert result.artifact.schema_version == "repomap_artifact_v1"
    assert result.artifact_path
    artifact_path = Path(result.artifact_path)
    assert artifact_path.exists()
    assert result.artifact.provenance["method"] in {"heuristic_fallback", "ast_pagerank"}
    assert result.artifact.provenance["scope"] == ["src", "node_modules", "dist", ".cortex"]
    assert result.artifact.stats["files_parsed"] == 3
    assert result.artifact.ranking
    assert result.artifact.ranking[0].path == "src/app.py"
    assert "node_modules/pkg/index.js" not in result.artifact.text
    assert "dist/out.js" not in result.artifact.text

    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "repomap_artifact_v1"
    assert saved["ok"] is True
    assert "artifact_path" not in saved


def test_run_repomap_empty_scope_emits_valid_empty_artifact(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)

    result = run_repomap(root=root, scope=["src"], max_files=5, max_text_bytes=512)

    assert result.ok is True
    assert result.artifact.stats["files_parsed"] == 0
    assert result.artifact.ranking == []
    assert result.artifact.text == ""
    assert result.artifact_path and Path(result.artifact_path).exists()


def test_run_repomap_auto_falls_back_scope_when_default_scope_missing(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "cortex").mkdir(parents=True)
    (root / "cortex" / "mod.py").write_text("class Engine:\n    pass\n", encoding="utf-8")

    result = run_repomap(root=root)

    assert result.ok is True
    assert result.artifact.stats["files_parsed"] == 1
    assert result.artifact.ranking[0].path == "cortex/mod.py"
    assert "cortex" in result.artifact.provenance["scope"]


def test_run_repomap_write_failure_returns_failure_envelope(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "bad-output").mkdir()

    result = run_repomap(root=root, scope=["src"], output_path="bad-output")

    assert result.ok is False
    assert result.artifact.error is not None
    assert result.artifact.error["code"] == "write_failed"
    assert result.artifact.error["failed_stage"] == "write"
    assert result.artifact.stats["files_parsed"] == 0


def test_run_repomap_without_timeout_does_not_inherit_config_timeout(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")

    class Config:
        watch_paths = ["src"]
        ignored_dirs: list[str] = []
        artifact_path = ".cortex/artifacts/repomap/latest.json"
        max_ranked_files = 5
        max_text_bytes = 1024
        session_start_timeout_ms = 0

    result = run_repomap(root=root, repomap_config=Config(), timeout_ms=None)

    assert result.ok is True
    assert result.artifact.provenance["timeout_ms"] is None


def test_run_repomap_uses_ast_with_simple_pagerank_when_networkx_missing(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr("cortex.repomap.repomap_missing_dependencies", lambda: ["networkx"])
    monkeypatch.setattr("cortex.repomap._pagerank_scores_networkx", lambda _paths, _edges: {})

    result = run_repomap(root=root, scope=["src"])

    assert result.ok is True
    assert result.artifact.provenance["method"] == "ast_pagerank"
    assert result.artifact.provenance["ast_requested"] is True
    assert result.artifact.provenance["ast_enabled"] is True
    assert result.artifact.provenance["missing_deps"] == ["networkx"]
    assert result.artifact.provenance["pagerank_backend"] == "simple"


def test_run_repomap_uses_ast_pagerank_when_deps_available(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.ts").write_text('import helper from "./helper";\n', encoding="utf-8")
    (root / "src" / "helper.ts").write_text("export default function helper() {}\n", encoding="utf-8")
    monkeypatch.setattr("cortex.repomap.repomap_missing_dependencies", lambda: [])
    monkeypatch.setattr(
        "cortex.repomap._pagerank_scores_networkx",
        lambda paths, edges: {path: (1.0 if path.endswith("helper.ts") else 0.0) for path in paths},
    )

    result = run_repomap(root=root, scope=["src"])

    assert result.ok is True
    assert result.artifact.provenance["method"] == "ast_pagerank"
    assert result.artifact.provenance["ast_enabled"] is True
    assert result.artifact.provenance["missing_deps"] == []
    assert result.artifact.provenance["pagerank_backend"] == "networkx"
    assert result.artifact.stats["graph_edges"] >= 1
    assert result.artifact.ranking[0].path == "src/helper.ts"


def test_rank_files_uses_deterministic_tie_breaker_by_path() -> None:
    analyses = [
        RepoMapFileAnalysis(path="src/bbb.py", byte_size=10, line_count=10, symbols=[], symbol_count=0),
        RepoMapFileAnalysis(path="src/aaa.py", byte_size=10, line_count=10, symbols=[], symbol_count=0),
    ]

    ranked = _rank_files(analyses, focus_files=[], max_files=10)

    assert [entry.path for entry in ranked] == ["src/aaa.py", "src/bbb.py"]


def test_build_dependency_edges_resolves_python_relative_imports() -> None:
    analyses = [
        RepoMapFileAnalysis(
            path="src/pkg/module.py",
            byte_size=32,
            line_count=2,
            symbols=[],
            symbol_count=0,
            imports=[".helpers"],
        ),
        RepoMapFileAnalysis(
            path="src/pkg/helpers.py",
            byte_size=16,
            line_count=1,
            symbols=[],
            symbol_count=0,
            imports=[],
        ),
    ]

    edges = _build_dependency_edges(analyses)

    assert ("src/pkg/module.py", "src/pkg/helpers.py") in edges


def test_pagerank_scores_prefers_dependency_hub() -> None:
    paths = ["src/main.ts", "src/feature.ts", "src/util.ts"]
    edges = [("src/main.ts", "src/util.ts"), ("src/feature.ts", "src/util.ts")]

    scores = _pagerank_scores(paths, edges)

    assert scores["src/util.ts"] > scores["src/main.ts"]
    assert scores["src/util.ts"] > scores["src/feature.ts"]


def test_rank_files_penalizes_lockfiles_and_boosts_astro_components() -> None:
    analyses = [
        RepoMapFileAnalysis(
            path="sample-site/package-lock.json",
            byte_size=100,
            line_count=200,
            symbols=[],
            symbol_count=0,
        ),
        RepoMapFileAnalysis(
            path="sample-site/src/components/GuidedDemo.astro",
            byte_size=100,
            line_count=200,
            symbols=[],
            symbol_count=0,
        ),
    ]

    ranked = _rank_files(analyses, focus_files=[], max_files=10)

    assert ranked[0].path == "sample-site/src/components/GuidedDemo.astro"
    assert ranked[1].path == "sample-site/package-lock.json"


def test_render_text_applies_truncation_note_and_byte_cap() -> None:
    ranking = [
        RepoMapRankingEntry(
            path=f"src/very_long_module_name_{i}.py",
            score=1.234 + i,
            symbols=[f"def symbol_{i}_{j}" for j in range(3)],
        )
        for i in range(20)
    ]

    text = _render_text(ranking, max_text_bytes=256)

    assert "truncated" in text
    assert len(text.encode("utf-8")) <= 256


def test_discover_files_skips_large_binary_and_hidden_files(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "good.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "src" / ".secret").write_text("hidden\n", encoding="utf-8")
    (root / "src" / "bin.dat").write_bytes(b"\x00\x01\x02")
    (root / "src" / "big.txt").write_text("x" * (MAX_DISCOVER_FILE_BYTES + 1), encoding="utf-8")

    files = _discover_files(root=root, scope=["src"], ignored_dirs=[], timeout_check=None)

    assert files == ["src/good.py"]
