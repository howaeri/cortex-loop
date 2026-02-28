# Testing Run Packet Template

Use this template for each baseline/enabled testing run.

## Run Metadata
- run_id:
- project:
- date:
- mode: baseline | enabled
- repo_map_method: heuristic_fallback | ast_pagerank | none
- task_type: frontend | backend | mixed

## Prompt + Objective
- prompt_file_or_text:
- objective:

## Inputs
- config snapshot:
- key toggles (strict/advisory, repomap on/off):

## Outputs
- changed files:
- build/test summary:
- cortex stop summary:

## Metrics
- human_oversight_minutes:
- interrupt_count:
- escaped_defects:
- completion_minutes:
- foundation_quality:

## Repo-Map Usefulness
- top ranked files:
- relevance score (top-10 relevant / top-10):
- noise observed:

## Diff + Result
- result quality summary:
- regressions:
- next action:

## Evidence Files
- check output:
- repomap artifact:
- graveyard output:
- transcript/session ref:

## Failure Taxonomy Tags
- tags: [discovery_miss, ranking_noise, hallucinated_path, policy_miss, env_friction, none]
