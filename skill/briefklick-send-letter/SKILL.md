---
name: briefklick-send-letter
description: Use when the user asks to send a physical letter in Germany (or to a German address) programmatically — phrasings include "send a letter to", "Brief schicken", "Einschreiben", "send this PDF as registered mail", or mentions attaching a PDF for postal delivery. Wraps the BriefKlick v2 API via the `briefklick` Python package.
---

# briefklick-send-letter

Send a real, physical letter via the [BriefKlick](https://www.briefklick.de/)
service. BriefKlick prints, encloses, franks, and posts the PDF on behalf of
the user.

## When to use

- User asks to "send a letter", "Brief schicken", "verschicken per Post", or
  names a recipient + German address.
- User mentions "Einschreiben", "Einwurf", "Einschreiben mit Rückschein".
- User wants to mail an attached PDF (invoice, Mahnung, Kündigung).
- User asks for postal send status, tracking, balance, or price list.

**Do NOT use** for:
- Email or digital delivery — use a mail client instead.
- Countries the BriefKlick `/countries` endpoint does not list.
- Sandbox / test runs — the BriefKlick API has **no sandbox**, every send is
  real and billed.

## Core safety rules

1. **Every `send()` call is chargeable.** Never call it speculatively.
2. **Preview first when content is not trivially obvious** — call
   `client.preview(doc.id)` and show the rendered PDF to the user before
   `client.send(doc.id, ...)`.
3. **Confirm with the user** before `send()` when:
   - the recipient/address was inferred from an ambiguous message, or
   - the Einschreiben mode was inferred, or
   - the balance is low (`client.get_balance()` returns < 1000 cents).
4. **Never hard-code the API key.** Rely on `.env` / `BRIEFKLICK_API_KEY`.
5. "**Einschreiben mit Rückschein**" is **not supported** by the API.
   If the user asks for it, explain this and suggest `Einschreiben.STANDARD`
   (signature required) — or stop and ask.

## Quick reference

### Mapping user phrasing → `Einschreiben`

| User says                                           | Use                         |
|-----------------------------------------------------|-----------------------------|
| "normal", "regular letter", "Brief", nothing said   | `Einschreiben.NORMAL` (0)   |
| "Einwurf", "Einwurf-Einschreiben"                   | `Einschreiben.EINWURF` (1)  |
| "Einschreiben", "registered mail", "per Einschreiben", "mit Unterschrift" | `Einschreiben.STANDARD` (2) |
| "Einschreiben mit Rückschein", "return receipt"     | **Not supported.** Ask user; closest is `STANDARD`. |

### Mapping natural-language address → `Recipient`

Given input like:

> send a letter to Peter Maier in 34533 Berlin, Bergstraße 88 with attached
> invoice.pdf as Einschreiben

Parse:
- **Name** → `"Peter Maier"`
- **Street** → `"Bergstraße 88"`
- **Postal code** → `"34533"` (5 digits, leading zero preserved)
- **City** → `"Berlin"`
- **Country** → default `"DE"` unless one is named

```python
Recipient(name="Peter Maier", street="Bergstraße 88",
          postal_code="34533", city="Berlin")
```

Keep the user's exact spelling (umlauts, ß) — the PDF will render it.

## Implementation

### Dependencies

The host project is expected to have `briefklick` installed. If not:

```bash
pip install briefklick
# or, from the source repo:
pip install -e path/to/briefklick-python
```

### Minimal send (one call)

```python
from briefklick import BriefKlickClient, Einschreiben, Recipient

with BriefKlickClient.from_env() as client:
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
    print(f"Sent! Order #{order.id}, charged {order.price_eur:.2f} €")
```

### Safer: preview → confirm → send

Use this when the letter content is generated or the request is ambiguous.

```python
from pathlib import Path
from briefklick import BriefKlickClient, Einschreiben, Recipient

with BriefKlickClient.from_env() as client:
    recipient = Recipient(
        name="Peter Maier",
        street="Bergstraße 88",
        postal_code="34533",
        city="Berlin",
    )

    doc = client.create_document(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=recipient,
        pdf=Path("invoice.pdf"),
    )

    Path("preview.pdf").write_bytes(client.preview(doc.id).pdf_bytes)
    # show preview.pdf to user, wait for explicit confirmation
    order = client.send(doc.id, einschreiben=Einschreiben.STANDARD)
    print("Order:", order.id, "Price €:", order.price_eur)
```

### Check status / tracking

```python
status = client.get_status(order.id)
# status.status ∈ {OrderStatus.NEW, SENT, ERROR}
# status.tracking is the Einschreiben tracking code when SENT
```

### Check balance / pricing

```python
balance_cents = client.get_balance()
prices = client.get_pricing()     # dict, values in Eurocents
```

## Error handling

Catch explicitly — don't swallow:

```python
from briefklick import (
    AuthenticationError, InsufficientFundsError,
    ValidationError, ServerError, TimeoutError_,
)

try:
    order = client.send_letter(...)
except InsufficientFundsError:
    # Tell the user to top up at briefklick.de
    ...
except AuthenticationError:
    # BRIEFKLICK_API_KEY is wrong / revoked
    ...
except ValidationError as e:
    # Address, file size, country code, etc. Inspect e.payload
    ...
except (ServerError, TimeoutError_):
    # Safe to retry with exponential backoff (2, 4, 8 s)
    ...
```

## Common mistakes

| Mistake                                                | Fix                                           |
|--------------------------------------------------------|-----------------------------------------------|
| Calling `send()` without user confirmation             | Use `preview()` + confirm prompt              |
| Reading the API key from `input()` or a string literal | Use `BriefKlickClient.from_env()`             |
| Treating `Einschreiben.STANDARD` as Rückschein         | There is no Rückschein; state this clearly    |
| Uploading PDF > 20 MB or > 90 pages                    | Pre-flight the file; client raises `ValueError` |
| Re-sending after a `ServerError` without backoff       | Exponential backoff, cap at 3 attempts        |
| Parsing "Berlin" postal code as `10115` when user wrote `34533` | Keep the postal code the user provided, do not "correct" it |

## Worked example — full LLM loop

User says:

> Send a letter to Peter Maier in 34533 Berlin, Bergstraße 88 with attached
> `invoice.pdf` as Einschreiben mit Rückschein.

Skill response:

1. Parse into a `Recipient` (see mapping above).
2. Detect "mit Rückschein" → **not supported**. Ask user whether
   `Einschreiben.STANDARD` (signature required) is acceptable; STOP if not.
3. Call `create_document` + `preview`.
4. Confirm `{pages, price_from_pricing, recipient}` with user.
5. Call `send(doc.id, einschreiben=Einschreiben.STANDARD)`.
6. Return `order.id`, `order.price_eur`, and any tracking from
   `get_status(order.id)` (polled after a short delay).

See `examples/natural_language_to_code.md` for the full prompt → code mapping.
