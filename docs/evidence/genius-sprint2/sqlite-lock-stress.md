# Sprint 2 Workstream C — SQLite Lock Stress

Date: 2026-02-27

## Test

Executed:
- `.venv/bin/pytest -q tests/test_store.py::test_concurrent_event_writes_do_not_flake`

Scenario:
- 80 concurrent `record_event` writes.
- 8 worker threads.
- Store configured with retry/backoff (`lock_retry_attempts=6`, `lock_retry_backoff_ms=2`, `busy_timeout_ms=1500`).

Expected:
- No lock-related failures.
- Final `events` row count equals 80.

Observed:
- `1 passed in 0.06s`

Raw output captured in `/tmp/cortex_s2_lock_stress.txt`.
