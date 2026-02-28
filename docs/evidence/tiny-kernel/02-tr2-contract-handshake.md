# TR-2 Contract Handshake (Anti-Bluff Upgrade)

Captured at: 2026-02-27T10:21:19Z

## Summary

Implemented authoritative requirement contract flow:

- Session start now accepts and persists `required_requirement_ids`.
- Stop now validates `requirement_audit.items` against persisted session contract IDs.
- Conflicting stop payload IDs are ignored when a session contract exists.
- If no session contract exists, stop payload IDs are used with an explicit warning.

## Behavioral guarantees

- Strict mode + requirement-audit gate enabled:
  - mismatch/missing required IDs triggers requirement-audit gap
  - `recommend_revert=true`
- Advisory mode:
  - mismatch still flagged as gap and warning
  - no revert/blocking

## Validation

- `.venv/bin/pytest -q tests/test_core.py`: `17 passed`
- `.venv/bin/pytest -q`: `65 passed`
- `.venv/bin/ruff check cortex tests`: `All checks passed!`

## Notes

- No new dependencies.
- No new DB tables.
- Core remains deterministic (no NLP scoring/parsing expansion).
