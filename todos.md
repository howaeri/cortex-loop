# TODOs — Roadmap and Status

## Planning Authority (Hard Rule)

`todos.md` is the only active planning source of truth.

- New tasks must be added here.
- Status changes must be updated here in the same PR/commit.
- Standalone planning docs are archival context only, never active authority.
- Historical plans are archived at `docs/archive/plans/`.

## Engineering Philosophy

These constraints are operating rules for this repo:

- Minimize lines, maximize leverage.
- Prefer evolved systems over pasted-on structures.
- Prefer niche-fit solutions over generic abstractions.
- If complexity rises without measured reliability gain, stop and redesign.
- If behavior cannot be enforced mechanically, it is not a real policy.

## 0) Archived Completed Work (Do Not Re-Open)

These tracks are completed and evidenced:
- [x] Hook lifecycle + kernel loop operational (`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`).
- [x] Invariant/challenge/graveyard/foundation subsystems wired and tested.
- [x] TOML genome migration complete (`cortex.toml`, stdlib `tomllib`, Python 3.11+).
- [x] CLI bootstrap/check flows implemented (`init`, `check`, `graveyard`, `repomap`).
- [x] Repo-map artifact contract stabilized (`repomap_artifact_v1`) and CLI JSON contract fixed.
- [x] Tiny-kernel hardening track (TR-0..TR-5) complete with evidence in `docs/evidence/tiny-kernel/`.
- [x] P1 alpha acceptance evidence created (anonymized summary in `docs/evidence/WEEKLY_ROLLUP_2026-02-27.md`).
- [x] P2/P3/P4 completion records and evidence are present.

## 1) Core Reliability Program (Active)

Program objective:
- Keep Cortex small while making enforcement more reliable.
- Replace brittle inference paths with explicit contracts.
- Back claims with reproducible evidence.

Design rules:
- No policy hidden in prompt prose; enforcement must be machine-checkable.
- Keep runtime dependency-free in core path unless a strict optional profile is justified.
- Every new rule has a regression test + explicit failure mode.
- Prefer deleting code over adding code when behavior can be preserved.

### Sprint 1 — Kernel Compression + Contract-First Stop Channel

Target outcome:
- `core.py` returns to orchestration role.
- Stop contract/source resolution and revert policy become standalone modules.

Implementation:
- [x] Add `cortex/stop_contract.py` to centralize stop field resolution and structured-source policy.
- [x] Add `cortex/stop_policy.py` to centralize deterministic status/revert decisions.
- [x] Refactor `CortexKernel.on_stop` to use those modules.
- [x] Keep stop response contract backward-compatible.
- [x] Add dedicated tests:
  - [x] `tests/test_stop_contract.py`
  - [x] `tests/test_stop_policy.py`
- [x] Add native submit path design note (`cortex_submit_task(...)`) to replace trailer dependency long-term (`docs/NATIVE_STOP_SUBMIT_DESIGN.md`).

Acceptance evidence:
- [x] `docs/evidence/genius-sprint1/line-counts-before-after.txt`
- [x] `docs/evidence/genius-sprint1/behavior-compat-notes.md`
- [x] `pytest -q` + `ruff check` logs captured in evidence folder.

Sprint 1 status:
- [x] Completed

### Sprint 2 — Matching, Safety, and Resilience

Target outcome:
- Better repeat-failure detection, safer invariant execution boundaries, and resilient store writes.

Sprint 2 archive reference:
- `docs/archive/plans/SPRINT2_FIRST_TIME_RIGHT_PLAN.md` (historical only)

Sprint 2 gates:
- [x] Gate 0 baseline lock artifacts captured (`docs/evidence/genius-sprint2/00-*`).
- [x] Workstream A complete (graveyard quality + deterministic behavior + evidence).
- [x] Workstream B complete (container preflight checks + evidence).
- [x] Workstream C complete (store dedup + lock stress + evidence).
- [x] Workstream D complete (compression pass + final line budget + summary).
- [x] Sprint 2 closeout complete (`pytest -q` + `ruff` + `todos` links updated).

Implementation:
- [x] Graveyard semantic uplift (normalized tokens + semantic overlap signal).
- [x] Add optional FTS5/BM25 path for semantic retrieval when available, with deterministic fallback.
- [x] Add invariant execution modes (`host`/`container`) with config and tests.
- [x] Add SQLite lock retry/backoff for write paths.
- [x] Add store write helper de-duplication pass (remove repeated lambda write patterns).
- [x] Add `cortex check` container-mode preflight warnings (engine presence, actionable output).
- [x] Add Sprint 2 mandatory compression pass to hit net line budget target.

Acceptance evidence:
- [x] `docs/evidence/genius-sprint2/graveyard-quality-cases.md`
- [x] `docs/evidence/genius-sprint2/container-mode-checks.md`
- [x] `docs/evidence/genius-sprint2/sqlite-lock-stress.md`
- [x] `docs/evidence/genius-sprint2/99-final-lines.txt`
- [x] `docs/evidence/genius-sprint2/summary.md`

### Sprint 3 — Agent-Agnostic Ingestion + Aider Parity Gates

Target outcome:
- Kernel is adapter-driven and parity claims are evidence-backed.

Implementation:
- [x] Add adapter boundary (`cortex/adapters.py`) + Claude adapter.
- [x] Add minimal `AiderAdapter` normalization implementation.
- [x] Add adapter contract tests shared across providers.
- [ ] Complete parity gates from `docs/REPOMAP_PARITY_CRITERIA.md`:
  - [ ] frontend-heavy repo run
  - [ ] backend-heavy repo run
  - [ ] mixed monorepo run
  - [ ] relevance >= 80% top-10 across all
  - [ ] runtime SLO checks (median/p95)

Acceptance evidence:
- [ ] `docs/evidence/parity/parity-exit-report.md`
- [ ] 5+ normalized baseline-vs-enabled packets in `docs/evidence/`.

### Sprint 4 — Share-Grade OSS Discipline

Target outcome:
- Repo is externally auditable and reproducible without handholding.

Implementation:
- [x] Publish hard “works now vs not yet” table in README.
- [x] Add contribution policy requiring evidence-backed changes.
- [x] Add release checklist (tests/lint/contracts/evidence).
- [x] Produce one clean-environment reproduction walkthrough.

Acceptance evidence:
- [x] `docs/evidence/release-v1/repro-walkthrough.md`
- [ ] tagged release checklist with all gates green.

## 2) Aider Graft Parity Gates (Still Required)

Source of truth:
- `docs/REPOMAP_PARITY_CRITERIA.md`

Parser policy (new, explicit):
- Operational mode may keep deterministic heuristic fallback for bootstrap/non-blocking behavior.
- Parity completion does **not** accept regex/heuristic-only parsing as sufficient.
- "Aider parity complete" requires tree-sitter-backed structural parsing in parity runs.

Open gates:
- [ ] Quality gate: 3 production-like repos, top-10 relevance >= 80% each.
- [ ] Stability gate: median <=2s, p95 <=5s, non-blocking SessionStart under timeout pressure.
- [ ] Regression gate: fixture breadth + ranking regression coverage maintained.
- [ ] Testing gate: >=5 comparable baseline-vs-enabled runs with outcome-linked decisions.
- [ ] Exit packet: gate-by-gate PASS/FAIL in `parity-exit-report.md`.
- [ ] Parser integrity gate (for parity claim):
  - [ ] Add a parity profile that requires tree-sitter deps to be present.
  - [ ] Fail parity runs when tree-sitter deps are missing (do not silently downgrade to heuristic mode).
  - [ ] Add syntax-stress fixtures (nested exports, multiline constructs, unconventional syntax) across TS/Python/mixed repos.
  - [ ] Record regex/fallback miss cases vs tree-sitter success cases in evidence packet.
  - [ ] Require parser backend + dependency state in parity report metadata.

## 3) Public-Ready Program (Immediate)

Program objective:
- Make the repo credible, safe, and easy for external contributors to use.
- Close trust gaps before wider sharing (legal, security, contribution UX, release hygiene, observability).
- Improve cross-project visibility so version/status is easy to track.

Public-ready exit bar (all required):
- [x] GitHub Community Profile >= 90% (target: 100%).
- [x] Branch/ruleset protections enabled on `main` with required CI checks.
- [x] CI green on clean clone (`pytest -q`, `ruff check cortex tests`) and required for merge.
- [x] Security disclosure and support pathways are explicit.
- [x] Release process is reproducible and documented (tag + changelog + checklist).
- [x] Project-level status/version observability exists across multiple downstream repos.

### PR-0 — Baseline and guardrails
- [x] Capture baseline evidence:
  - [x] `gh api repos/howaeri/cortex-loop/community/profile` JSON saved under `docs/evidence/public-ready/`.
  - [x] `gh api repos/howaeri/cortex-loop/rulesets` JSON saved under `docs/evidence/public-ready/`.
  - [x] Fresh-clone verification run packet saved (`clean-init.json`, `clean-check.json`, `clean-fleet.json`).
- [x] Add `docs/evidence/public-ready/README.md` with command index and timestamps.
- [x] Add a “Public Ready” section to `docs/RELEASE_CHECKLIST.md` so readiness is a release gate, not ad-hoc.

### PR-1 — Community health completeness (external trust baseline)
- [x] Add `LICENSE` (MIT full text; not metadata-only in `pyproject.toml`).
- [x] Add `CODE_OF_CONDUCT.md` (Contributor Covenant or equivalent).
- [x] Add `SECURITY.md` with:
  - [x] reporting channel
  - [x] response SLA targets
  - [x] disclosure policy and out-of-scope notes
- [x] Add `SUPPORT.md` (where to ask usage vs bug vs security questions).
- [x] Add `.github/ISSUE_TEMPLATE/`:
  - [x] bug report template with repro requirements
  - [x] feature request template with mission-fit rubric
  - [x] config/integration support template
- [x] Add `.github/PULL_REQUEST_TEMPLATE.md` requiring:
  - [x] tests/evidence updates
  - [x] contract-impact declaration
  - [x] `PHILOSOPHY_AUDIT` block for this repo
- [x] Add `.github/CODEOWNERS` for load-bearing areas (`cortex/`, `tests/`, `docs/`).
- [x] Verify GitHub Community Profile >= 90%, then 100% (after merge/push).

### PR-2 — Merge safety and automation
- [x] Add CI workflow `.github/workflows/ci.yml`:
  - [x] matrix Python versions (3.11+)
  - [x] run `pytest -q`
  - [x] run `ruff check cortex tests`
  - [x] fail fast on lint/test regressions
- [x] Add workflow for packaging sanity (`python -m build`, optional `twine check`).
- [x] Add `.github/dependabot.yml` (GitHub Actions + pip ecosystem).
- [x] Add branch protection/rulesets:
  - [x] require pull request review (>=1)
  - [x] require status checks to pass before merge
  - [x] block force pushes/deletions on `main`
  - [x] require up-to-date branch before merge (if workflow supports)
- [x] Capture ruleset JSON in `docs/evidence/public-ready/`.

### PR-3 — Release discipline and compatibility contract
- [x] Add `CHANGELOG.md` (Keep-a-Changelog format, SemVer-compatible tags).
- [x] Add release template/checklist section for:
  - [x] “works now vs not yet” delta
  - [x] schema/contract compatibility notes
  - [x] migration notes for downstream projects
- [x] Add version compatibility table in README:
  - [x] Cortex version
  - [x] `cortex.toml` schema expectations
  - [x] DB schema version/migration requirements
  - [x] hook contract expectations (Claude + adapters)
- [x] Add upgrade doc (`docs/UPGRADE.md`) with “from previous alpha” steps and rollback guidance.
- [ ] Add first tagged alpha release once CI + docs gates are green.

### PR-4 — Solve cross-project status/version observability (pain point)
- [x] Extend `cortex check` with `--json` mode:
  - [x] include `cortex_version`
  - [x] include config parse state + schema version
  - [x] include DB status + schema version
  - [x] include hook wiring summary
  - [x] include invariant path existence + warnings
  - [x] include repomap mode/dependency state
- [x] Add `cortex fleet status --roots <path...>`:
  - [x] prints compact table for many projects
  - [x] output modes: text + JSON
  - [x] non-zero exit only on hard errors, warnings remain visible
- [x] Add optional status artifact `.cortex/status.json` for downstream tooling and snapshots.
- [x] Add docs page `docs/FLEET_OPERATIONS.md`:
  - [x] how to monitor multiple testing projects
  - [x] how to pin Cortex version per project
  - [x] how to run upgrade waves safely
- [x] Add tests for JSON contract stability and multi-root aggregation.

### PR-5 — Public critique preemption (what outsiders will challenge first)
- [x] Critique: “Stop payload parsing is brittle”
  - [x] default projects to structured stop payload mode (starter + example config)
  - [x] message fallback opt-in only, explicitly labeled as degraded path
  - [x] document migration path to native submit/tool call
- [x] Critique: “Too coupled to Claude Code”
  - [x] keep adapter boundary strict in core routing
  - [x] ship minimal `AiderAdapter` and contract tests
  - [x] add provider-agnostic event schema doc
- [x] Critique: “Running invariants is unsafe”
  - [x] make container mode strongly documented with threat model
  - [x] add explicit warning when running host mode in untrusted repos
  - [x] publish secure defaults guidance by risk profile
  - [ ] follow-up: secure-by-default decision (still open)
    - [ ] decide policy: keep host default vs switch init default to container for new projects
    - [ ] if host remains default, require explicit trusted-repo acknowledgement in `cortex init`
    - [ ] add `cortex init --profile {trusted,untrusted}` and persist profile in `cortex.toml`
    - [ ] ensure `cortex check` fails (not warns) when profile is `untrusted` and `execution_mode = "host"`
    - [ ] add migration notes + before/after onboarding friction metrics in evidence packet
- [ ] Critique: “Graveyard similarity can miss semantic repeats”
  - [ ] maintain deterministic hybrid scoring tests
  - [ ] benchmark false-negative/false-positive rate on fixture set
  - [ ] set regression thresholds to prevent drift
- [ ] Critique: “SQLite lock risk under concurrency”
  - [ ] keep lock retry/backoff tests and stress evidence current
  - [ ] document throughput limits and escalation criteria

### PR-6 — Graft governance (critical as grafting expands)
- [x] Add `docs/GRAFT_POLICY.md` with required gates for each graft:
  - [x] provenance (source commit/tag/date, why selected)
  - [x] license compatibility (SPDX + obligations)
  - [x] adaptation scope (what copied, what rewritten, what omitted)
  - [x] fallback behavior when optional deps unavailable
  - [x] rollback path and kill-switch config
- [x] Add per-graft provenance notes under `docs/grafts/<name>.md`.
- [x] Add minimal “graft acceptance packet” template in `docs/evidence/templates/`.
- [x] Add explicit “no parity claim before evidence gate pass” rule for grafted features.
- [x] Add dependency profile impact report requirement for every new optional extra.

### PR-7 — Benchmarks and SLOs (quality bar made measurable)
- [ ] Reliability SLO:
  - [ ] 0 known failing tests on `main`
  - [ ] CI pass rate >= 95% trailing 30 days
- [ ] Performance SLO:
  - [ ] repo-map median runtime <= 2s and p95 <= 5s on parity fixtures
- [ ] Onboarding SLO:
  - [ ] fresh user can run `pip install -e .`, `cortex init`, `cortex check` in <= 10 minutes
  - [ ] first external contributor can open a passing PR without maintainer intervention
- [ ] Security/process SLO:
  - [ ] security report acknowledgement <= 48h
  - [ ] triage of standard issues <= 5 business days
- [ ] Observability SLO:
  - [ ] `cortex fleet status` covers all active testing projects in one run
  - [ ] version drift across projects is detectable automatically

### PR-8 — Evidence and publication packet
- [x] Add `docs/evidence/public-ready/public-ready-exit-report.md` with gate-by-gate PASS/FAIL.
- [x] Include command transcripts and raw JSON artifacts for each gate.
- [x] Add “known limitations” section with explicit non-claims.
- [x] Add “how to help” contributor onboarding flow in README + CONTRIBUTING.
- [ ] Publish share-ready tag only when PR-1..PR-8 gates pass.

### PR-9 — External Perception Pack (Immediate)

Objective:
- Make the repo legible in 3 minutes to a new human or AI reviewer.
- Present Cortex as a sharp, original maintainer-built system with clear proof, not just process.

Deliverables:
- [x] Add `START_HERE.md` with:
  - [x] 60-second overview
  - [x] 5-minute verify commands
  - [x] what is proven vs what is not claimed
  - [x] direct links to key docs and evidence
- [x] Add a short proof block near the top of `README.md`:
  - [x] “before vs after” quality deltas from real testing runs
  - [x] one benchmark table with source links
  - [x] one explicit limitation line to preserve trust
- [x] Add maintainer essay `docs/WHY_CORTEX.md` (first-person):
  - [x] problem origin (why this exists)
  - [x] design thesis (small mechanical pressure > prompt theater)
  - [x] what changed during testing
  - [x] what we still refuse to claim
  - [x] how contributors can push the next proof frontier
- [x] Add `docs/DEMO.md`:
  - [x] exact commands for “install -> init -> check -> repomap”
  - [x] expected outputs (brief, copy-pastable)
  - [x] failure modes and recovery commands
- [x] Add one canonical evidence packet pointer in README:
  - [x] single link for “show me proof now” (run index + one best packet)

Acceptance criteria:
- [ ] A new reviewer can answer in under 3 minutes:
  - [ ] What Cortex does
  - [ ] What is actually proven
  - [ ] What remains open
- [ ] A new reviewer can run demo commands in under 10 minutes without maintainer help.
- [ ] Tone reads as deliberate maintainer writing (not generated policy boilerplate).
- [x] No conflict with active truth sources (`todos.md`, `docs/SHARE_STATUS.md`, `docs/evidence/*`).

Research anchors (official references used for this plan):
- GitHub Community Profile and health files: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-community-profiles-for-public-repositories
- CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- Security policy (`SECURITY.md`): https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository
- Support resources (`SUPPORT.md`): https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/adding-support-resources-to-your-project
- Issue forms/templates: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
- Branch protection/rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- Dependabot config: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file
- Python packaging metadata (`pyproject.toml`): https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Publishing with GitHub Actions / Trusted Publishing flow: https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
- PyPI Trusted Publishers: https://docs.pypi.org/trusted-publishers/
- SemVer: https://semver.org/spec/v2.0.0.html
- Changelog convention: https://keepachangelog.com/en/1.1.0/
- OpenSSF Scorecard (supply-chain posture): https://github.com/ossf/scorecard

## 4) Next After Parity

### P5 — Storage/State Evolution (SQL-first)
- [ ] Keep core enforcement state in SQLite (`sessions`, `events`, `graveyard`, `invariants`, `challenge_results`).
- [ ] Define checkpoint shadow schema/design for runtime state evolution.
- [ ] Add migration/versioning policy for `.cortex/cortex.db`.
- [ ] Add backup/export command for evidence portability.

## 5) Longer-Term Goals (Locked)

North-star:
- Ship Cortex as a quality/judgment layer that measurably improves outcomes, lowers oversight load, preserves velocity, and reaches true repo-map parity for practical coding tasks.

Objective criteria:
- [ ] Repo-map parity on at least 3 real-world repo classes with evidence.
- [ ] SessionStart + manual preflight produce consistent usable artifacts.
- [ ] Invariant/challenge/graveyard/foundation loop measurably changes agent behavior.
- [ ] Testing trend improves (`interrupt_count` down, `escaped_defects` down).
- [ ] Turnkey setup works without manual surgery.

Mission guardrails:
- [ ] Do not turn Cortex into prompt theater.
- [ ] Do not become generic multi-agent framework bloat.
- [ ] Do not add bureaucracy without reliability gain.
- [ ] Do not claim parity without evidence packets.
- [ ] Prefer small, high-leverage, measurable changes.
