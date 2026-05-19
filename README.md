# townshipamerica-mcp

Python wrapper for the Township America MCP server — PLSS tools for AI agents.

## Installation

```bash
pip install townshipamerica-mcp
```

> Not yet on PyPI. Install from source: `pip install -e packages/python-sdk-mcp/`

Requires Python 3.11+.

## Quick Start

```python
from townshipamerica_mcp import TownshipMCPClient

client = TownshipMCPClient(api_key="ta_live_your_key_here")

# PLSS description → GPS coordinates
result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
print(result.legal_location)  # NW-25-24N-1E-6th-Meridian
print(result.lat, result.lng)  # 44.5, -110.3
print(result.state, result.county)  # Wyoming, Park

# GPS coordinates → PLSS description
result = client.coordinates_to_plss(lat=44.5, lng=-110.3)
print(result.legal_location)

# GeoJSON boundary
geojson = client.plss_to_geojson("NW 25 24N 1E 6th Meridian")
print(geojson["type"])  # FeatureCollection

# Validate a description (no API call)
v = client.validate_description("NW 25 24N 1E 6th Meridian")
print(v.valid, v.normalized)  # True, NW 25 24N 1E 6TH MERIDIAN

# Batch convert (up to 1,000)
batch = client.batch_convert([
    "NW 25 24N 1E 6th Meridian",
    "SE 12 4N 5E Boise Meridian",
])
print(batch.total, batch.converted, batch.failed)  # 2, 2, 0

# Federal Land Report (coming Q3 2025)
report = client.land_report("NW 25 24N 1E 6th Meridian")
print(report.status)  # coming_soon
```

## Context Manager

```python
with TownshipMCPClient(api_key="ta_live_...") as client:
    result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
```

## Launching the Node.js MCP Server

If you need the stdio MCP transport (for integration with custom MCP frameworks):

```python
proc = TownshipMCPClient.launch_mcp_server(api_key="ta_live_...")
# proc.stdin / proc.stdout are the MCP stdio transport pipes
```

Requires Node.js 22+ and npx installed.

## Authentication

Get your API key at [app.townshipamerica.com/settings/api-keys](https://app.townshipamerica.com/settings/api-keys).

Requires a [Pro+ subscription](https://townshipamerica.com/pricing) ($99/mo).

## Quota

Pro+ bundled API access includes 1,000 search calls/month. Batch counting: each item in a batch counts as one call. Exceeding quota raises `QuotaExceededError`. Reset occurs on your billing date.

Upgrade to Scale tier ($100/mo for 10,000 calls) at [townshipamerica.com/pricing](https://townshipamerica.com/pricing).

## Exceptions

| Exception             | Trigger                       |
| --------------------- | ----------------------------- |
| `AuthenticationError` | Invalid or missing API key    |
| `QuotaExceededError`  | Monthly quota exhausted       |
| `NotFoundError`       | Location not in PLSS database |
| `ValidationError`     | Malformed request             |
| `TownshipMCPError`    | Base class / other errors     |

## License

MIT — Maps & Apps Inc.
