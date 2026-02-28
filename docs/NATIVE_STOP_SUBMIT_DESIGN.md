# Native Stop Submit Design (`cortex_submit_task`)

Date: 2026-02-27

## Goal

Remove dependence on freeform assistant-message trailers for stop gating.

## Proposed contract

Introduce a native submission channel:
- tool/API name: `cortex_submit_task`
- payload schema:
  - `session_id: string`
  - `challenge_coverage: object`
  - `requirement_audit: object | null`
  - `required_requirement_ids: string[]`
  - `failed_approach: object | null`

## Enforcement model

1. If native submission exists for session stop event, it is authoritative.
2. `payload.cortex_stop` remains a backward-compatible structured path.
3. `last_assistant_message` trailer parsing becomes compatibility fallback only.
4. In strict mode with `require_structured_stop_payload=true`, trailer-only submissions are rejected.

## Migration steps

1. Add `cortex_submit_task` adapter event mapping to normalized stop payload.
2. Record submission source in stop metadata (`native`, `payload.cortex_stop`, `message_fallback`).
3. Add check warning when project still relies on message fallback.
4. After adoption window, default `allow_message_stop_fallback=false` in strict templates.

## Test plan

- Unit: native payload accepted, no fallback warnings.
- Unit: native + trailer conflict -> native wins.
- Integration: strict mode rejects trailer-only.
- Regression: existing payload.cortex_stop path remains valid.
