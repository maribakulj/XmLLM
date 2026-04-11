"""Tests for the Settings service."""

from __future__ import annotations

from pathlib import Path

from src.app.settings import AppMode, Settings


class TestSettings:
    def test_default_mode_is_local(self, tmp_storage: Path) -> None:
        s = Settings(storage_root=tmp_storage)
        assert s.app_mode == AppMode.LOCAL

    def test_db_path_derived(self, tmp_storage: Path) -> None:
        s = Settings(storage_root=tmp_storage, db_name="test.db")
        assert s.db_path == tmp_storage / "test.db"

    def test_ensure_directories_creates_all(self, tmp_storage: Path) -> None:
        s = Settings(storage_root=tmp_storage)
        s.ensure_directories()
        assert s.jobs_dir.exists()
        assert s.providers_dir.exists()
        assert s.exports_dir.exists()
        assert s.cache_dir.exists()

    def test_allowed_mime_types_set(self, tmp_storage: Path) -> None:
        s = Settings(storage_root=tmp_storage)
        mimes = s.allowed_mime_types_set
        assert "image/png" in mimes
        assert "image/jpeg" in mimes

    def test_space_mode_overrides_storage_root(self, monkeypatch: object) -> None:
        import pytest

        s = Settings(app_mode="space", storage_root=Path("./data"))
        assert s.storage_root == Path("/data")
        assert s.is_space is True
