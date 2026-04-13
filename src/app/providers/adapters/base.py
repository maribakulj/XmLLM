"""Base adapter ABC — defines how raw provider output is normalized."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument, RawProviderPayload
    from src.app.domain.models.geometry import GeometryContext


class BaseAdapter(ABC):
    """Abstract base for provider adapters.

    An adapter takes a RawProviderPayload and produces a CanonicalDocument.
    It handles the translation from provider-specific format to the canonical
    model, including geometry normalization and provenance tagging.
    """

    @property
    @abstractmethod
    def family(self) -> str:
        """The provider family this adapter handles (e.g. 'word_box_json')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Adapter version string (e.g. 'adapter.paddle.v1')."""
        ...

    @abstractmethod
    def normalize(
        self,
        raw: RawProviderPayload,
        geometry_context: GeometryContext,
        *,
        document_id: str,
        source_filename: str | None = None,
    ) -> CanonicalDocument:
        """Convert raw provider output to a CanonicalDocument.

        Args:
            raw: The raw provider payload.
            geometry_context: Describes the coordinate space of the provider output.
            document_id: ID for the produced CanonicalDocument.
            source_filename: Original filename of the input image.

        Returns:
            A validated CanonicalDocument.
        """
        ...
