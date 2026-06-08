---
name: briefklick-send-letter
description: Use when the user asks to send OR preview a physical letter in Germany (or to a German address) programmatically — phrasings include "send a letter to", "Brief schicken", "Einschreiben", "send this PDF as registered mail", "preview what the letter would look like", or mentions attaching a PDF for postal delivery. Wraps the BriefKlick v2 API via the `briefklick` Python package.
---

# briefklick-send-letter

Send or preview a real, physical letter via the
[BriefKlick](https://www.briefklick.de/) service. BriefKlick prints, encloses,
franks, and posts the PDF on behalf of the user.

## Two modes: preview vs. send

| Mode       | Endpoints used            | Chargeable? | Needs account balance? |
|------------|---------------------------|-------------|------------------------|
| **Preview** | `/create` + `/preview`   | **No**      | **No**                 |
| **Send**    | `/create` + `/send`      | **Yes**     | Yes                    |

→ **Default to preview mode first.** It is free, works with a zero-balance
account, and returns the exact PDF that BriefKlick would dispatch. Always
offer it when the user is exploring, unsure, or has not explicitly said
"send/versenden/abschicken".

## When to use

- User asks to "send a letter", "Brief schicken", "verschicken per Post", or
  names a recipient + German address.
- User asks to "preview", "show me what it would look like", "rendere",
  "Vorschau", "dry-run", or "test" a letter.
- User mentions "Einschreiben", "Einwurf", "Einschreiben mit Rückschein".
- User wants to mail an attached PDF (invoice, Mahnung, Kündigung).
- User asks for postal send status, tracking, balance, or price list.

**Do NOT use** for:
- Email or digital delivery — use a mail client instead.
- Countries the BriefKlick `/countries` endpoint does not list.
- Actual sending without an account balance (preview still works fine).
  The BriefKlick API has **no sandbox** for `send` — every send is real
  and billed, but preview is safe.

## Core safety rules

1. **Every `send()` call is chargeable.** Never call it speculatively.
2. **Prefer `preview_letter()` over `send_letter()`.** Preview is free and
   returns the same rendered PDF; use it as your default unless the user
   has explicitly asked to send/dispatch/abschicken.
3. **When sending, preview first.** Call `preview_letter()` (or
   `create_document()` + `preview()`) and show the PDF to the user before
   `send()`.
4. **Confirm with the user** before `send()` when:
   - the recipient/address was inferred from an ambiguous message, or
   - the Einschreiben mode was inferred, or
   - the balance is low (`client.get_balance()` returns < 1000 cents).
5. **Never hard-code the API key.** Rely on `.env` / `BRIEFKLICK_API_KEY`.
6. "**Einschreiben mit Rückschein**" is **not supported** by the API.
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

The host project is expected to have `briefklick` installed. If not, avoid
system-wide `pip` on managed Python installs; use a project venv or `uv`.

```bash
# In a project virtualenv
python -m pip install briefklick

# One-off Hermes/agent execution after package publication
uv run --with briefklick python your_script.py

# From a source checkout before publication
uv run --with /path/to/briefklick-python python your_script.py
```

### Preview only (zero-risk, recommended first step)

Works even with a zero-balance account. Returns the **exact PDF** BriefKlick
would dispatch — inspect it before any real send.

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
        pdf_path="invoice.pdf",   # or html=..., or pdf_bytes=...
    )
    preview.save("preview.pdf")
    print(f"Preview: {doc.pages} page(s). Not sent, not charged.")
```

Use this when the user says "preview", "show me", "what would this look like",
or when you need to confirm details before the real send.

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

### Safer: preview → confirm → send (reuses the same document id)

Use this when the letter content is generated or the request is ambiguous.
This avoids a second `/create` round-trip by reusing `doc.id` from the
preview step.

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

    doc, preview = client.preview_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=recipient,
        pdf_path="invoice.pdf",
    )
    preview.save("preview.pdf")

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
    # Ambiguous for /send: do not blindly retry and risk duplicate mail.
    # Reconcile first, then decide whether a second send is acceptable.
    ...
```

## Common mistakes

| Mistake                                                | Fix                                           |
|--------------------------------------------------------|-----------------------------------------------|
| Calling `send_letter()` when user only asked to "test" | Use `preview_letter()` — free, no balance     |
| Calling `send()` without user confirmation             | Use `preview_letter()` + confirm prompt       |
| Reading the API key from `input()` or a string literal | Use `BriefKlickClient.from_env()`             |
| Treating `Einschreiben.STANDARD` as Rückschein         | There is no Rückschein; state this clearly    |
| Uploading PDF > 20 MB or > 90 pages                    | Pre-flight the file; client raises `ValueError` |
| Blindly retrying `send()` after `ServerError` / timeout | Treat it as ambiguous; reconcile before retry |
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
