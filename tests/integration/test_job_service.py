"""Integration test: full job lifecycle via JobService."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.app.domain.models import RawProviderPayload
from src.app.jobs.models import JobStatus
from src.app.jobs.service import JobService
from src.app.persistence.db import Database
from src.app.persistence.file_store import FileStore

if TYPE_CHECKING:
    from pathlib import Path


class TestJobService:
    def _setup(self, tmp_storage: Path) -> tuple[JobService, Database, FileStore]:
        db = Database(tmp_storage / "test.db")
        db.connect()
        store = FileStore(tmp_storage)
        store.ensure_dirs()
        return JobService(db, store), db, store

    def test_full_pipeline_succeeds(self, tmp_storage: Path, fixtures_dir: Path) -> None:
        svc, db, store = self._setup(tmp_storage)

        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.word_box_json.v1",
            runtime_type="local",
            payload=payload,
            image_width=2480, image_height=3508,
        )

        # Create job
        job = svc.create_job(
            provider_id="paddleocr",
            provider_family="word_box_json",
            source_filename="test.png",
        )
        assert job.status == JobStatus.QUEUED

        # Run pipeline
        result = svc.run_job(job, raw, image_width=2480, image_height=3508)

        assert result.status == JobStatus.SUCCEEDED
        assert result.has_raw_payload
        assert result.has_canonical
        assert result.has_alto
        assert result.has_page_xml
        assert result.error is None
        assert result.duration_ms is not None
        assert result.duration_ms > 0

        # Verify artifacts on disk
        assert store.load_raw_payload(result.job_id) is not None
        assert store.load_canonical(result.job_id) is not None
        assert store.load_alto(result.job_id) is not None
        assert store.load_page_xml(result.job_id) is not None
        assert store.load_events(result.job_id) is not None

        # Verify in database
        db_job = svc.get_job(result.job_id)
        assert db_job is not None
        assert db_job.status == JobStatus.SUCCEEDED

        db.close()

    def test_job_appears_in_list(self, tmp_storage: Path, fixtures_dir: Path) -> None:
        svc, db, store = self._setup(tmp_storage)

        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=payload, image_width=2480, image_height=3508,
        )

        job = svc.create_job("paddleocr", "word_box_json")
        svc.run_job(job, raw, image_width=2480, image_height=3508)

        jobs = svc.list_jobs()
        assert len(jobs) >= 1
        assert any(j.job_id == job.job_id for j in jobs)
        db.close()

    def test_failed_job_captured(self, tmp_storage: Path) -> None:
        svc, db, store = self._setup(tmp_storage)

        raw = RawProviderPayload(
            provider_id="bad", adapter_id="v1", runtime_type="local",
            payload={"not": "a list"},  # will cause adapter to fail
        )

        job = svc.create_job("bad", "word_box_json")
        result = svc.run_job(job, raw, image_width=100, image_height=100)

        assert result.status == JobStatus.FAILED
        assert result.error is not None
        assert "list payload" in result.error

        # Should still be in DB
        db_job = svc.get_job(result.job_id)
        assert db_job is not None
        assert db_job.status == JobStatus.FAILED

        # Events should be saved even on failure
        events = store.load_events(result.job_id)
        assert events is not None
        db.close()

    def test_events_log_all_steps(self, tmp_storage: Path, fixtures_dir: Path) -> None:
        svc, db, store = self._setup(tmp_storage)

        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=payload, image_width=2480, image_height=3508,
        )

        job = svc.create_job("paddleocr", "word_box_json")
        svc.run_job(job, raw, image_width=2480, image_height=3508)

        events = store.load_events(job.job_id)
        assert events is not None
        steps = [e["step"] for e in events]
        assert "receive_file" in steps
        assert "save_raw" in steps
        assert "normalize" in steps
        assert "enrich" in steps
        assert "validate" in steps
        assert "compute_readiness" in steps
        assert "export_alto" in steps
        assert "export_page" in steps
        assert "persist" in steps
        db.close()

    def test_canonical_json_on_disk_is_valid(self, tmp_storage: Path, fixtures_dir: Path) -> None:
        svc, db, store = self._setup(tmp_storage)

        with open(fixtures_dir / "paddle_ocr_sample.json") as f:
            payload = json.load(f)

        raw = RawProviderPayload(
            provider_id="paddleocr", adapter_id="v1", runtime_type="local",
            payload=payload, image_width=2480, image_height=3508,
        )

        job = svc.create_job("paddleocr", "word_box_json")
        svc.run_job(job, raw, image_width=2480, image_height=3508)

        # Load canonical from disk and validate it
        from src.app.domain.models import CanonicalDocument
        canon_data = store.load_canonical(job.job_id)
        doc = CanonicalDocument.model_validate(canon_data)
        assert doc.document_id == job.job_id
        assert len(doc.pages) == 1
        db.close()
