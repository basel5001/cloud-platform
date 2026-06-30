"""SQLite database helper for the Internal Developer Platform."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

_SERVICES_DDL = """
CREATE TABLE IF NOT EXISTS services (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    type       TEXT    NOT NULL CHECK(type IN ('web', 'api', 'worker')),
    owner      TEXT    NOT NULL,
    repo_url   TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""

_ENVIRONMENTS_DDL = """
CREATE TABLE IF NOT EXISTS environments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id   INTEGER NOT NULL REFERENCES services(id),
    name         TEXT    NOT NULL CHECK(name IN ('dev', 'staging', 'prod')),
    status       TEXT    NOT NULL DEFAULT 'provisioning',
    region       TEXT    NOT NULL DEFAULT 'us-east-1',
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    destroyed_at TEXT,
    UNIQUE(service_id, name)
);
"""


class Database:
    """Thin wrapper around sqlite3 for the platform's storage needs."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("DATABASE_PATH", "platform.db")
        self._init_tables()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(_SERVICES_DDL)
            conn.execute(_ENVIRONMENTS_DDL)

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def create_service(
        self,
        name: str,
        svc_type: str,
        owner: str,
        repo_url: str,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cur = conn.execute(
                "INSERT INTO services (name, type, owner, repo_url, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, svc_type, owner, repo_url, now),
            )
            return dict(
                conn.execute("SELECT * FROM services WHERE id = ?", (cur.lastrowid,)).fetchone()
            )

    def list_services(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM services ORDER BY id").fetchall()]

    def get_service(self, service_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Environments
    # ------------------------------------------------------------------

    def create_environment(
        self,
        service_id: int,
        name: str,
        region: str = "us-east-1",
    ) -> dict[str, Any]:
        with self._connect() as conn:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cur = conn.execute(
                "INSERT INTO environments (service_id, name, status, region, created_at) VALUES (?, ?, 'provisioning', ?, ?)",
                (service_id, name, region, now),
            )
            return dict(
                conn.execute("SELECT * FROM environments WHERE id = ?", (cur.lastrowid,)).fetchone()
            )

    def list_environments(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [
                dict(r)
                for r in conn.execute("SELECT * FROM environments ORDER BY id").fetchall()
            ]

    def get_environment(self, env_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM environments WHERE id = ?", (env_id,)).fetchone()
            return dict(row) if row else None

    def update_environment_status(self, env_id: int, status: str) -> None:
        with self._connect() as conn:
            extra = ""
            params: list[Any] = [status]
            if status == "destroyed":
                extra = ", destroyed_at = ?"
                params.append(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            params.append(env_id)
            conn.execute(
                f"UPDATE environments SET status = ?{extra} WHERE id = ?",
                params,
            )

    def delete_environment(self, env_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE environments SET status = 'destroying' WHERE id = ? AND status != 'destroyed'",
                (env_id,),
            )
            return cur.rowcount > 0
