# Release Checklist

Use this before tagging a shareable release.

If a release increases complexity without measurable reliability gain, do not tag it.

## A) Verification

- [ ] `pytest -q` passes.
- [ ] `ruff check cortex tests` passes.
- [ ] CLI sanity:
  - [ ] `cortex --help`
  - [ ] `cortex init --root <tmp>`
  - [ ] `cortex check --root <tmp>`
  - [ ] hook commands run with minimal JSON payload

## B) Contracts

- [ ] Hook response contract unchanged, or documented.
- [ ] `repomap_artifact_v1` unchanged, or versioned.
- [ ] Stop-path behavior changes reflected in `ARCHITECTURE.md`.

## C) Evidence

- [ ] New reliability/performance claims have evidence artifacts.
- [ ] Repo-map parity claims map to `docs/REPOMAP_PARITY_CRITERIA.md`.
- [ ] If parity is incomplete, docs explicitly say so.

## D) Docs

- [ ] `README.md` status is current.
- [ ] `docs/SHARE_STATUS.md` is current.
- [ ] `todos.md` status is current.
- [ ] `ARCHITECTURE.md` matches implementation.

## E) Public readiness

- [ ] `LICENSE`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md` are present and current.
- [ ] `.github` templates/workflows align with current policy.
- [ ] `cortex check --json` and `cortex fleet status --json` evidence captured.
- [ ] `docs/evidence/public-ready/public-ready-exit-report.md` updated.

## F) Tag readiness

- [ ] Clean release commit.
- [ ] `CHANGELOG.md` updated.
- [ ] Release notes include:
  - completed gates
  - known limitations
  - next milestone focus
