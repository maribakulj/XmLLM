"""Job models — represents a single OCR processing run."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """State machine for job lifecycle."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class Job(BaseModel):
    """A single OCR processing job."""

    job_id: str = Field(min_length=1)
    status: JobStatus = JobStatus.QUEUED

    # Input
    provider_id: str = Field(min_length=1)
    provider_family: str = Field(min_length=1)
    source_filename: str | None = None
    image_width: int | None = Field(default=None, gt=0)
    image_height: int | None = Field(default=None, gt=0)

    # Results
    has_raw_payload: bool = False
    has_canonical: bool = False
    has_alto: bool = False
    has_page_xml: bool = False
    has_viewer: bool = False

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Errors and warnings
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None

    def to_summary(self) -> dict[str, Any]:
        """Lightweight summary for list views."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "provider_id": self.provider_id,
            "source_filename": self.source_filename,
            "created_at": self.created_at.isoformat(),
            "duration_ms": self.duration_ms,
            "has_alto": self.has_alto,
            "has_page_xml": self.has_page_xml,
            "error": self.error,
        }
