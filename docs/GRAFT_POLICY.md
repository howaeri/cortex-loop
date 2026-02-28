# Graft Policy

Cortex accepts grafts only when they improve reliability with bounded complexity.
This policy exists to avoid cargo-cult copy/paste from upstream projects.
If a graft cannot explain its value in Cortex terms, it should not land.

## Required gates for every graft

1. Provenance
- source project, commit/tag, and retrieval date
- reason this source is selected instead of alternatives

2. License compatibility
- upstream license
- compatibility statement with Cortex MIT license
- obligations (attribution, notices)

3. Adaptation scope
- what was copied verbatim
- what was rewritten
- what was deliberately omitted

4. Operational fallback
- behavior when optional deps are unavailable
- deterministic fallback path

5. Rollback plan
- config kill-switch or feature gate
- exact rollback steps

6. Evidence
- tests covering grafted behavior
- benchmark/relevance packet if ranking/discovery is affected
- explicit non-claims if parity not achieved

## Hard constraints

- No parity claim before objective gate pass.
- No optional dependency added without dependency-profile impact note.
- No dead scaffold from partial grafts.

## Required files

- `docs/grafts/<graft-name>.md` (provenance + adaptation record)
- evidence packet under `docs/evidence/`
