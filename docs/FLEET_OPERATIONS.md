# Fleet Operations

Use fleet operations when you run Cortex across multiple projects and need fast status/version visibility.
The goal is practical: one command that tells you which projects are healthy,
which are drifting, and which need intervention.

## Per-project status

`cortex check --root <project> --json --write-status`

This emits machine-readable status and writes `.cortex/status.json` for snapshots.

## Multi-project status

`cortex fleet status --roots /path/a /path/b /path/c`

Use `--json` for automation pipelines:

`cortex fleet status --roots /path/a /path/b --json`

The report includes:
- Cortex version
- config schema version
- DB schema/version and required table checks
- hook wiring validity
- invariant path availability
- repo-map mode/dependency state

## Version drift detection

Recommended policy:
1. Capture all fleet reports in CI/nightly jobs.
2. Alert when `cortex_version` differs across managed projects.
3. Alert when any project has `summary.errors > 0`.
4. Track warnings separately so advisory issues do not hide hard failures.

## Upgrade-wave workflow

1. Select pilot project.
2. Upgrade and run full check + invariant suite.
3. Roll out to remaining projects in batches.
4. Run `cortex fleet status --roots ... --json` after each batch.
5. Stop rollout if any new hard errors appear.

In practice, this keeps upgrades boring and reversible instead of ad-hoc.
