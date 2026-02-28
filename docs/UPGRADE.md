# Upgrade Guide

This guide covers upgrading Cortex across alpha versions with minimum risk.
It assumes you care more about predictable behavior than speed.

## Pre-upgrade checklist

1. Run current checks and capture output:
   - `cortex check --root <project>`
   - `cortex check --root <project> --json > .cortex/pre-upgrade-status.json`
2. Ensure repo is committed so rollback is trivial.
3. Confirm invariant suite is passing before upgrading.

## Upgrade steps

1. Upgrade Cortex in your environment.
2. Re-run `cortex init --root <project> --force` only if you want refreshed starter managed files.
3. Run `cortex check --root <project> --json --write-status`.
4. If `summary.errors > 0`, fix errors before running hooks.

## Structured stop payload migration

Cortex starter configs now default to:
- `require_structured_stop_payload = true`
- `allow_message_stop_fallback = false`

If your agent runtime cannot provide structured stop fields yet, temporary fallback:
- set `allow_message_stop_fallback = true`
- keep `require_structured_stop_payload = false`

Treat fallback mode as degraded and migrate off it.

## Rollback

1. Reinstall previous Cortex version.
2. Restore previous `cortex.toml` and `.cortex/status.json` snapshot.
3. Run `cortex check --root <project>` and confirm parity with pre-upgrade status.

If rollback is noisy, treat it as a signal that the upgrade plan needs a tighter
pre-check or a narrower rollout batch.

## Compatibility notes

- Config schema: `cortex_toml_v1`
- DB schema: SQLite `PRAGMA user_version = 1`
- Repo-map artifact schema: `repomap_artifact_v1`
