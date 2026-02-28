# Weekly Testing Rollup (2026-02-27)

## Trend lines

- Repo-map usefulness moved from low (initial heuristic run) to high (post-fix and AST-enabled runs).
- Noise suppression improved after the ranking hygiene patch (lockfiles no longer dominate top-ranked results).
- AST mode is available (`ast_pagerank`) when optional dependencies are installed.
- Stop contract reliability improved after requirement-audit parsing hardening.

## Quantitative snapshot

- Comparable normalized runs in index: 5
- Runs with repo-map enabled: 4
- Runs with top-ranked set judged highly relevant: 3/4
- Verified AST-mode run count: 1+

## Design changes justified by evidence

1. Ranking hygiene patch
- Trigger: lockfile false-positives and frontend under-ranking.
- Change: lockfile penalties + frontend path boosts.
- Evidence: `docs/evidence/genius-sprint2/summary.md`.

2. AST mode graft
- Trigger: heuristic-only ceiling and missing graph edges.
- Change: dependency-gated `ast_pagerank` path with deterministic fallback.
- Evidence: `docs/evidence/tiny-kernel/05-tr5-audit-packet.md`.

3. Requirement evidence parser hardening
- Trigger: requirement-audit gaps from common evidence string formats.
- Change: parser accepts `path:line-range` and `path note` patterns.
- Evidence: `tests/test_core.py`.

## Remaining gap

- Aider parity is still pending; additional baseline/enabled comparisons are required under `docs/REPOMAP_PARITY_CRITERIA.md`.
