from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .genome import HooksConfig, InvariantsConfig
from .store import SQLiteStore


@dataclass(slots=True)
class InvariantCaseResult:
    test_path: str
    status: str
    duration_ms: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_path": self.test_path,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(slots=True)
class InvariantReport:
    configured_paths: list[str]
    results: list[InvariantCaseResult] = field(default_factory=list)
    ok: bool = True
    had_errors: bool = False
    recommend_revert: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured_paths": self.configured_paths,
            "results": [r.to_dict() for r in self.results],
            "ok": self.ok,
            "had_errors": self.had_errors,
            "recommend_revert": self.recommend_revert,
        }


class InvariantRunner:
    def __init__(
        self,
        repo_root: Path,
        store: SQLiteStore,
        config: InvariantsConfig,
        hooks_config: HooksConfig,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.store = store
        self.config = config
        self.hooks_config = hooks_config

    def run(self, session_id: str, extra_pytest_args: Iterable[str] | None = None) -> InvariantReport:
        report = InvariantReport(configured_paths=list(self.config.suite_paths))
        args = list(extra_pytest_args or [])

        for suite_path in self.config.suite_paths:
            result = self._run_one(suite_path, args)
            report.results.append(result)
            self.store.record_invariant_result(
                session_id=session_id,
                test_path=result.test_path,
                status=result.status,
                duration_ms=result.duration_ms,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            if result.status in {"fail", "error", "missing"}:
                report.ok = False
            if result.status == "error":
                report.had_errors = True

        if self.hooks_config.mode == "strict" and not report.ok:
            report.recommend_revert = self.hooks_config.recommend_revert_on_invariant_failure
        return report

    def promote_session_test(self, session_id: str, source_path: str | Path) -> Path:
        source = (self.repo_root / source_path).resolve() if not Path(source_path).is_absolute() else Path(source_path)
        target_dir = self.repo_root / self.config.graduation.target_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        shutil.copy2(source, target)
        self.store.record_invariant_result(
            session_id=session_id,
            test_path=str(target.relative_to(self.repo_root)),
            status="graduated",
            duration_ms=0,
            stdout="",
            stderr="",
            graduated_from=str(source),
        )
        return target

    def _run_one(self, suite_path: str, extra_args: list[str]) -> InvariantCaseResult:
        path = self.repo_root / suite_path
        if not path.exists():
            return InvariantCaseResult(
                test_path=suite_path,
                status="missing",
                duration_ms=0,
                stdout="",
                stderr=f"Invariant path not found: {suite_path}",
            )

        started = time.perf_counter()
        try:
            cmd = self._pytest_command(path=path, suite_path=suite_path, extra_args=extra_args)
        except ValueError as exc:
            return InvariantCaseResult(
                test_path=suite_path,
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
                stdout="",
                stderr=str(exc),
            )
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            return InvariantCaseResult(
                test_path=suite_path,
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
                stdout="",
                stderr=str(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        status = "pass" if proc.returncode == 0 else "fail"
        return InvariantCaseResult(
            test_path=suite_path,
            status=status,
            duration_ms=duration_ms,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )

    def _pytest_command(self, *, path: Path, suite_path: str, extra_args: list[str]) -> list[str]:
        if self.config.execution_mode != "container":
            return [self.config.pytest_bin, str(path), *extra_args]
        target = self._container_suite_path(path, suite_path)
        return [
            self.config.container_engine,
            "run",
            "--rm",
            "-v",
            f"{self.repo_root}:{self.config.container_workdir}",
            "-w",
            self.config.container_workdir,
            self.config.container_image,
            "python",
            "-m",
            "pytest",
            target,
            *extra_args,
        ]

    def _container_suite_path(self, path: Path, suite_path: str) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except ValueError as exc:
            raise ValueError(
                f"Container invariant path is outside repo root: {path.resolve()} (root: {self.repo_root})"
            ) from exc
