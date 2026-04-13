"""Tests for the PAGE XML serializer."""

from __future__ import annotations

from lxml import etree
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
from src.app.domain.models.status import BlockRole, InputType
from src.app.serializers.page_xml import PAGE_NS, serialize_page_xml, serialize_page_xml_to_string


def _prov(ref: str = "$.test") -> Provenance:
    return Provenance(
        provider="test", adapter="test.v1", source_ref=ref,
        evidence_type=EvidenceType.PROVIDER_NATIVE,
    )


def _geo(x: float = 100, y: float = 200, w: float = 300, h: float = 50) -> Geometry:
    return Geometry(bbox=(x, y, w, h), status=GeometryStatus.EXACT)


def _geo_with_polygon() -> Geometry:
    return Geometry(
        bbox=(100, 200, 300, 50),
        polygon=[(98, 205), (402, 195), (404, 245), (100, 255)],
        status=GeometryStatus.EXACT,
    )


def _simple_doc() -> CanonicalDocument:
    """One-page doc with one region, one line, two words."""
    return CanonicalDocument(
        document_id="doc_page_test",
        source=Source(input_type=InputType.IMAGE, filename="test.png"),
        pages=[
            Page(
                id="p1", page_index=0, width=2480, height=3508,
                alto_readiness=AltoReadiness(level=ReadinessLevel.FULL),
                page_readiness=PageXmlReadiness(level=ReadinessLevel.FULL),
                reading_order=["tb1"],
                text_regions=[
                    TextRegion(
                        id="tb1", role=BlockRole.BODY,
                        geometry=_geo(100, 200, 1200, 900),
                        lang="fra", provenance=_prov(),
                        lines=[
                            TextLine(
                                id="tl1",
                                geometry=_geo(110, 220, 1100, 42),
                                lang="fra", provenance=_prov(),
                                words=[
                                    Word(id="w1", text="Bonjour",
                                         geometry=_geo(110, 220, 90, 40),
                                         lang="fra", confidence=0.96,
                                         provenance=_prov()),
                                    Word(id="w2", text="monde",
                                         geometry=_geo(220, 220, 80, 40),
                                         lang="fra", confidence=0.94,
                                         provenance=_prov()),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


class TestPageXmlSerialization:
    def test_produces_valid_xml(self) -> None:
        doc = _simple_doc()
        xml_bytes = serialize_page_xml(doc)
        root = etree.fromstring(xml_bytes)
        assert root.tag == f"{{{PAGE_NS}}}PcGts"

    def test_has_metadata(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        meta = root.find(f"{{{PAGE_NS}}}Metadata")
        assert meta is not None
        creator = meta.find(f"{{{PAGE_NS}}}Creator")
        assert creator is not None
        assert creator.text == "XmLLM"

    def test_pcgts_id(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        assert root.get("pcGtsId") == "doc_page_test"

    def test_page_dimensions(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        page = root.find(f"{{{PAGE_NS}}}Page")
        assert page is not None
        assert page.get("imageWidth") == "2480"
        assert page.get("imageHeight") == "3508"

    def test_reading_order(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        ro = root.find(f".//{{{PAGE_NS}}}ReadingOrder")
        assert ro is not None
        og = ro.find(f"{{{PAGE_NS}}}OrderedGroup")
        assert og is not None
        refs = og.findall(f"{{{PAGE_NS}}}RegionRefIndexed")
        assert len(refs) == 1
        assert refs[0].get("index") == "0"
        assert refs[0].get("regionRef") == "tb1"

    def test_text_region_exists(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        tr = root.find(f".//{{{PAGE_NS}}}TextRegion")
        assert tr is not None
        assert tr.get("id") == "tb1"
        assert tr.get("type") == "paragraph"

    def test_text_region_coords(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        tr = root.find(f".//{{{PAGE_NS}}}TextRegion")
        coords = tr.find(f"{{{PAGE_NS}}}Coords")
        assert coords is not None
        points = coords.get("points")
        assert points is not None
        # bbox (100,200,1200,900) → rectangle 4 points
        parts = points.split()
        assert len(parts) == 4
        assert parts[0] == "100,200"  # top-left

    def test_text_line_exists(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        tl = root.find(f".//{{{PAGE_NS}}}TextLine")
        assert tl is not None
        assert tl.get("id") == "tl1"

    def test_words_exist(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        words = root.findall(f".//{{{PAGE_NS}}}Word")
        assert len(words) == 2

    def test_word_text_equiv(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        words = root.findall(f".//{{{PAGE_NS}}}Word")
        te = words[0].find(f"{{{PAGE_NS}}}TextEquiv")
        assert te is not None
        unicode_el = te.find(f"{{{PAGE_NS}}}Unicode")
        assert unicode_el is not None
        assert unicode_el.text == "Bonjour"

    def test_word_confidence(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        words = root.findall(f".//{{{PAGE_NS}}}Word")
        assert words[0].get("conf") == "0.96"

    def test_line_text_equiv(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        tl = root.find(f".//{{{PAGE_NS}}}TextLine")
        te = tl.find(f"{{{PAGE_NS}}}TextEquiv")
        unicode_el = te.find(f"{{{PAGE_NS}}}Unicode")
        assert unicode_el.text == "Bonjour monde"

    def test_region_text_equiv(self) -> None:
        doc = _simple_doc()
        root = etree.fromstring(serialize_page_xml(doc))
        tr = root.find(f".//{{{PAGE_NS}}}TextRegion")
        # Region TextEquiv is after lines
        te_all = tr.findall(f"{{{PAGE_NS}}}TextEquiv")
        assert len(te_all) == 1
        unicode_el = te_all[0].find(f"{{{PAGE_NS}}}Unicode")
        assert unicode_el.text == "Bonjour monde"

    def test_string_output(self) -> None:
        doc = _simple_doc()
        xml_str = serialize_page_xml_to_string(doc)
        assert "<?xml version=" in xml_str
        assert "Bonjour" in xml_str
        assert "PcGts" in xml_str


class TestPageXmlPolygon:
    def test_uses_polygon_when_available(self) -> None:
        doc = CanonicalDocument(
            document_id="doc_poly",
            source=Source(input_type=InputType.IMAGE),
            pages=[Page(
                id="p1", page_index=0, width=2480, height=3508,
                text_regions=[TextRegion(
                    id="tb1", geometry=_geo_with_polygon(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo_with_polygon(), provenance=_prov(),
                        words=[Word(
                            id="w1", text="test",
                            geometry=_geo_with_polygon(), provenance=_prov(),
                        )],
                    )],
                )],
            )],
        )
        root = etree.fromstring(serialize_page_xml(doc))
        word = root.find(f".//{{{PAGE_NS}}}Word")
        coords = word.find(f"{{{PAGE_NS}}}Coords")
        points = coords.get("points")
        # Should use the polygon, not a rectangle from bbox
        parts = points.split()
        assert len(parts) == 4
        assert parts[0] == "98,205"  # first polygon point

    def test_falls_back_to_bbox_rectangle(self) -> None:
        doc = CanonicalDocument(
            document_id="doc_rect",
            source=Source(input_type=InputType.IMAGE),
            pages=[Page(
                id="p1", page_index=0, width=1000, height=1000,
                text_regions=[TextRegion(
                    id="tb1", geometry=_geo(10, 20, 100, 50), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(10, 20, 100, 50), provenance=_prov(),
                        words=[Word(
                            id="w1", text="test",
                            geometry=_geo(10, 20, 100, 50), provenance=_prov(),
                        )],
                    )],
                )],
            )],
        )
        root = etree.fromstring(serialize_page_xml(doc))
        word = root.find(f".//{{{PAGE_NS}}}Word")
        coords = word.find(f"{{{PAGE_NS}}}Coords")
        points = coords.get("points")
        parts = points.split()
        assert len(parts) == 4
        # bbox (10,20,100,50) → rectangle: top-left, top-right, bottom-right, bottom-left
        assert parts[0] == "10,20"
        assert parts[1] == "110,20"
        assert parts[2] == "110,70"
        assert parts[3] == "10,70"


class TestPageXmlRoles:
    def test_heading_role(self) -> None:
        doc = CanonicalDocument(
            document_id="doc_roles",
            source=Source(input_type=InputType.IMAGE),
            pages=[Page(
                id="p1", page_index=0, width=1000, height=1000,
                text_regions=[TextRegion(
                    id="tb1", role=BlockRole.HEADING,
                    geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(id="w1", text="Title", geometry=_geo(), provenance=_prov())],
                    )],
                )],
            )],
        )
        root = etree.fromstring(serialize_page_xml(doc))
        tr = root.find(f".//{{{PAGE_NS}}}TextRegion")
        assert tr.get("type") == "heading"

    def test_footnote_role(self) -> None:
        doc = CanonicalDocument(
            document_id="doc_fn",
            source=Source(input_type=InputType.IMAGE),
            pages=[Page(
                id="p1", page_index=0, width=1000, height=1000,
                text_regions=[TextRegion(
                    id="tb1", role=BlockRole.FOOTNOTE,
                    geometry=_geo(), provenance=_prov(),
                    lines=[TextLine(
                        id="tl1", geometry=_geo(), provenance=_prov(),
                        words=[Word(id="w1", text="Note", geometry=_geo(), provenance=_prov())],
                    )],
                )],
            )],
        )
        root = etree.fromstring(serialize_page_xml(doc))
        tr = root.find(f".//{{{PAGE_NS}}}TextRegion")
        assert tr.get("type") == "footnote"


class TestPageXmlMultipleRegions:
    def test_reading_order_multiple(self) -> None:
        doc = CanonicalDocument(
            document_id="doc_multi",
            source=Source(input_type=InputType.IMAGE),
            pages=[Page(
                id="p1", page_index=0, width=2000, height=3000,
                reading_order=["tb1", "tb2"],
                text_regions=[
                    TextRegion(
                        id="tb1", role=BlockRole.HEADING,
                        geometry=_geo(0, 0, 2000, 200), provenance=_prov(),
                        lines=[TextLine(
                            id="tl1", geometry=_geo(0, 0, 2000, 40),
                            provenance=_prov(),
                            words=[Word(
                                id="w1", text="Title",
                                geometry=_geo(0, 0, 200, 40),
                                provenance=_prov(),
                            )],
                        )],
                    ),
                    TextRegion(
                        id="tb2", role=BlockRole.BODY,
                        geometry=_geo(0, 250, 2000, 2500),
                        provenance=_prov(),
                        lines=[TextLine(
                            id="tl2", geometry=_geo(0, 250, 2000, 40),
                            provenance=_prov(),
                            words=[Word(
                                id="w2", text="Body",
                                geometry=_geo(0, 250, 200, 40),
                                provenance=_prov(),
                            )],
                        )],
                    ),
                ],
            )],
        )
        root = etree.fromstring(serialize_page_xml(doc))

        # Two text regions
        regions = root.findall(f".//{{{PAGE_NS}}}TextRegion")
        assert len(regions) == 2

        # Reading order with 2 refs
        refs = root.findall(f".//{{{PAGE_NS}}}RegionRefIndexed")
        assert len(refs) == 2
        assert refs[0].get("regionRef") == "tb1"
        assert refs[0].get("index") == "0"
        assert refs[1].get("regionRef") == "tb2"
        assert refs[1].get("index") == "1"
