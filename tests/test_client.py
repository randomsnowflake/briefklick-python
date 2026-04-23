from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import requests

from briefklick import (
    APIError,
    AuthenticationError,
    BriefKlickClient,
    ConfigurationError,
    Einschreiben,
    InsufficientFundsError,
    OrderStatus,
    Recipient,
    ServerError,
    ValidationError,
)
from briefklick.exceptions import TimeoutError_


RECIPIENT = Recipient(
    name="Peter Maier",
    street="Bergstraße 88",
    postal_code="34533",
    city="Berlin",
)


def test_constructor_requires_api_key() -> None:
    with pytest.raises(ConfigurationError):
        BriefKlickClient("")


def test_sets_apikey_header(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", json={"balance": 12345})
    client.get_balance()
    assert mock_http.last_request.headers["apikey"] == "test-key"


# ---- GET /balance ----------------------------------------------------------


def test_get_balance_returns_int(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", json={"balance": 12345})
    assert client.get_balance() == 12345


def test_get_balance_rejects_malformed_success_payload(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", json=["oops"])
    with pytest.raises(APIError) as info:
        client.get_balance()
    assert info.value.endpoint == "/balance"
    assert "Unexpected /balance response" in str(info.value)


# ---- GET /pricing, /countries ---------------------------------------------


def test_get_pricing_returns_dict(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/pricing", json={"standard": 95, "einschreiben": 395})
    assert client.get_pricing() == {"standard": 95, "einschreiben": 395}


def test_get_countries(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/countries", json=["DE", "AT", "CH"])
    assert client.get_countries() == ["DE", "AT", "CH"]


# ---- POST /create ----------------------------------------------------------


def test_create_with_pdf_bytes_uploads_multipart(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/create", json={"id": "abc123", "pages": 2})

    doc = client.create_document(
        sender="Max Mustermann",
        recipient=RECIPIENT,
        pdf=b"%PDF-1.4 fake",
    )

    assert doc.id == "abc123"
    assert doc.pages == 2

    req = mock_http.last_request
    # multipart/form-data body should include the pdf part and form fields
    assert req.headers["Content-Type"].startswith("multipart/form-data")
    body = req.body
    if hasattr(body, "read"):
        body = body.read()
    assert b"filename=\"document.pdf\"" in body
    assert b"Max Mustermann" in body
    assert "Peter Maier".encode("utf-8") in body
    assert b"34533 Berlin" in body


def test_create_with_pdf_path(tmp_path, client, mock_http, base_url) -> None:
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    mock_http.post(f"{base_url}/create", json={"id": "zzz", "pages": 1})

    doc = client.create_document(
        sender="Max Mustermann",
        recipient=RECIPIENT,
        pdf=pdf,
    )

    assert doc.id == "zzz"
    body = mock_http.last_request.body
    if hasattr(body, "read"):
        body = body.read()
    assert b"filename=\"invoice.pdf\"" in body


def test_create_with_file_like(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/create", json={"id": "zzz", "pages": 1})
    buf = io.BytesIO(b"%PDF-1.4")
    buf.name = "spend.pdf"
    client.create_document(sender="S", recipient=RECIPIENT, pdf=buf)
    body = mock_http.last_request.body
    if hasattr(body, "read"):
        body = body.read()
    assert b"filename=\"spend.pdf\"" in body


def test_create_with_html(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/create", json={"id": "qqq", "pages": 1})
    client.create_document(
        sender="S",
        recipient=RECIPIENT,
        html="<p>Hi</p>",
    )
    # Not multipart; urlencoded body should carry html
    body = mock_http.last_request.text
    assert "html=%3Cp%3EHi%3C%2Fp%3E" in body
    assert "countrycode=DE" in body


def test_create_debug_logging_redacts_sender_and_receiver(client, mock_http, base_url, caplog) -> None:
    mock_http.post(f"{base_url}/create", json={"id": "qqq", "pages": 1})
    caplog.set_level(logging.DEBUG, logger="briefklick")
    client.create_document(
        sender="Max Mustermann",
        recipient=RECIPIENT,
        html="<p>Hi</p>",
    )
    assert "Max Mustermann" not in caplog.text
    assert "Peter Maier" not in caplog.text
    assert "data_keys=['countrycode', 'emptypage', 'html', 'receiver', 'sender']" in caplog.text


def test_create_requires_exactly_one_of_pdf_or_html(client) -> None:
    with pytest.raises(ValueError):
        client.create_document(sender="a", recipient=RECIPIENT)
    with pytest.raises(ValueError):
        client.create_document(sender="a", recipient=RECIPIENT, pdf=b"x", html="x")


def test_create_rejects_oversized_pdf(client) -> None:
    too_big = b"x" * (20 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        client.create_document(sender="a", recipient=RECIPIENT, pdf=too_big)


# ---- POST /send ------------------------------------------------------------


def test_send_registered_mail(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/send", json={"id": 55, "price": 395})
    order = client.send("abc123", einschreiben=Einschreiben.STANDARD)
    assert order.id == 55
    assert order.price_cents == 395
    assert order.price_eur == 3.95

    body = mock_http.last_request.text
    assert "einschreiben=2" in body
    assert "id=abc123" in body


def test_send_defaults_to_normal(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/send", json={"id": 1, "price": 95})
    client.send("abc")
    assert "einschreiben=0" in mock_http.last_request.text


# ---- POST /status ----------------------------------------------------------


def test_get_status_parses_tracking_and_date(client, mock_http, base_url) -> None:
    mock_http.post(
        f"{base_url}/status",
        json={
            "status": 1,
            "tracking": "RR 123 456 789 DE",
            "created": "2025-02-01 08:30:00",
        },
    )
    status = client.get_status(55)
    assert status.status == OrderStatus.SENT
    assert status.tracking == "RR 123 456 789 DE"
    assert status.created == datetime(2025, 2, 1, 8, 30, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    assert status.created is not None and status.created.tzinfo is not None
    assert status.is_sent is True


def test_get_status_handles_missing_tracking(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/status", json={"status": 0})
    s = client.get_status(1)
    assert s.tracking is None
    assert s.created is None
    assert s.status == OrderStatus.NEW


def test_get_status_rejects_unknown_status_code(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/status", json={"status": 99})
    with pytest.raises(APIError) as info:
        client.get_status(1)
    assert info.value.endpoint == "/status"
    assert "unknown status code 99" in str(info.value)


# ---- POST /preview ---------------------------------------------------------


def test_preview_decodes_base64_pdf(client, mock_http, base_url) -> None:
    pdf = b"%PDF-1.4 preview"
    mock_http.post(
        f"{base_url}/preview",
        json={"file": base64.b64encode(pdf).decode(), "pages": 1},
    )
    preview = client.preview("abc")
    assert preview.pdf_bytes == pdf
    assert preview.pages == 1


def test_preview_rejects_invalid_base64_pdf(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/preview", json={"file": "%%%not-base64%%%", "pages": 1})
    with pytest.raises(APIError) as info:
        client.preview("abc")
    assert info.value.endpoint == "/preview"
    assert "Unexpected /preview response" in str(info.value)


# ---- high-level send_letter -----------------------------------------------


def test_preview_letter_calls_create_then_preview_and_never_send(client, mock_http, base_url) -> None:
    pdf = b"%PDF-1.4 preview-only"
    mock_http.post(f"{base_url}/create", json={"id": "doc-prev", "pages": 2})
    mock_http.post(
        f"{base_url}/preview",
        json={"file": base64.b64encode(pdf).decode(), "pages": 2},
    )
    send_mock = mock_http.post(f"{base_url}/send", status_code=500)

    doc, preview = client.preview_letter(
        sender="Max Mustermann",
        recipient=RECIPIENT,
        html="<p>hi</p>",
    )

    assert doc.id == "doc-prev"
    assert doc.pages == 2
    assert preview.pages == 2
    assert preview.pdf_bytes == pdf
    assert send_mock.called is False, "preview_letter must not hit /send"

    urls = [req.url for req in mock_http.request_history]
    assert urls[0].endswith("/create")
    assert urls[1].endswith("/preview")


def test_preview_letter_requires_exactly_one_payload(client) -> None:
    with pytest.raises(ValueError):
        client.preview_letter(sender="s", recipient=RECIPIENT)
    with pytest.raises(ValueError):
        client.preview_letter(
            sender="s",
            recipient=RECIPIENT,
            pdf_bytes=b"x",
            html="y",
        )


def test_send_letter_chains_create_and_send(client, mock_http, base_url) -> None:
    mock_http.post(f"{base_url}/create", json={"id": "doc1", "pages": 1})
    mock_http.post(f"{base_url}/send", json={"id": 77, "price": 395})

    order = client.send_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=RECIPIENT,
        pdf_bytes=b"%PDF-1.4",
        einschreiben=Einschreiben.STANDARD,
    )
    assert order.id == 77
    assert order.price_cents == 395

    history = mock_http.request_history
    assert history[0].url.endswith("/create")
    assert history[1].url.endswith("/send")
    assert "id=doc1" in history[1].text


def test_send_letter_requires_exactly_one_payload(client) -> None:
    with pytest.raises(ValueError):
        client.send_letter(sender="s", recipient=RECIPIENT)
    with pytest.raises(ValueError):
        client.send_letter(
            sender="s",
            recipient=RECIPIENT,
            pdf_bytes=b"x",
            html="y",
        )


# ---- error handling --------------------------------------------------------


@pytest.mark.parametrize(
    "status_code,exc",
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (402, InsufficientFundsError),
        (400, ValidationError),
        (404, ValidationError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_error_status_maps_to_exception(client, mock_http, base_url, status_code, exc) -> None:
    mock_http.get(
        f"{base_url}/balance",
        status_code=status_code,
        json={"error": "boom"},
    )
    with pytest.raises(exc) as info:
        client.get_balance()
    assert info.value.status_code == status_code
    assert info.value.payload == {"error": "boom"}
    assert info.value.endpoint == "/balance"


def test_insufficient_funds_detected_in_body(client, mock_http, base_url) -> None:
    mock_http.post(
        f"{base_url}/send",
        status_code=400,
        json={"error": "Guthaben zu niedrig"},
    )
    with pytest.raises(InsufficientFundsError):
        client.send("abc")


def test_server_error_with_insufficient_in_message_is_not_insufficient_funds(
    client, mock_http, base_url
) -> None:
    """5xx errors must never be classified as InsufficientFundsError.

    Regression: the heuristic used to fire on any status code, so e.g. a
    503 whose body mentions "insufficient replicas" wrongly looked like a
    balance problem to the caller.
    """
    mock_http.get(
        f"{base_url}/balance",
        status_code=503,
        json={"error": "insufficient replicas"},
    )
    with pytest.raises(ServerError):
        client.get_balance()


def test_timeout_raises_timeout_error(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", exc=requests.Timeout)
    with pytest.raises(TimeoutError_):
        client.get_balance()


def test_connection_error_raises_api_error(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", exc=requests.ConnectionError("unreachable"))
    with pytest.raises(APIError) as info:
        client.get_balance()
    assert info.value.status_code == 0


def test_error_without_json_body(client, mock_http, base_url) -> None:
    mock_http.get(f"{base_url}/balance", status_code=500, text="proxy error")
    with pytest.raises(ServerError) as info:
        client.get_balance()
    assert "proxy error" in str(info.value)


# ---- env loading -----------------------------------------------------------


def test_from_env_reads_api_key(monkeypatch) -> None:
    monkeypatch.setenv("BRIEFKLICK_API_KEY", "envkey")
    monkeypatch.setenv("BRIEFKLICK_BASE_URL", "https://example.test/v2")
    c = BriefKlickClient.from_env()
    assert c.api_key == "envkey"
    assert c.base_url == "https://example.test/v2"


def test_from_env_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("BRIEFKLICK_API_KEY", raising=False)
    monkeypatch.setattr(
        "briefklick.client.load_dotenv",
        lambda *a, **k: False,
    )
    with pytest.raises(ConfigurationError):
        BriefKlickClient.from_env()


def test_context_manager_closes_session() -> None:
    with BriefKlickClient("k") as c:
        assert c._session is not None
    # second close is a no-op
    c.close()
