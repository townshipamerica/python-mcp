"""Exceptions for the Township America MCP client."""


class TownshipMCPError(Exception):
    """Base exception for all Township America MCP errors."""


class AuthenticationError(TownshipMCPError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class QuotaExceededError(TownshipMCPError):
    """
    Raised when the Pro+ bundled quota is exhausted (HTTP 429).

    Upgrade to Scale tier ($100/mo for 10,000 calls) or wait for next month:
    https://townshipamerica.com/pricing
    """


class NotFoundError(TownshipMCPError):
    """Raised when no PLSS result is found for the given input."""


class ValidationError(TownshipMCPError):
    """Raised when the input fails server-side validation (HTTP 400)."""
