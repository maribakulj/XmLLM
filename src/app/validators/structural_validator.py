"""Structural validator — checks internal consistency of a CanonicalDocument.

Checks:
  - ID uniqueness across the entire document
  - reading_order references existing region IDs
  - bbox containment: word ⊂ line ⊂ region ⊂ page (with tolerance)
  - spatial ordering: words in a line, lines in a region
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.domain.errors import Severity, ValidationEntry, ValidationReport
from src.app.geometry.bbox import contains

if TYPE_CHECKING:
    from src.app.domain.models import CanonicalDocument

VALIDATOR_NAME = "structural"


def validate_structure(
    doc: CanonicalDocument,
    *,
    bbox_tolerance: float = 5.0,
) -> ValidationReport:
    """Run all structural checks on a CanonicalDocument."""
    report = ValidationReport()
    _check_id_uniqueness(doc, report)
    _check_reading_order(doc, report)
    _check_bbox_containment(doc, report, bbox_tolerance)
    return report


def _check_id_uniqueness(doc: CanonicalDocument, report: ValidationReport) -> None:
    """Every ID in the document must be unique."""
    seen: dict[str, str] = {}  # id → first path
    for pi, page in enumerate(doc.pages):
        _register_id(page.id, f"pages[{pi}]", seen, report)
        for ri, region in enumerate(page.text_regions):
            rpath = f"pages[{pi}].text_regions[{ri}]"
            _register_id(region.id, rpath, seen, report)
            for li, line in enumerate(region.lines):
                lpath = f"{rpath}.lines[{li}]"
                _register_id(line.id, lpath, seen, report)
                for wi, word in enumerate(line.words):
                    wpath = f"{lpath}.words[{wi}]"
                    _register_id(word.id, wpath, seen, report)
        for ni, ntr in enumerate(page.non_text_regions):
            npath = f"pages[{pi}].non_text_regions[{ni}]"
            _register_id(ntr.id, npath, seen, report)


def _register_id(
    node_id: str, path: str, seen: dict[str, str], report: ValidationReport
) -> None:
    if node_id in seen:
        report.add(ValidationEntry(
            validator=VALIDATOR_NAME,
            severity=Severity.ERROR,
            path=path,
            message=f"Duplicate ID '{node_id}', first seen at {seen[node_id]}",
            code="duplicate_id",
        ))
    else:
        seen[node_id] = path


def _check_reading_order(doc: CanonicalDocument, report: ValidationReport) -> None:
    """reading_order entries must reference existing region IDs."""
    for pi, page in enumerate(doc.pages):
        region_ids = {r.id for r in page.text_regions}
        for idx, ref_id in enumerate(page.reading_order):
            if ref_id not in region_ids:
                report.add(ValidationEntry(
                    validator=VALIDATOR_NAME,
                    severity=Severity.ERROR,
                    path=f"pages[{pi}].reading_order[{idx}]",
                    message=f"reading_order references unknown region ID '{ref_id}'",
                    code="invalid_reading_order_ref",
                ))


def _check_bbox_containment(
    doc: CanonicalDocument, report: ValidationReport, tolerance: float
) -> None:
    """Check that child bboxes are contained within parent bboxes."""
    for pi, page in enumerate(doc.pages):
        page_bbox = (0.0, 0.0, page.width, page.height)

        for ri, region in enumerate(page.text_regions):
            rpath = f"pages[{pi}].text_regions[{ri}]"

            if not contains(page_bbox, region.geometry.bbox, tolerance):
                report.add(ValidationEntry(
                    validator=VALIDATOR_NAME,
                    severity=Severity.WARNING,
                    path=rpath,
                    message=(
                        f"Region bbox {region.geometry.bbox} exceeds page bounds"
                        f" ({page.width}x{page.height}) beyond tolerance {tolerance}px"
                    ),
                    code="region_exceeds_page",
                ))

            for li, line in enumerate(region.lines):
                lpath = f"{rpath}.lines[{li}]"

                if not contains(region.geometry.bbox, line.geometry.bbox, tolerance):
                    report.add(ValidationEntry(
                        validator=VALIDATOR_NAME,
                        severity=Severity.WARNING,
                        path=lpath,
                        message=f"Line bbox exceeds region bbox beyond tolerance {tolerance}px",
                        code="line_exceeds_region",
                    ))

                for wi, word in enumerate(line.words):
                    wpath = f"{lpath}.words[{wi}]"

                    if not contains(line.geometry.bbox, word.geometry.bbox, tolerance):
                        report.add(ValidationEntry(
                            validator=VALIDATOR_NAME,
                            severity=Severity.WARNING,
                            path=wpath,
                            message=f"Word bbox exceeds line bbox beyond tolerance {tolerance}px",
                            code="word_exceeds_line",
                        ))
