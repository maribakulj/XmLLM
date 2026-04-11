"""Tests for readiness and export eligibility models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.app.domain.models import (
    AltoReadiness,
    DocumentReadiness,
    ExportEligibility,
    MissingCapability,
    PageXmlReadiness,
    ReadinessLevel,
)


class TestAltoReadiness:
    def test_full_no_missing(self) -> None:
        r = AltoReadiness(level=ReadinessLevel.FULL)
        assert r.missing == []

    def test_partial_with_missing(self) -> None:
        r = AltoReadiness(
            level=ReadinessLevel.PARTIAL,
            missing=[MissingCapability.WORD_GEOMETRY, MissingCapability.CONFIDENCE],
        )
        assert len(r.missing) == 2

    def test_none_with_missing(self) -> None:
        r = AltoReadiness(
            level=ReadinessLevel.NONE,
            missing=[MissingCapability.PAGE_DIMENSIONS],
        )
        assert r.level == ReadinessLevel.NONE

    def test_full_with_missing_rejected(self) -> None:
        with pytest.raises(ValidationError, match="full.*missing"):
            AltoReadiness(
                level=ReadinessLevel.FULL,
                missing=[MissingCapability.WORD_GEOMETRY],
            )

    def test_none_without_missing_rejected(self) -> None:
        with pytest.raises(ValidationError, match="none.*no missing"):
            AltoReadiness(level=ReadinessLevel.NONE, missing=[])


class TestPageXmlReadiness:
    def test_full_no_missing(self) -> None:
        r = PageXmlReadiness(level=ReadinessLevel.FULL)
        assert r.missing == []

    def test_full_with_missing_rejected(self) -> None:
        with pytest.raises(ValidationError, match="full.*missing"):
            PageXmlReadiness(
                level=ReadinessLevel.FULL,
                missing=[MissingCapability.LINE_GEOMETRY],
            )

    def test_none_without_missing_rejected(self) -> None:
        with pytest.raises(ValidationError, match="none.*no missing"):
            PageXmlReadiness(level=ReadinessLevel.NONE, missing=[])


class TestExportEligibility:
    def test_defaults_to_none(self) -> None:
        e = ExportEligibility()
        assert e.alto_export == ReadinessLevel.NONE
        assert e.page_export == ReadinessLevel.NONE
        assert e.viewer_render == ReadinessLevel.NONE

    def test_independent_levels(self) -> None:
        e = ExportEligibility(
            alto_export=ReadinessLevel.FULL,
            page_export=ReadinessLevel.PARTIAL,
            viewer_render=ReadinessLevel.DEGRADED,
        )
        assert e.alto_export == ReadinessLevel.FULL
        assert e.page_export == ReadinessLevel.PARTIAL
        assert e.viewer_render == ReadinessLevel.DEGRADED


class TestDocumentReadiness:
    def test_defaults(self) -> None:
        dr = DocumentReadiness()
        assert dr.level == ReadinessLevel.NONE
        assert dr.page_readiness == []

    def test_with_pages(self) -> None:
        dr = DocumentReadiness(
            level=ReadinessLevel.PARTIAL,
            page_readiness=[ReadinessLevel.FULL, ReadinessLevel.PARTIAL],
        )
        assert len(dr.page_readiness) == 2
