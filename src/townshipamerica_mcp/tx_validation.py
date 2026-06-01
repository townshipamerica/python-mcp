"""Lightweight Texas TXSS shape detection for local validate_description."""

from __future__ import annotations

import re

_TXSS_MARKERS = re.compile(
    r"\babstract\b|\babs\.?\s*[0-9]|\ba\s*-\s*[0-9]+|\bblock\s+\d+\b|\bblk\.?\s*\d+\b|\bsurvey\b|\bleague\b|\blabor\b|\blabors\b",
    re.IGNORECASE,
)

_TX_COUNTY = re.compile(
    r"\b[a-z][\w.'-]*(?:\s+[a-z][\w.'-]*)*\s+(?:county|co\.?)(?:\s*,?\s*(?:tx|texas))?\b",
    re.IGNORECASE,
)


def is_valid_txss(description: str) -> bool:
    d = description.strip()
    if not d:
        return False
    return bool(_TXSS_MARKERS.search(d) or _TX_COUNTY.search(d))


def normalize_txss(description: str) -> str:
    d = description.strip()
    d = re.sub(r"\s+", " ", d)
    d = re.sub(r"\ba\s*-\s*", "A-", d, flags=re.IGNORECASE)
    d = re.sub(r"\babstract\s*#?\s*", "Abstract ", d, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", d).strip()
