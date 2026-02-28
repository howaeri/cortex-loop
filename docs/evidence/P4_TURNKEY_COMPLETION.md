# P4 Turnkey Adoption UX Completion

Date: 2026-02-27

## Completed items

1. Hardened init templates and comments
- `cortex init` starter config/docs/hook templates in `cortex/cli.py` and `examples/cortex.toml`.

2. Actionable setup check
- `cortex check` emits explicit OK/warn/error with fix guidance in `cortex/cli.py`.

3. Optional dependency profiles documented
- `docs/DEPENDENCY_PROFILES.md` documents base/dev/repomap/full profiles.

4. Starter testing prompts added
- `docs/TESTING_STARTER_PROMPTS.md` provides copy-paste baseline/enabled/strict prompts.

5. Clean environment verification executed
- Evidence in `docs/evidence/p4-turnkey/` from fresh venv + fresh project bootstrap.

## Acceptance statement

A clean project can install Cortex, run `cortex init`, and pass `cortex check` without manual patching.
