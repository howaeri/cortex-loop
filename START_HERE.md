# Start Here

If you are new to Cortex, this page should give you enough context in about 3 minutes.

## 60-second overview

Cortex is a quality and judgment layer that sits around an existing coding agent.

It adds:
- external invariant tests the agent did not author
- required challenge coverage at stop time
- a graveyard that remembers failed approaches
- foundation warnings before editing unstable modules
- optional repo-map artifacts for file discovery

It does not try to be an agent framework.

## What is proven now

- Hook lifecycle is working (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`).
- Stop-time quality gates are working (challenge coverage + invariants + requirement audit).
- Graveyard/foundation checks are wired and tested.
- Repo-map artifact contract (`repomap_artifact_v1`) is stable and emitted in real testing runs.

## What is not claimed yet

- Aider repo-map parity is not complete.
- Current repo-map quality evidence is strongest on frontend-heavy testing repos.
- SessionStart behavior still depends on host/provider support.

## 5-minute verify

From repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,repomap]'
.venv/bin/pytest -q
.venv/bin/ruff check cortex tests
```

Quick project bootstrap check:

```bash
mkdir -p /tmp/cortex-smoke
.venv/bin/cortex init --root /tmp/cortex-smoke
.venv/bin/cortex check --root /tmp/cortex-smoke
.venv/bin/cortex repomap --root /tmp/cortex-smoke --json
```

## If you only read three files

1. `README.md` (current contract and usage surface)
2. `docs/SHARE_STATUS.md` (what works vs what is open)
3. `docs/evidence/RUN_INDEX.md` (actual run evidence)

## Canonical proof packet

Start with:
- `docs/evidence/RUN_INDEX.md`

Then inspect:
- `docs/evidence/tiny-kernel/05-tr5-audit-packet.md`
- `docs/evidence/genius-sprint2/summary.md`
- `docs/evidence/public-ready/public-ready-exit-report.md`
