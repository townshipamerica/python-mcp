"""Tests for TownshipMCPClient and client helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from townshipamerica.exceptions import (
    AuthenticationError as TAAuthenticationError,
    NotFoundError as TANotFoundError,
    RateLimitError,
    TownshipAmericaError,
    ValidationError as TAValidationError,
)
from townshipamerica.models import Feature, FeatureCollection, FeatureProperties, Point

from townshipamerica_mcp.client import (
    TownshipMCPClient,
    _fc_to_search_result,
    _map_error,
)
from townshipamerica_mcp.constants import MAX_BATCH_SIZE
from townshipamerica_mcp.plss_validation import is_valid_plss, normalize_plss
from townshipamerica_mcp.exceptions import (
    AuthenticationError,
    NotFoundError,
    QuotaExceededError,
    TownshipMCPError,
    ValidationError,
)


class TestNormalize:
    def test_expands_quarter_aliases(self):
        assert "NE" in normalize_plss("NORTHEAST 25 24N 1E 6TH MERIDIAN")

    def test_replaces_fraction_symbol(self):
        assert "1/4" in normalize_plss("SE¼ NW¼ 14 T2N R4E")

    def test_collapses_whitespace(self):
        assert normalize_plss("  NW   25   24N  1E  ") == "NW 25 24N 1E"


class TestPlssValidation:
    def test_valid_section_description(self):
        assert is_valid_plss("NW 25 24N 1E 6TH MERIDIAN")

    def test_invalid_description(self):
        assert not is_valid_plss("not a plss string")


class TestMapError:
    def test_maps_authentication(self):
        with pytest.raises(AuthenticationError):
            _map_error(TAAuthenticationError("bad key"))

    def test_maps_not_found(self):
        with pytest.raises(NotFoundError):
            _map_error(TANotFoundError("missing"))

    def test_maps_validation(self):
        with pytest.raises(ValidationError):
            _map_error(TAValidationError("invalid"))

    def test_maps_rate_limit(self):
        with pytest.raises(QuotaExceededError):
            _map_error(RateLimitError("quota"))

    def test_maps_generic(self):
        with pytest.raises(TownshipMCPError):
            _map_error(TownshipAmericaError("server error"))


class TestFcToSearchResult:
    def test_extracts_centroid_and_boundary(self, sample_feature_collection):
        result = _fc_to_search_result(sample_feature_collection)
        assert result.legal_location == "NW 25 24N 1E 6TH MERIDIAN"
        assert result.lat == pytest.approx(39.739)
        assert result.lng == pytest.approx(-104.987)
        assert result.state == "Colorado"
        assert result.county == "Adams"
        assert result.geometry is not None
        assert result.geometry["type"] == "Polygon"

    def test_raises_when_no_usable_features(self):
        fc = FeatureCollection(
            features=[
                Feature(
                    geometry=Point(coordinates=[0.0, 0.0]),
                    properties=FeatureProperties(),
                )
            ]
        )
        with pytest.raises(TownshipMCPError, match="no features"):
            _fc_to_search_result(fc)


class TestTownshipMCPClientInit:
    def test_rejects_empty_api_key(self):
        with pytest.raises(TownshipMCPError, match="api_key is required"):
            TownshipMCPClient(api_key="  ")


class TestValidateDescription:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_valid_description(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        result = client.validate_description("NW 25 24N 1E 6TH MERIDIAN")
        assert result.valid is True
        assert result.normalized is not None
        assert "NW" in result.normalized

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_invalid_description_returns_suggestion(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        result = client.validate_description("not plss")
        assert result.valid is False
        assert result.suggestion is not None

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_empty_description_raises(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(ValueError, match="must not be empty"):
            client.validate_description("")


class TestCoordinatesToPlss:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_rejects_out_of_range_lat(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(ValueError, match="lat must be"):
            client.coordinates_to_plss(91.0, 0.0)

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_rejects_out_of_range_lng(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(ValueError, match="lng must be"):
            client.coordinates_to_plss(0.0, 181.0)

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_success(self, mock_ta_class: MagicMock, sample_feature_collection):
        mock_ta_class.return_value.reverse.return_value = sample_feature_collection
        client = TownshipMCPClient(api_key="ta_test")
        result = client.coordinates_to_plss(39.739, -104.987)
        assert result.legal_location == "NW 25 24N 1E 6TH MERIDIAN"
        mock_ta_class.return_value.reverse.assert_called_once_with(-104.987, 39.739)

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_empty_features_raises_not_found(self, mock_ta_class: MagicMock):
        mock_ta_class.return_value.search.return_value = FeatureCollection(features=[])
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(NotFoundError):
            client.plss_to_coordinates("NW 25 24N 1E 6TH MERIDIAN")


class TestPlssToCoordinates:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_success(self, mock_ta_class: MagicMock, sample_feature_collection):
        mock_ta_class.return_value.search.return_value = sample_feature_collection
        client = TownshipMCPClient(api_key="ta_test")
        result = client.plss_to_coordinates("  NW 25 24N 1E 6TH MERIDIAN  ")
        assert result.lat == pytest.approx(39.739)
        mock_ta_class.return_value.search.assert_called_once_with("NW 25 24N 1E 6TH MERIDIAN")

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_maps_api_authentication_error(self, mock_ta_class: MagicMock):
        mock_ta_class.return_value.search.side_effect = TAAuthenticationError("401")
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(AuthenticationError):
            client.plss_to_coordinates("NW 25 24N 1E 6TH MERIDIAN")


class TestPlssToGeojson:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_returns_polygon_features(
        self, mock_ta_class: MagicMock, sample_feature_collection
    ):
        mock_ta_class.return_value.search.return_value = sample_feature_collection
        client = TownshipMCPClient(api_key="ta_test")
        geojson = client.plss_to_geojson("NW 25 24N 1E 6TH MERIDIAN")
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 1
        assert geojson["features"][0]["geometry"]["type"] == "Polygon"

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_no_polygon_raises_not_found(self, mock_ta_class: MagicMock):
        mock_ta_class.return_value.search.return_value = FeatureCollection(
            features=[
                Feature(
                    geometry=Point(coordinates=[-105.0, 39.7]),
                    properties=FeatureProperties(shape="centroid"),
                )
            ]
        )
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(NotFoundError, match="No GeoJSON"):
            client.plss_to_geojson("NW 25 24N 1E 6TH MERIDIAN")


class TestBatchConvert:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_rejects_empty_list(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        with pytest.raises(ValueError, match="must not be empty"):
            client.batch_convert([])

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_rejects_over_max_size(self, mock_ta_class: MagicMock):
        client = TownshipMCPClient(api_key="ta_test")
        descriptions = ["desc"] * (MAX_BATCH_SIZE + 1)
        with pytest.raises(ValueError, match=str(MAX_BATCH_SIZE)):
            client.batch_convert(descriptions)

    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_mixed_success_and_failure(
        self, mock_ta_class: MagicMock, sample_feature_collection
    ):
        mock_ta_class.return_value.batch_search.return_value = [
            sample_feature_collection,
            FeatureCollection(features=[]),
        ]
        client = TownshipMCPClient(api_key="ta_test")
        result = client.batch_convert(["good", "bad"])
        assert result.total == 2
        assert result.converted == 1
        assert result.failed == 1
        assert result.records[0].result is not None
        assert result.records[1].error == "Not found"


class TestContextManager:
    @patch("townshipamerica_mcp.client.TownshipAmerica")
    def test_close_on_exit(self, mock_ta_class: MagicMock):
        with TownshipMCPClient(api_key="ta_test") as client:
            pass
        mock_ta_class.return_value.close.assert_called_once()
