"""Local PLSS description validation (no API call)."""

from __future__ import annotations

import re

from .models import ValidationResult

# PLSS regex patterns (from web-app land-description rules; shared with typescript-mcp)
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

_QUARTER_ALIASES = {
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
    "NORTH EAST": "NE",
    "NORTH WEST": "NW",
    "SOUTH EAST": "SE",
    "SOUTH WEST": "SW",
}

_INVALID_SUGGESTION = (
    "PLSS descriptions follow the pattern: [Quarter] [Section] [Township][N/S] "
    "[Range][E/W] [Principal Meridian]. "
    "Example: 'NW 25 24N 1E 6th Meridian' or 'T4N R5E Sec 12 NE'. "
    "Ensure township/range direction letters (N/S, E/W) are present and a meridian name is included."
)


def is_valid_plss(description: str) -> bool:
    d = description.strip()
    return bool(
        _SECOND_DIVISION_PATTERN.search(d)
        or _FIRST_DIVISION_PATTERN.search(d)
        or _TWP_PATTERN.search(d)
    )


def normalize_plss(description: str) -> str:
    d = description.strip().upper()
    for long, short in _QUARTER_ALIASES.items():
        d = re.sub(rf"\b{long}\b", short, d, flags=re.IGNORECASE)
    d = d.replace("¼", " 1/4")
    return re.sub(r"\s+", " ", d).strip()


def validate_plss_description(description: str) -> ValidationResult:
    """Validate and normalize a PLSS string locally (no API call)."""
    if not description or not description.strip():
        raise ValueError("description must not be empty")
    normalized = normalize_plss(description)
    valid = is_valid_plss(normalized) or is_valid_plss(description)
    if valid:
        return ValidationResult(valid=True, normalized=normalized)
    return ValidationResult(valid=False, suggestion=_INVALID_SUGGESTION)
