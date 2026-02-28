from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_repo_hygiene_files_pass() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "tools" / "repo_hygiene_check.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check-files"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
