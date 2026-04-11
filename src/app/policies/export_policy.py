"""Export policy — decides whether a specific export should proceed.

Uses the document policy and export eligibility to make a final go/no-go
decision for each export format.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.app.domain.models.readiness import ExportEligibility
from src.app.domain.models.status import ReadinessLevel
from src.app.policies.document_policy import DocumentPolicy


@dataclass(frozen=True)
class ExportDecision:
    """Result of an export policy check."""

    allowed: bool
    level: ReadinessLevel
    reason: str


def check_alto_export(
    eligibility: ExportEligibility,
    policy: DocumentPolicy | None = None,
) -> ExportDecision:
    """Check if ALTO export should proceed."""
    if policy is None:
        policy = DocumentPolicy()

    level = eligibility.alto_export

    if level == ReadinessLevel.NONE:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="ALTO export not possible: missing required data (word text/geometry or line geometry)",
        )

    if level == ReadinessLevel.PARTIAL and not policy.allow_partial_alto:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="ALTO export is partial but policy does not allow partial exports",
        )

    if level == ReadinessLevel.DEGRADED:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="ALTO export is degraded: too much data missing",
        )

    return ExportDecision(allowed=True, level=level, reason="OK")


def check_page_export(
    eligibility: ExportEligibility,
    policy: DocumentPolicy | None = None,
) -> ExportDecision:
    """Check if PAGE XML export should proceed."""
    if policy is None:
        policy = DocumentPolicy()

    level = eligibility.page_export

    if level == ReadinessLevel.NONE:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="PAGE export not possible: missing required data",
        )

    if level == ReadinessLevel.PARTIAL and not policy.allow_partial_page:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="PAGE export is partial but policy does not allow partial exports",
        )

    if level == ReadinessLevel.DEGRADED:
        return ExportDecision(
            allowed=False,
            level=level,
            reason="PAGE export is degraded: too much data missing",
        )

    return ExportDecision(allowed=True, level=level, reason="OK")
