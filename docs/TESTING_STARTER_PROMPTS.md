# Cortex Testing Starter Prompts

Use these in a fresh Claude Code session from the target project root.

## Prompt A — Baseline run (repo-map off)

```text
Run this task in baseline mode.

Rules:
- Do not use `cortex repomap` for discovery.
- Work in small, reviewable increments.
- Run project build/tests before final output.

At the end include:
CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true}}
```

## Prompt B — Enabled run (repo-map on)

```text
Run this task in enabled mode.

Rules:
- Run `cortex repomap --root . --debug-json` before major edits and use it to plan file discovery.
- Work in small, reviewable increments.
- Run project build/tests before final output.

At the end include:
CORTEX_STOP_JSON: {"challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true}}
```

## Prompt C — Requirement traceability run

```text
Before coding, list requirement IDs R1..Rn from this prompt.
At the end, include a traceability table with pass/fail and evidence.

End with:
CORTEX_STOP_JSON: {
  "challenge_coverage":{"null_inputs":true,"boundary_values":true,"error_handling":true,"graveyard_regression":true},
  "required_requirement_ids":["R1","R2"],
  "requirement_audit":{
    "items":[
      {"id":"R1","status":"pass","evidence":["cmd:pytest -q"]},
      {"id":"R2","status":"pass","evidence":["src/app.ts:42"]}
    ],
    "completeness_verdict":"pass"
  }
}
```
