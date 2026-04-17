import pytest

from briefklick import Recipient


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
        "Musterweg 1",
        "12345 Köln",
        "z.Hd. Frau Schmidt",
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
