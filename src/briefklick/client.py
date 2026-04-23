"""Synchronous HTTP client for the BriefKlick v2 API.

All endpoints are documented at https://api.briefklick.de/v2/swagger.json.

Typical usage::

    from briefklick import BriefKlickClient, Recipient, Einschreiben

    client = BriefKlickClient.from_env()
    order = client.send_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="invoice.pdf",
        einschreiben=Einschreiben.STANDARD,
    )
    print(order.id, order.price_eur)
"""

from __future__ import annotations

import base64
import logging
import os
from collections.abc import Mapping
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import IO, Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback, not supported
    ZoneInfo = None  # type: ignore[assignment]

import requests
from dotenv import load_dotenv

from .exceptions import (
    APIError,
    AuthenticationError,
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

__all__ = ["BriefKlickClient"]

logger = logging.getLogger("briefklick")

DEFAULT_BASE_URL = "https://api.briefklick.de/v2"
DEFAULT_TIMEOUT: tuple[float, float] = (10.0, 60.0)  # (connect, read)
MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB per API docs
MAX_PAGES = 90
# BriefKlick returns `/status.created` as a naive "YYYY-MM-DD HH:MM:SS" string
# in German local time. We attach Europe/Berlin so downstream arithmetic is
# correct. Falls back to UTC if tzdata is unavailable.
_BRIEFKLICK_TZ = ZoneInfo("Europe/Berlin") if ZoneInfo is not None else None
try:
    PACKAGE_VERSION = version("briefklick")
except PackageNotFoundError:
    PACKAGE_VERSION = "0.1.0"
DEFAULT_USER_AGENT = f"briefklick-python/{PACKAGE_VERSION}"


class BriefKlickClient:
    """Thin, synchronous wrapper around the BriefKlick v2 REST API.

    Parameters
    ----------
    api_key:
        Your BriefKlick API key. Use :meth:`from_env` to load it from
        a ``BRIEFKLICK_API_KEY`` environment variable / ``.env`` file.
    base_url:
        Override the API base URL (primarily for tests).
    timeout:
        ``(connect, read)`` timeout tuple in seconds.
    session:
        Optional pre-configured ``requests.Session`` (useful for retries
        and custom transports).
    user_agent:
        Custom User-Agent string sent with every request.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: tuple[float, float] | float = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ConfigurationError("api_key must be a non-empty string.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({
            "apikey": self.api_key,
            "User-Agent": user_agent,
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------ helpers

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | os.PathLike[str] | None = None,
        **kwargs: Any,
    ) -> "BriefKlickClient":
        """Build a client from environment variables / ``.env`` file.

        Reads ``BRIEFKLICK_API_KEY`` (required), ``BRIEFKLICK_BASE_URL``,
        ``BRIEFKLICK_TIMEOUT_CONNECT`` and ``BRIEFKLICK_TIMEOUT_READ``.
        """
        if env_file is not None:
            load_dotenv(env_file, override=False)
        else:
            load_dotenv(override=False)

        api_key = os.getenv("BRIEFKLICK_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError(
                "BRIEFKLICK_API_KEY is not set. Copy .env.example to .env "
                "and fill in your API key."
            )
        base_url = os.getenv("BRIEFKLICK_BASE_URL", DEFAULT_BASE_URL)
        try:
            connect = float(os.getenv("BRIEFKLICK_TIMEOUT_CONNECT", DEFAULT_TIMEOUT[0]))
            read = float(os.getenv("BRIEFKLICK_TIMEOUT_READ", DEFAULT_TIMEOUT[1]))
        except ValueError as exc:
            raise ConfigurationError(f"Invalid timeout in env: {exc}") from exc

        return cls(api_key, base_url=base_url, timeout=(connect, read), **kwargs)

    def close(self) -> None:
        """Release the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "BriefKlickClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---------------------------------------------------------------- HTTP core

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        data: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        logger.debug(
            "BriefKlick %s %s data_keys=%s file_keys=%s",
            method,
            endpoint,
            sorted(data) if data else [],
            sorted(files) if files else [],
        )
        try:
            response = self._session.request(
                method,
                url,
                data=data,
                files=files,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError_(
                f"Request to {endpoint} timed out after {self.timeout}s."
            ) from exc
        except requests.ConnectionError as exc:
            raise APIError(
                f"Connection error talking to {url}: {exc}",
                status_code=0,
                endpoint=endpoint,
            ) from exc

        return self._handle_response(response, endpoint=endpoint)

    @staticmethod
    def _handle_response(response: requests.Response, *, endpoint: str) -> Any:
        # Try JSON first, fall back to plain text.
        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = response.text or None

        if response.ok:
            return payload

        status = response.status_code
        message = _extract_error_message(payload) or response.reason or "Unknown error"

        if status in (401, 403):
            raise AuthenticationError(
                f"Authentication failed: {message}",
                status_code=status,
                payload=payload,
                endpoint=endpoint,
            )
        # Only classify 4xx responses as "insufficient funds". A 5xx whose
        # error string happens to contain "insufficient" (e.g. "insufficient
        # replicas") is a server problem, not a balance problem.
        lower_message = str(message).lower()
        if status == 402 or (
            400 <= status < 500
            and ("insufficient" in lower_message or "guthaben" in lower_message)
        ):
            raise InsufficientFundsError(
                f"Insufficient account balance: {message}",
                status_code=status,
                payload=payload,
                endpoint=endpoint,
            )
        if 400 <= status < 500:
            raise ValidationError(
                f"API rejected request: {message}",
                status_code=status,
                payload=payload,
                endpoint=endpoint,
            )
        raise ServerError(
            f"BriefKlick server error: {message}",
            status_code=status,
            payload=payload,
            endpoint=endpoint,
        )

    @staticmethod
    def _expect_mapping(payload: Any, *, endpoint: str) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise APIError(
                f"Unexpected {endpoint} response: expected object, got {type(payload).__name__}.",
                status_code=200,
                payload=payload,
                endpoint=endpoint,
            )
        return payload

    # --------------------------------------------------------------- endpoints

    def get_balance(self) -> int:
        """Return the current account balance in Eurocents."""
        data = self._expect_mapping(self._request("GET", "/balance"), endpoint="/balance")
        try:
            return int(data["balance"])
        except (KeyError, TypeError, ValueError) as exc:
            raise APIError(
                f"Unexpected /balance response: {data!r}",
                status_code=200,
                payload=data,
                endpoint="/balance",
            ) from exc

    def get_pricing(self) -> dict[str, Any]:
        """Return the raw pricing table (values in Eurocents)."""
        return dict(self._expect_mapping(self._request("GET", "/pricing"), endpoint="/pricing"))

    def get_countries(self) -> Any:
        """Return the list of supported destination countries."""
        return self._request("GET", "/countries")

    def create_document(
        self,
        *,
        sender: str,
        recipient: Recipient | str,
        pdf: str | os.PathLike[str] | bytes | IO[bytes] | None = None,
        html: str | None = None,
        country_code: str | None = None,
        empty_page: bool = False,
    ) -> Document:
        """Upload a document. Returns a :class:`Document` with id + page count.

        Exactly one of ``pdf`` or ``html`` must be provided.

        ``pdf`` may be a path (``str``/``Path``), raw ``bytes``, or any
        readable binary file-like object.
        """
        # Use ``is not None`` rather than truthiness so that a caller passing
        # an empty ``bytes`` / empty ``html`` argument gets a clear validation
        # error from downstream checks instead of a misleading "provide one".
        if (pdf is not None) == (html is not None):
            raise ValueError("Provide exactly one of pdf= or html=.")

        receiver = recipient.format() if isinstance(recipient, Recipient) else str(recipient)
        if not receiver.strip():
            raise ValueError("recipient must produce a non-empty receiver string.")
        if receiver.count("\n") >= 6:
            raise ValueError("receiver may contain at most 6 lines (5 newlines).")

        form: dict[str, Any] = {
            "sender": sender,
            "receiver": receiver,
            "emptypage": 1 if empty_page else 0,
        }
        resolved_country = country_code or (
            recipient.country_code if isinstance(recipient, Recipient) else None
        )
        if resolved_country:
            form["countrycode"] = resolved_country.upper()

        files: dict[str, Any] | None = None
        opened_file: IO[bytes] | None = None
        try:
            if pdf is not None:
                pdf_bytes, filename = _coerce_pdf(pdf)
                if len(pdf_bytes) > MAX_PDF_BYTES:
                    raise ValueError(
                        f"PDF is {len(pdf_bytes)} bytes; BriefKlick limit is {MAX_PDF_BYTES}."
                    )
                files = {"pdf": (filename, pdf_bytes, "application/pdf")}
            else:
                form["html"] = html

            data = self._expect_mapping(
                self._request("POST", "/create", data=form, files=files),
                endpoint="/create",
            )
        finally:
            if opened_file is not None:
                opened_file.close()

        try:
            doc = Document(id=str(data["id"]), pages=int(data["pages"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise APIError(
                f"Unexpected /create response: {data!r}",
                status_code=200,
                payload=data,
                endpoint="/create",
            ) from exc
        if doc.pages > MAX_PAGES:
            logger.warning(
                "Document %s has %d pages (BriefKlick max is %d).",
                doc.id, doc.pages, MAX_PAGES,
            )
        return doc

    def preview(self, document_id: str) -> Preview:
        """Return a preview PDF for the given document id."""
        data = self._expect_mapping(
            self._request("POST", "/preview", data={"id": document_id}),
            endpoint="/preview",
        )
        try:
            pdf_bytes = base64.b64decode(data["file"], validate=True)
            pages = int(data["pages"])
        except (KeyError, TypeError, ValueError) as exc:
            raise APIError(
                f"Unexpected /preview response: {data!r}",
                status_code=200,
                payload=data,
                endpoint="/preview",
            ) from exc
        return Preview(pdf_bytes=pdf_bytes, pages=pages)

    def send(
        self,
        document_id: str,
        *,
        einschreiben: Einschreiben | int = Einschreiben.NORMAL,
        color: Color | int = Color.BW,
    ) -> Order:
        """Dispatch a previously created document (**chargeable!**)."""
        form = {
            "id": document_id,
            "einschreiben": int(einschreiben),
            "farbig": int(color),
        }
        data = self._expect_mapping(self._request("POST", "/send", data=form), endpoint="/send")
        try:
            return Order(id=int(data["id"]), price_cents=int(data["price"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise APIError(
                f"Unexpected /send response: {data!r}",
                status_code=200,
                payload=data,
                endpoint="/send",
            ) from exc

    def get_status(self, order_id: int) -> Status:
        """Look up status for a previously sent order."""
        data = self._expect_mapping(self._request("POST", "/status", data={"id": int(order_id)}), endpoint="/status")
        try:
            raw_status = int(data.get("status", 0))
        except (TypeError, ValueError) as exc:
            raise APIError(
                f"Unexpected /status response: {data!r}",
                status_code=200,
                payload=data,
                endpoint="/status",
            ) from exc
        if raw_status not in OrderStatus._value2member_map_:
            raise APIError(
                f"Unexpected /status response: unknown status code {raw_status}.",
                status_code=200,
                payload=data,
                endpoint="/status",
            )
        created_raw = data.get("created")
        created_dt: datetime | None = None
        if created_raw:
            try:
                created_dt = datetime.strptime(str(created_raw), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                created_dt = None
            else:
                # BriefKlick emits naive local time; attach the correct tz so
                # callers get an aware datetime suitable for comparisons.
                if _BRIEFKLICK_TZ is not None:
                    created_dt = created_dt.replace(tzinfo=_BRIEFKLICK_TZ)
        tracking = data.get("tracking") or None
        return Status(
            status=OrderStatus(raw_status),
            tracking=tracking,
            created=created_dt,
            raw=dict(data) if isinstance(data, dict) else {},
        )

    # ----------------------------------------------------------- high-level API

    def preview_letter(
        self,
        *,
        sender: str,
        recipient: Recipient | str,
        pdf_path: str | os.PathLike[str] | None = None,
        pdf_bytes: bytes | None = None,
        html: str | None = None,
        country_code: str | None = None,
        empty_page: bool = False,
    ) -> tuple[Document, Preview]:
        """Create a document and return its preview — **never sends, never charges**.

        This is the safest way to experiment with the API: both ``/create``
        and ``/preview`` are free, so you can iterate on sender text,
        recipient formatting, and letter content at zero cost. Returns
        ``(document, preview)``; write ``preview.pdf_bytes`` to disk and
        inspect it before any real ``send()`` call.

        Provide exactly one of ``pdf_path``, ``pdf_bytes`` or ``html``.
        """
        provided = sum(p is not None for p in (pdf_path, pdf_bytes, html))
        if provided != 1:
            raise ValueError("Provide exactly one of pdf_path, pdf_bytes, or html.")

        pdf_arg: Any = pdf_path if pdf_path is not None else pdf_bytes
        document = self.create_document(
            sender=sender,
            recipient=recipient,
            pdf=pdf_arg,
            html=html,
            country_code=country_code,
            empty_page=empty_page,
        )
        return document, self.preview(document.id)

    def send_letter(
        self,
        *,
        sender: str,
        recipient: Recipient | str,
        pdf_path: str | os.PathLike[str] | None = None,
        pdf_bytes: bytes | None = None,
        html: str | None = None,
        einschreiben: Einschreiben | int = Einschreiben.NORMAL,
        color: Color | int = Color.BW,
        country_code: str | None = None,
        empty_page: bool = False,
    ) -> Order:
        """Create and dispatch a letter in a single call.

        Provide exactly one of ``pdf_path``, ``pdf_bytes`` or ``html``.
        """
        provided = sum(p is not None for p in (pdf_path, pdf_bytes, html))
        if provided != 1:
            raise ValueError("Provide exactly one of pdf_path, pdf_bytes, or html.")

        pdf_arg: Any = pdf_path if pdf_path is not None else pdf_bytes
        document = self.create_document(
            sender=sender,
            recipient=recipient,
            pdf=pdf_arg,
            html=html,
            country_code=country_code,
            empty_page=empty_page,
        )
        return self.send(document.id, einschreiben=einschreiben, color=color)


# ---------------------------------------------------------------- utilities


def _coerce_pdf(value: Any) -> tuple[bytes, str]:
    """Turn path/bytes/file-like into (bytes, filename)."""
    if isinstance(value, (str, os.PathLike)):
        path = Path(os.fspath(value))
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")
        return path.read_bytes(), path.name
    if isinstance(value, (bytes, bytearray)):
        return bytes(value), "document.pdf"
    if hasattr(value, "read"):
        content = value.read()
        if not isinstance(content, (bytes, bytearray)):
            raise TypeError("File-like object must yield bytes, not str.")
        name = getattr(value, "name", "document.pdf") or "document.pdf"
        if isinstance(name, (str, os.PathLike)):
            name = Path(os.fspath(name)).name
        return bytes(content), str(name)
    raise TypeError(f"Unsupported pdf value: {type(value).__name__}")


def _extract_error_message(payload: Any) -> str | None:
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload.strip() or None
    if isinstance(payload, dict):
        for key in ("error", "message", "msg", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
