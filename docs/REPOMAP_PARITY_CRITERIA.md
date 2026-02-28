# Repo-Map Aider Graft Parity Criteria

This document locks the objective criteria for calling the Cortex repo-map graft "Aider parity complete".

Current state: Aider graft is alpha (operational but not parity-complete).

## Scope of parity

Parity means practical usefulness for file discovery and planning quality on real coding tasks, not source-level implementation matching.

## Required gates

1. Contract gate
- Artifact remains `repomap_artifact_v1` compatible.
- Provenance method is explicit (`ast_pagerank`, `heuristic_fallback`, or `none`).
- Fallback behavior is deterministic and non-blocking.

2. Parser integrity gate
- Parity runs must use tree-sitter-backed structural parsing (no regex/heuristic-only parity claim).
- If tree-sitter dependencies are missing, parity evaluation fails (operational fallback is allowed, parity claim is not).
- Evidence packet must include parser backend/dependency state and at least one syntax-stress fixture result.

3. Quality gate
- In at least 3 production-like repos (frontend-heavy, backend-heavy, mixed), top-10 ranked files are judged task-relevant at or above 80% for representative tasks.
- Lockfiles/vendor/build outputs are suppressed from top-10 unless explicitly focused.

4. Stability gate
- `cortex repomap` runs within budget on medium repos (target median <=2s, p95 <=5s).
- `SessionStart` integration remains bounded/non-blocking (timeout honored, no hook crashes).

5. Regression gate
- Ranking regressions from testing runs are captured as tests.
- At least one fixture each for Astro/TS, Python, and mixed docs+code exists and passes.

6. Testing gate
- At least 5 baseline-vs-enabled comparisons exist with evidence packets.
- Comparisons include outcomes, top-file usefulness notes, and resulting code/test changes.

## Exit decision

Aider graft parity is complete only when all gates above pass simultaneously.

If quality gate fails but contract/stability pass, status is "operational but not parity".
