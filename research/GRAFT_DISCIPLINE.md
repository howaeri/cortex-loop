# Graft Discipline

Do not import external architectures wholesale. Extract only the smallest mechanism that improves a known Cortex failure mode.

## Required pre-graft checklist

1. Define the failure mode and current impact.
2. Name the exact Cortex surface that will change.
3. Define the metric expected to improve.
4. Define the acceptance artifact that will prove improvement.
5. Define the rollback trigger.

## Decision stances

- `COPY`: only for small, contract-compatible utilities
- `ADAPT`: default stance; behavior kept, contracts translated to Cortex
- `REJECT`: any mechanism that weakens mechanical enforcement or adds generic framework mass

## Anti-patterns

- Prompt-policy additions without machine checks
- Broad abstractions without a measured reliability gain
- Cutovers without baseline vs enabled evidence
- Coupling Cortex kernel behavior to one tool provider

## Practical usage

Use this file as a gate before implementing any new graft task from `todos.md`.
If a proposal cannot pass this checklist in under one page, scope is too broad.
