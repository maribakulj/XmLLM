"""Integration tests for the FastAPI routes.

Tests the full API surface: providers, jobs, exports, viewer.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from src.app.main import app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with lifespan — ensures DB/FileStore/JobService are initialized."""
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "data"))
    # Force re-creation of settings
    from src.app import settings as settings_mod
    monkeypatch.setattr(
        settings_mod,
        "get_settings",
        lambda: settings_mod.Settings(storage_root=tmp_path / "data"),
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture
def paddle_payload_bytes(fixtures_dir: Path) -> bytes:
    with open(fixtures_dir / "paddle_ocr_sample.json", "rb") as f:
        return f.read()


# -- Health ------------------------------------------------------------------


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# -- Providers ---------------------------------------------------------------


class TestProviders:
    def test_register_and_list(self, client: TestClient) -> None:
        r = client.post("/providers", json={
            "provider_id": "test_paddle",
            "display_name": "PaddleOCR Test",
            "runtime_type": "local",
            "model_id_or_path": "/models/paddle",
            "family": "word_box_json",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["provider_id"] == "test_paddle"

        # List
        r = client.get("/providers")
        assert r.status_code == 200
        providers = r.json()
        assert any(p.get("provider_id") == "test_paddle" for p in providers)

    def test_get_provider(self, client: TestClient) -> None:
        client.post("/providers", json={
            "provider_id": "get_test",
            "display_name": "Get Test",
            "runtime_type": "local",
            "model_id_or_path": "/models/test",
            "family": "word_box_json",
        })
        r = client.get("/providers/get_test")
        assert r.status_code == 200
        assert r.json()["provider_id"] == "get_test"

    def test_get_nonexistent_provider(self, client: TestClient) -> None:
        r = client.get("/providers/nonexistent")
        assert r.status_code == 404

    def test_delete_provider(self, client: TestClient) -> None:
        client.post("/providers", json={
            "provider_id": "del_test",
            "display_name": "Del Test",
            "runtime_type": "local",
            "model_id_or_path": "/models/test",
            "family": "word_box_json",
        })
        r = client.delete("/providers/del_test")
        assert r.status_code == 204

        r = client.get("/providers/del_test")
        assert r.status_code == 404

    def test_delete_nonexistent_provider(self, client: TestClient) -> None:
        r = client.delete("/providers/nonexistent")
        assert r.status_code == 404

    def test_register_invalid(self, client: TestClient) -> None:
        r = client.post("/providers", json={
            "provider_id": "",  # invalid: empty
            "display_name": "Bad",
            "runtime_type": "local",
            "model_id_or_path": "/x",
            "family": "word_box_json",
        })
        assert r.status_code == 422


# -- Jobs --------------------------------------------------------------------


class TestJobs:
    def _create_job(self, client: TestClient, payload_bytes: bytes) -> dict:
        r = client.post(
            "/jobs",
            params={
                "provider_id": "paddleocr",
                "provider_family": "word_box_json",
                "image_width": 2480,
                "image_height": 3508,
            },
            files={
                "raw_payload_file": (
                    "payload.json",
                    io.BytesIO(payload_bytes),
                    "application/json",
                ),
            },
        )
        assert r.status_code == 201
        return r.json()

    def test_create_and_run_job(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        data = self._create_job(client, paddle_payload_bytes)
        assert data["status"] == "succeeded"
        assert data["has_alto"] is True
        assert data["has_page_xml"] is True
        assert data["error"] is None

    def test_list_jobs(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        self._create_job(client, paddle_payload_bytes)
        r = client.get("/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) >= 1

    def test_get_job(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        created = self._create_job(client, paddle_payload_bytes)
        job_id = created["job_id"]

        r = client.get(f"/jobs/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["job_id"] == job_id
        assert data["status"] == "succeeded"

    def test_get_nonexistent_job(self, client: TestClient) -> None:
        r = client.get("/jobs/nonexistent")
        assert r.status_code == 404

    def test_get_job_logs(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        created = self._create_job(client, paddle_payload_bytes)
        job_id = created["job_id"]

        r = client.get(f"/jobs/{job_id}/logs")
        assert r.status_code == 200
        events = r.json()
        assert len(events) > 0
        steps = [e["step"] for e in events]
        assert "normalize" in steps
        assert "export_alto" in steps

    def test_invalid_payload(self, client: TestClient) -> None:
        r = client.post(
            "/jobs",
            params={
                "provider_id": "test",
                "provider_family": "word_box_json",
                "image_width": 100,
                "image_height": 100,
            },
            files={"raw_payload_file": ("bad.json", io.BytesIO(b"not json"), "application/json")},
        )
        assert r.status_code == 422


# -- Exports -----------------------------------------------------------------


class TestExports:
    def _create_job(self, client: TestClient, payload_bytes: bytes) -> str:
        r = client.post(
            "/jobs",
            params={
                "provider_id": "paddleocr",
                "provider_family": "word_box_json",
                "image_width": 2480,
                "image_height": 3508,
            },
            files={"raw_payload_file": ("p.json", io.BytesIO(payload_bytes), "application/json")},
        )
        return r.json()["job_id"]

    def test_get_raw_payload(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        job_id = self._create_job(client, paddle_payload_bytes)
        r = client.get(f"/jobs/{job_id}/raw")
        assert r.status_code == 200
        data = r.json()
        assert "provider_id" in data

    def test_get_canonical(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        job_id = self._create_job(client, paddle_payload_bytes)
        r = client.get(f"/jobs/{job_id}/canonical")
        assert r.status_code == 200
        data = r.json()
        assert "document_id" in data
        assert "pages" in data

    def test_get_alto(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        job_id = self._create_job(client, paddle_payload_bytes)
        r = client.get(f"/jobs/{job_id}/alto")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/xml"
        assert b"<alto" in r.content or b"alto" in r.content

    def test_get_page_xml(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        job_id = self._create_job(client, paddle_payload_bytes)
        r = client.get(f"/jobs/{job_id}/pagexml")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/xml"
        assert b"PcGts" in r.content

    def test_nonexistent_export(self, client: TestClient) -> None:
        r = client.get("/jobs/nonexistent/alto")
        assert r.status_code == 404

    def test_nonexistent_raw(self, client: TestClient) -> None:
        r = client.get("/jobs/nonexistent/raw")
        assert r.status_code == 404


# -- Viewer ------------------------------------------------------------------


class TestViewer:
    def test_viewer_fallback(self, client: TestClient, paddle_payload_bytes: bytes) -> None:
        r = client.post(
            "/jobs",
            params={
                "provider_id": "paddleocr",
                "provider_family": "word_box_json",
                "image_width": 2480,
                "image_height": 3508,
            },
            files={
                "raw_payload_file": (
                    "p.json",
                    io.BytesIO(paddle_payload_bytes),
                    "application/json",
                ),
            },
        )
        job_id = r.json()["job_id"]

        r = client.get(f"/jobs/{job_id}/viewer")
        assert r.status_code == 200
        data = r.json()
        assert "image_width" in data
        assert "image_height" in data

    def test_viewer_nonexistent(self, client: TestClient) -> None:
        r = client.get("/jobs/nonexistent/viewer")
        assert r.status_code == 404
