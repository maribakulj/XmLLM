"""text_consistency enricher — checks that word texts aggregate correctly.

Adds warnings to pages where the concatenation of words in a line
doesn't produce sensible text (e.g. empty words, suspicious patterns).
This enricher does NOT modify text — it only adds warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.enrichers import BaseEnricher

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument
    from src.app.policies.document_policy import DocumentPolicy


class TextConsistencyEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "text_consistency"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        new_pages = []
        changed = False

        for page in doc.pages:
            warnings = list(page.warnings)

            for region in page.text_regions:
                for line in region.lines:
                    line_warnings = self._check_line(region.id, line.id, line)
                    if line_warnings:
                        warnings.extend(line_warnings)
                        changed = True

            new_pages.append(page.model_copy(update={"warnings": warnings}))

        if changed:
            return doc.model_copy(update={"pages": new_pages})
        return doc

    @staticmethod
    def _check_line(region_id: str, line_id: str, line: object) -> list[str]:
        """Check text consistency within a line."""
        warnings: list[str] = []
        words = getattr(line, "words", [])

        if not words:
            return warnings

        for i, word in enumerate(words):
            text = getattr(word, "text", "")
            if not text.strip():
                warnings.append(
                    f"{region_id}/{line_id}: word {getattr(word, 'id', i)} has blank text"
                )

            # Check for suspiciously long "words" (likely unsplit lines)
            if len(text) > 100:
                warnings.append(
                    f"{region_id}/{line_id}: word {getattr(word, 'id', i)} "
                    f"is suspiciously long ({len(text)} chars) — may be an unsplit line"
                )

        return warnings
