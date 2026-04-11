"""Tests for the readiness validator."""

from __future__ import annotations

from src.app.domain.models import (
    AltoReadiness,
    CanonicalDocument,
    EvidenceType,
    Geometry,
    GeometryStatus,
    Page,
    PageXmlReadiness,
    Provenance,
    ReadinessLevel,
    Source,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.status import InputType, MissingCapability
from src.app.validators.readiness_validator import (
    compute_document_readiness,
    compute_page_alto_readiness,
    compute_page_pagexml_readiness,
)


def _prov() -> Provenance:
    return Provenance(
        provider="test", adapter="v1", source_ref="$",
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


def _geo(status: GeometryStatus = GeometryStatus.EXACT) -> Geometry:
    return Geometry(bbox=(10, 10, 100, 30), status=status)


def _complete_page() -> Page:
    """A fully complete page with all data."""
    return Page(
        id="p1", page_index=0, width=2480, height=3508,
        alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
        page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
        reading_order=["tb1"],
        text_regions=[
            TextRegion(
                id="tb1", geometry=_geo(), provenance=_prov(), lang="fra",
                lines=[
                    TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[
                            Word(id="w1", text="Hello", geometry=_geo(),
                                 provenance=_prov(), confidence=0.95),
                        ],
                    ),
                ],
            ),
        ],
    )


class TestAltoReadiness:
    def test_complete_page_is_full(self) -> None:
        page = _complete_page()
        r = compute_page_alto_readiness(page)
        assert r.level == ReadinessLevel.FULL
        assert r.missing == []

    def test_missing_word_geometry_is_none(self) -> None:
        page = Page(
            id="p1", page_index=0, width=2480, height=3508,
            text_regions=[
                TextRegion(
                    id="tb1", geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(
                            id="w1", text="Hello",
                            geometry=_geo(GeometryStatus.UNKNOWN),
                            provenance=_prov(),
                        )],
                    )],
                ),
            ],
        )
        r = compute_page_alto_readiness(page)
        assert r.level == ReadinessLevel.NONE
        assert MissingCapability.WORD_GEOMETRY in r.missing

    def test_missing_confidence_is_partial(self) -> None:
        page = Page(
            id="p1", page_index=0, width=2480, height=3508,
            reading_order=["tb1"],
            text_regions=[
                TextRegion(
                    id="tb1", geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(
                            id="w1", text="Hello", geometry=_geo(),
                            provenance=_prov(), confidence=None,
                        )],
                    )],
                ),
            ],
        )
        r = compute_page_alto_readiness(page)
        assert r.level == ReadinessLevel.PARTIAL
        assert MissingCapability.CONFIDENCE in r.missing

    def test_no_reading_order_is_partial(self) -> None:
        page = Page(
            id="p1", page_index=0, width=2480, height=3508,
            reading_order=[],
            text_regions=[
                TextRegion(
                    id="tb1", geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(
                            id="w1", text="Hello", geometry=_geo(),
                            provenance=_prov(), confidence=0.9,
                        )],
                    )],
                ),
            ],
        )
        r = compute_page_alto_readiness(page)
        assert r.level == ReadinessLevel.PARTIAL
        assert MissingCapability.READING_ORDER in r.missing

    def test_empty_page_is_none(self) -> None:
        page = Page(id="p1", page_index=0, width=2480, height=3508)
        r = compute_page_alto_readiness(page)
        assert r.level == ReadinessLevel.NONE


class TestPageXmlReadiness:
    def test_complete_page_is_full(self) -> None:
        page = _complete_page()
        r = compute_page_pagexml_readiness(page)
        assert r.level == ReadinessLevel.FULL

    def test_no_regions_is_none(self) -> None:
        page = Page(id="p1", page_index=0, width=2480, height=3508)
        r = compute_page_pagexml_readiness(page)
        assert r.level == ReadinessLevel.NONE

    def test_regions_without_word_geo_still_ok(self) -> None:
        """PAGE XML is more lenient — word geometry is not critical."""
        page = Page(
            id="p1", page_index=0, width=2480, height=3508,
            reading_order=["tb1"],
            text_regions=[
                TextRegion(
                    id="tb1", geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(
                            id="w1", text="Hello",
                            geometry=_geo(GeometryStatus.UNKNOWN),
                            provenance=_prov(),
                        )],
                    )],
                ),
            ],
        )
        r = compute_page_pagexml_readiness(page)
        # PAGE doesn't require word geometry — should still be achievable
        assert r.level in (ReadinessLevel.FULL, ReadinessLevel.PARTIAL)


class TestDocumentReadiness:
    def test_single_full_page(self) -> None:
        doc = CanonicalDocument(
            document_id="test",
            source=Source(input_type=InputType.IMAGE),
            pages=[_complete_page()],
        )
        dr = compute_document_readiness(doc)
        assert dr.level == ReadinessLevel.FULL

    def test_mixed_pages(self) -> None:
        full_page = _complete_page()
        empty_page = Page(id="p2", page_index=1, width=2480, height=3508)
        doc = CanonicalDocument(
            document_id="test",
            source=Source(input_type=InputType.IMAGE),
            pages=[full_page, empty_page],
        )
        dr = compute_document_readiness(doc)
        assert dr.level == ReadinessLevel.DEGRADED
        assert len(dr.page_readiness) == 2
