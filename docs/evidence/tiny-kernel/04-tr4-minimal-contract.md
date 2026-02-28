# TR-4 Minimal Contract Surface

Captured at: 2026-02-27T19:00:00Z

## Summary

Reduced `requirement_audit_report` in Stop responses to load-bearing fields only:

- `ok`
- `errors`
- `missing_required_ids`
- `item_count`
- `pass_count`
- `fail_count`

Removed noisy/derived fields from the public Stop payload while keeping enforcement logic unchanged.

## Code changes

- Added `cortex/stop_payload.py` and moved Stop trailer parsing/field resolution there.
- Consolidated list coercion/dedup helpers in `cortex/utils.py`.
- Updated `cortex/core.py` to publish a compact requirement report via `_minimal_requirement_audit_report(...)`.
- Kept full requirement gate behavior (strict/advisory, session contract enforcement, witnessed evidence checks).

## Validation

- `.venv/bin/pytest -q tests/test_core.py`: `19 passed`
- `.venv/bin/pytest -q`: `67 passed`
- `.venv/bin/ruff check cortex tests`: `All checks passed!`

## Payload size check

Using artifacts in this folder:

- baseline sample (`baseline-stop-payload.json`): `3608` bytes
- current Stop response sample (`tr4-stop-response.json`): `1397` bytes

Result: response artifact is materially smaller while preserving gate outcomes.
