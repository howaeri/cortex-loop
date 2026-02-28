from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .genome import ChallengesConfig
from .store import SQLiteStore
from .templates import BUILTIN_CHALLENGE_TEMPLATES


@dataclass(slots=True)
class ChallengeCoverage:
    category: str
    covered: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"category": self.category, "covered": self.covered, "evidence": self.evidence}


@dataclass(slots=True)
class ChallengeReport:
    active_categories: list[str]
    custom_paths: list[str]
    results: list[ChallengeCoverage]
    missing_categories: list[str]
    config_warnings: list[str]
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_categories": self.active_categories,
            "custom_paths": self.custom_paths,
            "results": [r.to_dict() for r in self.results],
            "missing_categories": self.missing_categories,
            "config_warnings": self.config_warnings,
            "ok": self.ok,
        }


class ChallengeEnforcer:
    def __init__(self, store: SQLiteStore, config: ChallengesConfig) -> None:
        self.store = store
        self.config = config

    def evaluate(
        self, session_id: str, coverage_payload: Mapping[str, Any] | None = None
    ) -> ChallengeReport:
        coverage_payload = coverage_payload or {}
        results: list[ChallengeCoverage] = []
        missing: list[str] = []
        config_warnings: list[str] = []

        missing_builtin = [
            name for name in BUILTIN_CHALLENGE_TEMPLATES if name not in self.config.active_categories
        ]
        if missing_builtin:
            config_warnings.append(
                "Built-in challenge categories missing from active set: " + ", ".join(missing_builtin)
            )

        for category in self.config.active_categories:
            raw = coverage_payload.get(category)
            covered, evidence = self._coerce_coverage(raw)
            if category not in BUILTIN_CHALLENGE_TEMPLATES:
                evidence.setdefault("warning", "Unknown category")
            if not covered:
                missing.append(category)
            result = ChallengeCoverage(category=category, covered=covered, evidence=evidence)
            results.append(result)
            self.store.record_challenge_result(session_id, category, covered, evidence)

        ok = not missing if self.config.require_coverage else True
        return ChallengeReport(
            active_categories=list(self.config.active_categories),
            custom_paths=list(self.config.custom_paths),
            results=results,
            missing_categories=missing,
            config_warnings=config_warnings,
            ok=ok,
        )

    @staticmethod
    def _coerce_coverage(raw: Any) -> tuple[bool, dict[str, Any]]:
        if isinstance(raw, bool):
            return raw, {}
        if isinstance(raw, Mapping):
            covered = bool(raw.get("covered", False))
            evidence = {str(k): v for k, v in raw.items() if str(k) != "covered"}
            return covered, evidence
        if raw is None:
            return False, {}
        return bool(raw), {"raw": raw}
