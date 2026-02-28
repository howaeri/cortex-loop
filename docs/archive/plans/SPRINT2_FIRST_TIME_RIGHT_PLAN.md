# Sprint 2 First-Time-Right Plan

Date: 2026-02-27
Status: completed
Owner: Cortex core

## 1) Sprint intent

Sprint 2 was not a feature sprint. The goal was to make the existing safety/matching/resilience stack correct, compact, and hard to regress.

Primary goal:
- Make Cortex do the right thing on first execution without requiring prompt retries or manual cleanup.

Secondary goal:
- Keep code footprint tight. New behavior must come with offsetting deletions where possible.

## 2) Constraints

- Core runtime stays stdlib-only.
- No contract regressions in hook responses.
- Every behavior change must have a failing test first.
- Net complexity budget is bounded:
  - Target: net LOC <= +80 across sprint.
  - Stretch: net LOC <= 0 after cleanup pass.
- Any helper that saves less than ~8 repeated lines should not be added.

## 3) Definition of "right first time"

A Sprint 2 change was accepted only if all were true:

1. Correctness:
- The new path is covered by focused tests and full suite remains green.

2. Determinism:
- For same inputs + same DB state, outputs match exactly (ordering + status + warnings).

3. Minimality:
- No duplicate policy logic remains in multiple modules.

4. Operability:
- `cortex check` explains misconfiguration with direct, actionable fixes.

5. Evidence:
- A short evidence packet exists for each workstream.

## 4) Execution order (gated)

### Gate 0 — Baseline lock

Create baseline snapshots before any Sprint 2 code edits:
- `wc -l` for:
  - `cortex/graveyard.py`
  - `cortex/invariants.py`
  - `cortex/store.py`
  - `cortex/cli.py`
- Full verification:
  - `pytest -q`
  - `ruff check cortex tests`
- Save to:
  - `docs/evidence/genius-sprint2/00-baseline-lines.txt`
  - `docs/evidence/genius-sprint2/00-baseline-pytest.txt`
  - `docs/evidence/genius-sprint2/00-baseline-ruff.txt`

No implementation work starts until Gate 0 artifacts exist.

## 5) Workstream A — Graveyard quality without bloat

### A.1 Objective

Increase conceptual repeat detection while keeping deterministic behavior and low code size.

### A.2 File-level plan

Primary file:
- `cortex/graveyard.py`

Possible support file:
- `cortex/store.py` (optional FTS query helper only)

Planned edits:
1. Keep current normalized token + overlap pipeline as default deterministic path.
2. Add optional retrieval tier:
- If SQLite FTS5 is available, use it only to narrow candidate set.
- Final score remains deterministic in Python (same current blend logic).
3. Ensure ranking stability:
- Ties sorted by score desc then entry id desc (or existing deterministic tie-break).
4. Keep `to_dict()` contract unchanged except optional additive debug fields.

### A.3 Tests (required before finish)

File:
- `tests/test_graveyard.py`

Required test cases:
1. FTS disabled fallback path matches previous behavior.
2. FTS enabled candidate narrowing does not change top match for existing fixtures.
3. Conceptual synonym case still matches.
4. Threshold + `max_matches` remain deterministic.
5. Empty query / empty files still returns empty list.

### A.4 Quality gates

- No breaking change in `GraveyardMatch.to_dict()` required fields.
- No regression in existing graveyard tests.
- Net LOC target for this workstream: +40 max, with cleanup pass after tests green.

### A.5 Evidence

- `docs/evidence/genius-sprint2/graveyard-quality-cases.md`
- Include 3 query->match examples (raw overlap miss, semantic catch, no-match).

## 6) Workstream B — Invariant safety boundary hardening

### B.1 Objective

Make `execution_mode=container` operationally reliable and preflight-validated.

### B.2 File-level plan

Primary files:
- `cortex/invariants.py`
- `cortex/cli.py`
- `cortex/genome.py` (only if config defaults/messages need tightening)

Planned edits:
1. Keep host mode as default.
2. In container mode, add preflight checks in `cortex check`:
- container engine binary exists (`docker` etc).
- clear warning when image availability is unknown (non-blocking by default).
3. Keep invariant result statuses stable (`pass`/`fail`/`error`/`missing`).
4. Ensure command rendering is centralized in one helper.

### B.3 Tests

Files:
- `tests/test_invariants.py`
- `tests/test_cli.py`

Required cases:
1. `cortex check` warns when `execution_mode=container` and engine missing.
2. `cortex check` clean when engine is present (monkeypatched which).
3. Container command still formed exactly once in runner.
4. Host mode unaffected.

### B.4 Quality gates

- No change to stop report contract for invariant results.
- CLI warnings are actionable and single-source (no duplicate warning text).
- Net LOC target for this workstream: +30 max.

### B.5 Evidence

- `docs/evidence/genius-sprint2/container-mode-checks.md`
- include one success and one missing-engine check output.

## 7) Workstream C — Store resilience + code dedup

### C.1 Objective

Keep lock resilience while reducing repeated write boilerplate.

### C.2 File-level plan

Primary file:
- `cortex/store.py`

Planned edits:
1. Replace repeated `lambda conn: conn.execute(...)` patterns with compact internal helpers:
- `_execute_write(sql, params)`
- optional `_insert_with_timestamp(...)` for repeated timestamp writes.
2. Preserve retry/backoff semantics exactly.
3. Keep SQL statements explicit (no dynamic SQL generation).

### C.3 Tests

File:
- `tests/test_store.py`

Required cases:
1. Existing round-trip tests still pass.
2. Lock retry still retries on lock and stops on non-lock.
3. Add a lightweight concurrent write stress test (threaded, bounded) to confirm no random lock flakes in CI-like conditions.

### C.4 Quality gates

- Public `SQLiteStore` method behavior unchanged.
- No SQL schema changes in this sprint.
- Net LOC target for this workstream: -20 to +10 (dedup should offset additions).

### C.5 Evidence

- `docs/evidence/genius-sprint2/sqlite-lock-stress.md`
- include run count, contention setup, pass/fail summary.

## 8) Workstream D — Sprint cleanup + compression pass

### D.1 Objective

Remove temporary scaffolding and tighten code after tests pass.

### D.2 Actions

1. Remove redundant local variables added during implementation.
2. Collapse trivially duplicated warning composition.
3. Re-run line counts and compare to Gate 0.
4. If net LOC exceeds budget, perform mandatory reduction pass before sprint close.

### D.3 Evidence

- `docs/evidence/genius-sprint2/99-final-lines.txt`
- `docs/evidence/genius-sprint2/99-final-pytest.txt`
- `docs/evidence/genius-sprint2/99-final-ruff.txt`
- `docs/evidence/genius-sprint2/summary.md`

## 9) Completion checklist

Sprint 2 completes only when all items below are checked:

- [x] Gate 0 baseline artifacts captured.
- [x] Workstream A tests + evidence complete.
- [x] Workstream B tests + evidence complete.
- [x] Workstream C tests + evidence complete.
- [x] Workstream D compression pass complete.
- [x] Full test suite green.
- [x] Ruff clean.
- [x] `todos.md` updated with exact completion state and links.

## 10) Anti-drift rules for Sprint 2

Do not do these inside Sprint 2:
- Add new agent providers (Aider adapter belongs to Sprint 3).
- Add new DB tables or schema migrations.
- Add non-stdlib runtime deps.
- Change user-facing contracts unless required for correctness.

If any of the above becomes necessary, stop and open a scoped decision note before coding.
