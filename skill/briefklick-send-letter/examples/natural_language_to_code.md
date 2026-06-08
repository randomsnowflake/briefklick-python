# Natural-language prompts → `briefklick` code

Use these as few-shot templates.

---

## Prompt 0 — preview only (free, default when user is exploring)

> Can you preview what a letter to Peter Maier in 34533 Berlin, Bergstraße 88
> with my invoice.pdf would look like?

```python
from pathlib import Path
from briefklick import BriefKlickClient, Recipient

with BriefKlickClient.from_env() as c:
    doc, preview = c.preview_letter(
        sender=SENDER,
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="invoice.pdf",
    )
    preview.save("preview.pdf")
    # `/create` + `/preview` are not chargeable — safe to run any time.
```

Use this when the user says "preview", "show me", "dry run", "Vorschau",
"test", "what would it look like", or has not explicitly asked to send.

## Prompt 1 — regular letter

> Send a letter to Peter Maier in 34533 Berlin, Bergstraße 88 with attached
> invoice.pdf.

```python
from briefklick import BriefKlickClient, Einschreiben, Recipient

with BriefKlickClient.from_env() as c:
    order = c.send_letter(
        sender="<SENDER LINE FROM USER CONTEXT>",
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="invoice.pdf",
        einschreiben=Einschreiben.NORMAL,
    )
```

## Prompt 2 — Einwurf-Einschreiben

> Kündigung.pdf als Einwurf-Einschreiben an Acme GmbH, Musterstraße 1, 50667 Köln

```python
recipient = Recipient(
    name="Acme GmbH",
    street="Musterstraße 1",
    postal_code="50667",
    city="Köln",
)
order = c.send_letter(
    sender=SENDER, recipient=recipient,
    pdf_path="Kündigung.pdf",
    einschreiben=Einschreiben.EINWURF,
)
```

## Prompt 3 — Standard-Einschreiben with preview

> Please send this PDF as registered mail to Anna Schmidt, Hauptstr. 5,
> 80331 München. I want to see a preview first.

```python
from pathlib import Path

doc = c.create_document(
    sender=SENDER,
    recipient=Recipient(
        name="Anna Schmidt",
        street="Hauptstr. 5",
        postal_code="80331",
        city="München",
    ),
    pdf=Path("letter.pdf"),
)

c.preview(doc.id).save("preview.pdf")
# -> show preview.pdf, obtain explicit user confirmation
order = c.send(doc.id, einschreiben=Einschreiben.STANDARD)
```

## Prompt 4 — "Einschreiben mit Rückschein"

> Mahnung.pdf an Peter Maier, Bergstraße 88, 34533 Berlin als
> Einschreiben mit Rückschein.

The BriefKlick API has no Rückschein flag. Ask the user before sending:

> The BriefKlick API does not support *Einschreiben mit Rückschein*.
> The closest option is **Einschreiben Standard** (signature required on
> delivery — the recipient must sign, but no physical return-receipt card).
> Shall I send it that way, or abort?

If user confirms → use `Einschreiben.STANDARD`. If not → do not send.

## Prompt 5 — HTML body, no PDF

> Send a short letter to Peter Maier (34533 Berlin, Bergstraße 88) saying
> "Dear Mr. Maier, ..." — no attachment.

```python
html = """
<p>Sehr geehrter Herr Maier,</p>
<p>...</p>
<p>Mit freundlichen Grüßen<br>Max Mustermann</p>
"""
order = c.send_letter(
    sender=SENDER,
    recipient=Recipient("Peter Maier", "Bergstraße 88", "34533", "Berlin"),
    html=html,
    einschreiben=Einschreiben.NORMAL,
)
```

## Prompt 6 — status check

> What happened to the letter I sent yesterday (order 12345)?

```python
status = c.get_status(12345)
print(status.status.name, status.tracking, status.created)
```

## Prompt 7 — balance

> How much credit is left on my BriefKlick account?

```python
print(f"{c.get_balance() / 100:.2f} €")
```
