"""Domain models — public API.

Import from here rather than from individual modules:

    from src.app.domain.models import CanonicalDocument, Word, Page, Geometry
"""

from src.app.domain.models.canonical_document import (
    Audit,
    CanonicalDocument,
    Hyphenation,
    NonTextRegion,
    Page,
    Source,
    TextLine,
    TextRegion,
    Word,
)
from src.app.domain.models.geometry import (
    Baseline,
    BBox,
    ClipRect,
    Geometry,
    GeometryContext,
    Point,
    PolygonPoints,
)
from src.app.domain.models.provenance import Provenance
from src.app.domain.models.raw_payload import RawProviderPayload
from src.app.domain.models.readiness import (
    AltoReadiness,
    DocumentReadiness,
    ExportEligibility,
    PageXmlReadiness,
)
from src.app.domain.models.status import (
    BlockRole,
    CoordinateOrigin,
    EvidenceType,
    GeometryStatus,
    InputType,
    MissingCapability,
    NonTextKind,
    OverlayLevel,
    ReadinessLevel,
    Unit,
)
from src.app.domain.models.viewer_projection import (
    InspectionData,
    OverlayItem,
    ViewerProjection,
)

__all__ = [
    # Enums
    "BlockRole",
    "CoordinateOrigin",
    "EvidenceType",
    "GeometryStatus",
    "InputType",
    "MissingCapability",
    "NonTextKind",
    "OverlayLevel",
    "ReadinessLevel",
    "Unit",
    # Geometry
    "BBox",
    "Baseline",
    "ClipRect",
    "Geometry",
    "GeometryContext",
    "Point",
    "PolygonPoints",
    # Provenance
    "Provenance",
    # Readiness
    "AltoReadiness",
    "DocumentReadiness",
    "ExportEligibility",
    "PageXmlReadiness",
    # Canonical document
    "Audit",
    "CanonicalDocument",
    "Hyphenation",
    "NonTextRegion",
    "Page",
    "Source",
    "TextLine",
    "TextRegion",
    "Word",
    # Raw payload
    "RawProviderPayload",
    # Viewer
    "InspectionData",
    "OverlayItem",
    "ViewerProjection",
]
