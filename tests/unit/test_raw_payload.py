"""Tests for the RawProviderPayload model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.app.domain.models import RawProviderPayload


class TestRawProviderPayload:
    def test_valid_dict_payload(self) -> None:
        rp = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.paddle.v1",
            runtime_type="local",
            payload={"pages": [{"blocks": []}]},
        )
        assert rp.provider_id == "paddleocr"

    def test_valid_list_payload(self) -> None:
        rp = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.paddle.v1",
            runtime_type="local",
            payload=[[[100, 200], [300, 200], [300, 250], [100, 250]], ["text", 0.95]],
        )
        assert isinstance(rp.payload, list)

    def test_empty_provider_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawProviderPayload(
                provider_id="",
                adapter_id="v1",
                runtime_type="local",
                payload={},
            )

    def test_with_image_dimensions(self) -> None:
        rp = RawProviderPayload(
            provider_id="paddle",
            adapter_id="v1",
            runtime_type="local",
            payload={},
            image_width=2480,
            image_height=3508,
        )
        assert rp.image_width == 2480

    def test_zero_dimension_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawProviderPayload(
                provider_id="paddle",
                adapter_id="v1",
                runtime_type="local",
                payload={},
                image_width=0,
                image_height=100,
            )

    def test_with_metadata(self) -> None:
        rp = RawProviderPayload(
            provider_id="paddle",
            adapter_id="v1",
            runtime_type="local",
            payload={"data": "test"},
            metadata={"processing_time_ms": 1234},
        )
        assert rp.metadata["processing_time_ms"] == 1234

    def test_json_roundtrip(self) -> None:
        rp = RawProviderPayload(
            provider_id="paddle",
            adapter_id="v1",
            runtime_type="local",
            model_id="PP-OCRv4",
            payload={"blocks": [{"text": "hello"}]},
        )
        data = rp.model_dump(mode="json")
        rp2 = RawProviderPayload.model_validate(data)
        assert rp2.provider_id == rp.provider_id
        assert rp2.model_id == "PP-OCRv4"
