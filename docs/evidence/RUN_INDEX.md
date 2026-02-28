# Testing Run Index

Canonical fields: `run_id`, `project`, `mode`, `task_type`, `repo_map_method`, `relevance_top10_pct`, `completion_minutes`, `interrupt_count`, `escaped_defects`, `foundation_quality`, `tags`, `evidence_packet`.

| run_id | project | mode | task_type | repo_map_method | relevance_top10_pct | completion_minutes | interrupt_count | escaped_defects | foundation_quality | tags | evidence_packet |
|---|---|---|---|---|---:|---:|---:|---:|---|---|---|
| frontend-baseline-2026-02-26 | anonymized_frontend_a | baseline | frontend | none | n/a | n/a | n/a | n/a | advisory | discovery_miss | docs/evidence/templates/testing-run-packet.md |
| frontend-enabled-2026-02-26 | anonymized_frontend_a | enabled | frontend | heuristic_fallback | 20 | n/a | n/a | n/a | advisory | ranking_noise | docs/evidence/genius-sprint1/behavior-compat-notes.md |
| frontend-postfix-2026-02-27 | anonymized_frontend_a | enabled | frontend | heuristic_fallback | 100 | n/a | n/a | n/a | advisory | none | docs/evidence/genius-sprint2/summary.md |
| workspace-enabled-2026-02-27-a | anonymized_workspace_b | enabled | frontend | heuristic_fallback | 100 | 11.34 | 0 | 0 | stable | none | docs/evidence/public-ready/public-ready-exit-report.md |
| workspace-enabled-2026-02-27-b | anonymized_workspace_b | enabled | frontend | ast_pagerank | 100 | 5.29 | 0 | 0 | stable | policy_miss | docs/evidence/tiny-kernel/05-tr5-audit-packet.md |

## Notes

- This index intentionally uses anonymized project labels.
- Personal client/project artifacts were removed from the public repository.
- Completion minutes are recorded when session start/end timestamps are available.
