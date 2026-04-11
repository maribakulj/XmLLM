"""lang_propagation enricher — propagates language from parent to child.

If a word has no language but its line or region does, the language is
propagated downward. The word's provenance is not changed — only lang is set.
"""

from __future__ import annotations

from src.app.domain.models import CanonicalDocument
from src.app.enrichers import BaseEnricher
from src.app.policies.document_policy import DocumentPolicy


class LangPropagationEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "lang_propagation"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        if not policy.allow_lang_propagation:
            return doc

        new_pages = []
        changed = False

        for page in doc.pages:
            new_regions = []
            for region in page.text_regions:
                region_lang = region.lang
                new_lines = []
                for line in region.lines:
                    line_lang = line.lang or region_lang
                    new_line = line
                    if line.lang is None and region_lang is not None:
                        new_line = line.model_copy(update={"lang": region_lang})
                        changed = True

                    new_words = []
                    for word in new_line.words:
                        if word.lang is None and line_lang is not None:
                            new_words.append(word.model_copy(update={"lang": line_lang}))
                            changed = True
                        else:
                            new_words.append(word)

                    if new_words != list(new_line.words):
                        new_line = new_line.model_copy(update={"words": new_words})

                    new_lines.append(new_line)

                new_regions.append(
                    region.model_copy(update={"lines": new_lines})
                    if new_lines != list(region.lines) else region
                )
            new_pages.append(
                page.model_copy(update={"text_regions": new_regions})
                if new_regions != list(page.text_regions) else page
            )

        if changed:
            return doc.model_copy(update={"pages": new_pages})
        return doc
