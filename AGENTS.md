# Cortex Repo Agent Contract

This file applies to agents editing this repository.
It does not define runtime policy for downstream Cortex users.

## Required decision loop

Run this loop three times: before coding, before finalizing a change, and before handoff.

1. `PHI_MINIFY` — Is this the smallest change that solves the problem?
2. `PHI_MISSION` — Does this improve Cortex’s quality/judgment mission directly?
3. `PHI_NICHE` — Is this the right mechanism for this problem, or generic bloat?

If any answer is no, redesign or cut scope.

## Hard stops

- Do not add complexity without measured reliability gain.
- Do not add abstractions broader than the target problem.
- Do not keep dead scaffolding.
- Do not treat archived plan docs as active authority.

## Repo Hygiene Guard (Contributor workflow only)

These rules apply to people/agents editing this repository. They are not runtime
gates for downstream Cortex users.

- Do not commit personal/client project names, domains, or account handles.
- Do not commit absolute local paths.
- Keep docs/comments/commit messages in neutral technical language.
- Avoid persona branding in repo text.
- Use anonymized labels in evidence artifacts (`project_a`, `workspace_b`).
- If a claim needs private evidence, summarize it and keep private artifacts out of git.

## Change Narration Discipline

To keep the repository looking professionally maintained:

- Commit and PR titles must describe the resulting state, not internal cleanup process.
- Prefer concise end-state wording (`Initial snapshot`, `docs: adjust wording in README`).
- Avoid transitional/meta phrasing (`scrubbed`, `final polish`, `public snapshot`, `quick fix`).
- Keep language stable and technical; no dramatic or temporary-sounding narration.

## Authority and planning

- Active backlog/status authority: `todos.md`
- Historical context only: `docs/archive/plans/`

## Required handoff block

Every final summary from an agent editing this repo should include:

`PHILOSOPHY_AUDIT`
- `PHI_MINIFY`: pass|fail + one-line evidence
- `PHI_MISSION`: pass|fail + one-line evidence
- `PHI_NICHE`: pass|fail + one-line evidence
- `CUT_LIST`: what was removed, or why nothing could be removed
