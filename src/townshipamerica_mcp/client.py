"""
Township America MCP client — exposes MCP server tools as Python callables.

Backed by the :mod:`townshipamerica` SDK (same API as the stdio MCP server).
"""

from __future__ import annotations

from typing import Any

from townshipamerica import TownshipAmerica
from townshipamerica.exceptions import (
    AuthenticationError as TAAuthenticationError,
    NotFoundError as TANotFoundError,
    RateLimitError,
    TownshipAmericaError,
    ValidationError as TAValidationError,
)
from townshipamerica.models import FeatureCollection, MultiPolygon, Point, Polygon

from .exceptions import (
    AuthenticationError,
    NotFoundError,
    QuotaExceededError,
    TownshipMCPError,
    ValidationError,
)
from .constants import MAX_BATCH_SIZE
from .models import BatchResult, LandReportStub, SearchResult, ValidationResult
from .plss_validation import validate_plss_description


def _map_error(exc: TownshipAmericaError) -> None:
    if isinstance(exc, TAAuthenticationError):
        raise AuthenticationError(exc.message) from exc
    if isinstance(exc, TANotFoundError):
        raise NotFoundError(exc.message) from exc
    if isinstance(exc, TAValidationError):
        raise ValidationError(exc.message) from exc
    if isinstance(exc, RateLimitError):
        raise QuotaExceededError(exc.message) from exc
    raise TownshipMCPError(exc.message) from exc


def _fc_to_search_result(fc: FeatureCollection) -> SearchResult:
    centroid = fc.centroid
    grid = fc.grid
    feature = centroid or grid
    if feature is None:
        raise TownshipMCPError("Unexpected API response: no features returned")

    props = feature.properties
    lat = lng = 0.0
    if centroid and isinstance(centroid.geometry, Point):
        lat = centroid.geometry.latitude
        lng = centroid.geometry.longitude

    boundary = None
    if grid and isinstance(grid.geometry, (Polygon, MultiPolygon)):
        boundary = grid.geometry.model_dump()

    return SearchResult(
        legal_location=props.legal_location or "",
        lat=lat,
        lng=lng,
        state=props.state or "",
        county=props.county or "",
        geometry=boundary,
    )


class TownshipMCPClient:
    """
    Python wrapper for Township America MCP tools.

    Uses the :mod:`townshipamerica` SDK. For Claude Desktop, Cursor, and other MCP
    clients, run the ``townshipamerica-mcp`` console script instead.

    Args:
        api_key: Township America API key.
        base_url: Override the API base URL.
        timeout: Request timeout in seconds.

    Example::

        client = TownshipMCPClient(api_key="ta_…")
        result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
        print(result.lat, result.lng)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise TownshipMCPError(
                "api_key is required. Get one at https://townshipamerica.com/api"
            )
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self._ta = TownshipAmerica(**kwargs)

    def plss_to_coordinates(self, description: str) -> SearchResult:
        """Convert a PLSS legal land description to GPS coordinates."""
        try:
            fc = self._ta.search(description.strip())
            if not fc.features:
                raise NotFoundError(f'No results found for "{description}"')
            return _fc_to_search_result(fc)
        except TownshipAmericaError as exc:
            _map_error(exc)

    def coordinates_to_plss(self, lat: float, lng: float) -> SearchResult:
        """Find the PLSS legal land description for given GPS coordinates."""
        if not (-90 <= lat <= 90):
            raise ValueError(f"lat must be between -90 and 90, got {lat}")
        if not (-180 <= lng <= 180):
            raise ValueError(f"lng must be between -180 and 180, got {lng}")
        try:
            fc = self._ta.reverse(lng, lat)
            if not fc.features:
                raise NotFoundError(f"No PLSS data found for coordinates [{lat}, {lng}]")
            return _fc_to_search_result(fc)
        except TownshipAmericaError as exc:
            _map_error(exc)

    def plss_to_geojson(self, description: str) -> dict[str, Any]:
        """Return the GeoJSON boundary polygon for a PLSS legal land description."""
        try:
            fc = self._ta.search(description.strip())
            polygon_features = [
                f.model_dump()
                for f in fc.features
                if isinstance(f.geometry, (Polygon, MultiPolygon))
            ]
            if not polygon_features:
                raise NotFoundError(f'No GeoJSON found for "{description}"')
            return {"type": "FeatureCollection", "features": polygon_features}
        except TownshipAmericaError as exc:
            _map_error(exc)

    def validate_description(self, description: str) -> ValidationResult:
        """Validate and normalize a PLSS description string (no API call)."""
        return validate_plss_description(description)

    def batch_convert(self, descriptions: list[str]) -> BatchResult:
        """Convert multiple PLSS descriptions to GPS coordinates in one request."""
        if not descriptions:
            raise ValueError("descriptions must not be empty")
        if len(descriptions) > MAX_BATCH_SIZE:
            raise ValueError(
                f"batch_convert accepts at most {MAX_BATCH_SIZE} descriptions; "
                f"received {len(descriptions)}."
            )
        try:
            results = self._ta.batch_search(descriptions)
        except TownshipAmericaError as exc:
            _map_error(exc)

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
                except Exception as exc:
                    records.append({"input": inp, "result": None, "error": str(exc)})
        converted = sum(1 for r in records if r["result"] is not None)
        return BatchResult.from_dict(
            {
                "total": len(records),
                "converted": converted,
                "failed": len(records) - converted,
                "records": records,
            }
        )

    def land_report(self, description: str) -> LandReportStub:
        """Federal Land Report — coming Q3 2025."""
        if not description or not description.strip():
            raise ValueError("description must not be empty")
        return LandReportStub(
            status="coming_soon",
            description=description.strip(),
            message=(
                "Federal Land Report via MCP is coming Q3 2025. "
                "Currently available via the Township America web app at "
                "https://app.townshipamerica.com for Pro+ subscribers. "
                "A dedicated API-key-authenticated endpoint will be available for AI agents this quarter."
            ),
            preview_fields=[
                "federal_land_status",
                "blm_surface_ownership",
                "blm_mineral_ownership",
                "national_forest",
                "national_park",
                "tribal_lands",
                "water_rights",
                "patents",
            ],
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._ta.close()

    def __enter__(self) -> TownshipMCPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
