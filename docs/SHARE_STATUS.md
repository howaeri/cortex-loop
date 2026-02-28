# Cortex Share Status (Alpha)

Last updated: 2026-02-28

This file is the quick truth for external reviewers: what works today, what is still in progress, and what is explicitly not being claimed yet.

## Working now

| Area | Status |
| --- | --- |
| Hook kernel (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`) | Working |
| Invariants + challenge gate + requirement audit | Working |
| Graveyard persistence + repeat-warning matching | Working |
| Foundation churn warnings | Working |
| Repo-map artifact output (`repomap_artifact_v1`) | Working |
| Adapter boundary (`claude`, `aider`) | Working (`aider` is alpha/minimal) |

## Not claimed yet

| Area | Status |
| --- | --- |
| Aider graft maturity | Alpha (operational, not parity-complete) |
| Aider repo-map parity across mixed production-style repos | Not complete |
| Full parity exit packet (`parity-exit-report.md`) | Not complete |

## Why parity is still open

The implementation path is in place, but we still need consistent quality evidence across multiple repo types (frontend-heavy, backend-heavy, mixed monorepo) with relevance and runtime gates from `docs/REPOMAP_PARITY_CRITERIA.md`.

## Quick verification

```bash
pip install -e '.[dev,repomap]'
pytest -q
ruff check cortex tests
```

```bash
cortex check --root /path/to/project
cortex repomap --root /path/to/project --json
```

Expected repo-map contract:
- `schema_version = "repomap_artifact_v1"`
- `provenance.method` in `{ "ast_pagerank", "heuristic_fallback", "none" }`
- when `provenance.method = "ast_pagerank"`, backend in `{ "networkx", "simple" }`

## Canonical pointers

- Start point: `START_HERE.md`
- Active backlog: `todos.md`
- Architecture: `ARCHITECTURE.md`
- Mission: `MISSION.md`
- Maintainer essay: `docs/WHY_CORTEX.md`
- Repro demo: `docs/DEMO.md`
- Release gate: `docs/RELEASE_CHECKLIST.md`
- Evidence index: `docs/evidence/RUN_INDEX.md`
