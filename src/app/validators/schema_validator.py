"""Schema validator — validates a dict/JSON against the CanonicalDocument schema.

This wraps Pydantic validation as an explicit service, producing a
ValidationReport rather than raising exceptions.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.app.domain.errors import Severity, ValidationEntry, ValidationReport
from src.app.domain.models import CanonicalDocument

VALIDATOR_NAME = "schema"


def validate_schema(data: dict[str, Any]) -> tuple[CanonicalDocument | None, ValidationReport]:
    """Validate raw data against the CanonicalDocument schema.

    Returns:
        A tuple of (parsed document or None, validation report).
        If parsing succeeds, the document is returned with an empty report.
        If parsing fails, None is returned with errors in the report.
    """
    report = ValidationReport()
    try:
        doc = CanonicalDocument.model_validate(data)
        return doc, report
    except ValidationError as e:
        for error in e.errors():
            loc_parts = [str(p) for p in error["loc"]]
            path = ".".join(loc_parts) if loc_parts else "root"
            report.add(ValidationEntry(
                validator=VALIDATOR_NAME,
                severity=Severity.ERROR,
                path=path,
                message=error["msg"],
                code=error["type"],
            ))
        return None, report
