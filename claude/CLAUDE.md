# Cortex Governance Instructions

This repository is governed by Cortex hooks. Treat hook output as policy, not optional advice.

## Working rules in this repo

- Keep changes small and load-bearing.
- Avoid framework expansion unless reliability data justifies it.
- Use `todos.md` as the active plan.
- This file governs agents editing Cortex itself, not downstream runtime behavior.

Run this loop before coding, before final output, and before handoff:
- `PHI_MINIFY`: smallest viable change?
- `PHI_MISSION`: direct mission improvement?
- `PHI_NICHE`: best fit for this problem?

If any answer is no, cut scope or redesign.

## Stop-time requirements

Cortex expects challenge coverage at stop:
- `null_inputs`
- `boundary_values`
- `error_handling`
- `graveyard_regression`

In strict mode, invariant failure should be treated as a revert signal.

If an approach failed, include `failed_approach` with:
- summary
- reason
- files

If requirement traceability is configured, include `requirement_audit` and all required IDs.

Preferred path is structured stop payload fields (or `cortex_stop` object). Trailer parsing is fallback and may be disabled.

Fallback trailer format:

`CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true},"failed_approach":{"summary":"...","reason":"...","files":["path/to/file"]}}`

Use valid one-line JSON.

## Hook note

`SessionStart` is not consistently emitted by every Claude Code build. If unavailable, rely on `PreToolUse`/`PostToolUse`/`Stop`, and run `cortex repomap --root .` explicitly when needed.

Each hook module also accepts `--root` and `--config` for manual testing.
