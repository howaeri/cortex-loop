## Summary

## Scope and Mission Fit
- PHI_MINIFY:
- PHI_MISSION:
- PHI_NICHE:

## Behavioral Impact
- [ ] Hook response contract changed
- [ ] `repomap_artifact_v1` changed
- [ ] stop payload/strict gate behavior changed
- [ ] none of the above

If any box above is checked, explain compatibility/migration impact.

## Verification
- [ ] `pytest -q`
- [ ] `ruff check cortex tests`
- [ ] docs updated (`README.md`, `ARCHITECTURE.md`, `todos.md`) if behavior changed
- [ ] evidence artifacts added under `docs/evidence/` for claims

## PHILOSOPHY_AUDIT
- PHI_MINIFY: pass|fail + one-line evidence
- PHI_MISSION: pass|fail + one-line evidence
- PHI_NICHE: pass|fail + one-line evidence
- CUT_LIST: removed code or reason nothing removable remained
