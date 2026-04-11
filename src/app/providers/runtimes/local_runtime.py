"""Local runtime — loads and runs a model from a local directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.app.domain.models import RawProviderPayload
from src.app.providers.runtimes.base import BaseRuntime


class LocalRuntime(BaseRuntime):
    """Runtime for locally installed models.

    In V1 this is a skeleton — actual model loading will be integrated
    when specific providers (PaddleOCR, etc.) are wired in.
    """

    def execute(
        self,
        image_path: Path,
        model_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> RawProviderPayload:
        raise NotImplementedError(
            "LocalRuntime.execute is not yet implemented. "
            "In V1, provide raw payloads directly to the job service."
        )

    def is_available(self) -> bool:
        return True
