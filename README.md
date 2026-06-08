# briefklick-python

Idiomativer Python-Client für die [BriefKlick v2 API](https://api.briefklick.de/v2/swagger.json).
Mit BriefKlick kannst du physische Briefe aus Python heraus verschicken: PDF
oder HTML hochladen, BriefKlick druckt, kuvertiert, frankiert und gibt den Brief
in die Post.

> ℹ️ **Nicht mit BriefKlick verbunden.** Diese Bibliothek ist ein freier,
> unabhängiger Open-Source-Client. Sie ist kein offizielles Produkt von
> BriefKlick, wird nicht von BriefKlick empfohlen und steht in keiner Verbindung
> zum Betreiber. „BriefKlick“ wird hier nur verwendet, um die Drittanbieter-API
> zu beschreiben, mit der diese Bibliothek spricht. Alle Marken gehören ihren
> jeweiligen Inhabern.

> ⚠️ **BriefKlick hat keine Sandbox für `send()`.** Jeder echte Versand ist
> kostenpflichtig. `/create` und `/preview` sind dagegen **kostenlos**:
> `client.preview_letter(...)` liefert genau das PDF, das BriefKlick versenden
> würde, funktioniert auch ohne Guthaben und gibt nichts in Auftrag. Nutze die
> Vorschau großzügig, bevor du einen Brief wirklich versendest.

## Funktionen

- Schlanker synchroner Client auf Basis von `requests`, ohne exotische
  Laufzeit-Abhängigkeiten
- Typisierte Dataclasses (`Recipient`, `Document`, `Order`, `Status`, `Preview`)
  und Enums für `Einschreiben`, `Color` und `OrderStatus`
- Saubere Exception-Hierarchie (`AuthenticationError`, `InsufficientFundsError`,
  `ValidationError`, `ServerError`, `TimeoutError_`)
- Konfiguration über `.env` oder Umgebungsvariablen
- Produktionsfähige Timeouts: 10 s Verbindungsaufbau, 60 s Lesen, beides
  konfigurierbar
- `preview_letter(...)` als sicherer Null-Risiko-Flow: kostenlos, kein Guthaben
  nötig, kein Versand
- `send_letter(...)` als One-Shot-Helfer für `/create` + `/send`
- `Preview.save(...)` schreibt Vorschau-PDFs direkt auf die Platte
- 49 Offline-Unit-Tests, keine echten API-Aufrufe nötig
- PEP-561-Marker für Type Checker (`py.typed`)

## Installation

### Aus dem Repository entwickeln

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Direkt aus GitHub installieren

Solange das Paket noch nicht auf PyPI veröffentlicht ist:

```bash
pip install "briefklick @ git+https://github.com/randomsnowflake/briefklick-python.git"
```

Unterstützte Python-Versionen: **3.10+**. Laufzeit-Abhängigkeiten sind nur
`requests` und `python-dotenv`.

## Konfiguration

Kopiere die Beispiel-Konfiguration und trage deinen API-Key ein. Den Key bekommst
du in deinem Konto auf [briefklick.de](https://www.briefklick.de/).

```bash
cp .env.example .env
$EDITOR .env
```

```dotenv
BRIEFKLICK_API_KEY=dein_api_key_hier
# optional
# BRIEFKLICK_BASE_URL=https://api.briefklick.de/v2
# BRIEFKLICK_TIMEOUT_CONNECT=10
# BRIEFKLICK_TIMEOUT_READ=60
```

Committe niemals `.env`. Die Datei ist bereits in `.gitignore` ausgeschlossen.

## Schnellstart

### 1. Vorschau erzeugen, kostenlos und sicher

Das ist der empfohlene erste Schritt. Es wird **kein Brief versendet** und nichts
berechnet.

```python
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
        pdf_path="rechnung.pdf",
    )
    preview.save("vorschau.pdf")
    print(f"{doc.pages} Seite(n) gerendert, nichts versendet, nichts berechnet.")
```

### 2. Brief wirklich versenden

```python
from briefklick import BriefKlickClient, Einschreiben, Recipient

with BriefKlickClient.from_env() as client:
    print("Guthaben in Cent:", client.get_balance())

    order = client.send_letter(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=Recipient(
            name="Peter Maier",
            street="Bergstraße 88",
            postal_code="34533",
            city="Berlin",
        ),
        pdf_path="rechnung.pdf",
        einschreiben=Einschreiben.STANDARD,  # Einschreiben mit Unterschrift
    )
    print(f"Versendet: Auftrag #{order.id}, berechnet {order.price_eur:.2f} €")
```

## Einschreiben-Optionen

| Konstante | API-Wert | Bedeutung |
|---|---:|---|
| `Einschreiben.NORMAL` | 0 | Normaler Brief, ohne Sendungsverfolgung |
| `Einschreiben.EINWURF` | 1 | Einwurf-Einschreiben, Einwurf wird dokumentiert |
| `Einschreiben.STANDARD` | 2 | Standard-Einschreiben, Empfänger muss unterschreiben |

> 📌 **„Einschreiben mit Rückschein“** wird von der BriefKlick-API nicht
> angeboten. Wenn du einen Zustellnachweis brauchst, ist
> `Einschreiben.STANDARD` die nächstliegende verfügbare Option.

## Sicherer Versand-Workflow

Für automatisch generierte Briefe oder rechtlich relevante Schreiben solltest du
immer erst eine Vorschau erzeugen und erst danach versenden:

```python
from briefklick import BriefKlickClient, Einschreiben, Recipient

recipient = Recipient(
    name="Peter Maier",
    street="Bergstraße 88",
    postal_code="34533",
    city="Berlin",
)

with BriefKlickClient.from_env() as client:
    doc = client.create_document(
        sender="Max Mustermann · Musterweg 1 · 10115 Berlin",
        recipient=recipient,
        pdf="rechnung.pdf",
    )
    client.preview(doc.id).save("vorschau.pdf")

    # vorschau.pdf jetzt prüfen, erst danach wirklich versenden.
    order = client.send(doc.id, einschreiben=Einschreiben.STANDARD)
```

## Status und Tracking

```python
status = client.get_status(order.id)
if status.is_sent:
    print("Tracking:", status.tracking)
```

## Fehlerbehandlung

```python
from briefklick import (
    AuthenticationError,
    InsufficientFundsError,
    ServerError,
    TimeoutError_,
    ValidationError,
)

try:
    client.send_letter(...)
except InsufficientFundsError:
    ...  # Konto aufladen
except AuthenticationError:
    ...  # API-Key fehlt, ist falsch oder abgelaufen
except ValidationError as exc:
    ...  # falsche Adresse, PDF zu groß, unbekanntes Land, ...
except (ServerError, TimeoutError_):
    # Bei /send ist der Zustand unklar: Nicht blind erneut senden,
    # sonst riskierst du doppelte Briefe und doppelte Kosten.
    raise
```

## Entwicklung und Tests

Die Tests benötigen die optionale Dev-Abhängigkeit `requests-mock`. Installiere
das Paket deshalb im Entwicklungsmodus mit dem `dev`-Extra, bevor du `pytest`
ausführst:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

Optional mit Coverage:

```bash
python -m pytest --cov=briefklick
```

Ein nacktes `python -m pytest` in einer Umgebung ohne `.[dev]` schlägt fehl,
weil `requests-mock` nur für Tests gebraucht wird und nicht zu den
Laufzeit-Abhängigkeiten gehört.

Alle Tests laufen offline. `requests-mock` fängt sämtliche HTTP-Aufrufe ab, ein
API-Key ist für die Tests nicht nötig.

## Projektstruktur

```text
briefklick-python/
├── src/briefklick/          # Paket
│   ├── client.py            # BriefKlickClient
│   ├── models.py            # Recipient, Document, Order, Status, Preview, Enums
│   ├── exceptions.py        # Exception-Hierarchie
│   └── __init__.py
├── tests/                   # Offline-Tests
├── docs/                    # Erweiterte Beispiele und API-Referenz
├── skill/                   # LLM-Skill für Brief-Vorschau/-Versand
├── examples/                # Ausführbare Skripte
├── .env.example
├── pyproject.toml
└── README.md
```

## Dokumentation

- [`docs/usage.md`](docs/usage.md), ausführliche Beispiele und Rezepte zur
  Fehlerbehandlung
- [`docs/api_reference.md`](docs/api_reference.md), vollständige öffentliche
  API-Referenz
- [`skill/briefklick-send-letter/SKILL.md`](skill/briefklick-send-letter/SKILL.md),
  LLM-Skill für natürliche Sprache wie „schick einen Brief an Peter Maier in
  34533 Berlin …“

## Lizenz

MIT. Siehe [`LICENSE`](LICENSE).
