"""Application settings — single source of truth for configuration.

Auto-detects whether the app is running locally or on a Hugging Face Space
via the SPACE_ID environment variable.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppMode(str, Enum):
    LOCAL = "local"
    SPACE = "space"


def _detect_mode() -> AppMode:
    """Detect execution mode from environment."""
    if os.environ.get("SPACE_ID"):
        return AppMode.SPACE
    return AppMode(os.environ.get("APP_MODE", "local"))


class Settings(BaseSettings):
    """Central settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Execution mode -------------------------------------------------------
    app_mode: AppMode = Field(default_factory=_detect_mode)

    # -- Storage --------------------------------------------------------------
    storage_root: Path = Field(default=Path("./data"))
    db_name: str = "app.db"

    # -- Server ---------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 7860
    log_level: str = "info"

    # -- Upload limits --------------------------------------------------------
    max_upload_size: int = 52_428_800  # 50 MB
    allowed_mime_types: str = "image/png,image/jpeg,image/tiff,image/webp"

    # -- Provider defaults ----------------------------------------------------
    provider_timeout: int = 120
    api_provider_timeout: int = 60
    api_provider_max_retries: int = 2

    # -- Geometry -------------------------------------------------------------
    bbox_containment_tolerance: int = 5

    # -- HuggingFace ----------------------------------------------------------
    hf_home: Path | None = None

    # -- Derived properties ---------------------------------------------------

    @property
    def is_space(self) -> bool:
        return self.app_mode == AppMode.SPACE

    @property
    def db_path(self) -> Path:
        return self.storage_root / self.db_name

    @property
    def jobs_dir(self) -> Path:
        return self.storage_root / "jobs"

    @property
    def providers_dir(self) -> Path:
        return self.storage_root / "providers"

    @property
    def exports_dir(self) -> Path:
        return self.storage_root / "exports"

    @property
    def cache_dir(self) -> Path:
        return self.storage_root / "cache"

    @property
    def allowed_mime_types_set(self) -> set[str]:
        return {t.strip() for t in self.allowed_mime_types.split(",")}

    def ensure_directories(self) -> None:
        """Create all required storage directories."""
        for d in (
            self.storage_root,
            self.jobs_dir,
            self.providers_dir,
            self.exports_dir,
            self.cache_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def model_post_init(self, __context: object) -> None:
        """Apply Space-specific defaults after init."""
        if self.is_space:
            if self.storage_root == Path("./data"):
                object.__setattr__(self, "storage_root", Path("/data"))
            if self.hf_home is None:
                object.__setattr__(self, "hf_home", Path("/data/.huggingface"))
                os.environ.setdefault("HF_HOME", str(self.hf_home))


def get_settings() -> Settings:
    """Factory for dependency injection (FastAPI Depends)."""
    return Settings()
