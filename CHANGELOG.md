# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for stable releases.

## [Unreleased]

### Added
- Public-ready governance baseline (community health files, templates, CI workflow, dependency automation).
- `cortex check --json` and `cortex fleet status` for multi-project status/version observability.

### Changed
- Starter config and examples default to structured stop payload enforcement (`require_structured_stop_payload = true`).
- Host-mode invariant execution now emits explicit trust-boundary warning in setup checks.

## [0.1.0] - 2026-02-27

### Added
- Initial alpha kernel loop with hook lifecycle integration.
- Invariant/challenge/foundation/graveyard subsystems.
- Repo-map artifact alpha (`repomap_artifact_v1`).
