"""Python client for the BriefKlick v2 letter API."""

from .client import BriefKlickClient
from .exceptions import (
    APIError,
    AuthenticationError,
    BriefKlickError,
    ConfigurationError,
    InsufficientFundsError,
    ServerError,
    TimeoutError_,
    ValidationError,
)
from .models import (
    Color,
    Document,
    Einschreiben,
    Order,
    OrderStatus,
    Preview,
    Recipient,
    Status,
)

__all__ = [
    "BriefKlickClient",
    "BriefKlickError",
    "ConfigurationError",
    "APIError",
    "AuthenticationError",
    "InsufficientFundsError",
    "ValidationError",
    "ServerError",
    "TimeoutError_",
    "Color",
    "Document",
    "Einschreiben",
    "Order",
    "OrderStatus",
    "Preview",
    "Recipient",
    "Status",
]

__version__ = "0.1.0"
