"""Data models for Township America MCP tool responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """Result from plss_to_coordinates or coordinates_to_plss."""

    legal_location: str
    lat: float
    lng: float
    state: str
    county: str
    geometry: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResult":
        return cls(
            legal_location=data["legal_location"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            state=data["state"],
            county=data["county"],
            geometry=data.get("geometry"),
        )


@dataclass
class ValidationResult:
    """Result from validate_description."""

    valid: bool
    normalized: str | None = None
    suggestion: str | None = None
    survey_system: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationResult":
        return cls(
            valid=bool(data["valid"]),
            normalized=data.get("normalized"),
            suggestion=data.get("suggestion"),
            survey_system=data.get("survey_system"),
        )


@dataclass
class BatchRecord:
    """Single record within a batch_convert response."""

    input: str
    result: SearchResult | None = None
    error: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchRecord":
        raw_result = data.get("result")
        return cls(
            input=data["input"],
            result=SearchResult.from_dict(raw_result) if raw_result else None,
            error=data.get("error"),
        )


@dataclass
class BatchResult:
    """Result from batch_convert."""

    total: int
    converted: int
    failed: int
    records: list[BatchRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchResult":
        return cls(
            total=int(data["total"]),
            converted=int(data["converted"]),
            failed=int(data["failed"]),
            records=[BatchRecord.from_dict(r) for r in data.get("records", [])],
        )


@dataclass
class LandReportStub:
    """Stub response from land_report (coming Q3 2025)."""

    status: str
    description: str
    message: str
    preview_fields: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LandReportStub":
        return cls(
            status=data["status"],
            description=data["description"],
            message=data["message"],
            preview_fields=data.get("preview_fields", []),
        )
