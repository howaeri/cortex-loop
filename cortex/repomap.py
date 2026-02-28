from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "repomap_artifact_v1"
MAX_DISCOVER_FILE_BYTES = 512_000
READ_SAMPLE_BYTES = 8192
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cortex",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "coverage",
}
_BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".tar",
    ".jar",
    ".war",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".wav",
    ".sqlite",
    ".db",
    ".pyc",
    ".pyo",
}
_CODE_LIKE_SUFFIXES = {
    ".astro",
    ".svelte",
    ".vue",
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".scala",
    ".lua",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".sql",
    ".md",
    ".html",
    ".css",
    ".scss",
}
_RANK_SUFFIX_BOOSTS = {
    ".astro": 0.9,
    ".tsx": 0.5,
    ".jsx": 0.4,
}
_RANK_EXACT_FILENAME_PENALTIES = {
    "package-lock.json": 1.8,
    "pnpm-lock.yaml": 1.8,
    "yarn.lock": 1.8,
    "poetry.lock": 1.4,
    "cargo.lock": 1.4,
    "composer.lock": 1.2,
}
_FALLBACK_SCOPE_CANDIDATES = ("cortex", "src", "lib", "app", "packages", "tests")
_RANK_NAME_BOOSTS = {
    "core": 0.9,
    "main": 0.8,
    "app": 0.7,
    "index": 0.6,
    "server": 0.7,
    "client": 0.5,
    "api": 0.6,
    "router": 0.5,
    "service": 0.4,
    "model": 0.3,
    "store": 0.3,
}
_RANK_PATH_PENALTIES = {
    "tests": 0.85,
    "test": 0.85,
    "docs": 0.65,
    "examples": 0.7,
    "scripts": 0.8,
    "migrations": 0.8,
}
_RANK_PATH_BOOSTS = {
    "src": 0.15,
    "components": 0.2,
    "pages": 0.2,
    "layouts": 0.15,
}
_RELATIVE_IMPORT_SUFFIX_CANDIDATES = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".astro",
    ".vue",
    ".svelte",
)
_SYMBOL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b"), "class"),
    (re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\("), "def"),
    (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("), "def"),
    (re.compile(r"^\s*export\s+class\s+([A-Za-z_]\w*)\b"), "class"),
    (re.compile(r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\("), "function"),
    (re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\("), "function"),
    (re.compile(r"^\s*interface\s+([A-Za-z_]\w*)\b"), "interface"),
    (re.compile(r"^\s*type\s+([A-Za-z_]\w*)\b"), "type"),
    (re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\("), "const"),
    (re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*function\b"), "const"),
    (re.compile(r"^\s*([A-Za-z_]\w*)\s*\(\)\s*\{"), "function"),
]
_IMPORT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"""^\s*import\s+.*?\s+from\s+["']([^"']+)["']"""),
    re.compile(r"""^\s*import\s+["']([^"']+)["']"""),
    re.compile(r"""^\s*export\s+.*?\s+from\s+["']([^"']+)["']"""),
    re.compile(r"""require\(\s*["']([^"']+)["']\s*\)"""),
]
_OPTIONAL_DEPENDENCIES = {
    "numpy": "numpy",
    "networkx": "networkx",
}


@dataclass(slots=True)
class RepoMapRankingEntry:
    path: str
    score: float
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": round(float(self.score), 6),
            "symbols": list(self.symbols),
        }


@dataclass(slots=True)
class RepoMapFileAnalysis:
    path: str
    byte_size: int
    line_count: int
    symbols: list[str] = field(default_factory=list)
    symbol_count: int = 0
    imports: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RepoMapArtifact:
    ok: bool
    generated_at: str
    provenance: dict[str, Any]
    stats: dict[str, Any]
    ranking: list[RepoMapRankingEntry]
    text: str
    error: dict[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "generated_at": self.generated_at,
            "provenance": dict(self.provenance),
            "stats": dict(self.stats),
            "ranking": [entry.to_dict() for entry in self.ranking],
            "text": self.text,
        }
        if self.error is not None:
            data["error"] = dict(self.error)
        return data


@dataclass(slots=True)
class RepoMapRunResult:
    artifact: RepoMapArtifact
    artifact_path: str | None = None
    session_artifact_path: str | None = None

    @property
    def ok(self) -> bool:
        return self.artifact.ok

    def to_dict(self) -> dict[str, Any]:
        data = self.artifact.to_dict()
        if self.artifact_path:
            data["artifact_path"] = self.artifact_path
        if self.session_artifact_path:
            data["session_artifact_path"] = self.session_artifact_path
        return data


def run_repomap(
    *,
    root: str | Path,
    repomap_config: Any | None = None,
    scope: list[str] | None = None,
    focus_files: list[str] | None = None,
    output_path: str | None = None,
    max_files: int | None = None,
    max_text_bytes: int | None = None,
    session_id: str | None = None,
    timeout_ms: int | None = None,
) -> RepoMapRunResult:
    start = time.perf_counter()
    root_path = Path(root).resolve()
    config_scope = _get_attr(repomap_config, "watch_paths", ["src"])
    config_ignored = _get_attr(repomap_config, "ignored_dirs", [])
    config_artifact = _get_attr(repomap_config, "artifact_path", ".cortex/artifacts/repomap/latest.json")
    config_max_files = _get_attr(repomap_config, "max_ranked_files", 20)
    config_max_text_bytes = _get_attr(repomap_config, "max_text_bytes", 8192)
    config_prefer_ast = bool(_get_attr(repomap_config, "prefer_ast_graph", True))
    requested_scope = [str(v) for v in (scope or config_scope or ["src"])]
    selected_scope = _select_scope(
        root_path,
        requested_scope=requested_scope,
        user_scope_supplied=scope is not None,
    )
    selected_focus = [str(v) for v in (focus_files or [])]
    selected_output = output_path or str(config_artifact)
    selected_max_files = max(1, int(max_files if max_files is not None else config_max_files))
    selected_max_text_bytes = max(
        256, int(max_text_bytes if max_text_bytes is not None else config_max_text_bytes)
    )
    selected_timeout_ms = timeout_ms
    missing_deps = repomap_missing_dependencies()
    # AST dependency-edge discovery is built-in; networkx is an optional quality boost.
    ast_mode_active = config_prefer_ast

    if not root_path.exists() or not root_path.is_dir():
        artifact = _failure_artifact(
            code="scan_failed",
            message=f"Project root does not exist or is not a directory: {root_path}",
            root=root_path,
            scope=selected_scope,
            focus_files=selected_focus,
            start=start,
            timeout_ms=selected_timeout_ms,
            failed_stage="discovery",
        )
        return RepoMapRunResult(artifact=artifact)

    if _timed_out(start, selected_timeout_ms):
        artifact = _failure_artifact(
            code="timeout",
            message="Repo-map generation timed out before discovery started.",
            root=root_path,
            scope=selected_scope,
            focus_files=selected_focus,
            start=start,
            timeout_ms=selected_timeout_ms,
            failed_stage="discovery",
        )
        return RepoMapRunResult(artifact=artifact)

    try:
        files = _discover_files(
            root=root_path,
            scope=selected_scope,
            ignored_dirs=[str(v) for v in config_ignored],
            timeout_check=lambda: _timed_out(start, selected_timeout_ms),
        )
    except TimeoutError:
        artifact = _failure_artifact(
            code="timeout",
            message="Repo-map generation timed out during file discovery.",
            root=root_path,
            scope=selected_scope,
            focus_files=selected_focus,
            start=start,
            timeout_ms=selected_timeout_ms,
            failed_stage="discovery",
        )
        return RepoMapRunResult(artifact=artifact)
    except OSError as exc:
        artifact = _failure_artifact(
            code="scan_failed",
            message=f"Failed during file discovery: {exc}",
            root=root_path,
            scope=selected_scope,
            focus_files=selected_focus,
            start=start,
            timeout_ms=selected_timeout_ms,
            failed_stage="discovery",
        )
        return RepoMapRunResult(artifact=artifact)

    analyses = _analyze_files(root_path, files)
    dependency_edges: list[tuple[str, str]] = []
    graph_scores: dict[str, float] = {}
    pagerank_backend = "none"
    method = "heuristic_fallback"
    if ast_mode_active:
        dependency_edges = _build_dependency_edges(analyses)
        graph_scores, pagerank_backend = _pagerank_scores_with_backend(
            [item.path for item in analyses], dependency_edges
        )
        method = "ast_pagerank"
    ranking = _rank_files(
        analyses,
        selected_focus,
        selected_max_files,
        graph_scores=graph_scores,
    )
    text = _render_text(ranking, selected_max_text_bytes)
    symbols_found = sum(item.symbol_count for item in analyses)
    artifact = RepoMapArtifact(
        ok=True,
        generated_at=_now_iso8601(),
        provenance={
            "method": method,
            "source_root": str(root_path),
            "scope": selected_scope,
            "focus_files": selected_focus,
            "duration_ms": _duration_ms(start),
            "timeout_ms": selected_timeout_ms,
            "ast_requested": config_prefer_ast,
            "ast_enabled": ast_mode_active,
            "missing_deps": missing_deps,
            "pagerank_backend": pagerank_backend,
        },
        stats={
            "files_parsed": len(files),
            "symbols_found": symbols_found,
            "graph_edges": len(dependency_edges),
            "byte_count": len(text.encode("utf-8")),
        },
        ranking=ranking,
        text=text,
    )

    latest_path = _resolve_output_path(root_path, selected_output)
    try:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        session_path: Path | None = None
        if session_id:
            session_path = root_path / ".cortex" / "artifacts" / "repomap" / f"{session_id}.json"
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session_path.write_text(
                json.dumps(artifact.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
    except OSError as exc:
        failed = _failure_artifact(
            code="write_failed",
            message=f"Failed to write repo-map artifact: {exc}",
            root=root_path,
            scope=selected_scope,
            focus_files=selected_focus,
            start=start,
            timeout_ms=selected_timeout_ms,
            failed_stage="write",
        )
        return RepoMapRunResult(artifact=failed)

    return RepoMapRunResult(
        artifact=artifact,
        artifact_path=str(latest_path),
        session_artifact_path=str(session_path) if session_id else None,
    )


def _discover_files(
    *,
    root: Path,
    scope: list[str],
    ignored_dirs: list[str],
    timeout_check: callable | None = None,
) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()
    ignored_names = set(DEFAULT_IGNORED_DIRS) | {str(v) for v in ignored_dirs}

    for scope_entry in scope or ["src"]:
        if timeout_check and timeout_check():
            raise TimeoutError("repo-map discovery timed out")
        target = (root / scope_entry).resolve() if not Path(scope_entry).is_absolute() else Path(scope_entry)
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if not target.exists():
            continue
        if target.is_file():
            rel = _norm_rel_path(target, root)
            if rel and rel not in seen and not _ignored(rel, ignored_names) and _is_text_candidate(target):
                discovered.append(rel)
                seen.add(rel)
            continue
        for dirpath, dirnames, filenames in os.walk(target):
            if timeout_check and timeout_check():
                raise TimeoutError("repo-map discovery timed out")
            current_dir = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not _ignored(_norm_rel_path(current_dir / d, root), ignored_names)]
            for filename in filenames:
                path = current_dir / filename
                rel = _norm_rel_path(path, root)
                if not rel or rel in seen or _ignored(rel, ignored_names):
                    continue
                if not _is_text_candidate(path):
                    continue
                discovered.append(rel)
                seen.add(rel)
    return sorted(discovered)


def _select_scope(root: Path, requested_scope: list[str], user_scope_supplied: bool) -> list[str]:
    normalized = [str(v) for v in requested_scope if str(v).strip()] or ["src"]
    if user_scope_supplied or _scope_targets_exist(root, normalized):
        return normalized
    fallback = [name for name in _FALLBACK_SCOPE_CANDIDATES if (root / name).exists()]
    return fallback or ["."]


def _scope_targets_exist(root: Path, scope: list[str]) -> bool:
    for entry in scope:
        target = Path(entry)
        if not target.is_absolute():
            target = root / target
        if target.exists():
            return True
    return False


def _analyze_files(root: Path, files: list[str]) -> list[RepoMapFileAnalysis]:
    analyses: list[RepoMapFileAnalysis] = []
    for rel in files:
        analyses.append(_analyze_file(root, rel))
    return analyses


def _analyze_file(root: Path, rel_path: str) -> RepoMapFileAnalysis:
    path = root / rel_path
    byte_size = 0
    line_count = 0
    symbols: list[str] = []
    symbol_count = 0
    imports: list[str] = []
    try:
        byte_size = path.stat().st_size
    except OSError:
        byte_size = 0
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        text = ""
    if text:
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        symbols, symbol_count, imports = _extract_symbols_and_imports(rel_path, text)
    return RepoMapFileAnalysis(
        path=rel_path,
        byte_size=byte_size,
        line_count=line_count,
        symbols=symbols,
        symbol_count=symbol_count,
        imports=imports,
    )


def _extract_symbols_and_imports(
    rel_path: str,
    text: str,
    max_symbols: int = 4,
) -> tuple[list[str], int, list[str]]:
    suffix = Path(rel_path).suffix.lower()
    if suffix == ".py":
        py_symbols, py_count, py_imports = _extract_python_symbols_and_imports(text, max_symbols=max_symbols)
        if py_count > 0 or py_imports:
            return py_symbols, py_count, py_imports
    symbols, count = _extract_symbol_summaries(text, max_symbols=max_symbols)
    imports = _extract_import_targets(text)
    return symbols, count, imports


def _extract_python_symbols_and_imports(
    text: str,
    *,
    max_symbols: int = 4,
) -> tuple[list[str], int, list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], 0, []

    seen: set[str] = set()
    summaries: list[str] = []
    count = 0
    imports: list[str] = []
    import_seen: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            label = f"class {node.name}"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            label = f"def {node.name}"
        else:
            label = ""
        if label and label not in seen:
            seen.add(label)
            count += 1
            if len(summaries) < max_symbols:
                summaries.append(label)

        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name.strip()
                if target and target not in import_seen:
                    import_seen.add(target)
                    imports.append(target)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * max(0, int(node.level))
            base = str(node.module or "").strip()
            if base:
                target = f"{prefix}{base}"
                if target not in import_seen:
                    import_seen.add(target)
                    imports.append(target)
                continue
            for alias in node.names:
                target = f"{prefix}{str(alias.name).strip()}"
                if target and target not in import_seen:
                    import_seen.add(target)
                    imports.append(target)

    return summaries, count, imports


def _extract_symbol_summaries(text: str, max_symbols: int = 4) -> tuple[list[str], int]:
    seen: set[str] = set()
    summaries: list[str] = []
    count = 0
    for line in text.splitlines():
        for pattern, kind in _SYMBOL_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            name = match.group(1)
            if not name:
                continue
            label = f"{kind} {name}"
            if label in seen:
                continue
            seen.add(label)
            count += 1
            if len(summaries) < max_symbols:
                summaries.append(label)
            break
    return summaries, count


def _extract_import_targets(text: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        for pattern in _IMPORT_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            target = str(match.group(1) or "").strip()
            if not target:
                continue
            if target not in seen:
                seen.add(target)
                targets.append(target)
            break
    return targets


def _render_entry_chunk(entry: RepoMapRankingEntry) -> str:
    lines = [f"{entry.path} ({entry.score:.3f})\n"]
    for symbol in entry.symbols:
        lines.append(f"  - {symbol}\n")
    return "".join(lines)


def _truncate_utf8(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    clipped = raw[:max_bytes]
    while clipped:
        try:
            return clipped.decode("utf-8")
        except UnicodeDecodeError as exc:
            clipped = clipped[: exc.start]
    return ""


def _build_dependency_edges(analyses: list[RepoMapFileAnalysis]) -> list[tuple[str, str]]:
    available_paths = {item.path for item in analyses}
    python_index = _build_python_module_index(available_paths)
    edges: set[tuple[str, str]] = set()
    for analysis in analyses:
        src = analysis.path
        suffix = Path(src).suffix.lower()
        for raw_target in analysis.imports:
            target = raw_target.split("?", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            dst = None
            if suffix == ".py":
                dst = _resolve_python_import(src, target, python_index)
            if dst is None:
                dst = _resolve_relative_import(src, target, available_paths)
            if dst and dst != src and dst in available_paths:
                edges.add((src, dst))
    return sorted(edges)


def _build_python_module_index(paths: set[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for rel in paths:
        path = Path(rel)
        if path.suffix.lower() != ".py":
            continue
        if path.name == "__init__.py":
            module_name = ".".join(path.parts[:-1])
        else:
            module_name = ".".join(path.with_suffix("").parts)
        if module_name and module_name not in index:
            index[module_name] = rel
    return index


def _resolve_python_import(source_path: str, target: str, index: dict[str, str]) -> str | None:
    if not target:
        return None
    module_name = target
    if target.startswith("."):
        level = len(target) - len(target.lstrip("."))
        module_tail = target[level:]
        source = Path(source_path)
        package_parts = (
            list(source.parts[:-1]) if source.name == "__init__.py" else list(source.with_suffix("").parts[:-1])
        )
        trim = max(0, level - 1)
        if trim > len(package_parts):
            return None
        base_parts = package_parts[: len(package_parts) - trim] if trim else package_parts
        tail_parts = [part for part in module_tail.split(".") if part]
        if not base_parts and not tail_parts:
            return None
        module_name = ".".join(base_parts + tail_parts)

    return index.get(module_name)


def _resolve_relative_import(source_path: str, target: str, available_paths: set[str]) -> str | None:
    if not target.startswith((".", "/")):
        return None
    source = PurePosixPath(source_path)
    raw = str(source.parent / target) if target.startswith(".") else target.lstrip("/")
    base = _normalize_rel(raw)
    if not base:
        return None
    if base in available_paths:
        return base
    base_path = PurePosixPath(base)
    if base_path.suffix:
        return None
    candidates: list[str] = []
    for suffix in _RELATIVE_IMPORT_SUFFIX_CANDIDATES:
        candidates.append(f"{base}{suffix}")
        candidates.append(str(PurePosixPath(base) / f"index{suffix}"))
    for candidate in candidates:
        normalized = _normalize_rel(candidate)
        if normalized and normalized in available_paths:
            return normalized
    return None


def _normalize_rel(path: str) -> str:
    parts: list[str] = []
    for piece in path.replace("\\", "/").split("/"):
        if piece in {"", "."}:
            continue
        if piece == "..":
            if not parts:
                return ""
            parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _pagerank_scores(paths: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    scores, _ = _pagerank_scores_with_backend(paths, edges)
    return scores


def _pagerank_scores_with_backend(
    paths: list[str], edges: list[tuple[str, str]]
) -> tuple[dict[str, float], str]:
    if not paths:
        return {}, "none"
    scores = _pagerank_scores_networkx(paths, edges)
    backend = "networkx"
    if not scores:
        scores = _pagerank_scores_simple(paths, edges)
        backend = "simple"
    peak = max(scores.values(), default=0.0)
    if peak <= 0:
        return ({path: 0.0 for path in paths}, backend)
    return ({path: float(scores.get(path, 0.0) / peak) for path in paths}, backend)


def _pagerank_scores_networkx(paths: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    try:
        import networkx as nx
    except Exception:  # noqa: BLE001
        return {}
    graph = nx.DiGraph()
    graph.add_nodes_from(paths)
    graph.add_edges_from(edges)
    if graph.number_of_nodes() == 0:
        return {}
    try:
        pagerank = nx.pagerank(graph, alpha=0.85)
    except Exception:  # noqa: BLE001
        return {}
    return {path: float(pagerank.get(path, 0.0)) for path in paths}


def _pagerank_scores_simple(
    paths: list[str],
    edges: list[tuple[str, str]],
    *,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> dict[str, float]:
    nodes = list(paths)
    n = len(nodes)
    if n == 0:
        return {}
    node_set = set(nodes)
    outgoing: dict[str, set[str]] = {node: set() for node in nodes}
    incoming: dict[str, set[str]] = {node: set() for node in nodes}
    for src, dst in edges:
        if src not in node_set or dst not in node_set:
            continue
        outgoing[src].add(dst)
        incoming[dst].add(src)

    rank = {node: 1.0 / n for node in nodes}
    base = (1.0 - alpha) / n
    for _ in range(max_iter):
        dangling = sum(rank[node] for node, outs in outgoing.items() if not outs)
        next_rank: dict[str, float] = {}
        diff = 0.0
        for node in nodes:
            inbound = 0.0
            for src in incoming[node]:
                outs = outgoing[src]
                if outs:
                    inbound += rank[src] / len(outs)
            value = base + alpha * (inbound + dangling / n)
            next_rank[node] = value
            diff += abs(value - rank[node])
        rank = next_rank
        if diff <= tol:
            break

    total = sum(rank.values())
    if total <= 0:
        return {node: 0.0 for node in nodes}
    return {node: float(value / total) for node, value in rank.items()}


def _rank_files(
    analyses: list[RepoMapFileAnalysis],
    focus_files: list[str],
    max_files: int,
    *,
    graph_scores: dict[str, float] | None = None,
) -> list[RepoMapRankingEntry]:
    graph_scores = graph_scores or {}
    focus = {str(v).replace("\\", "/") for v in focus_files}
    focus_basenames = {Path(path).name for path in focus}
    scored: list[RepoMapRankingEntry] = []
    for analysis in analyses:
        path = analysis.path.replace("\\", "/")
        path_obj = Path(path)
        suffix = path_obj.suffix.lower()
        depth = path.count("/")
        score = 1.0
        if suffix in _CODE_LIKE_SUFFIXES:
            score += 1.6
        score += _RANK_SUFFIX_BOOSTS.get(suffix, 0.0)
        if path in focus:
            score += 25.0
        elif path_obj.name in focus_basenames:
            score += 4.0
        score += max(0.0, 0.8 - min(depth, 10) * 0.08)
        score += min(1.5, analysis.symbol_count * 0.2)
        score += min(0.8, analysis.line_count / 400.0)

        stem = path_obj.stem.lower()
        for name, boost in _RANK_NAME_BOOSTS.items():
            if stem == name or stem.startswith(f"{name}_") or stem.endswith(f"_{name}"):
                score += boost
        for part in path_obj.parts[:-1]:
            score += _RANK_PATH_BOOSTS.get(part.lower(), 0.0)
            score -= _RANK_PATH_PENALTIES.get(part.lower(), 0.0)
        score -= _RANK_EXACT_FILENAME_PENALTIES.get(path_obj.name.lower(), 0.0)
        if "generated" in stem or "snapshot" in stem:
            score -= 0.4
        score += 2.0 * max(0.0, float(graph_scores.get(path, 0.0)))

        scored.append(
            RepoMapRankingEntry(
                path=path,
                score=max(0.0, score),
                symbols=list(analysis.symbols),
            )
        )
    scored.sort(key=lambda item: (-item.score, item.path))
    return scored[: max(0, max_files)]


def _render_text(ranking: list[RepoMapRankingEntry], max_text_bytes: int) -> str:
    if not ranking:
        return ""
    budget = max(256, max_text_bytes)
    chunks: list[tuple[str, int]] = []
    used = 0
    truncated = False
    total = len(ranking)

    for entry in ranking:
        chunk = _render_entry_chunk(entry)
        chunk_bytes = len(chunk.encode("utf-8"))
        if used + chunk_bytes > budget:
            truncated = True
            break
        chunks.append((chunk, chunk_bytes))
        used += chunk_bytes

    if truncated:
        note = f"... (truncated, showing {len(chunks)}/{total} files within {budget} bytes)\n"
        note_bytes = len(note.encode("utf-8"))
        while chunks and used + note_bytes > budget:
            _, removed_bytes = chunks.pop()
            used -= removed_bytes
            note = f"... (truncated, showing {len(chunks)}/{total} files within {budget} bytes)\n"
            note_bytes = len(note.encode("utf-8"))
        if used + note_bytes <= budget:
            chunks.append((note, note_bytes))
        else:
            return _truncate_utf8(note, budget)

    return "".join(chunk for chunk, _ in chunks)


def _resolve_output_path(root: Path, output_path: str) -> Path:
    candidate = Path(output_path)
    return candidate if candidate.is_absolute() else (root / candidate)


def _failure_artifact(
    *,
    code: str,
    message: str,
    root: Path,
    scope: list[str],
    focus_files: list[str],
    start: float,
    timeout_ms: int | None,
    failed_stage: str,
) -> RepoMapArtifact:
    return RepoMapArtifact(
        ok=False,
        generated_at=_now_iso8601(),
        provenance={
            "method": "none",
            "source_root": str(root),
            "scope": list(scope),
            "focus_files": list(focus_files),
            "duration_ms": _duration_ms(start),
            "timeout_ms": timeout_ms,
        },
        stats={
            "files_parsed": 0,
            "symbols_found": 0,
            "graph_edges": 0,
            "byte_count": 0,
        },
        ranking=[],
        text="",
        error={
            "code": code,
            "message": message,
            "retryable": code in {"deps_missing", "timeout", "scan_failed", "write_failed"},
            "failed_stage": failed_stage,
        },
    )


def _get_attr(config: Any, name: str, default: Any) -> Any:
    return getattr(config, name, default) if config is not None else default


def repomap_missing_dependencies() -> list[str]:
    missing: list[str] = []
    for package_name, module_name in _OPTIONAL_DEPENDENCIES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


def _now_iso8601() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _duration_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _timed_out(start: float, timeout_ms: int | None) -> bool:
    if timeout_ms is None:
        return False
    if timeout_ms <= 0:
        return True
    return _duration_ms(start) > timeout_ms


def _norm_rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return ""


def _ignored(rel_path: str, ignored_dirs: set[str]) -> bool:
    if not rel_path:
        return True
    parts = [part for part in rel_path.replace("\\", "/").split("/") if part]
    for part in parts[:-1]:
        if part in ignored_dirs:
            return True
    filename = parts[-1]
    if filename.startswith(".") and filename not in {".env", ".gitignore"}:
        return True
    if filename.endswith((".min.js", ".min.css", ".map")):
        return True
    return False


def _is_text_candidate(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        if path.stat().st_size > MAX_DISCOVER_FILE_BYTES:
            return False
    except OSError:
        return False
    if path.suffix.lower() in _BINARY_SUFFIXES:
        return False
    try:
        sample = path.read_bytes()[:READ_SAMPLE_BYTES]
    except OSError:
        return False
    return b"\x00" not in sample
