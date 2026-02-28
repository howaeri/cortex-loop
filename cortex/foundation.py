from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

from .genome import FoundationConfig


@dataclass(slots=True)
class FoundationFinding:
    path: str
    churn_count: int
    level: str

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "churn_count": self.churn_count, "level": self.level}


@dataclass(slots=True)
class FoundationReport:
    generated_at: str
    enabled: bool
    git_available: bool
    watch_paths: list[str]
    warnings: list[str] = field(default_factory=list)
    findings: list[FoundationFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "enabled": self.enabled,
            "git_available": self.git_available,
            "watch_paths": self.watch_paths,
            "warnings": self.warnings,
            "findings": [f.to_dict() for f in self.findings],
        }

    def by_path(self) -> dict[str, FoundationFinding]:
        return {finding.path: finding for finding in self.findings}


class FoundationAnalyzer:
    def __init__(self, repo_root: Path, config: FoundationConfig) -> None:
        self.repo_root = repo_root
        self.config = config

    def analyze(self) -> FoundationReport:
        now = datetime.now(timezone.utc).isoformat()
        if not self.config.enabled:
            return FoundationReport(
                generated_at=now,
                enabled=False,
                git_available=False,
                watch_paths=list(self.config.watch_paths),
                warnings=["Foundation analysis disabled in cortex.toml."],
            )

        if not self._is_git_repo():
            return FoundationReport(
                generated_at=now,
                enabled=True,
                git_available=False,
                watch_paths=list(self.config.watch_paths),
                warnings=["Git repository not detected; skipping churn analysis."],
            )

        counts = self._collect_churn_counts()
        findings: list[FoundationFinding] = []
        warnings: list[str] = []
        for path, count in counts.most_common():
            level = ""
            if count >= self.config.stability_thresholds.high_churn_count:
                level = "high"
            elif count >= self.config.stability_thresholds.warn_churn_count:
                level = "warn"
            else:
                continue
            findings.append(FoundationFinding(path=path, churn_count=count, level=level))

        if findings:
            warnings.append(
                f"Foundation analysis found {len(findings)} churn-heavy files in watched paths."
            )

        return FoundationReport(
            generated_at=now,
            enabled=True,
            git_available=True,
            watch_paths=list(self.config.watch_paths),
            warnings=warnings,
            findings=findings,
        )

    def warnings_for_target_files(self, target_files: Iterable[str]) -> list[str]:
        report = self.analyze()
        if not report.findings:
            return report.warnings

        target_set = {self._norm_path(path) for path in target_files if path}
        if not target_set:
            return report.warnings

        findings = report.by_path()
        matched: list[str] = []
        for path in sorted(target_set):
            finding = findings.get(path)
            if finding is None:
                continue
            matched.append(
                f"Target file {path} is {finding.level}-churn ({finding.churn_count} touches in recent window)."
            )
        return report.warnings + matched

    def _is_git_repo(self) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def _collect_churn_counts(self) -> Counter[str]:
        cmd = ["git", "log", "--name-only", "--pretty=format:", f"-n{self.config.churn_window_commits}"]
        cmd.extend(["--", *self.config.watch_paths])
        result = subprocess.run(
            cmd,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return Counter()

        counts: Counter[str] = Counter()
        for raw in result.stdout.splitlines():
            path = raw.strip()
            if not path:
                continue
            norm = self._norm_path(path)
            if self._ignored(norm):
                continue
            counts[norm] += 1
        return counts

    def _ignored(self, path: str) -> bool:
        parts = set(PurePosixPath(path).parts)
        return any(ignored in parts for ignored in self.config.ignored_dirs)

    @staticmethod
    def _norm_path(path: str) -> str:
        return str(PurePosixPath(path))
