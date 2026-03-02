"""
Claude API Client – Wraps Anthropic SDK for document analysis and offer generation.
"""

import os
import anthropic

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it before starting the server."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def extract_requirements_from_text(document_text: str) -> dict:
    """
    Send tender document text to Claude and extract structured requirements.
    Returns a dict with extracted door requirements.
    """
    client = get_client()

    system_prompt = """Du bist ein erfahrener Türen-Fachberater der Frank Türen AG in der Schweiz.
Deine Aufgabe ist es, Ausschreibungsdokumente zu analysieren und die genauen Türanforderungen
strukturiert zu extrahieren.

Extrahiere alle Türpositionen mit folgenden Informationen (falls vorhanden):
- position: Positions-Nummer oder Bezeichnung
- menge: Anzahl der Türen
- tuertyp: Art der Tür (z.B. Stahltür, Holztür, Alutür, Brandschutztür, etc.)
- breite: Breite in mm
- hoehe: Höhe in mm
- brandschutz: Brandschutzklasse (z.B. T30, T60, T90, EI30, EI60, EI90, EI120)
- schallschutz: Schalldämmmaß in dB (z.B. Rw=32dB)
- einbruchschutz: Widerstandsklasse (z.B. RC2, RC3, RC4, WK2, WK3)
- verglasung: Verglasungsanteil oder -typ
- oberflaechenbehandlung: Farbe/Beschichtung/Pulverbeschichtung
- zubehör: Türbeschläge, Schlösser, Schließer, etc.
- besonderheiten: Weitere Anforderungen

Antworte NUR mit einem validen JSON-Objekt in folgendem Format:
{
  "projekt": "Projektname falls erkennbar",
  "auftraggeber": "Auftraggeber falls erkennbar",
  "positionen": [
    {
      "position": "1.1",
      "beschreibung": "Kurzbeschreibung",
      "menge": 2,
      "einheit": "Stk",
      "tuertyp": "Stahltür",
      "breite": 900,
      "hoehe": 2100,
      "brandschutz": "T30",
      "schallschutz": null,
      "einbruchschutz": "RC2",
      "verglasung": null,
      "oberflaechenbehandlung": "RAL 7016",
      "zubehoer": "Türdrücker, Türschließer",
      "besonderheiten": ""
    }
  ],
  "gesamtanzahl_tueren": 2,
  "hinweise": "Weitere Hinweise aus dem Dokument"
}"""

    user_message = f"""Analysiere folgendes Ausschreibungsdokument und extrahiere alle Türanforderungen:

---DOKUMENT ANFANG---
{document_text[:12000]}
---DOKUMENT ENDE---

Extrahiere alle Türpositionen als strukturiertes JSON."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    import json
    return json.loads(response_text)


def generate_offer_text(
    requirements: dict,
    matched_products: list,
    project_info: dict,
) -> str:
    """
    Generate a formal offer text based on matched products.
    """
    client = get_client()

    import json
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%d.%m.%Y")
    valid_until = (datetime.now() + timedelta(days=90)).strftime("%d.%m.%Y")

    system_prompt = """Du bist ein professioneller Angebotsverfasser der Frank Türen AG, Buochs NW, Schweiz.
Erstelle formelle, professionelle Angebote auf Deutsch in schweizer Geschäftsstil.
Frank Türen AG fertigt hochwertige Stahl- und Metalltüren."""

    user_message = f"""Erstelle ein formelles Angebot basierend auf folgenden Informationen:

PROJEKTINFO:
{json.dumps(project_info, ensure_ascii=False, indent=2)}

ANFORDERUNGEN AUS AUSSCHREIBUNG:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

GEMATCHTE PRODUKTE:
{json.dumps(matched_products, ensure_ascii=False, indent=2)}

ANGEBOTSDATEN:
- Angebotsdatum: {today}
- Gültig bis: {valid_until}
- Zahlungsbedingungen: 30 Tage netto

Erstelle ein professionelles Angebot mit:
1. Kopfzeile (Frank Türen AG, Angebotsnummer, Datum, Gültigkeit)
2. Empfängeradresse (aus Projektinfo)
3. Betreff mit Projektnamen
4. Einleitungstext
5. Positionsliste (Pos.-Nr., Beschreibung, Menge, Einheit, Einzelpreis CHF [Preis basierend auf Produktkategorie], Gesamtpreis CHF)
6. Zwischensumme, MwSt (8.1%), Gesamtbetrag
7. Konditionen und Schlusstext
8. Unterschrift Frank Türen AG

Verwende realistische Preisangaben für Stahl/Metalltüren (Richtwerte: einfache Stahltür CHF 800-1500, Brandschutztür CHF 1200-3000, Sicherheitstür RC2 CHF 1500-4000 je nach Größe).
Markiere Preise als "Richtpreise exkl. Montage" wenn keine exakten Daten vorliegen."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text


def generate_gap_report_text(
    requirements: dict,
    unmatched_positions: list,
    project_info: dict,
) -> str:
    """
    Generate a gap report for positions that could not be matched.
    """
    client = get_client()

    import json

    system_prompt = """Du bist ein technischer Berater der Frank Türen AG.
Erstelle professionelle Gap-Reports auf Deutsch, die fehlende Produkte und mögliche Alternativen aufzeigen."""

    user_message = f"""Erstelle einen Gap-Report für nicht erfüllbare Anforderungen:

PROJEKT: {json.dumps(project_info, ensure_ascii=False, indent=2)}

NICHT ERFÜLLBARE POSITIONEN:
{json.dumps(unmatched_positions, ensure_ascii=False, indent=2)}

ALLE ANFORDERUNGEN:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

Erstelle einen detaillierten Gap-Report mit:
1. Zusammenfassung: X von Y Positionen nicht erfüllbar
2. Für jede nicht erfüllbare Position:
   - Anforderung (was wurde gefordert)
   - Grund (warum nicht erfüllbar)
   - Empfehlung (Sonderanfertigung / alternative Spezifikation / Lieferantenpartner)
3. Handlungsempfehlungen
4. Nächste Schritte"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text
