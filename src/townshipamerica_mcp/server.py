"""MCP server exposing Township America PLSS and Texas TXSS tools to AI agents."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from townshipamerica import AsyncTownshipAmerica
from townshipamerica.exceptions import RateLimitError, TownshipAmericaError
from townshipamerica.models import Polygon, MultiPolygon

from .client import _fc_to_search_result
from .constants import (
    API_KEY_ENV,
    API_KEY_HELP_URL,
    BASE_URL_ENV,
    DEFAULT_AUTOCOMPLETE_LIMIT,
    LEGACY_API_KEY_ENV,
    MAX_AUTOCOMPLETE_LIMIT,
    MAX_BATCH_SIZE,
    QUOTA_EXCEEDED_MESSAGE,
)
from .plss_validation import validate_plss_description

logger = logging.getLogger("townshipamerica_mcp")

server: Server = Server("townshipamerica")


def _get_api_key() -> str:
    key = (
        os.environ.get(API_KEY_ENV, "").strip()
        or os.environ.get(LEGACY_API_KEY_ENV, "").strip()
    )
    if not key:
        raise RuntimeError(
            f"Set {API_KEY_ENV} (preferred) or {LEGACY_API_KEY_ENV} to your Township America API key. "
            f"Generate a key at {API_KEY_HELP_URL}."
        )
    return key


def _make_client() -> AsyncTownshipAmerica:
    base_url = os.environ.get(BASE_URL_ENV)
    kwargs: dict[str, Any] = {"api_key": _get_api_key()}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncTownshipAmerica(**kwargs)


def _longitude(arguments: dict[str, Any]) -> float:
    if "lng" in arguments:
        return float(arguments["lng"])
    if "lon" in arguments:
        return float(arguments["lon"])
    raise KeyError("lng")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the tool catalog visible to AI agents."""
    return [
        Tool(
            name="plss_to_coordinates",
            description=(
                "Convert a PLSS (Public Land Survey System) or Texas TXSS legal land description to GPS coordinates. "
                "Supports US legal descriptions such as 'NW 25 24N 1E 6th Meridian', 'T4N R5E Sec 12 NE¼', "
                "'A-175 Reeves County', etc. Returns the tract centroid and bounding polygon. "
                "Covers 30 PLSS states, 37 principal meridians, and all 254 Texas counties."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Legal land description (PLSS or Texas TXSS).",
                    }
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="coordinates_to_plss",
            description=(
                "Find the legal land description for given GPS coordinates (PLSS or Texas TXSS). "
                "Returns section/township/range/meridian for PLSS locations or the Texas abstract/block/survey match for TXSS."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude in decimal degrees."},
                    "lng": {"type": "number", "description": "Longitude in decimal degrees."},
                },
                "required": ["lat", "lng"],
            },
        ),
        Tool(
            name="plss_to_geojson",
            description=(
                "Return the GeoJSON boundary polygon for a PLSS or Texas TXSS legal land description. "
                "Returns a FeatureCollection with the polygon or multipolygon footprint."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Legal land description (PLSS or Texas TXSS).",
                    }
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="validate_description",
            description=(
                "Validate and normalize a PLSS or Texas TXSS legal land description string. "
                "Returns whether the input matches known patterns, a normalized form, survey_system when valid, and suggestions if invalid. "
                "No API call is made — this runs locally."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Legal land description to validate.",
                    }
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="batch_convert",
            description=(
                "Convert multiple PLSS or Texas TXSS legal land descriptions to GPS coordinates in one request. "
                f"Accepts up to {MAX_BATCH_SIZE} descriptions per request. "
                "Returns total, converted, failed counts and per-input records."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"Array of legal land descriptions (max {MAX_BATCH_SIZE}).",
                        "maxItems": MAX_BATCH_SIZE,
                    }
                },
                "required": ["descriptions"],
            },
        ),
        Tool(
            name="autocomplete",
            description=(
                "Get autocomplete suggestions for a partial PLSS or Texas TXSS description (e.g. 'T2N R4' or 'A-175'). "
                f"Returns up to {MAX_AUTOCOMPLETE_LIMIT} candidate descriptions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Partial legal description (minimum 2 characters).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum suggestions (default {DEFAULT_AUTOCOMPLETE_LIMIT}, max {MAX_AUTOCOMPLETE_LIMIT}).",
                        "default": DEFAULT_AUTOCOMPLETE_LIMIT,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


def _ok(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, default=str, indent=2))]


def _err(message: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": message}, indent=2))]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "validate_description":
            description = arguments["description"]
            try:
                result = validate_plss_description(description)
                payload: dict[str, Any] = {
                    "valid": result.valid,
                    "input": description,
                }
                if result.normalized is not None:
                    payload["normalized"] = result.normalized
                if result.survey_system is not None:
                    payload["survey_system"] = result.survey_system
                if result.suggestion is not None:
                    payload["suggestion"] = result.suggestion
                return _ok(payload)
            except ValueError as exc:
                return _err(str(exc))

        async with _make_client() as client:
            if name == "plss_to_coordinates":
                description = arguments["description"]
                result = await client.search(description)
                payload = result.model_dump()
                return _ok(_summarize_search(payload, description))

            if name == "coordinates_to_plss":
                lat = float(arguments["lat"])
                lng = _longitude(arguments)
                if not (-90 <= lat <= 90):
                    return _err(f"lat must be between -90 and 90, got {lat}")
                if not (-180 <= lng <= 180):
                    return _err(f"lng must be between -180 and 180, got {lng}")
                result = await client.reverse(lng, lat)
                if not result.features:
                    return _err(
                        f"No legal land description found for coordinates [{lat}, {lng}]. "
                        "PLSS covers 30 US states and Texas uses TXSS — this location may be outside surveyed coverage."
                    )
                sr = _fc_to_search_result(result)
                return _ok(
                    {
                        "legal_location": sr.legal_location,
                        "lat": sr.lat,
                        "lng": sr.lng,
                        "state": sr.state,
                        "county": sr.county,
                        "geometry": sr.geometry,
                    }
                )

            if name == "plss_to_geojson":
                description = arguments["description"]
                result = await client.search(description)
                polygon_features = [
                    f.model_dump()
                    for f in result.features
                    if isinstance(f.geometry, (Polygon, MultiPolygon))
                ]
                if not polygon_features:
                    return _err(f'No GeoJSON found for "{description}"')
                return _ok({"type": "FeatureCollection", "features": polygon_features})

            if name == "batch_convert":
                descriptions = arguments.get("descriptions", [])
                if not isinstance(descriptions, list) or not descriptions:
                    return _err("descriptions must be a non-empty array of strings")
                if len(descriptions) > MAX_BATCH_SIZE:
                    return _err(
                        f"batch_convert accepts at most {MAX_BATCH_SIZE} descriptions; "
                        f"received {len(descriptions)}."
                    )
                results = await client.batch_search(descriptions)
                records = []
                for i, fc in enumerate(results):
                    inp = descriptions[i]
                    if fc is None or not fc.features:
                        records.append({"input": inp, "result": None, "error": "Not found"})
                    else:
                        try:
                            sr = _fc_to_search_result(fc)
                            records.append(
                                {
                                    "input": inp,
                                    "result": {
                                        "legal_location": sr.legal_location,
                                        "lat": sr.lat,
                                        "lng": sr.lng,
                                        "state": sr.state,
                                        "county": sr.county,
                                        "geometry": sr.geometry,
                                    },
                                }
                            )
                        except Exception as exc:  # noqa: BLE001
                            records.append({"input": inp, "result": None, "error": str(exc)})
                converted = sum(1 for r in records if r["result"] is not None)
                return _ok(
                    {
                        "total": len(records),
                        "converted": converted,
                        "failed": len(records) - converted,
                        "records": records,
                    }
                )

            if name == "autocomplete":
                query = arguments["query"]
                if not isinstance(query, str) or len(query.strip()) < 2:
                    return _err("'query' must be at least 2 characters.")
                limit = int(arguments.get("limit", DEFAULT_AUTOCOMPLETE_LIMIT))
                limit = max(1, min(limit, MAX_AUTOCOMPLETE_LIMIT))
                result = await client.autocomplete(query, limit=limit)
                return _ok(result.model_dump())

            return _err(f"Unknown tool: {name}")

    except RateLimitError:
        logger.exception("Township America quota exceeded")
        return _err(QUOTA_EXCEEDED_MESSAGE)
    except TownshipAmericaError as exc:
        logger.exception("Township America API error")
        return _err(f"API error: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in tool %s", name)
        return _err(f"Unexpected error: {exc}")


def _summarize_search(payload: dict[str, Any], original: str) -> dict[str, Any]:
    """Pull the highest-signal fields out of the GeoJSON for AI consumption."""
    if not isinstance(payload, dict):
        return {"input": original, "raw": payload}
    features = payload.get("features") or []
    if not features:
        return {"input": original, "found": False, "raw": payload}
    first = features[0] if isinstance(features[0], dict) else {}
    props = first.get("properties", {}) if isinstance(first, dict) else {}
    geometry = first.get("geometry") if isinstance(first, dict) else None
    centroid = None
    if geometry and geometry.get("type") in ("Point",):
        centroid = geometry.get("coordinates")
    return {
        "input": original,
        "found": True,
        "legal_location": props.get("legal_location"),
        "state": props.get("state"),
        "county": props.get("county"),
        "survey_system": props.get("survey_system"),
        "meridian": props.get("meridian"),
        "centroid": centroid,
        "geojson": payload,
    }


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for the `townshipamerica-mcp` console script."""
    logging.basicConfig(
        level=os.environ.get("MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
