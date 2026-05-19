"""
Township America MCP client — exposes MCP server tools as Python callables.

Each method mirrors a tool in @townshipamerica/mcp-server and hits the same
AWS API Gateway endpoints using X-API-Key authentication.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any

import httpx

from .exceptions import (
    AuthenticationError,
    NotFoundError,
    QuotaExceededError,
    TownshipMCPError,
    ValidationError,
)
from .models import BatchResult, LandReportStub, SearchResult, ValidationResult

DEFAULT_BASE_URL = "https://developer.townshipamerica.com"
DEFAULT_TIMEOUT = 10.0
MAX_BATCH_SIZE = 1000

# PLSS regex patterns (mirrored from @townshipamerica/mcp-server)
_TWP_PATTERN = re.compile(
    r"(?:\d{1,2}|1\d{2}|200)(\.5)?[NSE](-|\s+)(?:\d{1,2}|1\d{2}|200)(\.5)?[NEW](-|\s+)(?:\b\w+\b\s*)+",
    re.IGNORECASE,
)
_FIRST_DIVISION_PATTERN = re.compile(
    r"(\d{1,4}[a-z]?|[a-z]{1,4}(\d{1,2})?)(-|\s+)(?:\d{1,2}|1\d{2}|200)(\.5)?[NSE](-|\s+)(?:\d{1,2}|1\d{2}|200)(\.5)?[NEW](-|\s+)(?:\b\w+\b\s*)+",
    re.IGNORECASE,
)
_SECOND_DIVISION_PATTERN = re.compile(
    r"(l\s*(\d{1,3})?|(nw|ne|sw|se){1,4}|[news]{1}(\d{1})?(nw|ne|sw|se){2,4}|\d{1,3}|(\w{1}))(-|\s+)(0?\d{1,6}[a-z]?|(nw|ne|sw|se){2}|[a-z]{1,2}(\d{1,3})?)(-|\s+)(?:\d{1,2}|1\d{2}|200)(\.5)?[NSE](-|\s+)(?:\d{1,2}|1\d{2}|200)(\.5)?[NEW](-|\s+)(?:\b\w+\b\s*)+",
    re.IGNORECASE,
)


def _is_valid_plss(description: str) -> bool:
    d = description.strip()
    return bool(
        _SECOND_DIVISION_PATTERN.search(d)
        or _FIRST_DIVISION_PATTERN.search(d)
        or _TWP_PATTERN.search(d)
    )


def _normalize(description: str) -> str:
    d = description.strip().upper()
    aliases = {
        "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
        "NORTH EAST": "NE", "NORTH WEST": "NW", "SOUTH EAST": "SE", "SOUTH WEST": "SW",
    }
    for long, short in aliases.items():
        d = re.sub(rf"\b{long}\b", short, d, flags=re.IGNORECASE)
    d = d.replace("¼", " 1/4")
    d = re.sub(r"\s+", " ", d).strip()
    return d


def _extract_search_result(fc: dict[str, Any]) -> SearchResult:
    features = fc.get("features", [])
    centroid = next((f for f in features if f.get("properties", {}).get("shape") == "centroid"), None)
    grid = next((f for f in features if f.get("properties", {}).get("shape") == "grid"), None)

    props = (centroid or grid or {}).get("properties", {})
    if not props:
        raise TownshipMCPError("Unexpected API response: no features returned")

    coords = centroid["geometry"]["coordinates"] if centroid else [0, 0]
    lng, lat = float(coords[0]), float(coords[1])

    boundary = grid["geometry"] if grid and grid.get("geometry", {}).get("type") == "Polygon" else None

    return SearchResult(
        legal_location=props["legal_location"],
        lat=lat,
        lng=lng,
        state=props["state"],
        county=props["county"],
        geometry=boundary,
    )


class TownshipMCPClient:
    """
    Python wrapper for the Township America MCP server tools.

    Authenticates against the AWS API Gateway using the Pro+ API key.
    Quota enforcement is handled server-side (1,000 calls/month on Pro+ bundled).

    Args:
        api_key: Township America Pro+ API key (starts with ``ta_live_``).
        base_url: Override the API base URL (default: ``developer.townshipamerica.com``).
        timeout: Request timeout in seconds (default: 10).

    Example::

        client = TownshipMCPClient(api_key="ta_live_abc123")
        result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
        print(result.lat, result.lng)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_key.strip():
            raise TownshipMCPError(
                "api_key is required. "
                "Generate a key at https://app.townshipamerica.com/settings/api-keys"
            )
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "X-API-Key": api_key,
                "User-Agent": "townshipamerica-mcp-python/0.1.0",
            },
            timeout=timeout,
        )

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            resp = self._client.get(path, params=params)
            self._raise_for_status(resp)
            result: dict[str, Any] = resp.json()
            return result
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise TownshipMCPError(f"Request failed: {exc}") from exc

    def _post(self, path: str, body: Any) -> Any:
        try:
            resp = self._client.post(path, json=body, headers={"Content-Type": "application/json"})
            self._raise_for_status(resp)
            return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise TownshipMCPError(f"Request failed: {exc}") from exc

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.is_success:
            return
        try:
            body = resp.json()
            message = str(body.get("error") or body.get("message") or resp.reason_phrase)
        except Exception:
            message = resp.reason_phrase
        if resp.status_code == 400:
            raise ValidationError(message)
        if resp.status_code == 401:
            raise AuthenticationError(message)
        if resp.status_code == 404:
            raise NotFoundError(message)
        if resp.status_code == 429:
            raise QuotaExceededError(
                "Pro+ bundled quota exceeded (1,000 calls/month). "
                "Upgrade to Scale tier ($100/mo for 10,000 calls): "
                "https://townshipamerica.com/pricing"
            )
        raise TownshipMCPError(f"API error {resp.status_code}: {message}")

    def plss_to_coordinates(self, description: str) -> SearchResult:
        """
        Convert a PLSS legal land description to GPS coordinates.

        Args:
            description: PLSS description, e.g. ``"NW 25 24N 1E 6th Meridian"``.

        Returns:
            :class:`SearchResult` with lat, lng, state, county, and optional boundary.

        Raises:
            :class:`NotFoundError`: If no result is found.
            :class:`QuotaExceededError`: If the monthly quota is exhausted.
        """
        data = self._get("/search/legal-location", params={"location": description.strip()})
        features = data.get("features", [])
        if not features:
            raise NotFoundError(f'No results found for "{description}"')
        return _extract_search_result(data)

    def coordinates_to_plss(self, lat: float, lng: float) -> SearchResult:
        """
        Find the PLSS legal land description for given GPS coordinates.

        Args:
            lat: Latitude in decimal degrees.
            lng: Longitude in decimal degrees.

        Returns:
            :class:`SearchResult` with the nearest PLSS description.

        Raises:
            :class:`NotFoundError`: If the location is outside PLSS coverage.
            :class:`QuotaExceededError`: If the monthly quota is exhausted.
        """
        if not (-90 <= lat <= 90):
            raise ValueError(f"lat must be between -90 and 90, got {lat}")
        if not (-180 <= lng <= 180):
            raise ValueError(f"lng must be between -180 and 180, got {lng}")
        data = self._get("/search/coordinates", params={"location": f"{lng},{lat}"})
        features = data.get("features", [])
        if not features:
            raise NotFoundError(f"No PLSS data found for coordinates [{lat}, {lng}]")
        return _extract_search_result(data)

    def plss_to_geojson(self, description: str) -> dict[str, Any]:
        """
        Get the GeoJSON boundary polygon for a PLSS legal land description.

        Args:
            description: PLSS description, e.g. ``"NW 25 24N 1E 6th Meridian"``.

        Returns:
            GeoJSON FeatureCollection dict with Polygon features.

        Raises:
            :class:`NotFoundError`: If no result is found.
            :class:`QuotaExceededError`: If the monthly quota is exhausted.
        """
        data = self._get("/search/legal-location", params={"location": description.strip()})
        features = data.get("features", [])
        if not features:
            raise NotFoundError(f'No GeoJSON found for "{description}"')
        polygon_features = [f for f in features if f.get("geometry", {}).get("type") == "Polygon"]
        return {"type": "FeatureCollection", "features": polygon_features}

    def validate_description(self, description: str) -> ValidationResult:
        """
        Validate and normalize a PLSS description string (no API call).

        Args:
            description: PLSS description to validate.

        Returns:
            :class:`ValidationResult` with ``valid``, ``normalized``, and ``suggestion``.
        """
        if not description or not description.strip():
            raise ValueError("description must not be empty")
        normalized = _normalize(description)
        valid = _is_valid_plss(normalized) or _is_valid_plss(description)
        if valid:
            return ValidationResult(valid=True, normalized=normalized)
        return ValidationResult(
            valid=False,
            suggestion=(
                "PLSS descriptions follow the pattern: [Quarter] [Section] [Township][N/S] "
                "[Range][E/W] [Principal Meridian]. "
                "Example: 'NW 25 24N 1E 6th Meridian' or 'T4N R5E Sec 12 NE'."
            ),
        )

    def batch_convert(self, descriptions: list[str]) -> BatchResult:
        """
        Convert multiple PLSS descriptions to GPS coordinates in one request.

        Args:
            descriptions: List of PLSS descriptions (max 1,000).

        Returns:
            :class:`BatchResult` with total, converted, failed counts and per-record results.

        Raises:
            :class:`ValueError`: If more than 1,000 descriptions are provided.
            :class:`QuotaExceededError`: If the monthly quota is exhausted.
        """
        if not descriptions:
            raise ValueError("descriptions must not be empty")
        if len(descriptions) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Pro+ bundled tier supports up to {MAX_BATCH_SIZE:,} descriptions per batch. "
                f"Received {len(descriptions)}."
            )
        data: list[dict[str, Any] | None] = self._post("/batch/legal-location", descriptions)
        records = []
        for i, fc in enumerate(data):
            inp = descriptions[i]
            if fc is None or not fc.get("features"):
                records.append({"input": inp, "result": None, "error": "Not found"})
            else:
                try:
                    sr = _extract_search_result(fc)
                    records.append({
                        "input": inp,
                        "result": {
                            "legal_location": sr.legal_location,
                            "lat": sr.lat, "lng": sr.lng,
                            "state": sr.state, "county": sr.county,
                            "geometry": sr.geometry,
                        },
                    })
                except Exception as exc:
                    records.append({"input": inp, "result": None, "error": str(exc)})
        converted = sum(1 for r in records if r["result"] is not None)
        return BatchResult.from_dict({
            "total": len(records),
            "converted": converted,
            "failed": len(records) - converted,
            "records": records,
        })

    def land_report(self, description: str) -> LandReportStub:
        """
        Federal Land Report — coming Q3 2025.

        Args:
            description: PLSS legal land description.

        Returns:
            :class:`LandReportStub` with status ``coming_soon`` and preview fields.
        """
        if not description or not description.strip():
            raise ValueError("description must not be empty")
        return LandReportStub(
            status="coming_soon",
            description=description.strip(),
            message=(
                "Federal Land Report via MCP is coming Q3 2025. "
                "Currently available via the Township America web app at "
                "https://app.townshipamerica.com for Pro+ subscribers."
            ),
            preview_fields=[
                "federal_land_status", "blm_surface_ownership", "blm_mineral_ownership",
                "national_forest", "national_park", "tribal_lands", "water_rights", "patents",
            ],
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "TownshipMCPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def launch_mcp_server(api_key: str) -> subprocess.Popen[bytes]:
        """
        Launch the Node.js MCP server as a subprocess (stdio transport).

        This is a convenience helper for embedding the MCP server in custom
        MCP framework integrations. Requires Node.js 22+ and npx.

        Args:
            api_key: Township America Pro+ API key.

        Returns:
            A ``subprocess.Popen`` instance. The caller is responsible for
            managing the lifecycle (stdin/stdout for MCP stdio transport).
        """
        return subprocess.Popen(
            ["npx", "-y", "@townshipamerica/mcp-server"],
            env={**dict(__import__("os").environ), "TA_API_KEY": api_key},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
        )
