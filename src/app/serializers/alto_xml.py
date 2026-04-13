"""ALTO XML serializer — deterministic conversion from CanonicalDocument to ALTO v4.

This serializer is a pure output transformation.  It MUST NOT:
  - Call any model or provider
  - Reconstruct segmentation
  - Correct text
  - Invent coordinates
  - Make export eligibility decisions

It receives a validated CanonicalDocument and produces ALTO XML bytes.

ALTO mapping:
  Page         → <Page>
  TextRegion   → <TextBlock>
  TextLine     → <TextLine>
  Word         → <String>

Coordinate mapping:
  bbox[0] → HPOS
  bbox[1] → VPOS
  bbox[2] → WIDTH
  bbox[3] → HEIGHT
  text    → CONTENT
  confidence → WC
  hyphenation.part=1 → SUBS_TYPE="HypPart1"
  hyphenation.part=2 → SUBS_TYPE="HypPart2"
  hyphenation.full_form → SUBS_CONTENT
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.app.geometry.quantization import RoundingStrategy, quantize_bbox

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument, Page, TextLine, TextRegion, Word

ALTO_NS = "http://www.loc.gov/standards/alto/ns-v4#"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.loc.gov/standards/alto/ns-v4# "
    "http://www.loc.gov/standards/alto/v4/alto-4-2.xsd"
)

NSMAP = {
    None: ALTO_NS,
    "xsi": XSI_NS,
}


def serialize_alto(
    doc: CanonicalDocument,
    *,
    rounding: RoundingStrategy = RoundingStrategy.ROUND,
    pretty_print: bool = True,
    encoding: str = "UTF-8",
) -> bytes:
    """Serialize a CanonicalDocument to ALTO v4 XML bytes.

    Args:
        doc: The validated canonical document.
        rounding: Strategy for converting float coordinates to integers.
        pretty_print: Whether to indent the XML output.
        encoding: Output encoding.

    Returns:
        The ALTO XML as bytes.
    """
    root = _build_alto_tree(doc, rounding)
    return etree.tostring(
        root,
        pretty_print=pretty_print,
        xml_declaration=True,
        encoding=encoding,
    )


def serialize_alto_to_string(
    doc: CanonicalDocument,
    *,
    rounding: RoundingStrategy = RoundingStrategy.ROUND,
) -> str:
    """Serialize to a UTF-8 string (convenience for tests)."""
    return serialize_alto(doc, rounding=rounding).decode("utf-8")


# -- Tree construction --------------------------------------------------------


def _build_alto_tree(
    doc: CanonicalDocument, rounding: RoundingStrategy
) -> etree._Element:
    root = etree.Element(f"{{{ALTO_NS}}}alto", nsmap=NSMAP)
    root.set(f"{{{XSI_NS}}}schemaLocation", SCHEMA_LOCATION)

    # <Description>
    desc = etree.SubElement(root, f"{{{ALTO_NS}}}Description")
    _add_description(desc, doc)

    # <Layout>
    layout = etree.SubElement(root, f"{{{ALTO_NS}}}Layout")
    for page in doc.pages:
        _add_page(layout, page, rounding)

    return root


def _add_description(desc: etree._Element, doc: CanonicalDocument) -> None:
    """Add <Description> metadata."""
    measurement = etree.SubElement(desc, f"{{{ALTO_NS}}}MeasurementUnit")
    measurement.text = "pixel"

    src_info = etree.SubElement(desc, f"{{{ALTO_NS}}}sourceImageInformation")
    file_name = etree.SubElement(src_info, f"{{{ALTO_NS}}}fileName")
    file_name.text = doc.source.filename or doc.document_id

    # Processing info
    processing = etree.SubElement(desc, f"{{{ALTO_NS}}}Processing")
    processing.set("ID", "proc_1")
    sw = etree.SubElement(processing, f"{{{ALTO_NS}}}processingSoftware")
    sw_name = etree.SubElement(sw, f"{{{ALTO_NS}}}softwareName")
    sw_name.text = "XmLLM"
    sw_version = etree.SubElement(sw, f"{{{ALTO_NS}}}softwareVersion")
    sw_version.text = doc.schema_version


def _add_page(
    layout: etree._Element, page: Page, rounding: RoundingStrategy
) -> None:
    """Add a <Page> with its <PrintSpace> and blocks."""
    page_el = etree.SubElement(layout, f"{{{ALTO_NS}}}Page")
    page_el.set("ID", page.id)
    page_el.set("PHYSICAL_IMG_NR", str(page.page_index + 1))
    page_el.set("WIDTH", str(int(page.width)))
    page_el.set("HEIGHT", str(int(page.height)))

    # <PrintSpace> covers the entire page
    ps = etree.SubElement(page_el, f"{{{ALTO_NS}}}PrintSpace")
    ps.set("HPOS", "0")
    ps.set("VPOS", "0")
    ps.set("WIDTH", str(int(page.width)))
    ps.set("HEIGHT", str(int(page.height)))

    for region in page.text_regions:
        _add_text_block(ps, region, rounding)


def _add_text_block(
    parent: etree._Element, region: TextRegion, rounding: RoundingStrategy
) -> None:
    """Add a <TextBlock> with its lines."""
    tb = etree.SubElement(parent, f"{{{ALTO_NS}}}TextBlock")
    tb.set("ID", region.id)
    _set_bbox_attrs(tb, region.geometry.bbox, rounding)

    if region.lang:
        tb.set("LANG", region.lang)

    for line in region.lines:
        _add_text_line(tb, line, rounding)


def _add_text_line(
    parent: etree._Element, line: TextLine, rounding: RoundingStrategy
) -> None:
    """Add a <TextLine> with its strings."""
    tl = etree.SubElement(parent, f"{{{ALTO_NS}}}TextLine")
    tl.set("ID", line.id)
    _set_bbox_attrs(tl, line.geometry.bbox, rounding)

    for i, word in enumerate(line.words):
        if i > 0:
            _add_sp(tl)
        _add_string(tl, word, rounding)


def _add_string(
    parent: etree._Element, word: Word, rounding: RoundingStrategy
) -> None:
    """Add a <String> element for a word."""
    s = etree.SubElement(parent, f"{{{ALTO_NS}}}String")
    s.set("ID", word.id)
    _set_bbox_attrs(s, word.geometry.bbox, rounding)
    s.set("CONTENT", word.text)

    if word.confidence is not None:
        s.set("WC", f"{word.confidence:.2f}")

    if word.lang:
        s.set("LANG", word.lang)

    # Hyphenation
    if word.hyphenation and word.hyphenation.is_hyphenated:
        if word.hyphenation.part == 1:
            s.set("SUBS_TYPE", "HypPart1")
        elif word.hyphenation.part == 2:
            s.set("SUBS_TYPE", "HypPart2")
        if word.hyphenation.full_form:
            s.set("SUBS_CONTENT", word.hyphenation.full_form)


def _add_sp(parent: etree._Element) -> None:
    """Add a <SP> (space) element between words."""
    etree.SubElement(parent, f"{{{ALTO_NS}}}SP")


# -- Helpers ------------------------------------------------------------------


def _set_bbox_attrs(
    el: etree._Element,
    bbox: tuple[float, float, float, float],
    rounding: RoundingStrategy,
) -> None:
    """Set HPOS, VPOS, WIDTH, HEIGHT attributes from a canonical bbox."""
    hpos, vpos, width, height = quantize_bbox(bbox, rounding)
    el.set("HPOS", str(hpos))
    el.set("VPOS", str(vpos))
    el.set("WIDTH", str(width))
    el.set("HEIGHT", str(height))
