"""Tests for the SQLite database layer."""

from __future__ import annotations

from pathlib import Path

from src.app.jobs.models import Job, JobStatus
from src.app.persistence.db import Database


class TestDatabase:
    def test_connect_creates_tables(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()
        # Should not raise
        db.conn.execute("SELECT * FROM jobs LIMIT 1")
        db.conn.execute("SELECT * FROM providers LIMIT 1")
        db.close()

    def test_save_and_get_job(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        job = Job(
            job_id="job_001",
            provider_id="paddle",
            provider_family="word_box_json",
            source_filename="test.png",
        )
        db.save_job(job)

        loaded = db.get_job("job_001")
        assert loaded is not None
        assert loaded.job_id == "job_001"
        assert loaded.status == JobStatus.QUEUED
        assert loaded.provider_id == "paddle"
        assert loaded.source_filename == "test.png"
        db.close()

    def test_update_job(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        job = Job(job_id="job_002", provider_id="p", provider_family="f")
        db.save_job(job)

        updated = job.model_copy(update={
            "status": JobStatus.SUCCEEDED,
            "has_alto": True,
        })
        db.save_job(updated)

        loaded = db.get_job("job_002")
        assert loaded is not None
        assert loaded.status == JobStatus.SUCCEEDED
        assert loaded.has_alto is True
        db.close()

    def test_list_jobs(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        for i in range(5):
            db.save_job(Job(job_id=f"job_{i:03d}", provider_id="p", provider_family="f"))

        jobs = db.list_jobs(limit=3)
        assert len(jobs) == 3

        all_jobs = db.list_jobs()
        assert len(all_jobs) == 5
        db.close()

    def test_get_nonexistent_job(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()
        assert db.get_job("nonexistent") is None
        db.close()

    def test_job_with_warnings(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        job = Job(
            job_id="job_warn",
            provider_id="p",
            provider_family="f",
            warnings=["bbox overflow", "missing confidence"],
        )
        db.save_job(job)

        loaded = db.get_job("job_warn")
        assert loaded is not None
        assert len(loaded.warnings) == 2
        assert "bbox overflow" in loaded.warnings
        db.close()

    def test_job_with_error(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        job = Job(
            job_id="job_err",
            provider_id="p",
            provider_family="f",
            status=JobStatus.FAILED,
            error="Provider timeout",
        )
        db.save_job(job)

        loaded = db.get_job("job_err")
        assert loaded is not None
        assert loaded.status == JobStatus.FAILED
        assert loaded.error == "Provider timeout"
        db.close()

    def test_provider_crud(self, tmp_storage: Path) -> None:
        db = Database(tmp_storage / "test.db")
        db.connect()

        data = {"provider_id": "paddle", "family": "word_box_json"}
        db.save_provider_record("paddle", data)

        loaded = db.get_provider_record("paddle")
        assert loaded is not None
        assert loaded["provider_id"] == "paddle"

        all_providers = db.list_provider_records()
        assert len(all_providers) == 1

        assert db.delete_provider_record("paddle")
        assert db.get_provider_record("paddle") is None
        db.close()
