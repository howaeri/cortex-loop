# Sprint 2 Workstream A — Graveyard Quality Cases

Date: 2026-02-27

## Case outputs

From `/tmp/cortex_s2_graveyard_examples.txt`:

1. semantic catch
- Query: `cache latency failure`
- Top match: `Redis timeout connection`
- Result: semantic overlap catches conceptual repeat (`semantic_score=0.333`) with normalized overlap `['cache', 'fail', 'timeout']`.

2. file-overlap catch
- Query: `unrelated words` with file `src/db/query.py`
- Top match: `Offset pagination`
- Result: file overlap path still catches prior failure even when keyword overlap is empty.

3. no-match
- Query: `ui hero spacing polish` with file `src/landing.tsx`
- Result: no match, preventing false positives.

## Notes

- Candidate retrieval now uses optional SQLite FTS5/BM25 narrowing.
- Final scoring and ranking remain deterministic in Python.
- If FTS is unavailable or returns no candidates, the matcher falls back to full-scan scoring.
