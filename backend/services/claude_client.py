"""
Claude API Client – Wraps Anthropic SDK for document analysis and offer generation.
"""

import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

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


def ai_match_products(
    requirement_text: str,
    requirement_fields: dict,
    candidates_text: str,
    candidate_indices: list[int],
    feedback_examples: list[dict],
) -> dict:
    """
    Stage 2: Use Claude to semantically match a requirement against pre-filtered candidates.
    Includes past corrections as few-shot learning examples.
    """
    client = get_client()

    # Build few-shot examples from feedback
    feedback_block = ""
    if feedback_examples:
        feedback_block = "\n\n## BISHERIGE KORREKTUREN (Lernbeispiele)\n"
        feedback_block += "Folgende Korrekturen wurden von Fachpersonal vorgenommen. Beachte diese Muster bei deiner Entscheidung:\n\n"
        for i, fb in enumerate(feedback_examples, 1):
            feedback_block += (
                f"Korrektur {i}:\n"
                f"  Anforderung: {fb.get('requirement_text', '')}\n"
                f"  FALSCHES Produkt: {fb.get('wrong_product', {}).get('product_summary', '?')}\n"
                f"  RICHTIGES Produkt: {fb.get('correct_product', {}).get('product_summary', '?')}\n"
            )
            if fb.get("user_note"):
                feedback_block += f"  Bemerkung: {fb['user_note']}\n"
            feedback_block += "\n"

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG in Buochs NW, Schweiz.
Du kennst das gesamte FTAG-Produktsortiment und hilfst beim Matching von Ausschreibungsanforderungen
zu den richtigen Produkten.

## DEINE AUFGABE
Gegeben eine Türanforderung aus einer Ausschreibung und eine Liste von Produktkandidaten aus dem
FTAG-Katalog, bestimme das beste passende Produkt.

## BEWERTUNGSKRITERIEN (Priorität)
1. Türtyp (Stahl, Holz, Alu) muss übereinstimmen
2. Brandschutzklasse (T30/EI30, T60/EI60, T90/EI90) muss mindestens erfüllt werden
3. Einbruchschutzklasse (RC2/WK2, RC3/WK3) muss mindestens erfüllt werden
4. Masse (Breite x Höhe) sollten passen oder anpassbar sein
5. Weitere Spezifikationen (Schallschutz, Verglasung, Oberfläche)

## REGELN
- T30 und EI30 sind gleichwertig, ebenso T60/EI60, T90/EI90
- RC und WK sind gleichwertig (RC2 = WK2, RC3 = WK3)
- Ein Produkt mit HÖHERER Klasse erfüllt NIEDRIGERE Anforderungen (T60 erfüllt T30)
- Wenn kein Kandidat passt, sage "unmatched" – erfinde keine Matches
- Bei Unsicherheit sage "partial" und erkläre warum
{feedback_block}
## ANTWORTFORMAT
Antworte NUR mit validem JSON:
{{
  "best_match_rank": <Nummer des besten Kandidaten (1-basiert) oder null>,
  "confidence": <0.0 bis 1.0>,
  "status": "matched" | "partial" | "unmatched",
  "reason": "<kurze deutsche Begründung, max 2 Sätze>",
  "alternative_ranks": [<bis zu 2 weitere Kandidaten-Nummern>]
}}"""

    user_message = f"""## ANFORDERUNG
{requirement_text}

Strukturierte Felder:
{json.dumps(requirement_fields, ensure_ascii=False, indent=2)}

## PRODUKTKANDIDATEN AUS FTAG-KATALOG
{candidates_text}

Welcher Kandidat passt am besten zur Anforderung?"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning(f"AI match returned invalid JSON: {response_text[:200]}")
        return {
            "best_match_index": candidate_indices[0] if candidate_indices else None,
            "best_match_rank": 1 if candidate_indices else None,
            "confidence": 0.3,
            "status": "partial",
            "reason": "KI-Antwort konnte nicht verarbeitet werden – Vorfilter-Ergebnis verwendet",
            "alternative_indices": [],
        }

    # Map rank back to DataFrame index
    best_rank = result.get("best_match_rank")
    best_index = None
    if best_rank and 1 <= best_rank <= len(candidate_indices):
        best_index = candidate_indices[best_rank - 1]

    alternative_indices = []
    for alt_rank in result.get("alternative_ranks", []):
        if isinstance(alt_rank, int) and 1 <= alt_rank <= len(candidate_indices):
            alternative_indices.append(candidate_indices[alt_rank - 1])

    return {
        "best_match_index": best_index,
        "best_match_rank": best_rank,
        "confidence": result.get("confidence", 0.0),
        "status": result.get("status", "unmatched"),
        "reason": result.get("reason", ""),
        "alternative_indices": alternative_indices,
    }
