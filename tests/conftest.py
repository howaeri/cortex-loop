from __future__ import annotations

from pathlib import Path

import pytest

from cortex.core import CortexKernel
from cortex.store import SQLiteStore


SAMPLE_TOML = """
[project]
name = "test-app"
type = "python"
root = "."

[invariants]
suite_paths = ["tests/invariants/sample_test.py"]
pytest_bin = "pytest"
run_on_stop = false

[invariants.graduation]
enabled = true
target_dir = "tests/invariants/graduated"

[challenges]
active_categories = ["null_inputs", "boundary_values", "error_handling", "graveyard_regression"]
custom_paths = [".cortex/challenges/custom.toml"]
require_coverage = true

[graveyard]
enabled = true
max_matches = 3
similarity_threshold = 0.2
min_keyword_overlap = 1

[foundation]
enabled = true
watch_paths = ["src", "pkg"]
ignored_dirs = ["node_modules", "dist", "__pycache__"]
churn_window_commits = 25

[foundation.stability_thresholds]
warn_churn_count = 2
high_churn_count = 4

[repomap]
enabled = true
run_on_session_start = true
prefer_ast_graph = true
watch_paths = ["src", "pkg"]
ignored_dirs = ["node_modules", "dist", ".git", ".cortex"]
max_ranked_files = 12
max_text_bytes = 4096
artifact_path = ".cortex/artifacts/repomap/latest.json"
non_blocking = true
session_start_timeout_ms = 1800

[hooks]
mode = "advisory"
fail_on_missing_challenge_coverage = false
recommend_revert_on_invariant_failure = true
require_requirement_audit = false
fail_on_requirement_audit_gap = false
require_evidence_for_passed_requirement = true

[metrics]
enabled = true
track = ["human_oversight_minutes", "interrupt_count", "escaped_defects", "completion_minutes", "foundation_quality"]
""".strip()


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "invariants").mkdir(parents=True)
    (tmp_path / "cortex.toml").write_text(SAMPLE_TOML + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStore:
    s = SQLiteStore(tmp_path / ".cortex" / "test.db")
    s.initialize()
    return s


@pytest.fixture
def kernel(tmp_project: Path) -> CortexKernel:
    return CortexKernel(
        root=tmp_project,
        config_path=tmp_project / "cortex.toml",
        db_path=tmp_project / ".cortex" / "cortex.db",
    )
