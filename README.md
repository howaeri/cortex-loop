![cortex-loop banner](docs/assets/cortex-loop-banner.png)

# Cortex

Cortex is a quality and judgment layer for AI coding agents.

I built it to be the pressure layer I wanted while shipping real projects: small, mechanical checks that make bluffing harder than verifying.

It does not replace an agent. It sits in the loop and applies pressure where agents usually cut corners: verification, adversarial coverage, repeated-failure memory, and foundation risk checks.

## Proof in 2 minutes

These are real testing outcomes from `docs/evidence/RUN_INDEX.md`.

| Case | Before | After | Evidence |
| --- | --- | --- | --- |
| Frontend discovery quality (top-10 relevance) | 20% (`heuristic_fallback`) | 100% (post-fix rerun) | `docs/evidence/RUN_INDEX.md` |
| Session completion time on a production-style workspace | 11.34m (`heuristic_fallback`) | 5.29m (`ast_pagerank`) | `docs/evidence/RUN_INDEX.md` |

Important limitation: these are testing comparisons, not controlled scientific A/B benchmarks.

If you want one place to validate claims fast, start here:
- `START_HERE.md`
- `docs/evidence/RUN_INDEX.md`

## What Cortex does

- Runs invariant tests the agent did not author.
- Requires challenge-category coverage (`null_inputs`, `boundary_values`, `error_handling`, `graveyard_regression`).
- Records failed approaches in a graveyard and warns on repeats.
- Runs foundation analysis (git churn) before major edits.
- Generates a repo-map artifact for faster file discovery (`repomap_artifact_v1`).

## What Cortex is not

- Not an agent framework.
- Not a Claude Code replacement.
- Not a multi-agent orchestrator.
- Not prompt theater.

## Current status (alpha)

| Area | Status |
| --- | --- |
| Hook lifecycle (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`) | Working |
| Invariants + challenge gate + requirement audit | Working |
| Graveyard + foundation warnings | Working |
| Repo-map artifact contract | Working |
| Aider graft status | Alpha (operational, not parity-complete) |

Parity definition lives in `docs/REPOMAP_PARITY_CRITERIA.md`.

## Compatibility snapshot

| Surface | Value |
| --- | --- |
| Package version | `0.1.0` |
| Config schema | `cortex_toml_v1` |
| Repo-map artifact schema | `repomap_artifact_v1` |
| DB schema | `PRAGMA user_version = 1` |
| Supported adapters | `claude` (default), `aider` (alpha/minimal normalization) |

## Install

Requires Python 3.11+.

```bash
pip install -e .
```

For optional repo-map ranking deps:

```bash
pip install -e '.[repomap]'
```

## Quickstart

```bash
cortex init --root /path/to/project
cortex check --root /path/to/project
```

`cortex init` creates:
- `cortex.toml`
- `tests/invariants/` (starter invariant test included)
- `.claude/settings.json`
- `.claude/CLAUDE.md`
- `.cortex/cortex.db`

## Core flow

```text
Claude hook event
  -> hooks/*.py
  -> CortexKernel (core.py)
  -> subsystems (foundation, graveyard, challenges, invariants, repomap, store)
  -> JSON response
```

On stop, Cortex evaluates challenge coverage, runs invariants, records failed approaches, and returns a structured stop report. In strict mode, invariant failure sets `recommend_revert=true`.

## CLI commands

- `cortex init` bootstrap config, hooks, DB, starter invariants.
- `cortex check` validate setup (`--json`, `--write-status` supported).
- `cortex fleet status --roots ...` check many projects in one run.
- `cortex repomap` emit repo-map artifact.
- `cortex graveyard` list failed approaches.
- `cortex show-genome` print parsed `cortex.toml`.
- `cortex hook <event>` run a hook manually (`--adapter {claude,aider}`).

## Repo-map notes

- Default output path: `.cortex/artifacts/repomap/latest.json`.
- `--json` emits pure artifact JSON.
- `--debug-json` emits artifact + CLI debug envelope.
- With `[repomap].prefer_ast_graph=true`, method is `ast_pagerank` and backend is `networkx` or `simple`.

## Security model

Invariant execution defaults to host mode. For untrusted repos, use container mode:

```toml
[invariants]
execution_mode = "container"
container_engine = "docker"
container_image = "python:3.12-slim"
```

Details: `docs/SECURE_DEFAULTS.md`.

## Useful docs

- Start here: `START_HERE.md`
- Why this exists: `docs/WHY_CORTEX.md`
- Repro demo: `docs/DEMO.md`
- Mission: `MISSION.md`
- Architecture: `ARCHITECTURE.md`
- Active backlog: `todos.md`
- Share status: `docs/SHARE_STATUS.md`
- Release gate: `docs/RELEASE_CHECKLIST.md`
- Contributing: `CONTRIBUTING.md`

## Verify quickly

```bash
pip install -e '.[dev,repomap]'
pytest -q
ruff check cortex tests
cortex check --root .
```

## Contributing

Small, test-backed PRs are preferred.

Every behavioral claim should include evidence under `docs/evidence/`.

## Notifications

To avoid inbox noise:
- This repo does not run Dependabot version-update PR automation.
- Set GitHub watch mode to **Releases only**.
