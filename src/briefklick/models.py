"""Typed value objects used by the BriefKlick client."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
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
        lines.append(self.street.strip())
        lines.append(f"{self.postal_code.strip()} {self.city.strip()}".strip())
        for extra in self.extra_lines:
            if extra and extra.strip():
                lines.append(extra.strip())
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
        if len(parts) < 2:
            raise ValueError("Need at least a street line and a postal-code/city line.")
        # Assume the last line is "PLZ City"
        postal, _, city = parts[-1].partition(" ")
        street = parts[-2]
        address_line2 = parts[0] if len(parts) >= 3 else None
        extras = tuple(parts[1:-2]) if len(parts) > 3 else ()
        return cls(
            name=name,
            street=street,
            postal_code=postal,
            city=city,
            country_code=country_code,
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
