"""RawProviderPayload — the source truth.

This is an opaque wrapper around whatever the provider returned.
It is stored for audit, debug, comparison, and reproducibility.
It is never used for export or rendering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RawProviderPayload(BaseModel):
    """Opaque container for the raw output of a provider."""

    model_config = ConfigDict(frozen=True)

    provider_id: str = Field(min_length=1)
    adapter_id: str = Field(min_length=1)
    runtime_type: str = Field(min_length=1)
    model_id: str | None = None

    payload: dict[str, Any] | list[Any]
    """The raw JSON-serialisable output from the provider."""

    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    image_width: int | None = Field(default=None, gt=0)
    image_height: int | None = Field(default=None, gt=0)

    metadata: dict[str, Any] | None = None
