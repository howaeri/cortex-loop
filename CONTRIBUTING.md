# Contributing

Thanks for helping. Cortex benefits most from narrow, test-backed changes that improve reliability without adding avoidable complexity.

## Before you open a PR

1. Start with a failing test (or a reproducible bug report if a test is not feasible yet).
2. Implement the smallest change that makes it pass.
3. Run:

```bash
pytest -q
ruff check cortex tests
python3 tools/repo_hygiene_check.py --check-files
```

## Required updates per behavior change

If behavior or contracts changed, update:
- `README.md`
- `ARCHITECTURE.md`
- `todos.md` (status/checklist state)

If you make reliability/performance claims, add evidence under:
- `docs/evidence/`

Include commands and observed outputs so someone else can reproduce your claim.

## Contract safety rules

Do not silently break these interfaces:
- hook JSON request/response shape
- `repomap_artifact_v1` schema
- stop-path policy semantics in strict mode

If a contract must change, document compatibility impact and migration steps in the PR.

## Repository hygiene rules

These checks govern work on Cortex itself (not runtime behavior in downstream projects):

- No personal/client names, domains, account handles, or absolute local paths in committed files.
- Keep commit messages and docs neutral and technical ("adjusted wording" style).
- No persona/branding language in project docs or PR summaries.
- Write commit titles as end-state statements, not process narration.
  - Good: `Initial snapshot`, `docs: adjust testing terminology`
  - Avoid: `Initial scrubbed public snapshot`, `final polish pass`

CI enforces this with:

```bash
python3 tools/repo_hygiene_check.py --check-files --check-commits
```

## PR checklist

- [ ] Scope is narrow and reversible.
- [ ] Tests added/updated and passing.
- [ ] `ruff` is clean.
- [ ] Docs updated for user-visible changes.
- [ ] Evidence attached for any performance/parity/reliability claim.
- [ ] `PHILOSOPHY_AUDIT` included in PR summary.

## Fastest way to help

- Reproduce and minimize an open issue.
- Add a failing regression test first.
- Submit the smallest patch that fixes it.
- For repo-map changes, attach baseline vs enabled artifacts and top-file relevance notes.
