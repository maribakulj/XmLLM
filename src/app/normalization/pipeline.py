"""Normalization pipeline — orchestrates raw → canonical conversion.

The pipeline:
  1. Resolves the adapter from the provider registry
  2. Runs the adapter to produce a CanonicalDocument
  3. Returns the document (enrichers and validators are separate steps)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.providers.registry import get_adapter

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument, RawProviderPayload
    from src.app.domain.models.geometry import GeometryContext


def normalize(
    raw: RawProviderPayload,
    family: str,
    geometry_context: GeometryContext,
    *,
    document_id: str,
    source_filename: str | None = None,
) -> CanonicalDocument:
    """Run the normalization pipeline: raw payload → CanonicalDocument.

    Args:
        raw: The raw provider output.
        family: Provider family name (determines which adapter to use).
        geometry_context: Coordinate space of the provider output.
        document_id: ID for the produced document.
        source_filename: Original input filename.

    Returns:
        A validated CanonicalDocument.
    """
    adapter = get_adapter(family)
    return adapter.normalize(
        raw,
        geometry_context,
        document_id=document_id,
        source_filename=source_filename,
    )
