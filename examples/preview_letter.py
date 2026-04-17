"""Preview a letter without sending it (free, no account balance required).

Usage:
    cp .env.example .env && $EDITOR .env
    python examples/preview_letter.py [path/to/letter.pdf]

If no PDF is passed, sends a small HTML body instead — handy for quickly
verifying your API key + address formatting from a zero-balance account.
"""

from __future__ import annotations

import sys
from pathlib import Path

from briefklick import BriefKlickClient, Recipient


def main(pdf_path: str | None) -> int:
    recipient = Recipient(
        name="Peter Maier",
        street="Bergstraße 88",
        postal_code="34533",
        city="Berlin",
    )

    with BriefKlickClient.from_env() as client:
        print(f"Balance: {client.get_balance() / 100:.2f} €")

        kwargs: dict = {
            "sender": "Max Mustermann · Musterweg 1 · 10115 Berlin",
            "recipient": recipient,
        }
        if pdf_path:
            kwargs["pdf_path"] = pdf_path
        else:
            kwargs["html"] = (
                "<h1>Preview test</h1>"
                "<p>This letter is only rendered for preview — nothing is sent.</p>"
            )

        doc, preview = client.preview_letter(**kwargs)
        out = Path("preview.pdf")
        out.write_bytes(preview.pdf_bytes)
        print(
            f"✅ Preview ready: {out} ({len(preview.pdf_bytes)} bytes, "
            f"{preview.pages} page(s), doc={doc.id})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) >= 2 else None))
