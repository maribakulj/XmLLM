"""Base runtime ABC — defines how a provider is executed."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.app.domain.models import RawProviderPayload


class BaseRuntime(ABC):
    """Abstract base for provider runtimes (local, hub, api)."""

    @abstractmethod
    def execute(
        self,
        image_path: Path,
        model_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> RawProviderPayload:
        """Run the provider on an image and return the raw output.

        Args:
            image_path: Path to the input image file.
            model_id: Model identifier (local path, hub ID, or API model name).
            options: Additional provider-specific options.

        Returns:
            RawProviderPayload wrapping the provider's raw JSON output.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this runtime is usable in the current environment."""
        ...
