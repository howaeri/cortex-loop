# TR-0 Baseline Snapshot

Captured at: 2026-02-27T10:13:52Z

## Scope

Baseline for Tiny Revolutionary Kernel track before TR-1 compression/refactor.

## Line Counts

Source: `docs/evidence/tiny-kernel/baseline-line-counts.txt`

- `cortex/core.py`: 635
- `cortex/genome.py`: 153
- `cortex/cli.py`: 716
- `tests/test_core.py`: 418
- Total tracked lines: 1922

## Test/Lint Health

Source files:

- `docs/evidence/tiny-kernel/baseline-pytest.txt`
- `docs/evidence/tiny-kernel/baseline-ruff.txt`

Results:

- Pytest: `62 passed in 1.18s`
- Ruff: `All checks passed!`

## Stop Payload Sample (Testing)

Source:

- `docs/evidence/tiny-kernel/baseline-stop-payload.json`

Notes:

- Payload captured from an anonymized testing `Stop` event.
- Sample payload size: 3608 bytes.
- Contains last assistant report plus `CORTEX_STOP_JSON` trailer.

## TR-0 Exit Criteria

- [x] Baseline line counts captured.
- [x] Baseline pytest/ruff outputs captured.
- [x] Real testing stop payload captured.
- [x] Baseline note written.
