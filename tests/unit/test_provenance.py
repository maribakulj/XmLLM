"""Tests for the Provenance model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.app.domain.models import EvidenceType, Provenance


class TestProvenance:
    def test_valid_native(self) -> None:
        p = Provenance(
            provider="paddleocr-vl",
            adapter="adapter.paddle.v1",
            source_ref="$.pages[0].blocks[0]",
            evidence_type=EvidenceType.PROVIDER_NATIVE,
        )
        assert p.derived_from == []

    def test_valid_derived(self) -> None:
        p = Provenance(
            provider="enricher.polygon_to_bbox",
            adapter="enricher.v1",
            source_ref="tl1",
            evidence_type=EvidenceType.DERIVED,
            derived_from=["tl1"],
        )
        assert p.derived_from == ["tl1"]

    def test_native_with_derived_from_rejected(self) -> None:
        with pytest.raises(ValidationError, match="provider_native.*empty derived_from"):
            Provenance(
                provider="paddle",
                adapter="adapter.v1",
                source_ref="$.x",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
                derived_from=["some_id"],
            )

    def test_empty_provider_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Provenance(
                provider="",
                adapter="adapter.v1",
                source_ref="$.x",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

    def test_empty_adapter_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Provenance(
                provider="paddle",
                adapter="",
                source_ref="$.x",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

    def test_empty_source_ref_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Provenance(
                provider="paddle",
                adapter="adapter.v1",
                source_ref="",
                evidence_type=EvidenceType.PROVIDER_NATIVE,
            )

    def test_repaired_evidence_type(self) -> None:
        p = Provenance(
            provider="bbox_repair",
            adapter="enricher.v1",
            source_ref="w1",
            evidence_type=EvidenceType.REPAIRED,
            derived_from=["w1"],
        )
        assert p.evidence_type == EvidenceType.REPAIRED

    def test_manual_evidence_type(self) -> None:
        p = Provenance(
            provider="manual",
            adapter="manual.v1",
            source_ref="user_correction",
            evidence_type=EvidenceType.MANUAL,
        )
        assert p.evidence_type == EvidenceType.MANUAL

    def test_frozen(self) -> None:
        p = Provenance(
            provider="paddle",
            adapter="v1",
            source_ref="$.x",
            evidence_type=EvidenceType.PROVIDER_NATIVE,
        )
        with pytest.raises(ValidationError):
            p.provider = "other"  # type: ignore[misc]

    def test_json_roundtrip(self) -> None:
        p = Provenance(
            provider="paddleocr-vl",
            adapter="adapter.paddle.v1",
            source_ref="$.pages[0]",
            evidence_type=EvidenceType.PROVIDER_NATIVE,
        )
        data = p.model_dump()
        p2 = Provenance.model_validate(data)
        assert p == p2
