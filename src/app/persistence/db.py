"""SQLite database — lightweight persistence for jobs and providers.

Uses synchronous sqlite3 for V1 simplicity.  The schema auto-creates
on first access.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.app.jobs.models import Job, JobStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued',
    provider_id TEXT NOT NULL,
    provider_family TEXT NOT NULL,
    source_filename TEXT,
    image_width INTEGER,
    image_height INTEGER,
    has_raw_payload INTEGER NOT NULL DEFAULT 0,
    has_canonical INTEGER NOT NULL DEFAULT 0,
    has_alto INTEGER NOT NULL DEFAULT 0,
    has_page_xml INTEGER NOT NULL DEFAULT 0,
    has_viewer INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    warnings TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    """Thin wrapper around sqlite3 for jobs and providers."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        return self._conn  # type: ignore[return-value]

    # -- Jobs -----------------------------------------------------------------

    def save_job(self, job: Job) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO jobs
               (job_id, status, provider_id, provider_family, source_filename,
                image_width, image_height, has_raw_payload, has_canonical,
                has_alto, has_page_xml, has_viewer, created_at, started_at,
                completed_at, error, warnings)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.job_id,
                job.status.value,
                job.provider_id,
                job.provider_family,
                job.source_filename,
                job.image_width,
                job.image_height,
                int(job.has_raw_payload),
                int(job.has_canonical),
                int(job.has_alto),
                int(job.has_page_xml),
                int(job.has_viewer),
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.error,
                json.dumps(job.warnings),
            ),
        )
        self.conn.commit()

    def get_job(self, job_id: str) -> Job | None:
        row = self.conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def list_jobs(self, limit: int = 100, offset: int = 0) -> list[Job]:
        rows = self.conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        from datetime import datetime

        def _parse_dt(v: str | None) -> Any:
            if v is None:
                return None
            return datetime.fromisoformat(v)

        return Job(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            provider_id=row["provider_id"],
            provider_family=row["provider_family"],
            source_filename=row["source_filename"],
            image_width=row["image_width"],
            image_height=row["image_height"],
            has_raw_payload=bool(row["has_raw_payload"]),
            has_canonical=bool(row["has_canonical"]),
            has_alto=bool(row["has_alto"]),
            has_page_xml=bool(row["has_page_xml"]),
            has_viewer=bool(row["has_viewer"]),
            created_at=_parse_dt(row["created_at"]),
            started_at=_parse_dt(row["started_at"]),
            completed_at=_parse_dt(row["completed_at"]),
            error=row["error"],
            warnings=json.loads(row["warnings"]),
        )

    # -- Providers ------------------------------------------------------------

    def save_provider_record(self, provider_id: str, data: dict) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO providers (provider_id, data, created_at, updated_at)
               VALUES (?, ?, COALESCE((SELECT created_at FROM providers WHERE provider_id = ?), ?), ?)""",
            (provider_id, json.dumps(data, default=str), provider_id, now, now),
        )
        self.conn.commit()

    def get_provider_record(self, provider_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT data FROM providers WHERE provider_id = ?", (provider_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])

    def list_provider_records(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT data FROM providers ORDER BY created_at"
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def delete_provider_record(self, provider_id: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM providers WHERE provider_id = ?", (provider_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0
