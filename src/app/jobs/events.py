"""Job events — structured log of each pipeline step."""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Generator

from pydantic import BaseModel, Field


class JobStep(str, Enum):
    """Named steps in the processing pipeline."""

    RECEIVE_FILE = "receive_file"
    CREATE_CONTEXT = "create_context"
    RESOLVE_PROVIDER = "resolve_provider"
    EXECUTE_RUNTIME = "execute_runtime"
    SAVE_RAW = "save_raw"
    NORMALIZE = "normalize"
    ENRICH = "enrich"
    VALIDATE = "validate"
    COMPUTE_READINESS = "compute_readiness"
    EXPORT_ALTO = "export_alto"
    EXPORT_PAGE = "export_page"
    BUILD_VIEWER = "build_viewer"
    PERSIST = "persist"


class JobEvent(BaseModel):
    """A single pipeline step event."""

    step: JobStep
    status: str = "started"  # started, completed, failed, skipped
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    message: str | None = None
    error: str | None = None


class EventLog:
    """Collects events during job execution."""

    def __init__(self) -> None:
        self._events: list[JobEvent] = []

    @property
    def events(self) -> list[JobEvent]:
        return list(self._events)

    def add(self, event: JobEvent) -> None:
        self._events.append(event)

    @contextmanager
    def step(self, step: JobStep) -> Generator[JobEvent, None, None]:
        """Context manager that auto-times a pipeline step."""
        event = JobEvent(step=step, status="started")
        self._events.append(event)
        t0 = time.monotonic()
        try:
            yield event
            elapsed = (time.monotonic() - t0) * 1000
            # Since JobEvent is a Pydantic model, update via index
            idx = len(self._events) - 1
            self._events[idx] = event.model_copy(update={
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "duration_ms": elapsed,
            })
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            idx = len(self._events) - 1
            self._events[idx] = event.model_copy(update={
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "duration_ms": elapsed,
                "error": str(exc),
            })
            raise

    def skip(self, step: JobStep, reason: str) -> None:
        """Record a skipped step."""
        self._events.append(JobEvent(
            step=step,
            status="skipped",
            completed_at=datetime.now(timezone.utc),
            message=reason,
        ))

    def to_dicts(self) -> list[dict]:
        """Serialize all events for persistence."""
        return [e.model_dump(mode="json") for e in self._events]

    @property
    def has_failures(self) -> bool:
        return any(e.status == "failed" for e in self._events)

    @property
    def total_duration_ms(self) -> float:
        return sum(e.duration_ms or 0 for e in self._events)
