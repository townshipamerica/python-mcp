"""Tests for MCP server helpers and tool handlers."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from townshipamerica.exceptions import RateLimitError
from townshipamerica.models import FeatureCollection

from townshipamerica_mcp.constants import API_KEY_ENV, LEGACY_API_KEY_ENV
from townshipamerica_mcp.server import (
    _get_api_key,
    _summarize_search,
    call_tool,
    list_tools,
)


class TestGetApiKey:
    def test_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv(API_KEY_ENV, raising=False)
        monkeypatch.delenv(LEGACY_API_KEY_ENV, raising=False)
        with pytest.raises(RuntimeError, match=API_KEY_ENV):
            _get_api_key()

    def test_returns_stripped_primary_key(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv(LEGACY_API_KEY_ENV, raising=False)
        monkeypatch.setenv(API_KEY_ENV, "  ta_test  ")
        assert _get_api_key() == "ta_test"

    def test_falls_back_to_legacy_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv(API_KEY_ENV, raising=False)
        monkeypatch.setenv(LEGACY_API_KEY_ENV, "ta_legacy")
        assert _get_api_key() == "ta_legacy"


class TestSummarizeSearch:
    def test_non_dict_payload(self):
        summary = _summarize_search("raw", "input")
        assert summary["input"] == "input"
        assert summary["raw"] == "raw"

    def test_empty_features(self):
        summary = _summarize_search({"features": []}, "NW 25")
        assert summary["found"] is False

    def test_extracts_properties_and_centroid(self):
        payload = {
            "features": [
                {
                    "properties": {
                        "legal_location": "NW 25 24N 1E 6TH MERIDIAN",
                        "state": "Colorado",
                        "county": "Adams",
                        "meridian": "6th Meridian",
                    },
                    "geometry": {"type": "Point", "coordinates": [-104.99, 39.74]},
                }
            ]
        }
        summary = _summarize_search(payload, "NW 25")
        assert summary["found"] is True
        assert summary["legal_location"] == "NW 25 24N 1E 6TH MERIDIAN"
        assert summary["centroid"] == [-104.99, 39.74]
        assert "geojson" in summary


@pytest.mark.asyncio
async def test_list_tools_returns_seven_tools():
    tools = await list_tools()
    names = {t.name for t in tools}
    assert names == {
        "plss_to_coordinates",
        "coordinates_to_plss",
        "plss_to_geojson",
        "validate_description",
        "batch_convert",
        "autocomplete",
        "land_report",
    }


def _mock_async_client(fc: FeatureCollection | None = None) -> MagicMock:
    if fc is None:
        fc = FeatureCollection(features=[])
    client = MagicMock()
    client.search = AsyncMock(return_value=fc)
    client.reverse = AsyncMock(return_value=fc)
    client.batch_search = AsyncMock(return_value=[fc])
    client.autocomplete = AsyncMock(return_value=fc)
    return client


@pytest.mark.asyncio
async def test_call_tool_unknown_tool():
    @asynccontextmanager
    async def fake_make():
        yield _mock_async_client()

    with patch("townshipamerica_mcp.server._make_client", side_effect=fake_make):
        result = await call_tool("nonexistent", {})
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_plss_to_coordinates(sample_feature_collection):
    @asynccontextmanager
    async def fake_make():
        yield _mock_async_client(sample_feature_collection)

    with patch("townshipamerica_mcp.server._make_client", side_effect=fake_make):
        result = await call_tool(
            "plss_to_coordinates", {"description": "NW 25 24N 1E 6TH MERIDIAN"}
        )
    payload = json.loads(result[0].text)
    assert payload["found"] is True
    assert payload["legal_location"] == "NW 25 24N 1E 6TH MERIDIAN"


@pytest.mark.asyncio
async def test_call_tool_validate_description_local_no_api():
    result = await call_tool(
        "validate_description", {"description": "NW 25 24N 1E 6TH MERIDIAN"}
    )
    payload = json.loads(result[0].text)
    assert payload["valid"] is True
    assert "normalized" in payload

    result = await call_tool("validate_description", {"description": "hello world"})
    payload = json.loads(result[0].text)
    assert payload["valid"] is False
    assert "suggestion" in payload


@pytest.mark.asyncio
async def test_call_tool_coordinates_accepts_lng_and_lon(sample_feature_collection):
    @asynccontextmanager
    async def fake_make():
        client = _mock_async_client(sample_feature_collection)
        yield client

    with patch("townshipamerica_mcp.server._make_client", side_effect=fake_make):
        for lon_key in ("lng", "lon"):
            result = await call_tool(
                "coordinates_to_plss", {"lat": 39.739, lon_key: -104.987}
            )
            payload = json.loads(result[0].text)
            assert payload["legal_location"] == "NW 25 24N 1E 6TH MERIDIAN"


@pytest.mark.asyncio
async def test_call_tool_land_report_stub():
    result = await call_tool(
        "land_report", {"description": "NW 25 24N 1E 6TH MERIDIAN"}
    )
    payload = json.loads(result[0].text)
    assert payload["status"] == "coming_soon"


@pytest.mark.asyncio
async def test_call_tool_quota_error():
    @asynccontextmanager
    async def fake_make():
        client = _mock_async_client()
        client.search = AsyncMock(side_effect=RateLimitError("429"))
        yield client

    with patch("townshipamerica_mcp.server._make_client", side_effect=fake_make):
        result = await call_tool(
            "plss_to_coordinates", {"description": "NW 25 24N 1E 6TH MERIDIAN"}
        )
    payload = json.loads(result[0].text)
    assert "quota exceeded" in payload["error"].lower()


@pytest.mark.asyncio
async def test_call_tool_batch_convert_requires_nonempty_array():
    @asynccontextmanager
    async def fake_make():
        yield _mock_async_client()

    with patch("townshipamerica_mcp.server._make_client", side_effect=fake_make):
        result = await call_tool("batch_convert", {"descriptions": []})
    payload = json.loads(result[0].text)
    assert "error" in payload
