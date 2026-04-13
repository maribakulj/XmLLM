"""API runtime — calls an external HTTP endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.app.providers.runtimes.base import BaseRuntime

if TYPE_CHECKING:
    from pathlib import Path

    from src.app.domain.models import RawProviderPayload


class ApiRuntime(BaseRuntime):
    """Runtime that calls an external API endpoint.

    Supports OpenAI-compatible and custom endpoints.
    In V1 this is a skeleton — actual HTTP calls will be added
    when API-based providers are integrated.
    """

    def __init__(self, timeout: int = 60, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries

    def execute(
        self,
        image_path: Path,
        model_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> RawProviderPayload:
        raise NotImplementedError(
            "ApiRuntime.execute is not yet implemented. "
            "In V1, provide raw payloads directly to the job service."
        )

    def is_available(self) -> bool:
        return True
