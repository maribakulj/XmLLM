"""Hub runtime — loads a model from the Hugging Face Hub."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.app.providers.runtimes.base import BaseRuntime

if TYPE_CHECKING:
    from pathlib import Path

    from src.app.domain.models import RawProviderPayload


class HubRuntime(BaseRuntime):
    """Runtime for models loaded from the Hugging Face Hub.

    Uses HF_HOME for caching. In V1 this is a skeleton.
    """

    def execute(
        self,
        image_path: Path,
        model_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> RawProviderPayload:
        raise NotImplementedError(
            "HubRuntime.execute is not yet implemented. "
            "In V1, provide raw payloads directly to the job service."
        )

    def is_available(self) -> bool:
        try:
            import huggingface_hub  # noqa: F401
            return True
        except ImportError:
            return False
