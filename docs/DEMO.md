# Cortex Demo (Install -> Init -> Check -> Repo-map)

This is the fastest reproducible demo path for a new reviewer.

## Demo flow

### 1) Install in a clean venv

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,repomap]'
```

### 2) Bootstrap a fresh project

```bash
mkdir -p /tmp/cortex-demo
.venv/bin/cortex init --root /tmp/cortex-demo
```

Expected:
- `cortex.toml`
- `.cortex/cortex.db`
- `tests/invariants/example_invariant_test.py`
- `.claude/settings.json`
- `.claude/CLAUDE.md`

### 3) Run setup preflight

```bash
.venv/bin/cortex check --root /tmp/cortex-demo
```

Expected:
- config parsed
- DB ready
- invariant paths present
- Claude hook wiring found

### 4) Generate repo-map artifact

```bash
.venv/bin/cortex repomap --root /tmp/cortex-demo --json
```

Expected:
- JSON with `schema_version = "repomap_artifact_v1"`
- `provenance.method` reported (`ast_pagerank` or `heuristic_fallback`)
- artifact written at `.cortex/artifacts/repomap/latest.json`

## Common failure modes and fixes

### Python version too old

Symptom:
- `tomllib`/install errors

Fix:
- Use Python 3.11+.

### Repo-map optional deps missing

Symptom:
- `cortex check` warns repo-map deps missing

Fix:
```bash
.venv/bin/pip install -e '.[repomap]'
```

### `SessionStart` hook missing in host environment

Symptom:
- no session-start repo-map artifact during hook run

Fix:
- run preflight manually:
```bash
.venv/bin/cortex repomap --root /path/to/project --json
```

### DB lock warnings under heavy concurrent writes

Symptom:
- transient write retries/log warnings

Fix:
- rerun the command; Cortex uses bounded retry/backoff.
- if frequent, reduce concurrent hook pressure and capture evidence under `docs/evidence/`.
