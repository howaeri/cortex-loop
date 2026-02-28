# Sprint 2 Workstream B — Container Mode Checks

Date: 2026-02-27

## Engine present (preflight OK)

Configuration:
- `invariants.execution_mode = "container"`
- `invariants.container_engine = "python3"` (used as a known-present binary for preflight proof)

Observed `cortex check` output includes:
- `Invariant container engine available: python3`

Raw output captured in `/tmp/cortex_s2_container_ok.txt`.

## Engine missing (actionable warning)

Configuration:
- `invariants.execution_mode = "container"`
- `invariants.container_engine = "definitely_missing_engine"`

Observed `cortex check` output includes:
- `invariants.execution_mode='container' but container engine 'definitely_missing_engine' is not on PATH; install 'definitely_missing_engine' or switch to execution_mode='host'`

Raw output captured in `/tmp/cortex_s2_container_missing.txt`.

## Outcome

- Container-mode misconfiguration is now surfaced during preflight.
- Warning text is actionable and non-blocking, preserving host-mode default behavior.
