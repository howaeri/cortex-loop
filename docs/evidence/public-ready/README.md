# Public-Ready Evidence

This folder captures objective evidence for public OSS readiness work.
Artifacts in this folder are intended to be share-safe and avoid local absolute
home-directory paths where possible.

## Baseline artifacts

- `community-profile-baseline.json`
- `rulesets-baseline.json`
- `repo-settings-baseline.json`
- `community-profile-current-remote.json`
- `branch-protection-after.json`
- `repo-settings-after.json`
- `clean-init.json`
- `clean-check.json`
- `clean-fleet.json`
- `local-pytest.txt`
- `local-ruff.txt`

## Validation commands

```bash
pytest -q
ruff check cortex tests
```

```bash
cortex check --root . --json --write-status
cortex fleet status --roots . --json
```
