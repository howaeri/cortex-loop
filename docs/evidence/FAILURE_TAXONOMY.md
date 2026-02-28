# Testing Failure Taxonomy

Use these tags in run packets and run index rows.

- `discovery_miss`: repo-map omitted files central to task implementation.
- `ranking_noise`: irrelevant files (lockfiles/docs/build output) outranked primary work files.
- `hallucinated_path`: agent referenced/edited nonexistent paths or wrong roots.
- `policy_miss`: challenge/requirement/invariant contract not supplied or malformed.
- `env_friction`: permissions/cwd/tooling mismatch caused avoidable interrupts.
- `none`: no material failure category observed.

## Severity guide

- `high`: blocked progress or escaped defect risk.
- `medium`: slowed progress materially; required manual correction.
- `low`: minor noise with no significant output impact.
