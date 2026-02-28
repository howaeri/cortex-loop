# Tiny-Kernel Audit Checklist

Mark each item `PASS` or `FAIL` with evidence link.

## Tiny

- `core.py` line count is below TR-0 baseline (`635`).
- Stop parsing and value resolution are extracted, not duplicated.
- Public Stop requirement report exposes only load-bearing fields.

## Reliable

- Required IDs are enforced from SessionStart contract when present.
- Conflicting Stop-provided required IDs are ignored with warning.
- False/checkable evidence claims produce deterministic requirement errors.
- Uncheckable evidence in advisory mode warns without blocking.

## Practical

- Full test suite passes.
- Ruff passes.
- Stop response remains human-readable and actionable.
- At least one captured run shows gate catching a real missed requirement.

## Revolutionary bar

- Tiny: less core code than baseline, with simpler policy flow.
- Reliable: catches a miss the model could otherwise self-report away.
- Practical: no new runtime dependencies and no observable velocity regression in tests.
