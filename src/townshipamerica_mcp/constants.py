"""Shared constants for Township America MCP (aligned with typescript-mcp)."""

API_KEY_ENV = "TOWNSHIP_AMERICA_API_KEY"
LEGACY_API_KEY_ENV = "TA_API_KEY"
BASE_URL_ENV = "TOWNSHIP_AMERICA_BASE_URL"

MAX_BATCH_SIZE = 100
MAX_AUTOCOMPLETE_LIMIT = 10
DEFAULT_AUTOCOMPLETE_LIMIT = 10

QUOTA_EXCEEDED_MESSAGE = (
    "Pro+ bundled quota exceeded for this endpoint (1,000 calls/month). "
    "Upgrade to standalone Scale tier ($100/mo for 10,000 calls) or wait for next month. "
    "Visit https://townshipamerica.com/pricing to manage your plan."
)

API_KEY_HELP_URL = "https://app.townshipamerica.com/settings/api-keys"
