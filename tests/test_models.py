from pathlib import Path

import pytest

from briefklick import Preview, Recipient


def test_recipient_formats_standard_german_address() -> None:
    r = Recipient(
        name="Peter Maier",
        street="Bergstraße 88",
        postal_code="34533",
        city="Berlin",
    )
    assert r.format() == "Peter Maier\nBergstraße 88\n34533 Berlin"


def test_recipient_appends_country_for_non_de() -> None:
    r = Recipient(
        name="John Doe",
        street="123 Main St",
        postal_code="10001",
        city="New York",
        country_code="us",
    )
    assert r.format().splitlines()[-1] == "US"


def test_recipient_includes_address_line2_and_extras() -> None:
    r = Recipient(
        name="Acme AG",
        address_line2="Abt. Buchhaltung",
        street="Musterweg 1",
        postal_code="12345",
        city="Köln",
        extra_lines=("z.Hd. Frau Schmidt",),
    )
    lines = r.format().splitlines()
    assert lines == [
        "Acme AG",
        "Abt. Buchhaltung",
        "z.Hd. Frau Schmidt",
        "Musterweg 1",
        "12345 Köln",
    ]


def test_recipient_rejects_more_than_six_lines() -> None:
    with pytest.raises(ValueError):
        Recipient(
            name="A",
            address_line2="B",
            street="C",
            postal_code="1",
            city="D",
            extra_lines=("E", "F", "G"),  # would be 7 lines
            country_code="DE",
        ).format()


def test_recipient_from_lines_roundtrip() -> None:
    r = Recipient.from_lines(
        "Peter Maier",
        ["c/o Hans", "Bergstraße 88", "34533 Berlin"],
    )
    assert "34533 Berlin" in r.format()
    assert "c/o Hans" in r.format()


def test_recipient_from_lines_preserves_multiple_prefix_lines() -> None:
    r = Recipient.from_lines(
        "Acme AG",
        ["Abt. Buchhaltung", "z.Hd. Frau Schmidt", "Musterweg 1", "12345 Köln"],
    )
    assert r.format().splitlines() == [
        "Acme AG",
        "Abt. Buchhaltung",
        "z.Hd. Frau Schmidt",
        "Musterweg 1",
        "12345 Köln",
    ]


def test_recipient_from_lines_roundtrips_international_addresses() -> None:
    original = Recipient(
        name="Acme AG",
        street="Musterweg 1",
        postal_code="1010",
        city="Wien",
        country_code="AT",
    )
    reconstructed = Recipient.from_lines(
        original.name,
        original.format().splitlines()[1:],
        country_code="AT",
    )
    assert reconstructed == original


def test_recipient_from_lines_requires_postal_code_and_city() -> None:
    with pytest.raises(ValueError):
        Recipient.from_lines("Acme AG", ["Musterweg 1", "Berlin"])


def test_recipient_from_lines_strips_extra_whitespace_around_city() -> None:
    """Multiple spaces between PLZ and city must not bleed into city/postal."""
    r = Recipient.from_lines(
        "Peter Maier",
        ["Bergstraße 88", "34533   Berlin"],
    )
    assert r.postal_code == "34533"
    assert r.city == "Berlin"
    # And formatting should round-trip cleanly without extra whitespace.
    assert r.format().splitlines()[-1] == "34533 Berlin"


def test_preview_save_writes_pdf_and_creates_parent_dirs(tmp_path: Path) -> None:
    preview = Preview(pdf_bytes=b"%PDF-1.4 preview", pages=1)

    output = preview.save(tmp_path / "nested" / "preview.pdf")

    assert output == tmp_path / "nested" / "preview.pdf"
    assert output.read_bytes() == b"%PDF-1.4 preview"
