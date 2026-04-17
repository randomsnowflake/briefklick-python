# Usage guide

This document shows end-to-end recipes. For a per-method reference see
[`api_reference.md`](api_reference.md).

## 0. Preview only (free, no balance required)

Lowest-risk way to interact with the API — `/create` and `/preview` are not
chargeable, so this works even with an empty account.

```python
from pathlib import Path
from briefklick import BriefKlickClient, Recipient

with BriefKlickClient.from_env() as c:
    doc, preview = c.preview_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=Recipient("Peter Maier", "Bergstraße 88", "34533", "Berlin"),
        pdf_path="invoice.pdf",
    )
    Path("preview.pdf").write_bytes(preview.pdf_bytes)
    print(f"Preview: {doc.pages} page(s). Nothing sent.")
```

## 1. One-shot: send a PDF as Einschreiben

```python
from briefklick import BriefKlickClient, Recipient, Einschreiben

with BriefKlickClient.from_env() as c:
    order = c.send_letter(
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
    print(order.id, f"{order.price_eur:.2f} €")
```

## 2. Two-step: preview before sending

Recommended when the PDF was auto-generated.

```python
from pathlib import Path
from briefklick import BriefKlickClient, Recipient, Einschreiben

with BriefKlickClient.from_env() as c:
    doc = c.create_document(
        sender="Max Mustermann",
        recipient=Recipient("Peter Maier", "Bergstraße 88", "34533", "Berlin"),
        pdf=Path("invoice.pdf"),
    )
    Path("preview.pdf").write_bytes(c.preview(doc.id).pdf_bytes)

    input(f"Review preview.pdf ({doc.pages} pages). Enter to send, Ctrl-C to abort…")
    order = c.send(doc.id, einschreiben=Einschreiben.STANDARD)
    print("Sent:", order.id)
```

## 3. Send HTML (no PDF dependency)

```python
from briefklick import BriefKlickClient, Recipient

html = """
<h1>Mahnung</h1>
<p>Sehr geehrter Herr Maier,</p>
<p>ausstehend: 199,99 €</p>
"""

with BriefKlickClient.from_env() as c:
    recipient = Recipient(
        name="Peter Maier",
        street="Bergstraße 88",
        postal_code="34533",
        city="Berlin",
    )
    doc = c.create_document(
        sender="Acme GmbH · Musterweg 1 · 10115 Berlin",
        recipient=recipient,
        html=html,
    )
    order = c.send(doc.id)
```

## 4. Track an order

```python
status = client.get_status(order.id)
print(status.status.name, status.tracking, status.created)

if status.is_sent and status.tracking:
    print(f"Track at deutschepost.de with {status.tracking}")
```

## 5. Balance & pricing

```python
print("Balance €:", client.get_balance() / 100)
print("Prices:", client.get_pricing())
```

## 6. Handling ambiguous send failures safely

```python
from briefklick import ServerError, TimeoutError_, InsufficientFundsError, AuthenticationError

try:
    order = client.send_letter(...)
except (ServerError, TimeoutError_):
    # Do NOT blindly retry send_letter(): without idempotency keys this can
    # create duplicate physical letters and duplicate charges.
    # Reconcile manually first: check BriefKlick dashboard / support or verify
    # whether the order appeared before sending again.
    raise
except (AuthenticationError, InsufficientFundsError):
    raise  # user/account errors need intervention, not retries
```

## 7. International mail

```python
from briefklick import Recipient

recipient = Recipient(
    name="Anna Smith",
    street="5 Rue de la Paix",
    postal_code="75002",
    city="Paris",
    country_code="FR",
)
# country code is attached to /create and rendered on the last address line
```

Run `client.get_countries()` to retrieve the current supported-country list.

## 8. Custom session (retries, proxies, corporate CA)

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from briefklick import BriefKlickClient

session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])),
)
client = BriefKlickClient.from_env(session=session)
```
