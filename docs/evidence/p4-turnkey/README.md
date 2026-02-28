# P4 Turnkey Verification (Clean Environment)

Date: 2026-02-27

## Procedure

1. Created clean virtual environment at `/tmp/cortex-clean-venv`.
2. Installed Cortex from local source with base profile:
   - `pip install -e <repo-root>`
3. Bootstrapped a new project:
   - `cortex init --root /tmp/cortex-clean-project`
4. Ran turnkey verification:
   - `cortex check --root /tmp/cortex-clean-project`
5. Generated repo-map artifact from clean project:
   - `cortex repomap --root /tmp/cortex-clean-project --json`

## Result

- Clean project passed `cortex check` without manual file edits.
- Hook wiring, config parse, DB tables, and starter invariant paths were valid immediately.
- Repo-map command succeeded on clean project.

## Evidence files

- `clean-init.json`
- `clean-check.txt`
- `clean-repomap.json`
