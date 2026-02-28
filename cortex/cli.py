from __future__ import annotations

import argparse
import json
import shlex
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .core import CortexKernel
from .genome import GENOME_SCHEMA_VERSION, load_genome
from .store import DB_SCHEMA_VERSION, SQLiteStore

REQUIRED_DB_TABLES = {"sessions", "graveyard", "invariants", "challenge_results", "events"}
REQUIRED_HOOK_COMMANDS = {
    "PreToolUse": "cortex.hooks.pre_tool_use",
    "PostToolUse": "cortex.hooks.post_tool_use",
    "Stop": "cortex.hooks.stop",
}
CLAUDE_DIRNAME = ".claude"
LEGACY_CLAUDE_DIRNAME = "claude"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return _run_init(args)

    if args.command == "check":
        return _run_check(args)

    if args.command == "fleet":
        return _run_fleet(args)

    if args.command == "graveyard":
        return _run_graveyard(args)

    if args.command == "repomap":
        return _run_repomap(args)

    if args.command == "init-db":
        root = Path(args.root).resolve()
        db_path = root / ".cortex" / "cortex.db"
        store = SQLiteStore(db_path)
        store.initialize()
        print(json.dumps({"ok": True, "db_path": str(db_path)}))
        return 0

    if args.command == "show-genome":
        genome = load_genome(Path(args.root).resolve() / "cortex.toml")
        print(json.dumps(genome.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "hook":
        payload = _read_payload(args.payload_file)
        kernel = CortexKernel(
            root=args.root,
            config_path=args.config_path,
            db_path=args.db_path,
            adapter_name=args.adapter,
        )
        result = kernel.dispatch(args.event, payload)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortex", description="Cortex hook kernel CLI")
    subparsers = parser.add_subparsers(dest="command")

    init = subparsers.add_parser("init", help="Bootstrap a new project with cortex.toml and storage")
    init.add_argument("--root", default=".", help="Target project root (default: current directory)")
    init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing cortex.toml in the target root",
    )

    check = subparsers.add_parser("check", help="Validate Cortex setup in the current project")
    check.add_argument("--root", default=".", help="Project root to validate (default: current directory)")
    check.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    check.add_argument(
        "--write-status",
        action="store_true",
        help="Write latest check report to .cortex/status.json",
    )

    fleet = subparsers.add_parser("fleet", help="Fleet-level Cortex operations")
    fleet_subparsers = fleet.add_subparsers(dest="fleet_command")
    fleet_status = fleet_subparsers.add_parser(
        "status", help="Check multiple project roots and summarize Cortex readiness"
    )
    fleet_status.add_argument(
        "--roots",
        nargs="+",
        required=True,
        help="One or more project roots to inspect",
    )
    fleet_status.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")

    graveyard = subparsers.add_parser("graveyard", help="List graveyard entries from .cortex/cortex.db")
    graveyard.add_argument("--root", default=".", help="Project root (default: current directory)")
    graveyard.add_argument("--limit", type=int, default=20, help="Max entries to show (default: 20)")

    repomap = subparsers.add_parser("repomap", help="Generate or inspect a repo-map artifact")
    repomap.add_argument("--root", default=".", help="Project root (default: current directory)")
    repomap.add_argument("--config-path", help="Override cortex.toml path")
    repomap_output = repomap.add_mutually_exclusive_group()
    repomap_output.add_argument(
        "--json", action="store_true", help="Print pure repo-map artifact JSON (repomap_artifact_v1)"
    )
    repomap_output.add_argument(
        "--debug-json", action="store_true", help="Print CLI/debug JSON envelope (artifact + metadata)"
    )
    repomap.add_argument("--output", help="Override artifact output path")
    repomap.add_argument("--stdout-text", action="store_true", help="Print text summary to stdout (when implemented)")
    repomap.add_argument("--scope", action="append", default=[], help="Limit scan scope path (repeatable)")
    repomap.add_argument("--focus-file", action="append", default=[], help="Prioritize a file path (repeatable)")
    repomap.add_argument("--max-files", type=int, help="Override max ranked files for this run")
    repomap.add_argument("--max-symbols", type=int, help="Reserved option for future symbol caps")
    repomap.add_argument("--max-text-bytes", type=int, help="Override text render byte cap for this run")
    repomap.add_argument(
        "--timeout-ms",
        type=int,
        help="Optional timeout for this CLI run (milliseconds). Omit for no CLI timeout.",
    )

    init_db = subparsers.add_parser("init-db", help="Initialize .cortex/cortex.db")
    init_db.add_argument("--root", default=".", help="Repository root (default: current directory)")

    show_genome = subparsers.add_parser("show-genome", help="Load and print cortex.toml")
    show_genome.add_argument("--root", default=".", help="Repository root (default: current directory)")

    hook = subparsers.add_parser("hook", help="Invoke a Cortex hook entrypoint")
    hook.add_argument("event", choices=["session-start", "pre-tool-use", "post-tool-use", "stop"])
    hook.add_argument("--root", default=".", help="Repository root (default: current directory)")
    hook.add_argument("--config-path", help="Override cortex.toml path")
    hook.add_argument("--db-path", help="Override SQLite database path")
    hook.add_argument(
        "--adapter",
        choices=["claude", "aider"],
        default="claude",
        help="Event adapter to normalize provider payloads (default: claude)",
    )
    hook.add_argument(
        "--payload-file",
        help="Read hook payload JSON from a file; otherwise reads JSON from stdin (or {} if empty).",
    )
    return parser


def _run_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    claude_dir = root / CLAUDE_DIRNAME
    managed_files = {
        root / "cortex.toml": _starter_config_toml(),
        claude_dir / "settings.json": _starter_claude_settings_json(sys.executable),
        claude_dir / "CLAUDE.md": _starter_claude_md(),
        root / "tests" / "invariants" / "example_invariant_test.py": _starter_invariant_test(),
    }
    existing_managed_files = [path for path in managed_files if path.exists()]
    if existing_managed_files and not args.force:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Refusing to overwrite existing Cortex-managed files. Use --force to overwrite.",
                    "existing": [str(path) for path in existing_managed_files],
                }
            ),
            file=sys.stderr,
        )
        return 1

    created: list[str] = []
    overwritten: list[str] = []
    root.mkdir(parents=True, exist_ok=True)

    invariants_dir = root / "tests" / "invariants"
    if not invariants_dir.exists():
        created.append(str(invariants_dir))
    invariants_dir.mkdir(parents=True, exist_ok=True)

    cortex_dir = root / ".cortex"
    if not cortex_dir.exists():
        created.append(str(cortex_dir))
    cortex_dir.mkdir(parents=True, exist_ok=True)

    if not claude_dir.exists():
        created.append(str(claude_dir))
    claude_dir.mkdir(parents=True, exist_ok=True)

    for path, content in managed_files.items():
        if path.exists():
            overwritten.append(str(path))
        else:
            created.append(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    db_path = cortex_dir / "cortex.db"
    if not db_path.exists():
        created.append(str(db_path))
    store = SQLiteStore(db_path)
    store.initialize()

    print(
        json.dumps(
            {
                "ok": True,
                "root": str(root),
                "created": created,
                "overwritten": overwritten,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    report = _collect_check_report(root)
    if args.write_status:
        report["status_artifact"] = _write_status_artifact(root, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_check_report(report)
    return 1 if report["summary"]["errors"] else 0


def _run_fleet(args: argparse.Namespace) -> int:
    if args.fleet_command != "status":
        print("Usage: cortex fleet status --roots <path...> [--json]", file=sys.stderr)
        return 1
    return _run_fleet_status(args)


def _run_fleet_status(args: argparse.Namespace) -> int:
    roots = [Path(p).resolve() for p in args.roots]
    reports = [_collect_check_report(root) for root in roots]
    payload = {
        "ok": all(r["summary"]["errors"] == 0 for r in reports),
        "generated_at": _now_iso(),
        "cortex_version": __version__,
        "projects": reports,
        "summary": {
            "projects": len(reports),
            "ok_projects": sum(1 for r in reports if r["summary"]["errors"] == 0),
            "warning_projects": sum(1 for r in reports if r["summary"]["warnings"] > 0),
            "error_projects": sum(1 for r in reports if r["summary"]["errors"] > 0),
        },
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_fleet_report(payload)
    return 0 if payload["ok"] else 1


def _collect_check_report(root: Path) -> dict[str, Any]:
    ok: list[str] = []
    warn: list[str] = []
    err: list[str] = []
    config_path = root / "cortex.toml"
    db_path = root / ".cortex" / "cortex.db"
    check_data: dict[str, Any] = {
        "root": str(root),
        "generated_at": _now_iso(),
        "cortex_version": __version__,
        "config_schema_version": GENOME_SCHEMA_VERSION,
        "config": {"path": str(config_path), "exists": config_path.exists(), "parse_error": None},
        "db": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "tables": [],
            "missing_tables": [],
            "schema_version": 0,
            "expected_schema_version": DB_SCHEMA_VERSION,
        },
        "hooks": {"settings_path": None, "legacy_settings_path": None, "valid": False},
        "invariants": {"paths": [], "missing_paths": []},
        "repomap": {"enabled": None, "prefer_ast_graph": None, "deps_missing": []},
        "ok": ok,
        "warnings": warn,
        "errors": err,
    }

    genome = None
    if not config_path.exists():
        err.append(f"Missing config file: {config_path}")
    else:
        genome = load_genome(config_path)
        check_data["config"]["parse_error"] = genome.parse_error
        if genome.parse_error:
            err.append(f"Config parse error in {config_path}: {genome.parse_error}")
        else:
            ok.append(f"Config parsed: {config_path}")

    if not db_path.exists():
        err.append(f"Missing database file: {db_path}")
    else:
        db_tables, db_schema_version, db_error = _inspect_db(db_path)
        check_data["db"]["tables"] = sorted(db_tables)
        check_data["db"]["schema_version"] = db_schema_version
        if db_error:
            err.append(f"Database check failed: {db_error}")
        else:
            missing_tables = sorted(REQUIRED_DB_TABLES - db_tables)
            check_data["db"]["missing_tables"] = missing_tables
            if missing_tables:
                err.append("Database missing required tables: " + ", ".join(missing_tables))
            else:
                ok.append(f"Database ready: {db_path} (required tables present)")
                if db_schema_version != DB_SCHEMA_VERSION:
                    warn.append(
                        f"Database schema version mismatch: found {db_schema_version}, expected {DB_SCHEMA_VERSION} "
                        "(run `cortex init-db --root <project>` to refresh metadata)"
                    )

    if genome and not genome.parse_error:
        check_data["invariants"]["paths"] = list(genome.invariants.suite_paths)
        check_data["repomap"]["enabled"] = genome.repomap.enabled
        check_data["repomap"]["prefer_ast_graph"] = genome.repomap.prefer_ast_graph

        if (
            genome.hooks.mode != "strict"
            and genome.hooks.fail_on_missing_challenge_coverage
            and genome.challenges.require_coverage
        ):
            warn.append(
                "hooks.fail_on_missing_challenge_coverage=true has no blocking effect while hooks.mode='advisory'; "
                "set [hooks].mode='strict' to enforce missing challenge coverage as a real gate"
            )
        if genome.hooks.require_structured_stop_payload and genome.hooks.allow_message_stop_fallback:
            warn.append(
                "hooks.require_structured_stop_payload=true while hooks.allow_message_stop_fallback=true; "
                "set allow_message_stop_fallback=false for fully deterministic structured stop gating"
            )

        if genome.invariants.suite_paths:
            for suite_path in genome.invariants.suite_paths:
                full_path = root / suite_path
                if not full_path.exists():
                    check_data["invariants"]["missing_paths"].append(suite_path)
                    warn.append(f"Invariant path missing (warning only): {suite_path}")
            if not check_data["invariants"]["missing_paths"]:
                ok.append(f"Invariant paths present: {len(genome.invariants.suite_paths)} configured")
        else:
            warn.append("No invariant suite paths configured in cortex.toml")
        _check_invariant_execution_mode(genome=genome, ok=ok, warn=warn)

        if genome.repomap.enabled:
            missing = _repomap_dependency_status() if genome.repomap.prefer_ast_graph else []
            check_data["repomap"]["deps_missing"] = list(missing)
            if genome.repomap.prefer_ast_graph and missing:
                warn.append(
                    "Repo-map enabled; optional ranking dependencies missing (AST graph + lightweight fallback remain available): "
                    + ", ".join(missing)
                    + " (install with: pip install -e '.[repomap]')"
                )
            elif genome.repomap.prefer_ast_graph:
                ok.append("Repo-map AST parser/ranking dependencies available")
            else:
                ok.append("Repo-map configured for heuristic-only mode (prefer_ast_graph=false)")
            repomap_artifact = root / genome.repomap.artifact_path
            check_data["repomap"]["artifact_path"] = str(repomap_artifact)
            check_data["repomap"]["artifact_exists"] = repomap_artifact.exists()
            if repomap_artifact.exists():
                ok.append(f"Repo-map artifact present: {repomap_artifact}")
            else:
                warn.append(
                    "Repo-map artifact missing (warning only): "
                    f"{genome.repomap.artifact_path} (run `cortex repomap --root {root}`)"
                )
        else:
            warn.append("Repo-map is disabled in cortex.toml (set [repomap].enabled = true to test it)")

    settings_path, legacy_settings_path = _resolve_claude_settings_path(root)
    check_data["hooks"]["settings_path"] = str(settings_path) if settings_path else None
    check_data["hooks"]["legacy_settings_path"] = (
        str(legacy_settings_path) if legacy_settings_path and legacy_settings_path.exists() else None
    )
    if settings_path is None:
        err.append(f"Missing Claude Code settings file: {root / CLAUDE_DIRNAME / 'settings.json'}")
    else:
        settings_error = _validate_claude_settings(settings_path)
        if settings_error:
            err.append(settings_error)
        else:
            check_data["hooks"]["valid"] = True
            ok.append(f"Claude hook wiring found in {settings_path}")
            if legacy_settings_path and legacy_settings_path.exists():
                warn.append(
                    "Legacy Claude settings also present at "
                    f"{legacy_settings_path}; prefer {root / CLAUDE_DIRNAME / 'settings.json'}"
                )

    check_data["summary"] = {"ok": len(ok), "warnings": len(warn), "errors": len(err)}
    check_data["status"] = "ok" if not err else "error"
    return check_data


def _run_graveyard(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    db_path = root / ".cortex" / "cortex.db"
    if not db_path.exists():
        print(f"Cortex graveyard: missing database at {db_path}", file=sys.stderr)
        return 1

    store = SQLiteStore(db_path)
    entries = store.list_graveyard(limit=max(1, args.limit))
    print(f"Cortex Graveyard ({root})")
    if not entries:
        print("No graveyard entries found.")
        return 0

    for entry in entries:
        print(f"[{entry['id']}] {entry['created_at']}")
        print(f"Summary: {entry['summary']}")
        print(f"Reason: {entry['reason']}")
        files = ", ".join(entry["files"]) if entry["files"] else "(none)"
        print(f"Files: {files}")
        print()
    return 0


def _run_repomap(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config_path = Path(args.config_path).resolve() if args.config_path else root / "cortex.toml"
    genome = load_genome(config_path)
    if genome.parse_error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "config_error",
                    "message": f"Failed to parse Cortex config: {genome.parse_error}",
                    "config_path": str(config_path),
                }
            ),
            file=sys.stderr,
        )
        return 1

    from .repomap import run_repomap

    result = run_repomap(
        root=root,
        repomap_config=genome.repomap,
        scope=[str(v) for v in args.scope] or None,
        focus_files=[str(v) for v in args.focus_file] or None,
        output_path=args.output,
        max_files=args.max_files,
        max_text_bytes=args.max_text_bytes,
        timeout_ms=args.timeout_ms,
    )
    payload = result.to_dict()
    payload["status"] = "ok" if result.ok else "error"
    payload["repomap"] = {
        "enabled": genome.repomap.enabled,
        "run_on_session_start": genome.repomap.run_on_session_start,
        "prefer_ast_graph": genome.repomap.prefer_ast_graph,
        "non_blocking": genome.repomap.non_blocking,
        "artifact_path": genome.repomap.artifact_path,
        "session_start_timeout_ms": genome.repomap.session_start_timeout_ms,
    }
    payload["requested"] = {
        "root": str(root),
        "config_path": str(config_path),
        "output": args.output or genome.repomap.artifact_path,
        "stdout_text": bool(args.stdout_text),
        "json": bool(args.json),
        "scope": [str(v) for v in args.scope],
        "focus_files": [str(v) for v in args.focus_file],
        "max_files": args.max_files if args.max_files is not None else genome.repomap.max_ranked_files,
        "max_symbols": args.max_symbols,
        "max_text_bytes": (
            args.max_text_bytes if args.max_text_bytes is not None else genome.repomap.max_text_bytes
        ),
        "timeout_ms": args.timeout_ms,
    }

    if args.json:
        print(json.dumps(result.artifact.to_dict(), indent=2, sort_keys=True))
    elif args.debug_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Cortex Repo-Map: {root}")
        print(f"Config: {config_path}")
        if result.ok:
            method = str(result.artifact.provenance.get("method", "heuristic_fallback"))
            if method == "ast_pagerank":
                print("Repo-map artifact generated (ast_pagerank mode).")
            else:
                print("Repo-map artifact generated (heuristic fallback mode).")
            if result.artifact_path:
                print(f"Artifact: {result.artifact_path}")
            stats = result.artifact.stats
            print(
                "Stats: "
                f"files_parsed={stats.get('files_parsed', 0)} "
                f"symbols_found={stats.get('symbols_found', 0)} "
                f"graph_edges={stats.get('graph_edges', 0)} "
                f"byte_count={stats.get('byte_count', 0)}"
            )
            if result.artifact.ranking:
                top_paths = ", ".join(entry.path for entry in result.artifact.ranking[:5])
                print(f"Top files: {top_paths}")
            else:
                print("Top files: (none)")
            if args.stdout_text and result.artifact.text:
                print()
                print(result.artifact.text, end="" if result.artifact.text.endswith("\n") else "\n")
        else:
            error = result.artifact.error or {}
            print(f"Repo-map generation failed: {error.get('code', 'unknown_error')}")
            print(error.get("message", "Unknown repo-map error"))
    return 0 if result.ok else 1


def _starter_config_toml() -> str:
    return """# Cortex project configuration (starter).
# Edit this file to point at your real invariant tests and project paths.

[project]
name = "your-project"
type = "generic"
root = "."

[invariants]
# External tests the agent did not author in the current task.
# Start with the invariants directory and add more explicit paths over time.
suite_paths = ["tests/invariants"]
pytest_bin = "pytest"
run_on_stop = true
# host: run pytest directly on this machine.
# container: run pytest inside a container boundary.
execution_mode = "host"
container_engine = "docker"
container_image = "python:3.11-slim"
container_workdir = "/workspace"

[invariants.graduation]
# Session-authored adversarial tests can be promoted here after review.
enabled = true
target_dir = "tests/invariants/graduated"

[challenges]
# Cortex checks coverage of each active category in the stop payload.
active_categories = [
  "null_inputs",
  "boundary_values",
  "error_handling",
  "graveyard_regression",
]
custom_paths = []
require_coverage = true

[graveyard]
# Failed approaches persist here and are surfaced in future sessions.
enabled = true
max_matches = 5
similarity_threshold = 0.35
min_keyword_overlap = 1

[foundation]
# Foundation analysis is advisory by default; tune paths and thresholds for your repo.
enabled = true
watch_paths = ["src"]
ignored_dirs = ["node_modules", "dist", "build", ".git", "__pycache__"]
churn_window_commits = 200

[foundation.stability_thresholds]
warn_churn_count = 8
high_churn_count = 15

[repomap]
# Optional Aider-inspired repo-map artifact generation (Sprint v1 graft path).
# Keep disabled until optional dependencies are installed:
#   pip install -e '.[repomap]'
enabled = false
run_on_session_start = false
# Use ast_pagerank when enabled; optional deps only improve ranking backend quality.
prefer_ast_graph = true
watch_paths = ["src"]
ignored_dirs = ["node_modules", "dist", "build", ".git", ".cortex", "__pycache__"]
max_ranked_files = 20
max_text_bytes = 8192
artifact_path = ".cortex/artifacts/repomap/latest.json"
non_blocking = true
session_start_timeout_ms = 2500

[hooks]
# advisory = warn only; strict = recommend revert on invariant failures.
mode = "advisory"
fail_on_missing_challenge_coverage = false
recommend_revert_on_invariant_failure = true
# Require a structured requirement audit in stop payload/trailer (advisory unless strict + fail_on_requirement_audit_gap).
require_requirement_audit = false
# In strict mode, revert when requirement audit is missing/invalid/incomplete.
fail_on_requirement_audit_gap = false
# Passed requirement entries must include evidence when true.
require_evidence_for_passed_requirement = true
# Structured payloads are the default hardening path for deterministic stop gates.
require_structured_stop_payload = true
# Message trailer parsing remains opt-in only and disabled by default.
allow_message_stop_fallback = false

[metrics]
enabled = true
track = [
  "human_oversight_minutes",
  "interrupt_count",
  "escaped_defects",
  "completion_minutes",
  "foundation_quality",
]
"""


def _starter_claude_settings_json(python_executable: str | None = None) -> str:
    text = _load_repo_template(
        "claude/settings.json",
        """{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m cortex.hooks.pre_tool_use"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m cortex.hooks.post_tool_use"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m cortex.hooks.stop"
          }
        ]
      }
    ]
  }
}
""",
    )
    if not python_executable:
        return text
    exe = shlex.quote(str(Path(python_executable)))
    return text.replace("python3 -m cortex.hooks.", f"{exe} -m cortex.hooks.")


def _starter_claude_md() -> str:
    return _load_repo_template(
        "claude/CLAUDE.md",
        """# Cortex Governance Instructions

Cortex is enforcing quality gates on this project via Claude Code hooks. Treat hook output as operational policy, not optional guidance.

The invariant suite runs on stop. In strict mode, invariant failures mean the safe default is revert and reassess before continuing.

Challenge categories must be covered and reported in the stop payload:

- `null_inputs`
- `boundary_values`
- `error_handling`
- `graveyard_regression`

The graveyard tracks failed approaches across sessions. If Cortex surfaces a graveyard warning, read it before proceeding and avoid repeating the same approach without a concrete change in conditions.

Foundation analysis flags unstable or high-churn files. If Cortex warns about churn, assess whether the target module is stable enough to build on before modifying it. If the foundation is weak, stabilize it first or explicitly justify the risk.

When finishing a task, report challenge coverage in the stop payload (`challenge_coverage`) so Cortex can evaluate category coverage mechanically.

If an approach fails, report it in the stop payload (`failed_approach`) with what was tried, why it failed, and which files were involved so it can be recorded in the graveyard.

When configured, report requirement traceability in the stop payload (`requirement_audit`) so Cortex can verify each prompt requirement has explicit status and evidence. If `required_requirement_ids` is provided, include every required ID in `requirement_audit.items`.

If direct stop-payload fields are not available in your Claude Code build, append a machine-readable trailer to your final assistant message so Cortex can parse it from `last_assistant_message`:

`CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true},"required_requirement_ids":["R1","R2"],"requirement_audit":{"items":[{"id":"R1","status":"pass","evidence":["src/app.ts:42"]},{"id":"R2","status":"fail","gap":"Missing accessibility review"}],"completeness_verdict":"fail"},"failed_approach":{"summary":"...","reason":"...","files":["path/to/file"]}}`

Use valid JSON on a single line. Omit `failed_approach` when nothing failed.

Session start integration note: Cortex provides `python3 -m cortex.hooks.session_start`, but `SessionStart` is not consistently available as a standard Claude Code hook event in all versions. If your Claude Code version supports `SessionStart`, wire it to that command in `.claude/settings.json`; otherwise rely on `PreToolUse`/`PostToolUse`/`Stop`.

Manual hook testing note: each hook module also accepts optional `--root` and `--config` arguments (for example `python3 -m cortex.hooks.stop --root /path/to/project --config /path/to/project/cortex.toml`). Claude Code does not need these because it runs hooks from the project root.
""",
    )


def _starter_invariant_test() -> str:
    return """from __future__ import annotations

from pathlib import Path


# Invariant tests are external constraints the current agent did not author.
# They encode project rules that should keep passing across sessions and tasks.
def test_cortex_config_exists() -> None:
    project_root = Path(__file__).resolve().parents[2]
    assert (project_root / "cortex.toml").exists()


# Example of a real invariant (commented out):
# def test_no_banned_imports() -> None:
#     project_root = Path(__file__).resolve().parents[2]
#     banned = "legacy_unsafe_module"
#     for path in project_root.rglob("*.py"):
#         if ".venv" in path.parts or ".cortex" in path.parts:
#             continue
#         assert banned not in path.read_text(encoding="utf-8")
"""


def _load_repo_template(rel_path: str, fallback: str) -> str:
    repo_template = Path(__file__).resolve().parents[1] / rel_path
    if repo_template.exists():
        return repo_template.read_text(encoding="utf-8")
    return fallback


def _inspect_db(db_path: Path) -> tuple[set[str], int, str | None]:
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            user_version_row = conn.execute("PRAGMA user_version").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return set(), 0, str(exc)
    user_version = int(user_version_row[0]) if user_version_row else 0
    return {str(row[0]) for row in rows}, user_version, None


def _check_invariant_execution_mode(*, genome: Any, ok: list[str], warn: list[str]) -> None:
    if genome.invariants.execution_mode == "host":
        warn.append(
            "invariants.execution_mode='host' runs tests on the host machine; use only for trusted repositories "
            "(switch to execution_mode='container' for stronger isolation)"
        )
        return
    engine = genome.invariants.container_engine.strip()
    if not engine:
        warn.append("invariants.execution_mode='container' but container_engine is empty; set [invariants].container_engine (for example 'docker') or switch to execution_mode='host'")
        return
    if shutil.which(engine):  # pragma: no branch
        ok.append(f"Invariant container engine available: {engine}")
        return
    warn.append(
        f"invariants.execution_mode='container' but container engine '{engine}' is not on PATH; install '{engine}' or switch to execution_mode='host'"
    )


def _repomap_dependency_status() -> list[str]:
    from .repomap import repomap_missing_dependencies
    return repomap_missing_dependencies()


def _resolve_claude_settings_path(root: Path) -> tuple[Path | None, Path | None]:
    preferred = root / CLAUDE_DIRNAME / "settings.json"
    legacy = root / LEGACY_CLAUDE_DIRNAME / "settings.json"
    if preferred.exists():
        return preferred, legacy
    if legacy.exists():
        return legacy, None
    return None, legacy


def _validate_claude_settings(settings_path: Path) -> str | None:
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return f"Failed to read {settings_path}: {exc}"

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return f"Invalid {settings_path}: missing top-level hooks object"

    for event_name, command_fragment in REQUIRED_HOOK_COMMANDS.items():
        event_entries = hooks.get(event_name)
        if not isinstance(event_entries, list):
            return f"Invalid {settings_path}: missing hooks.{event_name} list"
        if not _event_contains_command(event_entries, command_fragment):
            return (
                f"Invalid {settings_path}: hooks.{event_name} does not contain "
                f"command fragment '{command_fragment}'"
            )
    return None


def _event_contains_command(event_entries: list[Any], command_fragment: str) -> bool:
    for entry in event_entries:
        if not isinstance(entry, dict):
            continue
        nested_hooks = entry.get("hooks")
        if not isinstance(nested_hooks, list):
            continue
        for hook in nested_hooks:
            if not isinstance(hook, dict):
                continue
            command = hook.get("command")
            if isinstance(command, str) and command_fragment in command:
                return True
    return False


def _print_check_section(title: str, items: list[str]) -> None:
    print(f"{title}:")
    if not items:
        print("  (none)")
        return
    for item in items:
        print(f"  - {item}")


def _print_check_report(report: dict[str, Any]) -> None:
    print(f"Cortex Check: {report['root']}")
    _print_check_section("OK", report["ok"])
    _print_check_section("Needs Attention", report["warnings"])
    _print_check_section("Missing / Errors", report["errors"])
    summary = report["summary"]
    print(f"Summary: {summary['ok']} ok, {summary['warnings']} warnings, {summary['errors']} errors")


def _print_fleet_report(payload: dict[str, Any]) -> None:
    print("Cortex Fleet Status")
    for report in payload["projects"]:
        summary = report["summary"]
        status = "OK" if summary["errors"] == 0 else "ERROR"
        print(
            f"- {report['root']} [{status}] "
            f"ok={summary['ok']} warnings={summary['warnings']} errors={summary['errors']}"
        )
    summary = payload["summary"]
    print(
        "Fleet Summary: "
        f"projects={summary['projects']} ok_projects={summary['ok_projects']} "
        f"warning_projects={summary['warning_projects']} error_projects={summary['error_projects']}"
    )


def _write_status_artifact(root: Path, report: dict[str, Any]) -> str:
    status_path = root / ".cortex" / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(status_path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_payload(payload_file: str | None) -> dict[str, Any]:
    if payload_file:
        raw = Path(payload_file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    raw = raw.strip()
    if not raw:
        return {}
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("Hook payload must decode to a JSON object")
    return decoded


if __name__ == "__main__":
    raise SystemExit(main())
