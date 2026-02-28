from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

DB_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_FTS_TOKEN_RE = re.compile(r"^[a-z0-9_]+$")


@dataclass(slots=True)
class SQLiteStore:
    db_path: Path
    lock_retry_attempts: int = 3
    lock_retry_backoff_ms: int = 25
    busy_timeout_ms: int = 5000

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                  session_id TEXT PRIMARY KEY,
                  started_at TEXT NOT NULL,
                  ended_at TEXT,
                  status TEXT NOT NULL,
                  genome_path TEXT,
                  metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graveyard (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  summary TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  files_json TEXT NOT NULL,
                  keywords_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS invariants (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  test_path TEXT NOT NULL,
                  status TEXT NOT NULL,
                  duration_ms INTEGER NOT NULL,
                  stdout TEXT NOT NULL,
                  stderr TEXT NOT NULL,
                  graduated_from TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS challenge_results (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  category TEXT NOT NULL,
                  covered INTEGER NOT NULL,
                  evidence_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  hook TEXT NOT NULL,
                  tool_name TEXT,
                  status TEXT,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_session_hook ON events(session_id, hook);
                CREATE INDEX IF NOT EXISTS idx_graveyard_session ON graveyard(session_id);
                CREATE INDEX IF NOT EXISTS idx_challenge_results_session_category
                  ON challenge_results(session_id, category);
                CREATE INDEX IF NOT EXISTS idx_invariants_session_status
                  ON invariants(session_id, status);
                """
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {max(0, int(self.busy_timeout_ms))}")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _run_write(self, operation: Callable[[sqlite3.Connection], None]) -> None:
        attempts = max(0, int(self.lock_retry_attempts)) + 1
        backoff = max(0, int(self.lock_retry_backoff_ms)) / 1000.0
        for attempt in range(attempts):
            try:
                with self.connection() as conn:
                    operation(conn)
                return
            except sqlite3.OperationalError as exc:
                if not self._is_lock_error(exc) or attempt >= attempts - 1:
                    raise
                if backoff > 0:
                    time.sleep(backoff * (2**attempt))

    @staticmethod
    def _is_lock_error(exc: sqlite3.OperationalError) -> bool:
        return any(msg in str(exc).lower() for msg in ("database is locked", "database table is locked"))

    def upsert_session_start(
        self, session_id: str, status: str, genome_path: str | None, metadata: dict[str, Any] | None = None
    ) -> None:
        self._execute_write(
            """
            INSERT INTO sessions (session_id, started_at, status, genome_path, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
              status=excluded.status,
              genome_path=excluded.genome_path,
              metadata_json=excluded.metadata_json
            """,
            (
                session_id,
                _utc_now(),
                status,
                genome_path,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )

    def ensure_session_start(
        self, session_id: str, status: str, genome_path: str | None, metadata: dict[str, Any] | None = None
    ) -> None:
        self._execute_write(
            """
            INSERT OR IGNORE INTO sessions (session_id, started_at, status, genome_path, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                _utc_now(),
                status,
                genome_path,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )

    def close_session(self, session_id: str, status: str, metadata: dict[str, Any] | None = None) -> None:
        self._execute_write(
            """
            UPDATE sessions
            SET ended_at = ?, status = ?, metadata_json = ?
            WHERE session_id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(metadata or {}, sort_keys=True),
                session_id,
            ),
        )

    def record_event(
        self,
        session_id: str,
        hook: str,
        payload: dict[str, Any],
        tool_name: str | None = None,
        status: str | None = None,
    ) -> None:
        self._execute_write(
            """
            INSERT INTO events (session_id, hook, tool_name, status, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                hook,
                tool_name,
                status,
                json.dumps(payload, sort_keys=True),
                _utc_now(),
            ),
        )

    def insert_graveyard(
        self,
        session_id: str | None,
        summary: str,
        reason: str,
        files: list[str],
        keywords: list[str],
    ) -> None:
        self._execute_write(
            """
            INSERT INTO graveyard (session_id, summary, reason, files_json, keywords_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                summary,
                reason,
                json.dumps(files, sort_keys=True),
                json.dumps(keywords, sort_keys=True),
                _utc_now(),
            ),
        )

    def list_graveyard(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._list_graveyard_rows(limit)
        return [self._graveyard_row_to_item(row) for row in rows]

    def list_graveyard_fts_candidates(
        self,
        *,
        tokens: list[str],
        limit: int = 200,
        candidate_limit: int = 80,
    ) -> list[dict[str, Any]] | None:
        terms = [t for t in tokens if _FTS_TOKEN_RE.match(t)]
        if not terms or not (rows := self._list_graveyard_rows(limit)):
            return []
        with self.connection() as conn:
            try:
                conn.execute(
                    "CREATE TEMP VIRTUAL TABLE IF NOT EXISTS _cortex_graveyard_fts "
                    "USING fts5(entry_id UNINDEXED, text)"
                )
                conn.execute("DELETE FROM _cortex_graveyard_fts")
            except sqlite3.OperationalError:
                return None

            conn.executemany(
                "INSERT INTO _cortex_graveyard_fts(entry_id, text) VALUES (?, ?)",
                [
                    (
                        str(row["id"]),
                        f"{row['summary']} {row['reason']} {row['keywords_json']}",
                    )
                    for row in rows
                ],
            )
            match_query = " OR ".join(terms[:12])
            matched = conn.execute(
                """
                SELECT entry_id
                FROM _cortex_graveyard_fts
                WHERE _cortex_graveyard_fts MATCH ?
                ORDER BY bm25(_cortex_graveyard_fts), CAST(entry_id AS INTEGER) DESC
                LIMIT ?
                """,
                (match_query, max(1, int(candidate_limit))),
            ).fetchall()

        if not matched:
            return []
        row_map = {int(row["id"]): row for row in rows}
        ordered_ids = [int(row["entry_id"]) for row in matched]
        return [self._graveyard_row_to_item(row_map[eid]) for eid in ordered_ids if eid in row_map]

    def record_invariant_result(
        self,
        session_id: str,
        test_path: str,
        status: str,
        duration_ms: int,
        stdout: str,
        stderr: str,
        graduated_from: str | None = None,
    ) -> None:
        self._execute_write(
            """
            INSERT INTO invariants
              (session_id, test_path, status, duration_ms, stdout, stderr, graduated_from, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                test_path,
                status,
                duration_ms,
                stdout,
                stderr,
                graduated_from,
                _utc_now(),
            ),
        )

    def record_challenge_result(
        self, session_id: str, category: str, covered: bool, evidence: dict[str, Any] | None = None
    ) -> None:
        self._execute_write(
            """
            INSERT INTO challenge_results (session_id, category, covered, evidence_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                category,
                1 if covered else 0,
                json.dumps(evidence or {}, sort_keys=True),
                _utc_now(),
            ),
        )

    def _execute_write(self, sql: str, params: tuple[Any, ...]) -> None:
        self._run_write(lambda conn: conn.execute(sql, params))

    def _list_graveyard_rows(self, limit: int) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT id, session_id, summary, reason, files_json, keywords_json, created_at
                FROM graveyard
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    @staticmethod
    def _graveyard_row_to_item(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "summary": row["summary"],
            "reason": row["reason"],
            "files": json.loads(row["files_json"]),
            "keywords": json.loads(row["keywords_json"]),
            "created_at": row["created_at"],
        }
