"""Custom exceptions for the BriefKlick client."""

from __future__ import annotations

from typing import Any


class BriefKlickError(Exception):
    """Base class for all BriefKlick client errors."""


class ConfigurationError(BriefKlickError):
    """Raised when the client is misconfigured (missing API key, bad URL, ...)."""


class APIError(BriefKlickError):
    """Raised when the API returns a non-2xx response.

    Attributes:
        status_code: HTTP status code returned by the API.
        payload: Parsed response body (dict, str, or ``None``).
        endpoint: The endpoint path that produced the error.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        payload: Any = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload
        self.endpoint = endpoint

    def __str__(self) -> str:
        base = super().__str__()
        parts = [f"{base} (status={self.status_code}"]
        if self.endpoint:
            parts.append(f"endpoint={self.endpoint}")
        parts.append(")")
        return ", ".join(parts[:-1]) + parts[-1]


class AuthenticationError(APIError):
    """Raised on HTTP 401/403 responses (bad or missing API key)."""


class InsufficientFundsError(APIError):
    """Raised when the account does not have enough credit to send the letter."""


class ValidationError(APIError):
    """Raised when the API rejects the payload (HTTP 4xx, client-side issue)."""


class ServerError(APIError):
    """Raised on HTTP 5xx responses (BriefKlick server problem)."""


class TimeoutError_(BriefKlickError):  # noqa: N801 - matches builtin name intentionally
    """Raised when an HTTP request exceeds the configured timeout."""


# Export a friendlier alias without shadowing the builtin unless explicitly imported.
TimeoutError = TimeoutError_
