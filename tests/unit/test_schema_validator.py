"""Tests for the schema validator."""

from __future__ import annotations

from src.app.validators.schema_validator import validate_schema


class TestSchemaValidator:
    def test_valid_document(self) -> None:
        data = {
            "schema_version": "1.0.0",
            "document_id": "doc1",
            "source": {"input_type": "image"},
            "pages": [{
                "id": "p1",
                "page_index": 0,
                "width": 2480,
                "height": 3508,
                "text_regions": [{
                    "id": "tb1",
                    "geometry": {"bbox": [100, 200, 300, 50], "status": "exact"},
                    "provenance": {
                        "provider": "test", "adapter": "v1",
                        "source_ref": "$", "evidence_type": "provider_native",
                        "derived_from": [],
                    },
                    "lines": [{
                        "id": "tl1",
                        "geometry": {"bbox": [100, 200, 300, 50], "status": "exact"},
                        "provenance": {
                            "provider": "test", "adapter": "v1",
                            "source_ref": "$", "evidence_type": "provider_native",
                            "derived_from": [],
                        },
                        "words": [{
                            "id": "w1",
                            "text": "Hello",
                            "geometry": {"bbox": [100, 200, 50, 30], "status": "exact"},
                            "provenance": {
                                "provider": "test", "adapter": "v1",
                                "source_ref": "$", "evidence_type": "provider_native",
                                "derived_from": [],
                            },
                        }],
                    }],
                }],
            }],
        }
        doc, report = validate_schema(data)
        assert doc is not None
        assert report.is_valid

    def test_missing_required_field(self) -> None:
        data = {
            "source": {"input_type": "image"},
            "pages": [],
        }
        doc, report = validate_schema(data)
        assert doc is None
        assert not report.is_valid
        assert report.error_count > 0

    def test_invalid_schema_version(self) -> None:
        data = {
            "schema_version": "bad",
            "document_id": "doc1",
            "source": {"input_type": "image"},
            "pages": [{"id": "p1", "page_index": 0, "width": 100, "height": 100}],
        }
        doc, report = validate_schema(data)
        assert doc is None
        assert not report.is_valid

    def test_empty_pages(self) -> None:
        data = {
            "document_id": "doc1",
            "source": {"input_type": "image"},
            "pages": [],
        }
        doc, report = validate_schema(data)
        assert doc is None
        assert report.error_count > 0

    def test_error_paths_populated(self) -> None:
        data = {
            "document_id": "",
            "source": {"input_type": "image"},
            "pages": [],
        }
        doc, report = validate_schema(data)
        assert doc is None
        for entry in report.errors:
            assert entry.path
            assert entry.message
            assert entry.validator == "schema"
