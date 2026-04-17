# API reference

All imports live on the top-level package:

```python
from briefklick import (
    BriefKlickClient,
    Recipient, Document, Order, Status, Preview,
    Einschreiben, Color, OrderStatus,
    BriefKlickError, ConfigurationError,
    APIError, AuthenticationError,
    InsufficientFundsError, ValidationError, ServerError,
    TimeoutError_,
)
```

## `BriefKlickClient`

### `BriefKlickClient(api_key, *, base_url=..., timeout=(10, 60), session=None, user_agent=...)`

Direct constructor. Prefer `from_env()` unless you need tight control.

### `BriefKlickClient.from_env(*, env_file=None, **kwargs) -> BriefKlickClient`

Reads configuration from environment / `.env` file:

| Variable                      | Required | Default                        |
|-------------------------------|----------|--------------------------------|
| `BRIEFKLICK_API_KEY`          | yes      | —                              |
| `BRIEFKLICK_BASE_URL`         | no       | `https://api.briefklick.de/v2` |
| `BRIEFKLICK_TIMEOUT_CONNECT`  | no       | `10`                           |
| `BRIEFKLICK_TIMEOUT_READ`     | no       | `60`                           |

Raises `ConfigurationError` if the API key is missing.

### Endpoints

| Method                                                                   | Wraps         |
|--------------------------------------------------------------------------|---------------|
| `get_balance() -> int`                                                   | `GET /balance`   |
| `get_pricing() -> dict`                                                  | `GET /pricing`   |
| `get_countries() -> Any`                                                 | `GET /countries` |
| `create_document(*, sender, recipient, pdf=None, html=None, country_code=None, empty_page=False) -> Document` | `POST /create`   |
| `preview(document_id) -> Preview`                                        | `POST /preview`  |
| `send(document_id, *, einschreiben=NORMAL, color=BW) -> Order`           | `POST /send`     |
| `get_status(order_id) -> Status`                                         | `POST /status`   |
| `preview_letter(*, sender, recipient, pdf_path \| pdf_bytes \| html, country_code=None, empty_page=False) -> (Document, Preview)` | `/create` + `/preview` (free) |
| `send_letter(*, sender, recipient, pdf_path \| pdf_bytes \| html, einschreiben=NORMAL, color=BW, country_code=None, empty_page=False) -> Order` | `/create` + `/send` |

Also supports context-manager usage (`with BriefKlickClient(...) as c:`).

### Constraints enforced client-side

- PDF size ≤ **20 MB** (BriefKlick limit)
- Page count warned when > **90 pages**
- `receiver` string ≤ **6 lines** (enforced in `Recipient.format()` and
  `create_document`)

## Dataclasses

### `Recipient`

```python
Recipient(
    name: str,
    street: str,
    postal_code: str,
    city: str,
    country_code: str = "DE",
    address_line2: str | None = None,
    extra_lines: tuple[str, ...] = (),
)
```

- `.format() -> str` — builds the multi-line receiver string BriefKlick expects
- `.from_lines(name, lines, country_code="DE")` — parse pre-formatted addresses

### `Document(id: str, pages: int)`

Result of `/create`.

### `Order(id: int, price_cents: int)`

Result of `/send`.

- `.price_eur -> float` — convenience property.

### `Status(status, tracking, created, raw)`

Result of `/status`.

- `.is_sent -> bool`
- `.is_error -> bool`

### `Preview(pdf_bytes: bytes, pages: int)`

Result of `/preview`. `pdf_bytes` is already base64-decoded — write straight
to disk.

## Enums

### `Einschreiben(IntEnum)` — values for `POST /send`

| Member       | Value | Meaning                                          |
|--------------|------:|--------------------------------------------------|
| `NORMAL`     | 0     | Regular letter (no registered mail)              |
| `EINWURF`    | 1     | Einwurf-Einschreiben (mailbox, documented)       |
| `STANDARD`   | 2     | Standard-Einschreiben (signature required)       |

> The BriefKlick API does **not** offer a Rückschein flag.

### `Color(IntEnum)`

| Member  | Value |
|---------|------:|
| `BW`    | 0     |
| `COLOR` | 1     |

### `OrderStatus(IntEnum)`

| Member   | Value | Meaning                            |
|----------|------:|------------------------------------|
| `NEW`    | 0     | Order accepted, not yet processed  |
| `SENT`   | 1     | Letter dispatched                  |
| `ERROR`  | 2     | Processing failed                  |

## Exceptions

```
BriefKlickError
├── ConfigurationError             # missing/bad API key, bad env
├── TimeoutError_                  # connect/read timeout
└── APIError(status_code, payload, endpoint)
    ├── AuthenticationError        # 401, 403
    ├── InsufficientFundsError     # 402 or "Guthaben" in message
    ├── ValidationError            # 4xx otherwise
    └── ServerError                # 5xx
```

Every `APIError` exposes `.status_code`, `.payload`, and `.endpoint` so you
can log structured error reports.
