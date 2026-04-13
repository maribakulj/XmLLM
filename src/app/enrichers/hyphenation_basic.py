"""hyphenation_basic enricher — detects hyphenated words at line boundaries.

If a word ends with '-' at the end of a line, and the next line starts with
a lowercase word, marks both as hyphenated with the combined full_form.
"""

from __future__ import annotations

from src.app.domain.models import CanonicalDocument, Hyphenation, TextLine
from src.app.enrichers import BaseEnricher
from src.app.policies.document_policy import DocumentPolicy


class HyphenationBasicEnricher(BaseEnricher):
    @property
    def name(self) -> str:
        return "hyphenation_basic"

    def enrich(
        self, doc: CanonicalDocument, policy: DocumentPolicy
    ) -> CanonicalDocument:
        if not policy.allow_hyphenation_detection:
            return doc

        new_pages = []
        changed = False

        for page in doc.pages:
            new_regions = []
            for region in page.text_regions:
                new_lines = list(region.lines)
                modified = self._process_lines(new_lines)
                if modified:
                    changed = True
                new_regions.append(region.model_copy(update={"lines": new_lines}))
            new_pages.append(page.model_copy(update={"text_regions": new_regions}))

        if changed:
            return doc.model_copy(update={"pages": new_pages})
        return doc

    @staticmethod
    def _process_lines(lines: list[TextLine]) -> bool:
        """Process adjacent lines for hyphenation. Mutates the list in place."""
        modified = False

        for i in range(len(lines) - 1):
            line_a = lines[i]
            line_b = lines[i + 1]

            if not line_a.words or not line_b.words:
                continue

            last_word = line_a.words[-1]
            first_word = line_b.words[0]

            # Skip if already hyphenated
            if last_word.hyphenation is not None:
                continue

            # Check: last word ends with '-' and next word starts lowercase
            if not last_word.text.endswith("-"):
                continue
            if not first_word.text or not first_word.text[0].islower():
                continue

            # Build full form
            stem = last_word.text.rstrip("-")
            full_form = stem + first_word.text

            # Update last word of line A
            new_last = last_word.model_copy(update={
                "hyphenation": Hyphenation(
                    is_hyphenated=True, part=1, full_form=full_form
                ),
            })
            new_words_a = list(line_a.words[:-1]) + [new_last]
            lines[i] = line_a.model_copy(update={"words": new_words_a})

            # Update first word of line B
            new_first = first_word.model_copy(update={
                "hyphenation": Hyphenation(
                    is_hyphenated=True, part=2, full_form=full_form
                ),
            })
            new_words_b = [new_first] + list(line_b.words[1:])
            lines[i + 1] = line_b.model_copy(update={"words": new_words_b})

            modified = True

        return modified
