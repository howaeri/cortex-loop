# Architectural Blueprint for AI Agent Enforcement Loops
## February 2026 Landscape and Cortex Integration Plan

## Scope

This document merges two prior drafts:

- an older concise draft with strong signal and Cortex-specific framing,
- a newer detailed draft with broader ecosystem depth.

The goal of this merged version is practical: keep the clarity of the concise version while retaining the highest-value technical detail from the long form.

## Executive Summary

By February 2026, the industry consensus is clear: model capability alone does not create reliable software outcomes. The winning pattern is external mechanical pressure:

- strict tool and lifecycle contracts,
- deterministic verification gates,
- durable state and replay,
- bounded execution environments,
- adversarial validation loops.

Cortex is directionally aligned. Its strongest assets are the kernel hook lifecycle, invariant gate model, graveyard failure memory, and repository stability checks. The highest-leverage next step is disciplined grafting: adopt proven mechanisms where reliability gain is measurable, while keeping Cortex small, auditable, and provider-agnostic.

## What We Kept from Each Version

| Source | Kept because it helps | Applied in this merged doc |
| --- | --- | --- |
| Old concise draft | Tight structure, low-noise prose, direct Cortex mapping | Every section now includes explicit Cortex action paths |
| New detailed draft | Up-to-date ecosystem patterns and concrete examples | Added targeted depth (ACI, sandboxing, MCP, GraphRAG, adversarial testing) without turning this into framework theater |

## 1) Agent-Computer Interface (ACI)

### Landscape

Generic human terminals are still a poor default for autonomous coding agents. They waste context on low-value output and provide weak edit feedback loops.

The mature 2026 pattern is ACI-style interaction:

- structure-first reads (symbol/AST focused, paginated),
- immediate edit validation,
- typed/localized corrective responses,
- minimal context pollution.

### Cortex Implication

Cortex adapters should remain provider-normalization boundaries but add ACI behavior where it increases reliability:

- `PreToolUse`: context shaping for broad reads,
- `PostToolUse`: local syntax/edit validation envelopes,
- `core.py`: deterministic routing based on normalized events.

### Acceptance Criteria

- malformed edit feedback is returned before expensive suite execution,
- token-heavy tool outputs are reduced by default when safe,
- no provider-specific branches are required inside kernel logic.

## 2) Execution Sandboxing and Capability Boundaries

### Landscape

Host execution remains risky for AI-generated code, especially in untrusted repos. Container mode is now baseline; low-latency isolation (micro-VM/WASM paths) is an emerging production direction.

A second shift is from prompt-level safety claims to capability-bounded execution: if authority is not granted, action is impossible.

### Cortex Implication

Keep current practical path (host + container), but harden defaults and policy clarity:

- secure-by-default profile for unknown repos,
- explicit risk labeling for host mode,
- bounded execution settings tied to strictness mode.

Longer term, evaluate micro-VM/WASM only if it proves measurable reliability/latency gains for invariant loops.

### Acceptance Criteria

- clear fail-closed behavior for unsafe execution combinations,
- reproducible enforcement logs for each execution mode,
- evidence before enabling new sandbox backends by default.

## 3) State Durability and Checkpointing

### Landscape

Even deterministic model settings produce divergent traces over long sessions. Durable checkpoints and replay tooling are now standard in serious agent orchestration.

LangGraph-style patterns are influential:

- explicit state schema,
- reducer-driven updates,
- checkpoint/replay/fork mechanics.

### Cortex Implication

Cortex already has strong SQLite audit durability. The practical graft is checkpoint shadowing, not immediate architecture replacement:

- immutable checkpoint snapshots alongside current event tables,
- replay support for failed sessions,
- parity validation before any control-path cutover.

### Acceptance Criteria

- failed sessions can be replayed deterministically from stored checkpoints,
- no regression in current store reliability under concurrency,
- checkpoint path remains optional until parity evidence is stable.

## 4) Multi-Agent Coordination and MCP

### Landscape

Parallel agent execution has become common, increasing coordination and integration complexity. MCP is becoming the normalization layer for tool/context exchange across ecosystems.

### Cortex Implication

Keep `core.py` provider-agnostic and make adapters the only provider-specific surface. Evolve toward MCP-compatible tool surfaces so Cortex can govern multiple ecosystems without bespoke rewrites.

Optional high-risk session enhancement: bounded cross-verification policies at stop (for example, independent perspective requirements before final accept).

### Acceptance Criteria

- kernel behavior remains adapter-normalized, not provider-coupled,
- integration contracts are testable with fixture-based adapter inputs,
- MCP mapping can be added without kernel rewrites.

## 5) Adversarial Validation Beyond Static Tests

### Landscape

Static suites are necessary but insufficient for agent-generated code. Leading systems increasingly use adversarial test generation to catch failures that pass nominal coverage.

### Cortex Implication

Current challenge categories are a strong base (`null_inputs`, `boundary_values`, `error_handling`, `graveyard_regression`). Expand with bounded adversarial pressure where risk is high:

- generate targeted break probes,
- if a probe breaks code, promote it to invariant regression,
- tie strict-stop decisions to invariant outcomes.

### Acceptance Criteria

- adversarial probes produce measurable escaped-defect reduction,
- promoted tests are deterministic and low-maintenance,
- runtime remains bounded (no unbounded generation loops).

## 6) Repository Context: Repomap and Graph-Aware Retrieval

### Landscape

Embedding-only retrieval misses structural dependency truth. 2026 systems increasingly combine semantic retrieval with explicit graph structure (entities + edges).

### Cortex Implication

Repomap should continue to degrade gracefully when optional AST deps are missing, while improving graph quality when available. The key integration is with foundation warnings:

- churn/high-risk edit detected,
- dependency blast radius surfaced,
- downstream verification pressure increased mechanically.

### Acceptance Criteria

- useful top-file relevance for real code tasks,
- reduced false-positive noise in ranked outputs,
- clear mode reporting (heuristic vs AST-assisted) in artifacts.

## 7) Failure Memory: Graveyard Evolution

### Landscape

Keyword-only failure memory misses semantic repeats. Pure embedding-only memory can be opaque and unstable.

### Cortex Implication

Keep deterministic lexical core, then augment selectively:

- FTS narrowing + weighted lexical scoring as baseline,
- optional semantic expansion layer behind feature flags,
- memory compaction for old low-value entries.

### Acceptance Criteria

- repeated conceptual failures are caught more often,
- precision does not collapse from noisy semantic matches,
- lookup latency stays low on growing datasets.

## 8) Prioritized Integration Sequence for Cortex

1. Strengthen adapter contract boundaries and ACI-style post-edit feedback.
2. Harden sandbox defaults and strict-mode execution policy.
3. Add checkpoint shadowing with replay tooling (no immediate cutover).
4. Improve repomap relevance and foundation blast-radius linkage.
5. Add bounded adversarial generation + promotion to invariants.
6. Introduce optional semantic graveyard augmentation behind flags.
7. Continue MCP-compatible normalization so multi-agent integrations stay tractable.

## 9) Operating Principles (Keep Cortex Small)

To avoid framework bloat while improving reliability:

- Do not add abstractions broader than the target reliability gap.
- Require evidence for every major graft (defect reduction, reduced oversight, lower interrupts).
- Keep strict behavior deterministic and auditable.
- Keep optional advanced paths behind explicit config flags.
- Prefer narrow contracts over orchestration sprawl.

## Strategic Conclusion

The strongest synthesis from both drafts is this:

- The old draft was right about architecture discipline.
- The new draft was right about where the ecosystem is moving.

Cortex should adopt the movement, but in a constrained way: minimal surface area, maximum enforcement value. If that discipline holds, Cortex remains a compact quality layer that materially improves agent reliability under real engineering pressure.
