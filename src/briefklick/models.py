"""Typed value objects used by the BriefKlick client."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Iterable


class Einschreiben(IntEnum):
    """Registered-mail (Einschreiben) modes supported by the BriefKlick API.

    The BriefKlick v2 API only exposes three modes; there is currently
    no flag for *Rückschein* (return receipt). If you need a legally
    equivalent proof of delivery, ``STANDARD`` (signature required)
    is the closest option.
    """

    NORMAL = 0           # No registered mail
    EINWURF = 1          # Einwurf-Einschreiben (delivered to mailbox, documented)
    STANDARD = 2         # Standard-Einschreiben (signature required on delivery)


class Color(IntEnum):
    """Print color options."""

    BW = 0               # Schwarz-Weiß
    COLOR = 1            # Farbig


class OrderStatus(IntEnum):
    """Order status codes returned by ``/status``."""

    NEW = 0              # Accepted, not yet dispatched
    SENT = 1             # Letter has been sent
    ERROR = 2            # Processing failed


@dataclass(frozen=True)
class Recipient:
    """A letter recipient.

    BriefKlick accepts up to 6 lines of recipient text. This helper
    builds the classic German address layout:

        [Name]
        [AddressLine1]
        ([AddressLine2])
        [PostalCode] [City]

    For international mail pass a non-"DE" ``country_code`` and the
    country is appended as an extra line.
    """

    name: str
    street: str
    postal_code: str
    city: str
    country_code: str = "DE"
    address_line2: str | None = None
    extra_lines: tuple[str, ...] = field(default_factory=tuple)

    def format(self) -> str:
        """Return the BriefKlick-compatible multi-line receiver string."""
        lines: list[str] = [self.name.strip()]
        if self.address_line2:
            lines.append(self.address_line2.strip())
        for extra in self.extra_lines:
            if extra and extra.strip():
                lines.append(extra.strip())
        lines.append(self.street.strip())
        lines.append(f"{self.postal_code.strip()} {self.city.strip()}".strip())
        if self.country_code.upper() != "DE":
            # Append country in CAPS per Weltpostverein convention.
            lines.append(self.country_code.upper())
        if len(lines) > 6:
            raise ValueError(
                f"Recipient would produce {len(lines)} lines; BriefKlick allows max 6."
            )
        return "\n".join(lines)

    @classmethod
    def from_lines(cls, name: str, lines: Iterable[str], country_code: str = "DE") -> "Recipient":
        """Construct a Recipient by passing raw address lines (for edge cases)."""
        parts = [line.strip() for line in lines if line and line.strip()]
        normalized_country = country_code.upper()
        if normalized_country != "DE" and parts and parts[-1].upper() == normalized_country:
            parts = parts[:-1]
        if len(parts) < 2:
            raise ValueError("Need at least a street line and a postal-code/city line.")
        # Assume the last line is "PLZ City"
        postal, _, city = parts[-1].partition(" ")
        postal = postal.strip()
        city = city.strip()
        if not postal or not city:
            raise ValueError("Last line must contain both postal code and city.")
        street = parts[-2]
        prefix = parts[:-2]
        address_line2 = prefix[0] if prefix else None
        extras = tuple(prefix[1:])
        return cls(
            name=name,
            street=street,
            postal_code=postal,
            city=city,
            country_code=normalized_country,
            address_line2=address_line2,
            extra_lines=extras,
        )


@dataclass(frozen=True)
class Document:
    """A document that has been uploaded via ``/create``."""

    id: str
    pages: int


@dataclass(frozen=True)
class Order:
    """A dispatched letter (result of ``/send``)."""

    id: int
    price_cents: int

    @property
    def price_eur(self) -> float:
        return self.price_cents / 100.0


@dataclass(frozen=True)
class Status:
    """Status of a previously sent order."""

    status: OrderStatus
    tracking: str | None
    created: datetime | None
    raw: dict

    @property
    def is_sent(self) -> bool:
        return self.status == OrderStatus.SENT

    @property
    def is_error(self) -> bool:
        return self.status == OrderStatus.ERROR


@dataclass(frozen=True)
class Preview:
    """Preview of the composed document."""

    pdf_bytes: bytes
    pages: int

    def save(self, path: str | os.PathLike[str]) -> Path:
        """Write the preview PDF to ``path`` and return the resulting path."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.pdf_bytes)
        return target
