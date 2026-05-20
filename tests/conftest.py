"""Shared fixtures for townshipamerica-mcp tests."""

from __future__ import annotations

import pytest
from townshipamerica.models import (
    Feature,
    FeatureCollection,
    FeatureProperties,
    Point,
    Polygon,
)


@pytest.fixture
def sample_feature_collection() -> FeatureCollection:
    """FeatureCollection with centroid and grid features."""
    props = FeatureProperties(
        shape="centroid",
        legal_location="NW 25 24N 1E 6TH MERIDIAN",
        state="Colorado",
        county="Adams",
    )
    centroid = Feature(
        geometry=Point(coordinates=[-104.987, 39.739]),
        properties=props,
    )
    grid_props = FeatureProperties(
        shape="grid",
        legal_location="NW 25 24N 1E 6TH MERIDIAN",
        state="Colorado",
        county="Adams",
    )
    grid = Feature(
        geometry=Polygon(
            coordinates=[
                [
                    [-105.0, 39.7],
                    [-104.9, 39.7],
                    [-104.9, 39.8],
                    [-105.0, 39.8],
                    [-105.0, 39.7],
                ]
            ]
        ),
        properties=grid_props,
    )
    return FeatureCollection(features=[centroid, grid])


@pytest.fixture
def empty_feature_collection() -> FeatureCollection:
    return FeatureCollection(features=[])
