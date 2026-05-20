"""
townshipamerica-mcp — Township America PLSS tools for AI agents.

MCP stdio server (Claude Desktop, Cursor, etc.)::

    townshipamerica-mcp

Python callables (scripts, notebooks)::

    from townshipamerica_mcp import TownshipMCPClient

    client = TownshipMCPClient(api_key="ta_…")
    result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
"""

from .client import TownshipMCPClient
from .exceptions import (
    AuthenticationError,
    NotFoundError,
    QuotaExceededError,
    TownshipMCPError,
    ValidationError,
)
from .models import BatchRecord, BatchResult, SearchResult, ValidationResult
from .server import main

__version__ = "1.0.1"

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
    "main",
]
