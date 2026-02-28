# Critique Hardening Plan (Five-Area Upgrade)

Date: 2026-02-27

This plan translated external critique into specific engineering changes, with tests, while keeping the core system small.

## Objectives

1. Remove brittle stop-gate behavior caused by freeform trailer parsing.
2. Improve graveyard repeat-failure detection beyond direct keyword overlap.
3. Decouple kernel policy from Claude-specific hook payload shapes.
4. Add safer invariant execution boundaries for untrusted codebases.
5. Reduce SQLite lock failures under bursty hook writes.

## Design Constraints

- Keep core runtime dependency-free (stdlib only).
- Preserve current public CLI and hook contracts unless additions are backward compatible.
- Keep fallback behavior explicit and machine-reportable.
- Add tests for every new enforcement decision.

## Area A — Stop Contract Hardening

### Problem
Stop-gate quality currently depends on parsing `CORTEX_STOP_JSON` from assistant prose when structured fields are absent.

### Changes
- Add hook config: `require_structured_stop_payload` (default `false`).
- Add hook config: `allow_message_stop_fallback` (default `true`).
- Update stop payload extraction to support explicit modes:
  - Structured sources: top-level payload fields and `payload.cortex_stop`.
  - Message fallback source: `last_assistant_message` trailer parsing, only if allowed.
- In strict mode, if `require_structured_stop_payload=true` and stop values come from message fallback only, mark contract violation and recommend revert.
- Keep trailer path available for compatibility, but make source explicit in warnings and stop metadata.

### Acceptance
- Structured payload path works without warnings.
- Invalid trailer is ignored deterministically with explicit warning.
- Strict + `require_structured_stop_payload=true` blocks trailer-only submissions.
- Advisory mode warns without blocking.

## Area B — Graveyard Similarity Upgrade

### Problem
Pure token overlap misses concept-level repeats with different wording.

### Changes
- Add deterministic token normalization:
  - lightweight stemming (`ing`/`ed`/plural reductions).
  - small synonym canonicalization map (e.g., redis→cache, latency→timeout, error/crash→fail).
- Add in-memory TF-IDF cosine signal over normalized tokens (no external deps).
- Blend score:
  - lexical overlap (existing)
  - file overlap (existing)
  - tf-idf semantic score (new)
- Keep existing threshold/min-overlap controls and deterministic output.

### Acceptance
- Existing graveyard tests pass unchanged.
- New test catches conceptually similar phrasing with low raw overlap.
- Threshold and max-match behavior remains stable.

## Area C — Adapter Boundary for Agent Events

### Problem
Kernel event ingestion is tightly aligned with Claude hook shape.

### Changes
- Introduce adapter layer:
  - `NormalizedEvent` schema.
  - `EventAdapter` protocol.
  - `ClaudeCodeAdapter` default implementation.
- Kernel `dispatch` uses adapter normalization before routing.
- Event name and common payload aliases normalized centrally (e.g., `tool` -> `tool_name`).
- Preserve existing hook scripts and CLI behavior.

### Acceptance
- Existing hook tests pass.
- New tests verify dispatch works with alias keys through adapter normalization.
- A custom adapter can be injected in tests to prove decoupled kernel ingress.

## Area D — Invariant Execution Boundaries

### Problem
Invariant subprocesses execute directly on host by default; unsafe for untrusted tasks.

### Changes
- Extend invariant config with execution controls:
  - `execution_mode = "host" | "container"` (default `host`).
  - `container_engine` (default `docker`).
  - `container_image` (default `python:3.11-slim`).
  - `container_workdir` (default `/workspace`).
- In container mode, run invariants via containerized command with bind mount and isolated workdir.
- Keep host mode as default for local speed and compatibility.

### Acceptance
- Host mode behavior unchanged.
- Container mode emits expected command structure (tested via subprocess monkeypatch).
- Missing container engine returns deterministic error result.

## Area E — SQLite Lock Resilience

### Problem
Burst writes can hit `database is locked` despite WAL+timeout.

### Changes
- Add write retry/backoff policy inside `SQLiteStore`:
  - bounded retries on lock-related `sqlite3.OperationalError`.
  - exponential backoff with small default delay.
- Apply retry path to all write operations.
- Keep reads simple; do not introduce connection pools or background writer threads yet.

### Acceptance
- Existing store tests pass.
- New tests verify lock errors retry then succeed.
- Non-lock operational errors still raise immediately.

## Delivery Checklist

- [ ] Implement all five areas with backward-compatible defaults.
- [ ] Add/extend tests for every area.
- [ ] Run `pytest -q` and `ruff check cortex tests`.
- [ ] Update user-facing docs for new config keys and behavior.
