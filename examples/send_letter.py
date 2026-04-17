"""Send a single PDF as Einschreiben.

Usage:
    cp .env.example .env && $EDITOR .env
    python examples/send_letter.py path/to/letter.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

from briefklick import BriefKlickClient, Einschreiben, Recipient


def main(pdf_path: str) -> int:
    recipient = Recipient(
        name="Peter Maier",
        street="Bergstraße 88",
        postal_code="34533",
        city="Berlin",
    )

    with BriefKlickClient.from_env() as client:
        balance_cents = client.get_balance()
        print(f"Current balance: {balance_cents / 100:.2f} €")

        doc = client.create_document(
            sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
            recipient=recipient,
            pdf=Path(pdf_path),
        )
        print(f"Created document {doc.id} ({doc.pages} page(s))")

        Path("preview.pdf").write_bytes(client.preview(doc.id).pdf_bytes)
        print("Wrote preview.pdf — inspect before sending.")

        confirm = input(f"Send {doc.pages}-page letter to {recipient.name}? [y/N] ")
        if confirm.strip().lower() != "y":
            print("Aborted.")
            return 1

        order = client.send(doc.id, einschreiben=Einschreiben.STANDARD)
        print(f"✅ Sent. Order #{order.id}, charged {order.price_eur:.2f} €")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: send_letter.py <path-to-pdf>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
