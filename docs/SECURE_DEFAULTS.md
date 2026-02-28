# Secure Defaults

## Recommended baseline (trusted repo)

- `invariants.execution_mode = "host"`
- `hooks.require_structured_stop_payload = true`
- `hooks.allow_message_stop_fallback = false`

## Recommended baseline (untrusted repo)

- `invariants.execution_mode = "container"`
- pin `container_engine`, `container_image`, and `container_workdir`
- keep structured stop payload requirements enabled

## Why

- Host-mode invariants execute arbitrary test code on your machine.
- Structured stop payloads reduce ambiguity from message parsing.
- Message-trailer fallback should be temporary and explicit.
