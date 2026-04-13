"""PAGE XML serializer — deterministic conversion from CanonicalDocument to PAGE XML.

This serializer follows the same rules as the ALTO serializer (see AGENTS.md §6):
  - No model calls, no segmentation reconstruction, no text correction
  - No coordinate invention, no export eligibility decisions
  - Pure deterministic mapping from validated CanonicalDocument

PAGE XML mapping:
  Page         → <Page>
  TextRegion   → <TextRegion>
  TextLine     → <TextLine>
  Word         → <Word>

Coordinate mapping:
  Uses <Coords points="x1,y1 x2,y2 x3,y3 x4,y4"/> — polygon if available,
  otherwise constructs a rectangle from the bbox.

Reading order:
  <ReadingOrder> / <OrderedGroup> / <RegionRefIndexed>

Text content:
  <TextEquiv><Unicode>text</Unicode></TextEquiv> at each level.

Namespace: http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lxml import etree

from src.app.domain.models.status import BlockRole
from src.app.geometry.polygon import bbox_to_polygon
from src.app.geometry.quantization import RoundingStrategy, quantize_value

if TYPE_CHECKING:
    from src.app.domain.models import (
        CanonicalDocument,
        Page,
        TextLine,
        TextRegion,
        Word,
    )

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15 "
    "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd"
)

NSMAP = {
    None: PAGE_NS,
    "xsi": XSI_NS,
}

# Mapping from canonical BlockRole to PAGE region type
_ROLE_TO_TYPE: dict[BlockRole | None, str] = {
    BlockRole.BODY: "paragraph",
    BlockRole.HEADING: "heading",
    BlockRole.FOOTNOTE: "footnote",
    BlockRole.CAPTION: "caption",
    BlockRole.MARGIN: "marginalia",
    BlockRole.PAGE_NUMBER: "page-number",
    BlockRole.HEADER: "header",
    BlockRole.FOOTER: "footer",
    BlockRole.OTHER: "other",
    None: "paragraph",
}


def serialize_page_xml(
    doc: CanonicalDocument,
    *,
    rounding: RoundingStrategy = RoundingStrategy.ROUND,
    pretty_print: bool = True,
    encoding: str = "UTF-8",
) -> bytes:
    """Serialize a CanonicalDocument to PAGE XML bytes.

    Args:
        doc: The validated canonical document.
        rounding: Strategy for coordinate rounding.
        pretty_print: Whether to indent output.
        encoding: Output encoding.

    Returns:
        PAGE XML as bytes.
    """
    root = _build_page_tree(doc, rounding)
    return etree.tostring(
        root,
        pretty_print=pretty_print,
        xml_declaration=True,
        encoding=encoding,
    )


def serialize_page_xml_to_string(
    doc: CanonicalDocument,
    *,
    rounding: RoundingStrategy = RoundingStrategy.ROUND,
) -> str:
    """Serialize to a UTF-8 string (convenience for tests)."""
    return serialize_page_xml(doc, rounding=rounding).decode("utf-8")


# -- Tree construction --------------------------------------------------------


def _build_page_tree(
    doc: CanonicalDocument, rounding: RoundingStrategy
) -> etree._Element:
    root = etree.Element(f"{{{PAGE_NS}}}PcGts", nsmap=NSMAP)
    root.set(f"{{{XSI_NS}}}schemaLocation", SCHEMA_LOCATION)
    root.set("pcGtsId", doc.document_id)

    # <Metadata>
    metadata = etree.SubElement(root, f"{{{PAGE_NS}}}Metadata")
    creator = etree.SubElement(metadata, f"{{{PAGE_NS}}}Creator")
    creator.text = "XmLLM"
    created = etree.SubElement(metadata, f"{{{PAGE_NS}}}Created")
    created.text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    last_change = etree.SubElement(metadata, f"{{{PAGE_NS}}}LastChange")
    last_change.text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")

    # One <Page> per canonical page (PAGE XML is per-page, but we handle multi-page)
    for page in doc.pages:
        _add_page(root, page, rounding)

    return root


def _add_page(
    parent: etree._Element, page: Page, rounding: RoundingStrategy
) -> None:
    page_el = etree.SubElement(parent, f"{{{PAGE_NS}}}Page")
    page_el.set("imageFilename", page.metadata.get("image_ref", "") if page.metadata else "")
    page_el.set("imageWidth", str(int(page.width)))
    page_el.set("imageHeight", str(int(page.height)))

    # <ReadingOrder>
    if page.reading_order:
        _add_reading_order(page_el, page)

    # <TextRegion> elements
    for region in page.text_regions:
        _add_text_region(page_el, region, rounding)

    # Non-text regions are not in PAGE TextRegion — could add as ImageRegion etc.
    # For now we skip them (Sprint scope).


def _add_reading_order(page_el: etree._Element, page: Page) -> None:
    ro = etree.SubElement(page_el, f"{{{PAGE_NS}}}ReadingOrder")
    og = etree.SubElement(ro, f"{{{PAGE_NS}}}OrderedGroup")
    og.set("id", f"ro_{page.id}")
    for idx, region_id in enumerate(page.reading_order):
        ref = etree.SubElement(og, f"{{{PAGE_NS}}}RegionRefIndexed")
        ref.set("index", str(idx))
        ref.set("regionRef", region_id)


def _add_text_region(
    parent: etree._Element, region: TextRegion, rounding: RoundingStrategy
) -> None:
    tr = etree.SubElement(parent, f"{{{PAGE_NS}}}TextRegion")
    tr.set("id", region.id)
    tr.set("type", _ROLE_TO_TYPE.get(region.role, "paragraph"))

    # <Coords>
    _add_coords(tr, region.geometry.bbox, region.geometry.polygon, rounding)

    # <TextLine> elements
    for line in region.lines:
        _add_text_line(tr, line, rounding)

    # Region-level <TextEquiv>
    _add_text_equiv(tr, region.text)


def _add_text_line(
    parent: etree._Element, line: TextLine, rounding: RoundingStrategy
) -> None:
    tl = etree.SubElement(parent, f"{{{PAGE_NS}}}TextLine")
    tl.set("id", line.id)

    # <Coords>
    _add_coords(tl, line.geometry.bbox, line.geometry.polygon, rounding)

    # <Word> elements
    for word in line.words:
        _add_word(tl, word, rounding)

    # Line-level <TextEquiv>
    _add_text_equiv(tl, line.text)


def _add_word(
    parent: etree._Element, word: Word, rounding: RoundingStrategy
) -> None:
    w = etree.SubElement(parent, f"{{{PAGE_NS}}}Word")
    w.set("id", word.id)

    if word.confidence is not None:
        w.set("conf", f"{word.confidence:.2f}")

    # <Coords>
    _add_coords(w, word.geometry.bbox, word.geometry.polygon, rounding)

    # <TextEquiv>
    _add_text_equiv(w, word.text)


# -- Helpers ------------------------------------------------------------------


def _add_coords(
    parent: etree._Element,
    bbox: tuple[float, float, float, float],
    polygon: list[tuple[float, float]] | None,
    rounding: RoundingStrategy,
) -> None:
    """Add a <Coords> element with points attribute.

    Uses the polygon if available, otherwise constructs a rectangle from bbox.
    """
    coords = etree.SubElement(parent, f"{{{PAGE_NS}}}Coords")

    points = polygon if polygon and len(polygon) >= 3 else bbox_to_polygon(bbox)

    points_str = " ".join(
        f"{quantize_value(x, rounding)},{quantize_value(y, rounding)}"
        for x, y in points
    )
    coords.set("points", points_str)


def _add_text_equiv(parent: etree._Element, text: str) -> None:
    """Add <TextEquiv><Unicode>text</Unicode></TextEquiv>."""
    te = etree.SubElement(parent, f"{{{PAGE_NS}}}TextEquiv")
    unicode_el = etree.SubElement(te, f"{{{PAGE_NS}}}Unicode")
    unicode_el.text = text
