# TESTING V1 Repo-Map Scope (Contract Freeze)

Status: Drafted for Sprint 1 Day 1 (M0)  
Scope: `v1 usable for testing` only (Aider repo-map graft)  
Decision date: 2026-02-26

Historical note: this document is preserved as-written intent from the original planning pass. It is not active planning authority.

## Goal (Copied / Re-anchored)

Deliver a **v1 testing-capable** Cortex repo-map graft inspired by Aider that improves codebase discovery on real tasks without weakening existing quality gates or blocking Claude Code sessions.

In practical terms, v1 means:

- Cortex can generate a repo-map artifact as a first-class artifact
- The repo-map path is optional-dependency and non-blocking
- We can testing it on real tasks and measure whether it reduces discovery churn (`grep/find` thrash, "where is X?" interruptions)

## Non-Goals (Copied / Re-anchored)

This document intentionally excludes:

- SWE-agent ACI corrective error loops
- LangGraph checkpoint/shadow runtime work
- Multi-agent orchestration
- Prompt/policy redesign unrelated to repo-map
- Large runtime refactors unrelated to repo-map delivery

## Architecture Decision (Locked for v1)

### Chosen Option: `Option A`

Host the repo-map graft as an **optional Python module inside this package**:

- Target module: `cortex/repomap.py`
- CLI entry path: `cortex repomap`
- Hook integration: `SessionStart` (config-gated, non-blocking)

### Why `Option A` (and not `Option B`)

`Option A` keeps the repo-map logic inside Cortex's tested/runtime contract:

- easier unit/integration testing in `tests/`
- easier artifact/path integration with `.cortex/`
- easier packaging (`pip install -e '.[repomap]'`)
- easier observability via existing store/events

`Option B` (external helper script) remains a fallback strategy if dependency or packaging friction becomes a blocker, but it is **not** the v1 plan.

## Dependency Strategy (Locked for v1)

### Packaging approach

Use a **`pyproject.toml` optional dependency extra**:

- Extra name: `repomap`
- Install command (dev/testing): `pip install -e '.[repomap]'`

Runtime behavior remains import-guarded:

- If repo-map deps are missing, `cortex repomap` returns an actionable error/warning
- `cortex check` warns (does not fail) on missing repo-map deps
- `SessionStart` continues without blocking

### Exact dependency pins (initial v1 pins)

Pinned to the Aider research snapshot ecosystem for first implementation parity:

- `grep-ast==0.9.0`
- `networkx==3.4.2`
- `tree-sitter-language-pack==0.13.0`
- `tree-sitter==0.25.2`

Notes:

- These versions match the pinned Aider snapshot dependency set observed in the local research clone (`requirements.txt`) at the time of this decision.
- If resolver conflicts occur during implementation, prefer preserving:
  - `grep-ast==0.9.0`
  - `networkx==3.4.2`
  and document any tree-sitter compatibility adjustment in this file before changing pins.

## Provenance + License Decision (Locked for v1)

### Source snapshot

- Source repo: Aider
- Snapshot commit: `7afaa26f8b8b7b56146f0674d2a67e795b616b7c`
- License: Apache-2.0
- Pinned snapshot record:
  - internal source snapshot registry (private, not published in this repo)

### Source paths (initial graft scope)

Primary mechanism source paths under the pinned snapshot:

- `aider/repomap.py` (AST tag extraction, graph ranking, compact tree rendering)

Referenced only for understanding / exclusions (not for direct reuse in v1 runtime):

- `aider/special.py` (important-file filtering behavior; v1 likely reimplements a simpler ignore/scope policy)
- Aider chat/IO/UI modules (explicitly excluded from graft)

### Extraction stance (v1)

This graft is **ADAPT**, not vendoring:

- Extraction stance: `ADAPT`
- Code copied directly: `No` (behavior reimplemented)
- Allowed carryover:
  - algorithm/flow ideas (AST tag extraction pipeline, graph ranking, pagerank-style ranking, compact tree render concept)
  - small snippets only if later proven necessary and license/provenance is recorded inline
- Disallowed in v1:
  - wholesale copying of `repomap.py`
  - Aider chat history weighting
  - GUI spinner / IO stack
  - Aider caching layer

### Cortex-specific modifications required by design

Even where behavior is inspired by Aider, Cortex changes the integration model:

- artifact-first output (`.cortex/artifacts/repomap/*.json`) instead of prompt text injection
- config-gated + non-blocking hook integration
- stable hook response contract (stdin JSON -> stdout JSON preserved)
- proof/benchmark tracking against Cortex metrics (not anecdotal usefulness claims)

## Graft Discipline Addendum (Anti-Reinvention, Locked for v1)

This v1 effort is a **graft project**, not a greenfield invention project.

That means:

- we should prefer adapting proven repo-map mechanisms over inventing new ones,
- we should only reimplement where Cortex's constraints require it,
- and we should document where we intentionally deviate from Aider's behavior.

### Practical rule for implementation decisions

Before adding non-trivial repo-map logic, confirm in notes/PR:

1. what Aider mechanism/path we inspected,
2. whether the new code is `vendor`, `adapt`, or `reimplement`,
3. why Cortex constraints require the chosen approach,
4. what behavior-parity check we will run (or why parity is not applicable yet).

### Temporary fallback policy (important)

Heuristic fallback implementations are allowed for testability and integration testing, but they must be treated as:

- **temporary**, and
- **not evidence that the Aider graft is complete**.

A heuristic fallback is successful only if it unblocks integration/proof work while a concrete parity task remains on the milestone path (AST extraction, graph edges, ranking quality).

## Complexity Budget Addendum (v1 Repo-Map Graft)

This v1 graft should favor **small, load-bearing integration steps** over broad subsystem expansion.

Practical implications for repo-map v1:

- prioritize artifact generation + hook integration + proof instrumentation before ranking sophistication
- prefer a thin adapter around proven OSS mechanisms over a novel Cortex-specific repo-map architecture
- add observability/provenance fields before adding more algorithmic knobs
- do not expand the kernel/hook contract unless v1 proof data shows it is necessary

v1 success is not "most advanced repo-map."  
v1 success is "small graft, measurable behavior improvement, no moat regression."

## `repomap_artifact_v1` Contract (Frozen for v1)

### Contract name

- Schema version string: `repomap_artifact_v1`

### Artifact locations (v1)

Primary output path:

- `.cortex/artifacts/repomap/latest.json`

Optional session-scoped archival path (when `session_id` is known):

- `.cortex/artifacts/repomap/<session_id>.json`

Behavior:

- `latest.json` is the canonical path used by hooks/CLI consumers
- Session copy is best-effort and optional in v1
- Failure artifacts are allowed and use the same schema envelope with `ok: false`

### Top-level JSON shape (normative)

Required top-level fields:

- `schema_version` (`string`) must equal `"repomap_artifact_v1"`
- `ok` (`boolean`)
- `generated_at` (`string`, ISO8601 UTC)
- `provenance` (`object`)
- `stats` (`object`)
- `ranking` (`array`)
- `text` (`string`)

Optional top-level fields:

- `error` (`object`) required when `ok == false`, absent on successful generation unless reporting degraded/partial output

### Field definitions (normative)

#### `schema_version`

- Type: `string`
- Value: `"repomap_artifact_v1"`

#### `ok`

- Type: `boolean`
- Meaning:
  - `true`: artifact generation succeeded enough to produce usable ranking/text
  - `false`: generation failed or timed out (non-blocking failure envelope)

#### `generated_at`

- Type: `string`
- Format: ISO8601 UTC timestamp (example: `2026-02-26T19:15:42Z`)
- Meaning: time the artifact (success or failure envelope) was written

#### `provenance`

Type: object. Required fields:

- `method` (`string`)
  - v1 values:
    - `ast_pagerank`
    - `heuristic_fallback` (if implemented later)
    - `none` (failure envelope only, if no map generated)
- `source_root` (`string`)
  - absolute path to analyzed project root
- `scope` (`array[string]`)
  - configured include roots / scan scope used for this generation
- `focus_files` (`array[string]`)
  - files explicitly prioritized by caller context (may be empty)

Optional fields (reserved for v1/v1.1, safe to omit initially):

- `session_id` (`string`)
- `duration_ms` (`integer`)
- `timeout_ms` (`integer`)
- `generator_version` (`string`)

#### `stats`

Type: object. Required fields:

- `files_parsed` (`integer`, >= 0)
- `symbols_found` (`integer`, >= 0)
- `graph_edges` (`integer`, >= 0)

At least one size metric must be present:

- `token_count` (`integer`, >= 0), optional in v1
- `byte_count` (`integer`, >= 0), required in v1 if `token_count` unavailable

v1 decision:

- `byte_count` is the required size metric for initial implementation
- `token_count` is optional and may be added later

#### `ranking`

Type: array of ranking entries. May be empty on failure.

Each ranking entry is an object with required fields:

- `path` (`string`) project-relative path
- `score` (`number`) ranking score (float; normalized scale not guaranteed)
- `symbols` (`array[string]`) compact symbol summaries for the file (may be empty)

Ordering requirements:

- sorted descending by `score`
- deterministic tie-breaker by `path` ascending

#### `text`

- Type: `string`
- Meaning: compact human/LLM-readable repo-map render
- May be empty when `ok == false`
- Should be bounded/truncated in implementation; truncation should preserve valid UTF-8 text

#### `error` (required when `ok == false`)

Type: object. Required fields:

- `code` (`string`)
- `message` (`string`)
- `retryable` (`boolean`)

Optional fields:

- `details` (`object`)
- `failed_stage` (`string`) e.g. `dependency_check`, `discovery`, `parse`, `ranking`, `render`, `write`

Initial `code` values for v1:

- `deps_missing`
- `timeout`
- `scan_failed`
- `parse_failed`
- `ranking_failed`
- `render_failed`
- `write_failed`
- `internal_error`

### Success example (`repomap_artifact_v1`)

```json
{
  "schema_version": "repomap_artifact_v1",
  "ok": true,
  "generated_at": "2026-02-26T19:15:42Z",
  "provenance": {
    "method": "ast_pagerank",
    "source_root": "/abs/path/to/project",
    "scope": [
      "src",
      "tests"
    ],
    "focus_files": [
      "src/app.ts"
    ],
    "duration_ms": 842,
    "timeout_ms": 2500
  },
  "stats": {
    "files_parsed": 120,
    "symbols_found": 850,
    "graph_edges": 2100,
    "byte_count": 9872
  },
  "ranking": [
    {
      "path": "src/core.ts",
      "score": 0.1532,
      "symbols": [
        "class Engine",
        "function init"
      ]
    },
    {
      "path": "src/utils.ts",
      "score": 0.0811,
      "symbols": [
        "function helper"
      ]
    }
  ],
  "text": "src/core.ts\\n  class Engine\\n  function init\\nsrc/utils.ts\\n  function helper\\n"
}
```

### Failure envelope example (non-blocking)

```json
{
  "schema_version": "repomap_artifact_v1",
  "ok": false,
  "generated_at": "2026-02-26T19:16:03Z",
  "provenance": {
    "method": "none",
    "source_root": "/abs/path/to/project",
    "scope": [
      "src"
    ],
    "focus_files": [],
    "duration_ms": 19,
    "timeout_ms": 2500
  },
  "stats": {
    "files_parsed": 0,
    "symbols_found": 0,
    "graph_edges": 0,
    "byte_count": 0
  },
  "ranking": [],
  "text": "",
  "error": {
    "code": "deps_missing",
    "message": "Repo-map dependencies are not installed. Install with: pip install -e '.[repomap]'",
    "retryable": true,
    "failed_stage": "dependency_check"
  }
}
```

## Performance Budgets (v1 targets)

These are target budgets used to evaluate acceptance, not hard guarantees yet.

### `cortex repomap` CLI (user-invoked)

Target repo size for budgeting ("medium repo"):

- ~5k-50k LOC
- <= 400 source files in configured scan scope
- local filesystem (no network)

Budget targets:

- median runtime: `<= 2s`
- p95 runtime: `<= 5s`

### `SessionStart` added latency (repo-map enabled)

Budget targets for synchronous hook path:

- median added latency: `<= 1s`
- p95 added latency: `<= 3s`

Design implication:

- repo-map generation must be timeout-bounded and non-blocking
- hooks may skip repo-map generation rather than exceed latency budgets

## Timeout + Fallback Behavior (v1, non-blocking)

### Timeouts (decision)

- `SessionStart` repo-map attempt timeout: `2500ms` default
- `cortex repomap` CLI timeout: no hard default timeout in v1 (user-invoked command may run longer), but command should support a timeout flag when implemented

### Fallback behavior (required)

Repo-map failures must **not** block a session or tool hook.

On any repo-map failure (`deps_missing`, timeout, parser error, ranking error):

1. Hook continues and returns normal `ok/proceed` behavior.
2. Cortex records an event with repo-map status (success/failure code).
3. Cortex may write a failure artifact envelope (`ok: false`) to `latest.json`.
4. Hook response includes a warning/advisory message (not a hard stop).

### What v1 does *not* do (yet)

- No background worker/asynchronous retries
- No artifact freshness cache policy beyond "last artifact wins"
- No hook-time auto-reuse scoring of older artifacts

Those can be added after v1 proves usefulness.

## Proof Worksheet Template (M0 requirement)

Use this template to capture baseline vs repo-map runs before claiming improvement.

Copy into a new file (for example `docs/proof/repomap_v1_baseline.md`) and fill per task.

```markdown
# Repo-Map v1 Proof Worksheet

## Run Metadata

- Date:
- Repo:
- Branch:
- Task ID / Summary:
- Scenario size (small/medium/large):
- Cortex commit:
- Repo-map mode: baseline (off) / on

## Quantitative Metrics

| Metric | Baseline (repo-map off) | Repo-map on | Delta | Notes |
| :--- | ---: | ---: | ---: | :--- |
| Time to first valid edit (min) |  |  |  |  |
| `grep/find/rg` discovery calls (count) |  |  |  |  |
| Interruptions asking "where is X?" (count) |  |  |  |  |
| Total completion time (min) |  |  |  |  |
| Repo-map generation runtime (ms) | n/a |  |  |  |
| SessionStart added latency (ms) | n/a |  |  |  |

## Qualitative Assessment

- Did the repo-map surface the right files early?
- Did it miss critical files/symbols?
- Was ranking order useful?
- Any regressions (noise, latency, wrong focus)?

## Verdict

- Useful enough to keep testing? yes / no
- Immediate fixes required before wider use:
```

## Implementation Guardrails (restate, so we don't drift)

- Repo-map output is an **artifact**, not auto-injected prompt prose.
- Repo-map deps are **optional**; core import path remains usable without them.
- Hook contract is load-bearing; repo-map failures are advisory/non-blocking.
- No SWE-agent ACI or checkpoint work is allowed inside this v1 scope.

## Day 1 Exit Criteria (This Document Covers)

This file is intended to satisfy Sprint Day 1 decisions before code work starts:

- artifact contract frozen (`repomap_artifact_v1`)
- dependency stack selected (exact initial pins)
- provenance/license notes recorded (snapshot + source path + stance)
- optional dependency packaging approach selected
- performance budgets defined
- timeout/fallback behavior defined
