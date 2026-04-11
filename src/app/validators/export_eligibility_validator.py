"""Export eligibility validator — decides what can be exported.

Consumes readiness assessments and document policy to produce
an ExportEligibility decision for the whole document.
"""

from __future__ import annotations

from src.app.domain.models import CanonicalDocument
from src.app.domain.models.readiness import ExportEligibility
from src.app.domain.models.status import ReadinessLevel
from src.app.policies.document_policy import DocumentPolicy
from src.app.validators.readiness_validator import (
    compute_page_alto_readiness,
    compute_page_pagexml_readiness,
)


def compute_export_eligibility(
    doc: CanonicalDocument,
    policy: DocumentPolicy | None = None,
) -> ExportEligibility:
    """Compute export eligibility for a document.

    Args:
        doc: The canonical document.
        policy: Document policy (uses default if None).

    Returns:
        ExportEligibility with per-format readiness levels.
    """
    if policy is None:
        policy = DocumentPolicy()

    alto_levels: list[ReadinessLevel] = []
    page_levels: list[ReadinessLevel] = []

    for page in doc.pages:
        alto_levels.append(compute_page_alto_readiness(page).level)
        page_levels.append(compute_page_pagexml_readiness(page).level)

    alto_export = _aggregate_levels(alto_levels)
    page_export = _aggregate_levels(page_levels)

    # Apply policy constraints
    if policy.strict_mode:
        # In strict mode, partial is downgraded to none
        if alto_export == ReadinessLevel.PARTIAL:
            alto_export = ReadinessLevel.NONE
        if page_export == ReadinessLevel.PARTIAL:
            page_export = ReadinessLevel.NONE

    # Viewer is more lenient — it can render degraded content
    if alto_export != ReadinessLevel.NONE or page_export != ReadinessLevel.NONE:
        viewer_render = ReadinessLevel.FULL
    elif any(len(p.text_regions) > 0 for p in doc.pages):
        viewer_render = ReadinessLevel.DEGRADED
    else:
        viewer_render = ReadinessLevel.NONE

    return ExportEligibility(
        alto_export=alto_export,
        page_export=page_export,
        viewer_render=viewer_render,
    )


def _aggregate_levels(levels: list[ReadinessLevel]) -> ReadinessLevel:
    """Aggregate per-page readiness into a single document-level readiness."""
    if not levels:
        return ReadinessLevel.NONE

    if all(l == ReadinessLevel.FULL for l in levels):
        return ReadinessLevel.FULL
    if all(l == ReadinessLevel.NONE for l in levels):
        return ReadinessLevel.NONE
    if any(l in (ReadinessLevel.FULL, ReadinessLevel.PARTIAL) for l in levels):
        return ReadinessLevel.PARTIAL
    return ReadinessLevel.DEGRADED
