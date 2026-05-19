"""
townshipamerica-mcp — Township America PLSS tools for AI agents.

This package exposes the MCP server tools as ordinary Python callables
so they can be called from scripts, notebooks, or custom MCP frameworks.

Usage::

    from townshipamerica_mcp import TownshipMCPClient

    client = TownshipMCPClient(api_key="ta_live_...")
    result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
    print(result.lat, result.lng)

    # Validate without making an API call
    v = client.validate_description("NW 25 24N 1E 6th Meridian")
    print(v.valid, v.normalized)
"""

from .client import TownshipMCPClient
from .models import (
    SearchResult,
    ValidationResult,
    BatchRecord,
    BatchResult,
)
from .exceptions import (
    TownshipMCPError,
    AuthenticationError,
    QuotaExceededError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "TownshipMCPClient",
    "SearchResult",
    "ValidationResult",
    "BatchRecord",
    "BatchResult",
    "TownshipMCPError",
    "AuthenticationError",
    "QuotaExceededError",
    "NotFoundError",
    "ValidationError",
]

__version__ = "0.1.0"
