# townshipamerica-mcp

[![PyPI](https://img.shields.io/pypi/v/townshipamerica-mcp)](https://pypi.org/project/townshipamerica-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Model Context Protocol (MCP) server that exposes Township America's PLSS conversion to AI agents — Claude, ChatGPT, Cursor, GitHub Copilot, Windsurf, or any MCP-compatible client.

Also includes a Python client (`TownshipMCPClient`) for scripts and notebooks, backed by the [townshipamerica](https://pypi.org/project/townshipamerica/) SDK.

[API Documentation](https://townshipamerica.com/api) · [GitHub](https://github.com/townshipamerica/python-mcp) · [PyPI](https://pypi.org/project/townshipamerica-mcp/) · [TypeScript MCP](https://github.com/townshipamerica/typescript-mcp)

Requires a [Pro+ subscription](https://townshipamerica.com/pricing) ($99/mo) for bundled API access.

## Installation

```bash
pip install townshipamerica-mcp
```

Requires Python 3.10+.

## Quick Start

Set your API key (generate at [app.townshipamerica.com/settings/api-keys](https://app.townshipamerica.com/settings/api-keys)):

```bash
export TOWNSHIP_AMERICA_API_KEY="ta_…"
```

### Tools

| Tool                   | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| `plss_to_coordinates`  | Convert a PLSS legal description to GPS coordinates   |
| `coordinates_to_plss`  | Reverse-lookup coordinates to a PLSS description      |
| `plss_to_geojson`      | Return the section/quarter/aliquot polygon as GeoJSON |
| `validate_description` | Validate and normalize locally (no API call)          |
| `batch_convert`        | Convert up to 100 descriptions in one request         |
| `autocomplete`         | Suggestions for partial PLSS input (max 10)           |
| `land_report`          | Federal Land Report — coming Q3 2025                  |

Coverage: 30 PLSS states, 37 principal meridians. Powered by BLM CadNSDI V2.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Restart Claude Desktop to apply.

### Cursor / VS Code / Continue

```jsonc
{
  "mcpServers": {
    "townshipamerica": {
      "command": "townshipamerica-mcp",
      "env": { "TOWNSHIP_AMERICA_API_KEY": "ta_…" },
    },
  },
}
```

### Stdio (any MCP client)

```bash
TOWNSHIP_AMERICA_API_KEY=ta_… townshipamerica-mcp
```

### Environment variables

| Variable                    | Default                                 | Purpose                                     |
| --------------------------- | --------------------------------------- | ------------------------------------------- |
| `TOWNSHIP_AMERICA_API_KEY`  | _(required)_                            | Your Pro+ API key (preferred)               |
| `TA_API_KEY`                | —                                       | Legacy alias for `TOWNSHIP_AMERICA_API_KEY` |
| `TOWNSHIP_AMERICA_BASE_URL` | `https://developer.townshipamerica.com` | Override the API endpoint                   |
| `MCP_LOG_LEVEL`             | `INFO`                                  | Log level for stderr                        |

## Quota

Pro+ bundled API access: 1,000 search calls/month. If exceeded, tools return a clear quota message with upgrade guidance. Visit [townshipamerica.com/pricing](https://townshipamerica.com/pricing).

## Python client

For programmatic use without an MCP host:

```python
from townshipamerica_mcp import TownshipMCPClient

client = TownshipMCPClient(api_key="ta_…")

result = client.plss_to_coordinates("NW 25 24N 1E 6th Meridian")
print(result.lat, result.lng)

v = client.validate_description("NW 25 24N 1E 6th Meridian")
print(v.valid, v.normalized)

batch = client.batch_convert(["NW 25 24N 1E 6th Meridian", "SE 12 4N 5E Boise Meridian"])
print(batch.converted, batch.failed)
```

For full SDK features (async, GeoPandas-friendly models), use `pip install townshipamerica`.

## Exceptions

| Exception             | Trigger                       |
| --------------------- | ----------------------------- |
| `AuthenticationError` | Invalid or missing API key    |
| `QuotaExceededError`  | Rate limit / quota exceeded   |
| `NotFoundError`       | Location not in PLSS database |
| `ValidationError`     | Malformed request             |
| `TownshipMCPError`    | Base class / other errors     |

## License

MIT — see [LICENSE](LICENSE).
