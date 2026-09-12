# SDK workflow

Use a project virtualenv or `uv`, not system-wide pip on managed Python. The package is `briefklick`; before publication a local source checkout can be used with `uv run --with /path/to/briefklick-python python your_script.py`.

## Stage 1: authorized preview upload only

```python
from briefklick import BriefKlickClient, Recipient

with BriefKlickClient.from_env() as client:
    recipient = Recipient(name="Peter Maier", street="Bergstraße 88",
                          postal_code="34533", city="Berlin")
    # Example preserves supplied values; do not silently rewrite the postcode.
    doc, preview = client.preview_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=recipient, pdf_path="invoice.pdf",
    )
    preview.save("preview.pdf")
    prices = client.get_pricing()  # values in Eurocents
    balance_cents = client.get_balance()
    print("Preview document:", doc.id, "Pages:", doc.pages, "Not sent.")
```

Show/inspect the preview, exact recipient, service and applicable price. Stop here until the user confirms those final details. Store the document ID with the local preview, not secrets. Changed content/recipient/service requires renewed preview/confirmation. HTML or pdf_bytes may replace pdf_path according to the installed SDK signature.

## Stage 2: only after explicit confirmation

```python
from briefklick import BriefKlickClient, Einschreiben

# confirmed_document_id comes from the shown, approved preview; never invent it.
with BriefKlickClient.from_env() as client:
    order = client.send(confirmed_document_id, einschreiben=Einschreiben.STANDARD)
    status = client.get_status(order.id)
    print("Order:", order.id, "Charged €:", order.price_eur, "Status:", status.status)
    # NEW = queued, SENT = dispatched, ERROR = failure; tracking when available.
```

Catch `AuthenticationError`, `InsufficientFundsError`, `ValidationError`, `ServerError`, and `TimeoutError_` explicitly. Auth errors need credential repair without exposing the key; insufficient funds need user top-up. Inspect validation payloads privately for invalid addresses/countries/files. A send server error/timeout may have created an order: reconcile first, do not put send inside a blind retry loop. An unavailable order ID is uncertainty, not permission to dispatch again.

No response state proves postal delivery. For unsupported Rückschein obtain the user's alternative choice before upload/send. File limits are 20 MB and 90 pages. Preview is free, not zero-disclosure-risk.
