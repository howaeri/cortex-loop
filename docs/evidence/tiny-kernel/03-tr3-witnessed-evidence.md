# TR-3 Witnessed Evidence Validation

Captured at: 2026-02-27T10:25:01Z

## Summary

Added deterministic witnessed evidence checks for requirement audits.

## What is now enforced

- Existing file-path evidence checks remain active.
- Evidence references are now classified as:
  - `path`
  - `command`
  - `tool`
  - `note`
- Each evidence ref gets deterministic status:
  - `verified`
  - `unverified`
  - `uncheckable`

## Witness source

- Session event history (`PreToolUse`/`PostToolUse`) from SQLite.
- Command candidates from event payload keys (`command`, `cmd`, nested `input/tool_input`).
- Tool names from recorded hook events.

## Enforcement behavior

- Strict mode:
  - unverified evidence contributes to requirement-audit errors and blocks via requirement gate.
- Advisory mode:
  - uncheckable evidence emits warnings/notes without forcing failure.

## Validation

- `.venv/bin/pytest -q tests/test_core.py`: `19 passed`
- `.venv/bin/pytest -q`: `67 passed`
- `.venv/bin/ruff check cortex tests`: `All checks passed!`

## Added test coverage

- strict-mode command mismatch (checkable false) blocks/reverts.
- advisory-mode command claim with no witnessed commands is uncheckable and warns only.
