# Extraction Patterns

This note captures the reusable mechanisms extracted from prior research passes.

## Repo map extraction

Keep:

- artifact-first output (`repomap_artifact_v1`)
- symbol/dependency-aware ranking when optional parsers exist
- deterministic fallback when optional dependencies are unavailable

Do not keep:

- UI/chat integration assumptions from source systems
- provider-specific runtime coupling

## Corrective interface (ACI-style)

Keep:

- typed corrective failures
- bounded retries for recoverable formatting/range/tool-shape issues

Do not keep:

- broad auto-retry loops that can hide policy failures
- retries on hard gates (invariants, strict stop requirements)

## Checkpointing

Keep:

- SQLite-backed checkpoints with explicit compatibility constraints
- shadow-mode validation before behavior cutover

Do not keep:

- runtime replatforming before parity evidence exists

## Extraction rule

For every graft, require:

1. clear Cortex pain point
2. measurable target metric
3. explicit proof artifact path

If any of the three is missing, reject the graft as non-load-bearing.
