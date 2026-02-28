# Repro Walkthrough (Clean Environment)

Date: 2026-02-27

Goal: verify Cortex installs and runs end-to-end from a clean shell.

## 1) Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,repomap]'
```

## 2) Core verification

```bash
pytest -q
ruff check cortex tests
```

Expected:
- tests pass
- lint passes

## 3) Bootstrap a fresh governed project

```bash
mkdir -p /tmp/cortex-demo
cortex init --root /tmp/cortex-demo
cortex check --root /tmp/cortex-demo
```

Expected:
- `cortex.toml` exists
- `.cortex/cortex.db` exists with required tables
- `.claude/settings.json` exists with hook wiring
- `tests/invariants/example_invariant_test.py` exists

## 4) Generate repo-map artifact

```bash
cortex repomap --root /tmp/cortex-demo --json
```

Expected:
- JSON output with `schema_version = "repomap_artifact_v1"`
- provenance method is `ast_pagerank` (deps available) or `heuristic_fallback` (deps missing)

## 5) Hook invocation sanity

```bash
echo '{"session_id":"demo-1","task":"sanity"}' | python3 -m cortex.hooks.session_start
echo '{"tool_name":"Write","target_files":["src/app.py"]}' | python3 -m cortex.hooks.pre_tool_use
echo '{"tool_name":"Write","status":"ok"}' | python3 -m cortex.hooks.post_tool_use
echo '{"session_id":"demo-1","challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true}}' | python3 -m cortex.hooks.stop
```

Expected:
- each command returns JSON
- no crashes
