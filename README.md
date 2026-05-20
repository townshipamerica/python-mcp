# townshipamerica-mcp

[![PyPI](https://img.shields.io/pypi/v/townshipamerica-mcp)](https://pypi.org/project/townshipamerica-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Model Context Protocol (MCP) server that exposes Township America's PLSS conversion to AI agents — Claude, ChatGPT, Cursor, GitHub Copilot, Windsurf, or any MCP-compatible client.

Also includes a Python client (`TownshipMCPClient`) for scripts and notebooks, backed by the [townshipamerica](https://pypi.org/project/townshipamerica/) SDK.

[API Documentation](https://townshipamerica.com/api) · [GitHub](https://github.com/townshipamerica/python-mcp) · [PyPI](https://pypi.org/project/townshipamerica-mcp/)

## Installation

```bash
pip install townshipamerica-mcp
```

Requires Python 3.10+. You also need a Township America API key — get one at [townshipamerica.com/api](https://townshipamerica.com/api).

## MCP server (Claude Desktop, Cursor, etc.)

Set your API key:

```bash
export TOWNSHIP_AMERICA_API_KEY="ta_…"
```

### Tools

| Tool | Purpose |
| --- | --- |
| `plss_to_coordinates` | Convert a PLSS legal description to GPS coordinates |
| `coordinates_to_plss` | Reverse-lookup coordinates to a PLSS description |
| `plss_to_geojson` | Return the section/quarter/aliquot polygon as GeoJSON |
| `validate_description` | Check whether a PLSS string is valid + normalized form |
| `batch_convert` | Process multiple descriptions in one call (up to 100) |
| `autocomplete` | Get suggestions for partial PLSS input |

Coverage: 30 PLSS states, 37 principal meridians. Powered by BLM CadNSDI V2.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "townshipamerica": {
      "command": "townshipamerica-mcp",
      "env": {
        "TOWNSHIP_AMERICA_API_KEY": "ta_…"
      }
    }
  }
}
```

### Cursor / VS Code / Continue

```jsonc
{
  "mcpServers": {
    "townshipamerica": {
      "command": "townshipamerica-mcp",
      "env": { "TOWNSHIP_AMERICA_API_KEY": "ta_…" }
    }
  }
}
```

### Stdio (any MCP client)

```bash
TOWNSHIP_AMERICA_API_KEY=ta_… townshipamerica-mcp
```

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `TOWNSHIP_AMERICA_API_KEY` | *(required)* | Your API key |
| `TOWNSHIP_AMERICA_BASE_URL` | `https://developer.townshipamerica.com` | Override the API endpoint |
| `MCP_LOG_LEVEL` | `INFO` | Log level for stderr (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |

## Python client

For programmatic use without an MCP host:

```python
from townshipamerica_mcp import TownshipMCPClient

client = TownshipMCPClient(api_key="ta_…")

result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
print(result.lat, result.lng)

result = client.coordinates_to_plss(lat=44.5, lng=-110.3)
print(result.legal_location)

v = client.validate_description("NW 25 24N 1E 6th Meridian")
print(v.valid, v.normalized)

batch = client.batch_convert(["NW 25 24N 1E 6th Meridian", "SE 12 4N 5E Boise Meridian"])
print(batch.converted, batch.failed)
```

```python
with TownshipMCPClient(api_key="ta_…") as client:
    geojson = client.plss_to_geojson("NW 25 24N 1E 6th Meridian")
```

For full SDK features (async, GeoPandas-friendly models), use `pip install townshipamerica` from [python-sdk](https://github.com/townshipamerica/python-sdk).

## Exceptions

| Exception | Trigger |
| --- | --- |
| `AuthenticationError` | Invalid or missing API key |
| `QuotaExceededError` | Rate limit / quota exceeded |
| `NotFoundError` | Location not in PLSS database |
| `ValidationError` | Malformed request |
| `TownshipMCPError` | Base class / other errors |

## License

MIT — see [LICENSE](LICENSE).

## Links

- [Township America API](https://townshipamerica.com/api)
- [Python SDK](https://github.com/townshipamerica/python-sdk)
- [MCP spec](https://modelcontextprotocol.io)
