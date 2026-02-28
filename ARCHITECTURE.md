# Cortex Architecture

This document is the technical map of Cortex as it exists today.

Design intent is simple: keep the hook surface thin, keep policy in the kernel, keep each subsystem focused on one job.

## System overview

```text
Claude/Aider event
  -> hooks/*.py
  -> CortexKernel (core.py)
  -> subsystems (genome, store, foundation, graveyard, challenges, invariants, repomap)
  -> structured JSON response
```

The kernel is orchestration. Subsystems hold behavior.

## Load-bearing components

### `core.py` (kernel)

Responsibilities:
- initialize config + storage
- dispatch normalized hook events
- coordinate subsystem calls
- return stable JSON contracts

Entry points:
- `on_session_start`
- `on_pre_tool_use`
- `on_post_tool_use`
- `on_stop`

`core.py` intentionally does not implement ranking, parsing, persistence, or test execution logic directly.

### `genome.py` (config loader)

- Reads `cortex.toml` with `tomllib`
- Maps config into dataclasses
- Applies defaults when config is missing
- Surfaces parse errors without crashing kernel startup

### `store.py` (SQLite persistence)

- Owns `.cortex/cortex.db`
- Raw `sqlite3`, no ORM
- WAL mode + foreign keys
- bounded retry/backoff for transient lock contention

Tables:
- `sessions`
- `graveyard`
- `invariants`
- `challenge_results`
- `events`

### `invariants.py` (external quality gate)

- Runs external pytest suites via subprocess
- Returns per-path + aggregate pass/fail/error
- Supports test graduation into permanent invariants
- In strict mode, invariant failure feeds revert recommendation

Execution modes:
- `host` (default)
- `container` (safer for untrusted repos)

### `challenges.py` (coverage policy)

Built-in required categories:
- `null_inputs`
- `boundary_values`
- `error_handling`
- `graveyard_regression`

The agent can choose specific tests, but cannot skip active categories.

### `graveyard.py` (failure memory)

- Records failed approaches with summary/reason/files/keywords
- Finds similar prior failures at session start and failure points
- Uses deterministic hybrid scoring:
  - TF-IDF-weighted keyword overlap
  - semantic token overlap
  - file-path overlap
- Optional FTS5 narrows candidates when available

### `foundation.py` (stability check)

- Uses git history to detect high-churn files/modules
- Returns `FoundationReport`
- Advisory by default; warns before edits on unstable areas

### `repomap.py` (artifact generator)

- Emits `repomap_artifact_v1`
- Two modes:
  - `ast_pagerank` when enabled
  - `heuristic_fallback` otherwise
- Writes artifact to `.cortex/artifacts/repomap/latest.json`
- Non-blocking failures with structured error envelope

### `adapters.py` (provider normalization)

- Converts provider payloads to Cortex event schema
- Current adapters:
  - `ClaudeCodeAdapter`
  - `AiderAdapter` (alpha/minimal normalization)

This boundary keeps kernel policy provider-agnostic.

### `stop_contract.py` + `stop_policy.py`

- `stop_contract.py` resolves stop payload source/shape and validates required structure
- `stop_policy.py` computes deterministic final session status and revert recommendation

This keeps stop logic testable and out of `core.py`.

### `hooks/` (integration surface)

Scripts:
- `session_start.py`
- `pre_tool_use.py`
- `post_tool_use.py`
- `stop.py`

Behavior:
- read JSON from stdin
- accept optional `--root` and `--config`
- instantiate kernel
- call one entry point
- print JSON to stdout

## Hook integration map

```text
SessionStart
  -> on_session_start
  -> genome + store + foundation + graveyard (+ optional repomap)

PreToolUse
  -> on_pre_tool_use
  -> store event + foundation target-file warnings

PostToolUse
  -> on_post_tool_use
  -> store event + graveyard check on failure signals

Stop
  -> on_stop
  -> stop_contract normalization
  -> challenge coverage evaluation
  -> invariant execution
  -> failed approach persistence
  -> stop_policy decision
  -> session close
```

## SQLite schema (reference)

```sql
sessions (
  session_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  status TEXT NOT NULL,
  genome_path TEXT,
  metadata_json TEXT NOT NULL
);

graveyard (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  summary TEXT NOT NULL,
  reason TEXT NOT NULL,
  files_json TEXT NOT NULL,
  keywords_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

invariants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  test_path TEXT NOT NULL,
  status TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  stdout TEXT NOT NULL,
  stderr TEXT NOT NULL,
  graduated_from TEXT,
  created_at TEXT NOT NULL
);

challenge_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  category TEXT NOT NULL,
  covered INTEGER NOT NULL,
  evidence_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  hook TEXT NOT NULL,
  tool_name TEXT,
  status TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

Indexes are applied on hot lookup paths (`events`, `graveyard`, `challenge_results`, `invariants`).

## Extension points

- Custom challenge templates: add paths via `challenges.custom_paths`.
- Custom invariants: point `invariants.suite_paths` to project-specific suites.
- Custom foundation checks: extend `FoundationAnalyzer` while keeping advisory/blocking behavior explicit.
- Adapter expansion: add provider adapters without changing kernel policy.

## Stability contracts

These are treated as compatibility surfaces:
- Hook request/response JSON shape
- `repomap_artifact_v1` schema
- SQLite table names and core columns

If one changes, it must be versioned or explicitly documented in upgrade notes.
