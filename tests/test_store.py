from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from cortex.store import SQLiteStore


def _table_names(store: SQLiteStore) -> set[str]:
    with store.connection() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row["name"] for row in rows}


def test_initialize_creates_tables(store: SQLiteStore) -> None:
    names = _table_names(store)
    assert {"sessions", "graveyard", "invariants", "challenge_results", "events"} <= names


def test_session_upsert_and_close_round_trip(store: SQLiteStore) -> None:
    store.upsert_session_start("sess-1", "running", "cortex.toml", {"phase": "start"})
    store.close_session("sess-1", "completed", {"phase": "stop"})

    with store.connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", ("sess-1",)).fetchone()

    assert row["status"] == "completed"
    assert row["genome_path"] == "cortex.toml"
    assert row["started_at"]
    assert row["ended_at"]
    assert json.loads(row["metadata_json"]) == {"phase": "stop"}


def test_graveyard_round_trip(store: SQLiteStore) -> None:
    store.insert_graveyard(
        session_id="sess-1",
        summary="Tried eager cache invalidation",
        reason="Race condition under concurrent writes",
        files=["src/cache.py", "src/service.py"],
        keywords=["cache", "invalidation", "race"],
    )
    rows = store.list_graveyard()
    assert len(rows) == 1
    row = rows[0]
    assert row["session_id"] == "sess-1"
    assert row["files"] == ["src/cache.py", "src/service.py"]
    assert row["keywords"] == ["cache", "invalidation", "race"]


def test_record_event_invariant_and_challenge_results(store: SQLiteStore) -> None:
    store.record_event("sess-1", "PreToolUse", {"tool": "Edit", "path": "x.py"}, tool_name="Edit", status="ok")
    store.record_invariant_result("sess-1", "tests/invariants/test_x.py", "pass", 12, "ok", "")
    store.record_challenge_result("sess-1", "null_inputs", True, {"tests": ["test_null"]})

    with store.connection() as conn:
        event = conn.execute("SELECT * FROM events WHERE session_id = ?", ("sess-1",)).fetchone()
        invariant = conn.execute("SELECT * FROM invariants WHERE session_id = ?", ("sess-1",)).fetchone()
        challenge = conn.execute(
            "SELECT * FROM challenge_results WHERE session_id = ?", ("sess-1",)
        ).fetchone()

    assert event["hook"] == "PreToolUse"
    assert event["tool_name"] == "Edit"
    assert json.loads(event["payload_json"])["tool"] == "Edit"
    assert invariant["status"] == "pass"
    assert invariant["duration_ms"] == 12
    assert challenge["category"] == "null_inputs"
    assert challenge["covered"] == 1
    assert json.loads(challenge["evidence_json"]) == {"tests": ["test_null"]}


def test_run_write_retries_lock_errors(store: SQLiteStore) -> None:
    attempts = {"count": 0}

    def operation(_conn) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise sqlite3.OperationalError("database is locked")

    store._run_write(operation)
    assert attempts["count"] == 2


def test_run_write_does_not_retry_non_lock_errors(store: SQLiteStore) -> None:
    attempts = {"count": 0}

    def operation(_conn) -> None:
        attempts["count"] += 1
        raise sqlite3.OperationalError("no such table: not_here")

    try:
        store._run_write(operation)
        raise AssertionError("expected sqlite3.OperationalError")
    except sqlite3.OperationalError:
        pass
    assert attempts["count"] == 1


def test_concurrent_event_writes_do_not_flake(tmp_path) -> None:
    store = SQLiteStore(
        tmp_path / ".cortex" / "cortex.db",
        lock_retry_attempts=6,
        lock_retry_backoff_ms=2,
        busy_timeout_ms=1500,
    )
    store.initialize()

    def _write_event(idx: int) -> None:
        store.record_event(
            session_id=f"sess-{idx % 4}",
            hook="PostToolUse",
            payload={"idx": idx},
            tool_name="Edit",
            status="ok",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(_write_event, range(80)):
            pass

    with store.connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
    assert row["n"] == 80
