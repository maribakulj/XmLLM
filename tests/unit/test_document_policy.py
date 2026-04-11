"""Tests for document policy and validation report."""

from __future__ import annotations

from src.app.domain.errors import Severity, ValidationEntry, ValidationReport
from src.app.policies.document_policy import (
    DocumentPolicy,
    PolicyMode,
    permissive_policy,
    strict_policy,
)


class TestDocumentPolicy:
    def test_default_is_standard(self) -> None:
        p = DocumentPolicy()
        assert p.mode == PolicyMode.STANDARD
        assert not p.strict_mode

    def test_strict(self) -> None:
        p = strict_policy()
        assert p.strict_mode
        assert not p.allow_bbox_inference
        assert not p.allow_partial_alto

    def test_permissive(self) -> None:
        p = permissive_policy()
        assert p.mode == PolicyMode.PERMISSIVE
        assert p.allow_bbox_inference
        assert p.bbox_containment_tolerance == 10.0

    def test_never_allows_text_invention(self) -> None:
        for factory in [DocumentPolicy, strict_policy, permissive_policy]:
            p = factory()
            assert p.allow_text_invention is False

    def test_never_allows_bbox_invention(self) -> None:
        for factory in [DocumentPolicy, strict_policy, permissive_policy]:
            p = factory()
            assert p.allow_bbox_invention is False

    def test_frozen(self) -> None:
        import pytest
        from pydantic import ValidationError

        p = DocumentPolicy()
        with pytest.raises(ValidationError):
            p.mode = PolicyMode.STRICT  # type: ignore[misc]


class TestValidationReport:
    def test_empty_is_valid(self) -> None:
        r = ValidationReport()
        assert r.is_valid
        assert r.error_count == 0
        assert r.warning_count == 0

    def test_with_error(self) -> None:
        r = ValidationReport()
        r.add(ValidationEntry(
            validator="test", severity=Severity.ERROR,
            path="pages[0]", message="bad",
        ))
        assert not r.is_valid
        assert r.error_count == 1

    def test_warnings_dont_invalidate(self) -> None:
        r = ValidationReport()
        r.add(ValidationEntry(
            validator="test", severity=Severity.WARNING,
            path="pages[0]", message="meh",
        ))
        assert r.is_valid
        assert r.warning_count == 1

    def test_merge(self) -> None:
        r1 = ValidationReport()
        r1.add(ValidationEntry(
            validator="a", severity=Severity.ERROR,
            path="x", message="e1",
        ))
        r2 = ValidationReport()
        r2.add(ValidationEntry(
            validator="b", severity=Severity.WARNING,
            path="y", message="w1",
        ))
        r1.merge(r2)
        assert r1.error_count == 1
        assert r1.warning_count == 1
        assert len(r1.entries) == 2

    def test_errors_property(self) -> None:
        r = ValidationReport()
        r.add(ValidationEntry(validator="a", severity=Severity.ERROR, path="x", message="e"))
        r.add(ValidationEntry(validator="b", severity=Severity.WARNING, path="y", message="w"))
        r.add(ValidationEntry(validator="c", severity=Severity.INFO, path="z", message="i"))
        assert len(r.errors) == 1
        assert len(r.warnings) == 1
