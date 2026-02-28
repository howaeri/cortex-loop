# Tiny-Kernel External Audit Protocol

Use this protocol to ask Claude/Gemini (fresh chat) for independent audits of the Cortex requirement gate.

## Inputs to provide

- `cortex/core.py`
- `cortex/requirements.py`
- `cortex/stop_payload.py`
- `tests/test_core.py`
- `docs/evidence/tiny-kernel/caught-missed-requirement-stop.json`

## Prompt A: enforcement correctness

"Audit the Stop enforcement path for deterministic anti-bluff behavior. List every requirement gate decision path (challenge coverage, requirement audit presence/gap, invariant result). For each, state exact trigger, strict/advisory behavior, and whether the outcome is machine-checkable. Report any path that could be bypassed by self-reporting."

## Prompt B: tiny-code quality

"Audit whether this implementation is minimal and load-bearing. Identify dead/duplicate logic, derived fields that can be removed, and any branch that does not change enforcement outcomes. Recommend the smallest refactor set that preserves behavior and test coverage."

## Prompt C: practical reliability

"Using the included caught-missed-requirement Stop artifact, verify that the kernel catches a missing required ID deterministically and recommends revert in strict mode. Explain why this is not prompt theater."

## Required audit output format

- Findings ordered by severity.
- File references with line numbers.
- Explicit pass/fail for: tiny, reliable, practical.
- At least one concrete change recommendation (or explicit statement of no further reduction opportunity).
