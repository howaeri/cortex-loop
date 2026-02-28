from __future__ import annotations

import subprocess
import shutil
import sys
from pathlib import Path

import pytest

from cortex.genome import HooksConfig, InvariantGraduationConfig, InvariantsConfig
from cortex.invariants import InvariantRunner
from cortex.store import SQLiteStore


@pytest.fixture
def pytest_bin() -> str:
    found = shutil.which("pytest") or str(Path(sys.executable).with_name("pytest"))
    if not Path(found).exists():
        pytest.fail("pytest binary not available for invariant runner tests")
    return found


def _runner(tmp_path: Path, pytest_bin: str) -> tuple[InvariantRunner, SQLiteStore]:
    store = SQLiteStore(tmp_path / ".cortex" / "cortex.db")
    store.initialize()
    cfg = InvariantsConfig(
        suite_paths=[],
        pytest_bin=pytest_bin,
        run_on_stop=True,
        graduation=InvariantGraduationConfig(enabled=True, target_dir="tests/invariants/graduated"),
    )
    runner = InvariantRunner(tmp_path, store, cfg, HooksConfig(mode="strict"))
    return runner, store


def test_runner_pass_result(tmp_path: Path, pytest_bin: str) -> None:
    test_file = tmp_path / "tests" / "invariants" / "test_pass.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = [str(test_file.relative_to(tmp_path))]
    report = runner.run("sess-1", extra_pytest_args=["-q"])
    assert report.ok is True
    assert len(report.results) == 1
    assert report.results[0].status == "pass"


def test_runner_fail_result_sets_revert_in_strict_mode(tmp_path: Path, pytest_bin: str) -> None:
    test_file = tmp_path / "tests" / "invariants" / "test_fail.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_fail():\n    assert 1 == 2\n", encoding="utf-8")
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = [str(test_file.relative_to(tmp_path))]
    report = runner.run("sess-1", extra_pytest_args=["-q"])
    assert report.ok is False
    assert report.recommend_revert is True
    assert report.results[0].status == "fail"


def test_runner_missing_path_handled(tmp_path: Path, pytest_bin: str) -> None:
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = ["tests/invariants/does_not_exist.py"]
    report = runner.run("sess-1")
    assert report.ok is False
    assert report.results[0].status == "missing"
    assert "not found" in report.results[0].stderr.lower()


def test_promote_session_test_copies_and_records(tmp_path: Path, pytest_bin: str) -> None:
    src = tmp_path / "tests" / "session" / "test_candidate.py"
    src.parent.mkdir(parents=True)
    src.write_text("def test_candidate():\n    assert True\n", encoding="utf-8")
    runner, store = _runner(tmp_path, pytest_bin)
    promoted = runner.promote_session_test("sess-1", src)
    assert promoted.exists()
    assert promoted.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    with store.connection() as conn:
        row = conn.execute(
            "SELECT status, test_path, graduated_from FROM invariants WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()
    assert row["status"] == "graduated"
    assert row["test_path"].endswith("tests/invariants/graduated/test_candidate.py")
    assert row["graduated_from"] == str(src)


def test_runner_container_mode_uses_container_command(
    tmp_path: Path, pytest_bin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_file = tmp_path / "tests" / "invariants" / "test_pass.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = [str(test_file.relative_to(tmp_path))]
    runner.config.execution_mode = "container"
    runner.config.container_engine = "docker"
    runner.config.container_image = "python:3.11-slim"
    runner.config.container_workdir = "/workspace"

    observed: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):  # noqa: ANN001
        observed["cmd"] = cmd
        observed["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    report = runner.run("sess-1", extra_pytest_args=["-q"])

    assert report.ok is True
    cmd = observed["cmd"]
    assert isinstance(cmd, list)
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert "-v" in cmd
    assert "-w" in cmd
    assert "python" in cmd
    assert "pytest" in cmd
    assert "tests/invariants/test_pass.py" in cmd


def test_runner_container_mode_missing_engine_is_error(
    tmp_path: Path, pytest_bin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_file = tmp_path / "tests" / "invariants" / "test_pass.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = [str(test_file.relative_to(tmp_path))]
    runner.config.execution_mode = "container"
    runner.config.container_engine = "missing-docker"

    def _fake_run(cmd, **kwargs):  # noqa: ANN001, ARG001
        raise FileNotFoundError("missing-docker")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    report = runner.run("sess-1", extra_pytest_args=["-q"])

    assert report.ok is False
    assert report.results[0].status == "error"
    assert "missing-docker" in report.results[0].stderr


def test_runner_container_mode_rejects_suite_outside_repo_root(
    tmp_path: Path, pytest_bin: str
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-test.py"
    outside.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    runner, _ = _runner(tmp_path, pytest_bin)
    runner.config.suite_paths = [str(outside)]
    runner.config.execution_mode = "container"
    runner.config.container_engine = "docker"

    report = runner.run("sess-1", extra_pytest_args=["-q"])

    assert report.ok is False
    assert report.results[0].status == "error"
    assert "outside repo root" in report.results[0].stderr.lower()


def test_runner_container_mode_uses_resolved_repo_root_for_bind_mount(
    tmp_path: Path, pytest_bin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_root = tmp_path / "real-root"
    real_root.mkdir(parents=True)
    link_root = tmp_path / "link-root"
    try:
        link_root.symlink_to(real_root, target_is_directory=True)
    except OSError:
        pytest.skip("symlink not supported on this filesystem")

    test_file = real_root / "tests" / "invariants" / "test_pass.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")

    store = SQLiteStore(real_root / ".cortex" / "cortex.db")
    store.initialize()
    cfg = InvariantsConfig(
        suite_paths=["tests/invariants/test_pass.py"],
        pytest_bin=pytest_bin,
        run_on_stop=True,
        graduation=InvariantGraduationConfig(enabled=True, target_dir="tests/invariants/graduated"),
    )
    runner = InvariantRunner(link_root, store, cfg, HooksConfig(mode="strict"))
    runner.config.execution_mode = "container"
    runner.config.container_engine = "docker"
    runner.config.container_image = "python:3.11-slim"
    runner.config.container_workdir = "/workspace"

    observed: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):  # noqa: ANN001
        observed["cmd"] = cmd
        observed["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    report = runner.run("sess-1", extra_pytest_args=["-q"])

    assert report.ok is True
    cmd = observed["cmd"]
    assert isinstance(cmd, list)
    mount = cmd[cmd.index("-v") + 1]
    assert mount.startswith(f"{real_root.resolve()}:")
