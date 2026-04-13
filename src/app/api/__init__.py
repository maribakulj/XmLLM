"""API layer — FastAPI dependencies and shared state.

This module provides dependency injection for the DB, FileStore, and
JobService, scoped to the application lifespan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.jobs.service import JobService
from src.app.persistence.db import Database
from src.app.persistence.file_store import FileStore

if TYPE_CHECKING:
    from src.app.settings import Settings

# Module-level singletons, initialized during lifespan startup.
_db: Database | None = None
_file_store: FileStore | None = None
_job_service: JobService | None = None


def init_services(settings: Settings) -> None:
    """Initialize singletons. Called once during app startup."""
    global _db, _file_store, _job_service
    _db = Database(settings.db_path)
    _db.connect()
    _file_store = FileStore(settings.storage_root)
    _file_store.ensure_dirs()
    _job_service = JobService(_db, _file_store)


def shutdown_services() -> None:
    """Clean up. Called during app shutdown."""
    global _db
    if _db:
        _db.close()
        _db = None


def get_db() -> Database:
    assert _db is not None, "Database not initialized — call init_services first"
    return _db


def get_file_store() -> FileStore:
    assert _file_store is not None, "FileStore not initialized"
    return _file_store


def get_job_service() -> JobService:
    assert _job_service is not None, "JobService not initialized"
    return _job_service
