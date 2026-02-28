# Sprint 2 Summary

Date: 2026-02-27
Status: completed

## Scope completed

- Workstream A: Graveyard matcher now uses optional FTS5/BM25 candidate narrowing with deterministic Python scoring fallback.
- Workstream B: `cortex check` now preflights `invariants.execution_mode = "container"` and warns when engine is missing.
- Workstream C: Store write path remains lock-resilient and now has bounded concurrent write stress coverage.
- Workstream D: Compression pass completed; net LOC increase is within sprint budget target.

## Verification

- Test suite: `109 passed`
- Lint: `All checks passed`

See:
- `99-final-pytest.txt`
- `99-final-ruff.txt`

## Line budget

Baseline (`00-baseline-lines.txt`):
- graveyard.py 178
- invariants.py 168
- store.py 291
- cli.py 731

Final (`99-final-lines.txt`):
- graveyard.py 186
- invariants.py 168
- store.py 345
- cli.py 747

Net delta: +78 lines (target <= +80 met).

## Evidence files

- `graveyard-quality-cases.md`
- `container-mode-checks.md`
- `sqlite-lock-stress.md`
- `99-final-lines.txt`
- `99-final-pytest.txt`
- `99-final-ruff.txt`
