"""Tests for the file store."""

from __future__ import annotations

from pathlib import Path

from src.app.persistence.file_store import FileStore


class TestFileStore:
    def test_ensure_dirs(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.ensure_dirs()
        assert (tmp_storage / "jobs").exists()
        assert (tmp_storage / "providers").exists()

    def test_save_and_load_json(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        data = {"key": "value", "number": 42}
        store.save_json("job_001", "test.json", data)
        loaded = store.load_json("job_001", "test.json")
        assert loaded == data

    def test_save_and_load_bytes(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        data = b"<alto>test</alto>"
        store.save_bytes("job_001", "alto.xml", data)
        loaded = store.load_bytes("job_001", "alto.xml")
        assert loaded == data

    def test_load_nonexistent_returns_none(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        assert store.load_json("missing", "test.json") is None
        assert store.load_bytes("missing", "test.xml") is None

    def test_save_raw_payload(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.save_raw_payload("job_001", {"payload": [1, 2, 3]})
        loaded = store.load_raw_payload("job_001")
        assert loaded == {"payload": [1, 2, 3]}

    def test_save_canonical(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.save_canonical("job_001", {"document_id": "doc1"})
        loaded = store.load_canonical("job_001")
        assert loaded["document_id"] == "doc1"

    def test_save_alto(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        xml = b"<?xml version='1.0'?><alto/>"
        store.save_alto("job_001", xml)
        assert store.load_alto("job_001") == xml

    def test_save_page_xml(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        xml = b"<?xml version='1.0'?><PcGts/>"
        store.save_page_xml("job_001", xml)
        assert store.load_page_xml("job_001") == xml

    def test_save_events(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        events = [{"step": "normalize", "status": "completed"}]
        store.save_events("job_001", events)
        loaded = store.load_events("job_001")
        assert loaded == events

    def test_list_jobs(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.save_json("job_aaa", "test.json", {})
        store.save_json("job_bbb", "test.json", {})
        jobs = store.list_jobs()
        assert "job_aaa" in jobs
        assert "job_bbb" in jobs

    def test_job_exists(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        assert not store.job_exists("job_001")
        store.save_json("job_001", "test.json", {})
        assert store.job_exists("job_001")

    def test_job_has_artifact(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.save_json("job_001", "canonical.json", {})
        assert store.job_has_artifact("job_001", "canonical.json")
        assert not store.job_has_artifact("job_001", "alto.xml")

    def test_provider_crud(self, tmp_storage: Path) -> None:
        store = FileStore(tmp_storage)
        store.ensure_dirs()
        store.save_provider("paddle", {"provider_id": "paddle", "family": "word_box_json"})
        assert store.load_provider("paddle") is not None
        assert "paddle" in store.list_providers()
        assert store.delete_provider("paddle")
        assert store.load_provider("paddle") is None

    def test_save_input_image(self, tmp_storage: Path, tmp_path: Path) -> None:
        store = FileStore(tmp_storage)
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        result = store.save_input_image("job_001", img)
        assert result.exists()
        assert result.name == "input.png"
        assert store.get_input_image_path("job_001") == result
