from __future__ import annotations

from pathlib import Path


def test_repo_has_license_file() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "LICENSE").exists()


def test_repo_has_public_health_files() -> None:
    root = Path(__file__).resolve().parents[2]
    required = [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "SUPPORT.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
    ]
    for rel in required:
        assert (root / rel).exists(), rel
