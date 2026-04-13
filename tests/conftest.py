"""Shared test fixtures for the XmLLM project."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.app.settings import Settings


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Temporary storage root for tests that need filesystem access."""
    storage = tmp_path / "data"
    storage.mkdir()
    return storage


@pytest.fixture
def test_settings(tmp_storage: Path) -> Settings:
    """Settings configured for testing — uses tmp_path for storage."""
    return Settings(
        app_mode="local",
        storage_root=tmp_storage,
        db_name="test.db",
        log_level="debug",
    )
