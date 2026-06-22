"""Tests for MCP response models."""

from __future__ import annotations

from townshipamerica_mcp.models import (
    BatchRecord,
    BatchResult,
    SearchResult,
    ValidationResult,
)


def test_search_result_from_dict():
    data = {
        "legal_location": "NW 25 24N 1E 6TH MERIDIAN",
        "lat": 39.739,
        "lng": -104.987,
        "state": "Colorado",
        "county": "Adams",
        "geometry": {"type": "Polygon", "coordinates": []},
    }
    result = SearchResult.from_dict(data)
    assert result.legal_location == data["legal_location"]
    assert result.lat == 39.739
    assert result.lng == -104.987
    assert result.geometry == data["geometry"]


def test_validation_result_from_dict():
    result = ValidationResult.from_dict(
        {"valid": True, "normalized": "NW 25 24N 1E 6TH MERIDIAN"}
    )
    assert result.valid is True
    assert result.normalized == "NW 25 24N 1E 6TH MERIDIAN"
    assert result.suggestion is None


def test_batch_record_from_dict_with_result():
    record = BatchRecord.from_dict(
        {
            "input": "NW 25 24N 1E 6TH MERIDIAN",
            "result": {
                "legal_location": "NW 25 24N 1E 6TH MERIDIAN",
                "lat": 39.7,
                "lng": -105.0,
                "state": "Colorado",
                "county": "Adams",
            },
        }
    )
    assert record.input == "NW 25 24N 1E 6TH MERIDIAN"
    assert record.result is not None
    assert record.result.lat == 39.7
    assert record.error is None


def test_batch_record_from_dict_with_error():
    record = BatchRecord.from_dict(
        {"input": "invalid", "result": None, "error": "Not found"}
    )
    assert record.result is None
    assert record.error == "Not found"


def test_batch_result_from_dict():
    result = BatchResult.from_dict(
        {
            "total": 2,
            "converted": 1,
            "failed": 1,
            "records": [
                {
                    "input": "a",
                    "result": {
                        "legal_location": "a",
                        "lat": 1.0,
                        "lng": 2.0,
                        "state": "CO",
                        "county": "X",
                    },
                },
                {"input": "b", "result": None, "error": "Not found"},
            ],
        }
    )
    assert result.total == 2
    assert result.converted == 1
    assert result.failed == 1
    assert len(result.records) == 2
