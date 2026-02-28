#!/usr/bin/env python3
"""Repository hygiene checks for contributors working on Cortex itself."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
FILE_EXCLUDE_PATHS = {"tools/repo_hygiene_check.py"}

FORBIDDEN_FILE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/Users/"), "absolute local path"),
    (re.compile(r"\bfounder\s+voice\b", re.IGNORECASE), "persona/branding phrasing"),
    (re.compile(r"\bgenius\s+girl\b", re.IGNORECASE), "persona/branding phrasing"),
)

FORBIDDEN_COMMIT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bscrubbed\b", re.IGNORECASE), "process/meta wording"),
    (re.compile(r"\bpublic\s+snapshot\b", re.IGNORECASE), "process/meta wording"),
    (re.compile(r"\bfinal\s+polish\b", re.IGNORECASE), "process/meta wording"),
    (re.compile(r"\bcleanup\s+pass\b", re.IGNORECASE), "process/meta wording"),
)


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _iter_repo_files() -> Iterable[Path]:
    for rel in _git_lines("ls-files"):
        path = REPO_ROOT / rel
        if path.is_file():
            yield path


def _read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="ignore")


def _scan_text(
    source: str,
    origin: str,
    patterns: tuple[tuple[re.Pattern[str], str], ...],
) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(source.splitlines(), start=1):
        for regex, reason in patterns:
            if regex.search(line):
                errors.append(f"{origin}:{i}: {reason}: {line.strip()}")
    return errors


def check_files() -> list[str]:
    errors: list[str] = []
    for path in _iter_repo_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in FILE_EXCLUDE_PATHS:
            continue
        text = _read_text(path)
        if text is None:
            continue
        errors.extend(_scan_text(text, rel, FORBIDDEN_FILE_PATTERNS))
    return errors


def check_commits(commit_range: str) -> list[str]:
    result = None
    last_error = ""
    for candidate in (commit_range, "HEAD"):
        try:
            result = subprocess.run(
                ["git", "log", "--format=%H%x1f%B%x1e", candidate],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            break
        except subprocess.CalledProcessError as exc:
            last_error = exc.stderr.strip() or str(exc)
    if result is None:
        return [f"commit-range error ({commit_range}): {last_error}"]

    errors: list[str] = []
    for block in result.stdout.split("\x1e"):
        if not block.strip():
            continue
        sha, _, body = block.partition("\x1f")
        errors.extend(_scan_text(body, f"commit:{sha[:12]}", FORBIDDEN_FILE_PATTERNS))
        errors.extend(_scan_text(body, f"commit:{sha[:12]}", FORBIDDEN_COMMIT_PATTERNS))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Cortex repo hygiene check")
    parser.add_argument("--check-files", action="store_true", help="scan tracked files")
    parser.add_argument("--check-commits", action="store_true", help="scan commit messages")
    parser.add_argument(
        "--commit-range",
        default="HEAD~1..HEAD",
        help="git commit range for --check-commits (default: HEAD~1..HEAD)",
    )
    args = parser.parse_args()

    check_files_enabled = args.check_files or not (args.check_files or args.check_commits)
    check_commits_enabled = args.check_commits or not (args.check_files or args.check_commits)

    errors: list[str] = []
    if check_files_enabled:
        errors.extend(check_files())
    if check_commits_enabled:
        errors.extend(check_commits(args.commit_range))

    if errors:
        print("repo hygiene check failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("repo hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
