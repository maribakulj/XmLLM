"""Enricher subsystem — post-normalization enrichment pipeline.

Enrichers transform a CanonicalDocument into a new CanonicalDocument
with additional derived data. They produce new instances (models are frozen).

Every enricher MUST:
  - Set provenance.evidence_type to 'derived' or 'inferred'
  - Update geometry.status if geometry was modified
  - Add warnings when appropriate
  - Respect the active DocumentPolicy
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.app.policies.document_policy import DocumentPolicy

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument


class BaseEnricher(ABC):
    """Abstract base for enrichers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Enricher name used in audit trail."""
        ...

    @abstractmethod
    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        """Apply enrichment, returning a new document."""
        ...


class EnricherPipeline:
    """Runs a configurable chain of enrichers."""

    def __init__(self, enrichers: list[BaseEnricher] | None = None) -> None:
        self._enrichers = enrichers or []

    def add(self, enricher: BaseEnricher) -> None:
        self._enrichers.append(enricher)

    def run(
        self, doc: CanonicalDocument, policy: DocumentPolicy | None = None
    ) -> CanonicalDocument:
        """Run all enrichers in order, threading the document through."""
        if policy is None:
            policy = DocumentPolicy()

        applied: list[str] = list(doc.audit.enrichers_applied)
        current = doc

        for enricher in self._enrichers:
            current = enricher.enrich(current, policy)
            applied.append(enricher.name)

        # Update audit with enrichers applied
        new_audit = doc.audit.model_copy(update={"enrichers_applied": applied})
        return current.model_copy(update={"audit": new_audit})
