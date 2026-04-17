# briefklick-python

Idiomatic Python client for the [BriefKlick v2 API](https://api.briefklick.de/v2/swagger.json).
BriefKlick lets you send physical letters in Germany (and a few more countries)
from your code — you upload a PDF, they print, enclose, stamp, and drop it in
the post.

> ⚠️ **BriefKlick has no sandbox for `send()`.** Every send call is chargeable.
> But `/create` and `/preview` are **free** — `client.preview_letter(...)`
> returns the exact PDF BriefKlick would dispatch, works with a zero-balance
> account, and never spends money. Use it liberally to iterate on content.

## Features

- Plain `requests`-based, synchronous, 0 exotic dependencies
- Typed dataclasses (`Recipient`, `Document`, `Order`, `Status`, …) and
  `Einschreiben` / `Color` enums
- Clean exception hierarchy (`AuthenticationError`, `InsufficientFundsError`,
  `ValidationError`, `ServerError`, `TimeoutError_`)
- `.env` / environment-variable configuration
- Production timeouts (connect 10 s, read 60 s) — configurable
- `preview_letter(...)` zero-risk helper (free, no balance needed, returns
  the exact rendered PDF)
- `send_letter(...)` one-shot helper that chains `/create` + `/send`
- 39 unit tests, no live API calls required

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # during development
# or, once published:
# pip install briefklick
```

Supported Python: 3.9+. Only runtime deps are `requests` and `python-dotenv`.

## Configuration

Copy the example and fill in your key (get one from
[briefklick.de](https://www.briefklick.de/)):

```bash
cp .env.example .env
$EDITOR .env
```

```dotenv
BRIEFKLICK_API_KEY=your_api_key_here
# optional
# BRIEFKLICK_BASE_URL=https://api.briefklick.de/v2
# BRIEFKLICK_TIMEOUT_CONNECT=10
# BRIEFKLICK_TIMEOUT_READ=60
```

Never commit `.env`. The repository's `.gitignore` already excludes it.

## Quickstart

### 1. Preview (free, safe, recommended first step)

```python
from pathlib import Path
from briefklick import BriefKlickClient, Recipient

with BriefKlickClient.from_env() as client:
    doc, preview = client.preview_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="invoice.pdf",
    )
    Path("preview.pdf").write_bytes(preview.pdf_bytes)
    print(f"{doc.pages} page(s) rendered — nothing sent, nothing charged.")
```

### 2. Send

```python
from briefklick import BriefKlickClient, Recipient, Einschreiben

with BriefKlickClient.from_env() as client:
    print("Balance (cents):", client.get_balance())

    order = client.send_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="invoice.pdf",
        einschreiben=Einschreiben.STANDARD,  # signature-required registered mail
    )
    print(f"Sent! Order #{order.id}, charged {order.price_eur:.2f} €")
```

### Registered mail options

| Constant              | API value | Description                                              |
|-----------------------|-----------|----------------------------------------------------------|
| `Einschreiben.NORMAL`     | 0 | Regular letter, no tracking                               |
| `Einschreiben.EINWURF`    | 1 | Einwurf-Einschreiben — delivered to mailbox, documented  |
| `Einschreiben.STANDARD`   | 2 | Standard-Einschreiben — requires signature on delivery   |

> 📌 **"Einschreiben mit Rückschein"** (registered + return receipt card) is
> **not exposed** by the BriefKlick API. If you need physical proof of
> delivery, `Einschreiben.STANDARD` (signature required) is the closest
> available option.

### Previewing before sending

```python
from pathlib import Path

with BriefKlickClient.from_env() as c:
    doc = c.create_document(
        sender="...", recipient=recipient, pdf=Path("invoice.pdf"),
    )
    preview = c.preview(doc.id)
    Path("preview.pdf").write_bytes(preview.pdf_bytes)   # review this first!
    order = c.send(doc.id, einschreiben=Einschreiben.STANDARD)
```

### Polling status

```python
status = client.get_status(order.id)
if status.is_sent:
    print("Tracking:", status.tracking)
```

### Error handling

```python
from briefklick import (
    AuthenticationError, InsufficientFundsError,
    ValidationError, ServerError,
)

try:
    client.send_letter(...)
except InsufficientFundsError:
    ...  # top up the account
except AuthenticationError:
    ...  # bad / expired API key
except ValidationError as e:
    ...  # malformed payload, file too big, unknown country, ...
except ServerError:
    ...  # 5xx — safe to retry with exponential backoff
```

## Testing

```bash
.venv/bin/pytest                # 39 tests, 90% coverage, ~0.2s
.venv/bin/pytest --cov=briefklick
```

All tests are offline; `requests-mock` intercepts every HTTP call. No API key
is required to run them.

## Project layout

```
briefklick-python/
├── src/briefklick/          # package
│   ├── client.py            # BriefKlickClient
│   ├── models.py            # Recipient, Document, Order, Status, enums
│   ├── exceptions.py        # exception hierarchy
│   └── __init__.py
├── tests/                   # 37 tests, offline
├── docs/                    # extended examples and API reference
├── skill/                   # SKILL.md for LLM-driven letter sending
├── examples/                # runnable scripts
├── .env.example
├── pyproject.toml
└── README.md
```

## Docs

- [`docs/usage.md`](docs/usage.md) — extended examples, error handling recipes
- [`docs/api_reference.md`](docs/api_reference.md) — full public API reference
- [`skill/SKILL.md`](skill/SKILL.md) — LLM-facing skill for sending letters
  from natural language ("send a letter to Peter Maier in 34533 Berlin…").

## License

MIT.  See [`LICENSE`](LICENSE).
