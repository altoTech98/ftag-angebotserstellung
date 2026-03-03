"""
Claude API Client – Wraps Anthropic SDK for document analysis and offer generation.

NOTE: This module is no longer actively used. All AI functions have been moved to
local_llm.py (Ollama-based). This file is kept for optional backward compatibility.
The anthropic SDK is no longer a required dependency.
"""

import os
import re
import json
import logging

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if anthropic is None:
        raise ImportError(
            "anthropic SDK is not installed. Install it with: pip install anthropic\n"
            "Note: The application now uses Ollama (local_llm.py) by default."
        )
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it before starting the server."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _repair_json(text: str):
    """
    Attempt to repair common JSON issues from Claude responses:
    - Trailing commas before ] or }
    - Truncated JSON (close open brackets/braces)
    - Single-line comments
    """
    # Remove single-line comments (// ...)
    text = re.sub(r'//[^\n]*', '', text)

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Try parsing as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to fix truncated JSON by closing brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')

    # Find last complete object (ends with })
    last_complete = text.rfind('}')
    if last_complete > 0:
        truncated = text[:last_complete + 1]
        # Close any remaining open brackets
        truncated += ']' * max(0, truncated.count('[') - truncated.count(']'))
        truncated += '}' * max(0, truncated.count('{') - truncated.count('}'))
        # Remove trailing commas again after truncation
        truncated = re.sub(r',\s*([}\]])', r'\1', truncated)
        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

    # Last resort: add closing brackets
    fixed = text + '}' * max(0, open_braces) + ']' * max(0, open_brackets)
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
    return json.loads(fixed)


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


def _door_signature(door: dict) -> str:
    """Create a signature for grouping similar doors."""
    parts = [
        str(door.get("tuertyp") or ""),
        str(door.get("brandschutz") or ""),
        str(door.get("schallschutz") or ""),
        str(door.get("einbruchschutz") or ""),
        str(door.get("breite") or ""),
        str(door.get("hoehe") or ""),
        str(door.get("verglasung") or ""),
        str(door.get("oberflaechenbehandlung") or ""),
    ]
    return "|".join(parts).lower()


def normalize_door_positions(
    doors: list[dict],
    supplementary_context: str = "",
    unmapped_columns_sample: dict = None,
    on_progress=None,
) -> dict:
    """
    Use Claude to normalize/enrich ALREADY STRUCTURED door data from Excel parsing.

    Optimization: Groups identical door types together and normalizes only unique types,
    then applies normalized fields back to all doors in each group.

    Args:
        doors: Structured door dicts from excel_parser
        supplementary_context: Additional text from PDF specs
        unmapped_columns_sample: {column_name: [sample_values]} for unknown columns

    Returns:
        Standard requirements dict compatible with match_requirements_ai()
    """
    client = get_client()

    # --- Deduplication: group doors by type signature ---
    groups = {}  # signature -> [door_indices]
    representatives = {}  # signature -> first door (used for normalization)
    for i, door in enumerate(doors):
        sig = _door_signature(door)
        if sig not in groups:
            groups[sig] = []
            representatives[sig] = door
        groups[sig].append(i)

    unique_doors = list(representatives.values())
    logger.info(
        f"Door deduplication: {len(doors)} total → {len(unique_doors)} unique types "
        f"(saving {len(doors) - len(unique_doors)} duplicate normalizations)"
    )

    # Fast fallback normalization for structured Excel data (no Claude needed)
    # The Excel parser already provides structured fields; AI normalization is
    # only marginally better but adds minutes of processing time.
    if on_progress:
        on_progress(f"Normalisierung ({len(unique_doors)} Typen)...")
    all_fallback = _fallback_normalize(unique_doors)
    normalized_by_sig = {}
    for orig_door, fb in zip(unique_doors, all_fallback):
        sig = _door_signature(orig_door)
        normalized_by_sig[sig] = fb

    # Expand back to all doors, preserving original tuer_nr and menge
    all_positions = []
    for i, door in enumerate(doors):
        sig = _door_signature(door)
        template = normalized_by_sig.get(sig)
        if template:
            pos = dict(template)  # Copy normalized template
            pos["position"] = door.get("tuer_nr", template.get("position", ""))
            pos["menge"] = door.get("menge", 1)
            # Preserve room info
            if door.get("raum"):
                beschr = pos.get("beschreibung", "")
                pos["beschreibung"] = f"{beschr} (Raum: {door['raum']})" if beschr else f"Raum: {door['raum']}"
        else:
            # Fallback
            pos = _fallback_normalize([door])[0]
        all_positions.append(pos)

    # Build standard output format
    projekt = ""
    auftraggeber = ""
    if all_positions:
        first_nr = all_positions[0].get("position", "")
        if first_nr:
            projekt = f"Projekt (Türliste: {len(all_positions)} Positionen)"

    return {
        "projekt": projekt,
        "auftraggeber": auftraggeber,
        "positionen": all_positions,
        "gesamtanzahl_tueren": sum(p.get("menge", 1) for p in all_positions),
        "hinweise": f"Strukturiert aus Excel extrahiert ({len(doors)} Zeilen, "
                    f"{len(unique_doors)} unique Typen). "
                    + (f"PDF-Kontext: {len(supplementary_context)} Zeichen." if supplementary_context else ""),
    }


def _normalize_batch(
    client,
    doors: list[dict],
    supplementary_context: str,
    unmapped_columns_sample: dict | None,
) -> list[dict]:
    """Normalize a batch of doors via Claude."""

    # Build compact door data (exclude _raw_row and _merge_conflicts)
    compact_doors = []
    for d in doors:
        compact = {k: v for k, v in d.items() if not k.startswith("_") and v is not None}
        compact_doors.append(compact)

    doors_json = json.dumps(compact_doors, ensure_ascii=False, indent=1)

    context_block = ""
    if supplementary_context:
        context_block = f"\n\n## ZUSÄTZLICHER KONTEXT AUS PDF-SPEZIFIKATIONEN\n{supplementary_context[:8000]}\n"

    unmapped_block = ""
    if unmapped_columns_sample:
        unmapped_block = "\n\n## NICHT ZUGEORDNETE SPALTEN (Beispielwerte)\n"
        for col, values in list(unmapped_columns_sample.items())[:10]:
            unmapped_block += f"- {col}: {', '.join(str(v) for v in values[:5])}\n"
        unmapped_block += "\nFalls diese Spalten relevante Türdaten enthalten, integriere die Informationen.\n"

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG in Buochs NW, Schweiz.

## AUFGABE
Du erhältst BEREITS STRUKTURIERTE Türdaten aus einer Excel-Türliste. Deine Aufgabe ist NUR:
1. Werte normalisieren (z.B. "Stahl T30 1flg" → tuertyp="Stahltür", brandschutz="T30")
2. Fehlende Felder aus Beschreibung/Besonderheiten ableiten
3. Brandschutz standardisieren: T30→EI30, T60→EI60 etc. (bevorzuge EI-Format)
4. Einbruchschutz standardisieren: WK2→RC2, WK3→RC3 etc. (bevorzuge RC-Format)
5. Masse in mm sicherstellen
6. Zusatzinformationen aus dem PDF-Kontext einfliessen lassen

## WICHTIG
- Du EXTRAHIERST NICHT aus Rohdaten – die Daten sind bereits strukturiert!
- Verändere tuer_nr NICHT (das ist die Original-ID)
- Wenn ein Feld leer/null ist und du es nicht ableiten kannst, lasse es null
- Erstelle eine kurze beschreibung aus den vorhandenen Feldern
{context_block}{unmapped_block}
## ANTWORTFORMAT
Antworte NUR mit einem JSON-Array. Pro Tür ein Objekt im Standardformat:
[
  {{
    "position": "<tuer_nr>",
    "beschreibung": "<kurze Zusammenfassung>",
    "menge": <int>,
    "einheit": "Stk",
    "tuertyp": "<Stahltür|Holztür|Alutür|Brandschutztür|...>",
    "breite": <mm oder null>,
    "hoehe": <mm oder null>,
    "brandschutz": "<EI30|EI60|EI90|... oder null>",
    "schallschutz": "<Rw=32dB|... oder null>",
    "einbruchschutz": "<RC2|RC3|... oder null>",
    "verglasung": "<Beschreibung oder null>",
    "oberflaechenbehandlung": "<RAL xxxx|... oder null>",
    "zubehoer": "<Beschläge, Schliesser, etc. oder null>",
    "besonderheiten": "<Zusätzliche Anforderungen>"
  }}
]"""

    user_message = f"""Normalisiere folgende {len(doors)} Türpositionen:

{doors_json}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16384,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=180.0,  # 3 minute timeout per batch
        )

        response_text = message.content[0].text.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # Use robust JSON repair
        try:
            positions = _repair_json(response_text)
        except json.JSONDecodeError as je:
            logger.warning(f"JSON repair also failed: {je}. Response (first 500): {response_text[:500]}")
            return _fallback_normalize(doors)

        if not isinstance(positions, list):
            positions = [positions]

        # Ensure menge defaults
        for p in positions:
            if not p.get("menge"):
                p["menge"] = 1
            if not p.get("einheit"):
                p["einheit"] = "Stk"

        logger.info(f"Normalized batch: {len(doors)} doors → {len(positions)} positions via Claude")
        return positions

    except Exception as e:
        logger.warning(f"Claude normalization failed for batch ({len(doors)} doors): {e}")
        logger.info("Using fallback normalization for this batch")
        return _fallback_normalize(doors)


def _fallback_normalize(doors: list[dict]) -> list[dict]:
    """Convert structured door dicts to standard format without Claude."""
    positions = []
    for d in doors:
        parts = []
        if d.get("tuertyp"):
            parts.append(d["tuertyp"])
        if d.get("brandschutz"):
            parts.append(d["brandschutz"])
        if d.get("breite") and d.get("hoehe"):
            parts.append(f"{d['breite']}x{d['hoehe']}mm")

        positions.append({
            "position": d.get("tuer_nr", ""),
            "beschreibung": " ".join(parts) if parts else "Tür",
            "menge": d.get("menge", 1),
            "einheit": "Stk",
            "tuertyp": d.get("tuertyp"),
            "breite": d.get("breite"),
            "hoehe": d.get("hoehe"),
            "brandschutz": d.get("brandschutz"),
            "schallschutz": d.get("schallschutz"),
            "einbruchschutz": d.get("einbruchschutz"),
            "verglasung": d.get("verglasung"),
            "oberflaechenbehandlung": d.get("oberflaechenbehandlung"),
            "zubehoer": d.get("beschlaege"),
            "besonderheiten": d.get("besonderheiten", ""),
        })
    return positions


# ─────────────────────────────────────────────
# NEW: Category-aware AI matching functions
# ─────────────────────────────────────────────

def classify_door_categories(
    unique_doors: list[dict],
    available_categories: list[str],
) -> list[dict]:
    """
    Classify each unique door type into one of the FTAG product categories.
    Returns list of {"door_index": int, "category": str, "confidence": float}.
    """
    client = get_client()

    categories_str = ", ".join(available_categories)
    doors_block = ""
    for i, door in enumerate(unique_doors):
        parts = []
        for key in ["tuertyp", "brandschutz", "einbruchschutz", "schallschutz",
                     "breite", "hoehe", "verglasung", "beschlaege", "besonderheiten",
                     "fluegel_anzahl", "zargentyp", "beschreibung"]:
            val = door.get(key)
            if val:
                parts.append(f"{key}: {val}")
        # Also check raw row for extra context
        raw = door.get("_raw_row", {})
        if not parts and raw:
            for k, v in list(raw.items())[:5]:
                if v and str(v).strip() not in ("", "-"):
                    parts.append(f"{k}: {str(v)[:50]}")
        doors_block += f"\nTür {i}: {' | '.join(parts) if parts else 'keine Details'}"

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG.

## AUFGABE
Ordne jede Türanforderung einer FTAG-Produktkategorie zu.

## VERFÜGBARE KATEGORIEN
{categories_str}

## REGELN
- "Rahmentüre" = Standardtüren mit Stahlrahmen (häufigste Kategorie)
- "Zargentüre" = Türen mit separater Zarge/Umfassungszarge
- "Futtertüre" = Türen mit Futterrahmen/Blockfutter
- "Schiebetüre" = Schiebetüren
- "Festverglasung" = Feststehende Verglasungen ohne Türfunktion
- "Brandschutzvorhang" = Textilbasierte Brandschutzabschlüsse
- "Brandschutztor" = Grosse Brandschutztore (>3m)
- "Ganzglas Tür" = Vollglas-Türen
- "Pendeltüre" = Pendeltüren (beide Richtungen)
- "Vollwand" = Trennwände ohne Türfunktion
- Wenn unklar, wähle "Rahmentüre" als Standard

## ANTWORTFORMAT
JSON-Array:
[{{"door_index": 0, "category": "Rahmentüre", "confidence": 0.9}}, ...]"""

    user_message = f"""Klassifiziere folgende {len(unique_doors)} Türtypen:\n{doors_block}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=60.0,
        )

        response_text = message.content[0].text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        results = _repair_json(response_text)
        if not isinstance(results, list):
            results = [results]

        return results

    except Exception as e:
        logger.warning(f"Category classification failed: {e}")
        # Fallback: assign all to Rahmentüre
        return [{"door_index": i, "category": "Rahmentüre", "confidence": 0.3}
                for i in range(len(unique_doors))]


def match_main_products_batch(
    door_types: list[dict],
    products_text: str,
    category_name: str,
) -> list[dict]:
    """
    Match a batch of door types against products in a specific category.
    Returns list of match results per door type.
    """
    client = get_client()

    doors_block = ""
    for i, door in enumerate(door_types):
        parts = []
        for key in ["tuertyp", "brandschutz", "einbruchschutz", "schallschutz",
                     "breite", "hoehe", "verglasung", "oberflaechenbehandlung",
                     "besonderheiten", "fluegel_anzahl", "zargentyp",
                     "schloss_typ", "glas_typ", "tuerschliesser", "beschreibung"]:
            val = door.get(key)
            if val:
                parts.append(f"{key}: {val}")
        raw = door.get("_raw_row", {})
        if not parts and raw:
            for k, v in list(raw.items())[:8]:
                if v and str(v).strip() not in ("", "-"):
                    parts.append(f"{k}: {str(v)[:60]}")
        doors_block += f"\n\n### TÜR {i}:\n{chr(10).join(parts) if parts else 'keine Details'}"

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG in Buochs NW, Schweiz.

## AUFGABE
Matche jede Türanforderung gegen die Produkte der Kategorie "{category_name}".
Jedes Produkt ist als kompakte Zeile mit [Row-Nr] dargestellt.

## BEWERTUNGSKRITERIEN (Priorität)
1. Brandschutzklasse: EI30=T30, EI60=T60, EI90=T90 (höhere erfüllt niedrigere)
2. Widerstandsklasse: RC2=WK2, RC3=WK3 (höhere erfüllt niedrigere)
3. Anzahl Flügel: 1-flg / 2-flg muss passen
4. Türblatt-Art: muss zum Anforderungsprofil passen
5. Lichtmass: Kundenmasse müssen innerhalb max. Masse des Produkts liegen
6. Schallschutz: dB-Wert muss mindestens erreicht werden
7. Glasausschnitt: falls gefordert, muss Produkt dies unterstützen

## REGELN
- Wähle das BESTE passende Produkt (höchste Übereinstimmung)
- "machbar" = alle wesentlichen Anforderungen erfüllt
- "teilweise_machbar" = Hauptanforderungen erfüllt, Details unklar
- "nicht_machbar" = keine passende Produktlinie
- Gib den benötigten Zubehör-Typ an (Schloss, Glas, Schliessblech)
- Prüfe IMMER ob die Masse des Kunden innerhalb der max. Masse des Produkts liegen

## ANTWORTFORMAT
JSON-Array mit einem Objekt pro Tür:
[
  {{
    "door_index": 0,
    "status": "machbar",
    "matched_row": 42,
    "confidence": 0.92,
    "reason": "EI30 Rahmentüre 1-flg passt, Masse innerhalb Bereich",
    "zubehoer_bedarf": {{
      "schloss": "Panikschloss gefordert",
      "glas": "Glasausschnitt OG 30x30",
      "schliessblech": null
    }},
    "gap_hinweise": []
  }}
]"""

    user_message = f"""## PRODUKTE ({category_name})
{products_text}

## TÜRANFORDERUNGEN
{doors_block}

Matche jede Tür gegen die Produkte."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=120.0,
        )

        response_text = message.content[0].text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        results = _repair_json(response_text)
        if not isinstance(results, list):
            results = [results]

        return results

    except Exception as e:
        logger.error(f"Main product matching failed for {category_name}: {e}")
        return [{"door_index": i, "status": "nicht_machbar", "matched_row": None,
                 "confidence": 0.0, "reason": f"KI-Matching fehlgeschlagen: {str(e)[:100]}",
                 "zubehoer_bedarf": {}, "gap_hinweise": []}
                for i in range(len(door_types))]


def match_accessories_batch(
    requirements: list[dict],
    accessories_text: str,
    accessory_type: str,
) -> list[dict]:
    """
    Match accessory requirements against ZZ products.
    accessory_type: "Schloss", "Glas", or "Schliessblech"
    """
    client = get_client()

    reqs_block = ""
    for i, req in enumerate(requirements):
        desc = req.get("description", "")
        door_ref = req.get("door_ref", "")
        reqs_block += f"\n{i}. Tür {door_ref}: {desc}"

    type_context = {
        "Schloss": "Achte auf: Schlossart, Panikfunktion, Dornmass, 1-flg/2-flg Kompatibilität.",
        "Glas": "Achte auf: Brandschutzklasse des Glases, Schallschutz dB, Glasdicke.",
        "Schliessblech": "Achte auf: Widerstandsklasse (RC), Rahmen- vs Zargen-Variante.",
    }

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG.

## AUFGABE
Matche Zubehör-Anforderungen ({accessory_type}) gegen verfügbare FTAG-Produkte.

## HINWEISE
{type_context.get(accessory_type, "")}

## ANTWORTFORMAT
JSON-Array:
[
  {{
    "req_index": 0,
    "status": "matched" | "gap",
    "matched_row": 650,
    "reason": "Passend: Panikschloss Glutz mit SV-Funktion",
    "alternative_row": null
  }}
]"""

    user_message = f"""## VERFÜGBARE {accessory_type.upper()}-PRODUKTE
{accessories_text}

## ANFORDERUNGEN
{reqs_block}

Matche jede Anforderung."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=90.0,
        )

        response_text = message.content[0].text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        results = _repair_json(response_text)
        if not isinstance(results, list):
            results = [results]

        return results

    except Exception as e:
        logger.error(f"Accessory matching failed for {accessory_type}: {e}")
        return [{"req_index": i, "status": "gap", "matched_row": None,
                 "reason": f"KI-Matching fehlgeschlagen: {str(e)[:100]}"}
                for i in range(len(requirements))]


def ai_match_products_batch(
    positions_data: list[dict],
    feedback_examples: list[dict],
) -> list[dict]:
    """
    Batch matching: Match ALL positions in a single Claude call.
    Each entry in positions_data: {req_text, req_fields, candidates_text, candidate_indices}
    Returns list of match results (one per position).
    """
    client = get_client()

    # Build few-shot examples from feedback
    feedback_block = ""
    if feedback_examples:
        feedback_block = "\n\n## BISHERIGE KORREKTUREN & BESTÄTIGUNGEN (Lernbeispiele)\n"
        for i, fb in enumerate(feedback_examples, 1):
            fb_type = fb.get("type", "correction")
            if fb_type == "confirmation":
                feedback_block += (
                    f"Bestätigung {i}: Anforderung '{fb.get('requirement_text', '')}' "
                    f"→ RICHTIGES Produkt: {fb.get('confirmed_product', {}).get('product_summary', '?')}\n"
                )
            else:
                feedback_block += (
                    f"Korrektur {i}: Anforderung '{fb.get('requirement_text', '')}' "
                    f"→ FALSCH: {fb.get('wrong_product', {}).get('product_summary', '?')} "
                    f"→ RICHTIG: {fb.get('correct_product', {}).get('product_summary', '?')}"
                )
                if fb.get("user_note"):
                    feedback_block += f" (Bemerkung: {fb['user_note']})"
                feedback_block += "\n"

    # Build positions block
    positions_block = ""
    for i, pos_data in enumerate(positions_data):
        positions_block += f"\n### POSITION {i+1}: {pos_data['req_text']}\n"
        positions_block += f"Felder: {json.dumps(pos_data['req_fields'], ensure_ascii=False)}\n"
        positions_block += f"Kandidaten:\n{pos_data['candidates_text']}\n"

    system_prompt = f"""Du bist ein erfahrener Türen-Fachberater der Frank Türen AG in Buochs NW, Schweiz.

## AUFGABE
Matche ALLE folgenden Positionen aus einer Ausschreibung gegen die jeweiligen Produktkandidaten.

## BEWERTUNGSKRITERIEN (Priorität)
1. Türtyp (Stahl, Holz, Alu) muss übereinstimmen
2. Brandschutzklasse (T30/EI30, T60/EI60, T90/EI90) muss mindestens erfüllt werden
3. Einbruchschutzklasse (RC2/WK2, RC3/WK3) muss mindestens erfüllt werden
4. Masse (Breite x Höhe) sollten passen oder anpassbar sein
5. Weitere Spezifikationen (Schallschutz, Verglasung, Oberfläche)

## REGELN
- T30=EI30, T60=EI60, T90=EI90 (gleichwertig)
- RC2=WK2, RC3=WK3, RC4=WK4 (gleichwertig)
- HÖHERE Klasse erfüllt NIEDRIGERE (T60 erfüllt T30)
- Wenn kein Kandidat passt → "unmatched"
- Bei Unsicherheit → "partial"

## CONFIDENCE-KALIBRIERUNG
- 0.9–1.0: ALLE Kriterien (Türtyp, Brandschutz, Einbruchschutz, Masse) exakt erfüllt
- 0.7–0.9: Hauptkriterien (Türtyp + Brandschutz/Einbruchschutz) erfüllt, Nebenkriterien offen
- 0.5–0.7: Türtyp stimmt, aber Brand-/Einbruchschutz weicht ab oder ist unklar
- 0.3–0.5: Nur grobe Ähnlichkeit, wesentliche Anforderungen nicht erfüllt
- 0.0–0.3: Kein sinnvoller Match
WICHTIG: Setze confidence NICHT höher als 0.6 wenn Brandschutz oder Einbruchschutz NICHT erfüllt sind.
{feedback_block}
## ANTWORTFORMAT
Antworte NUR mit einem JSON-Array. Pro Position ein Objekt:
[
  {{
    "position_index": 0,
    "best_match_rank": <1-basiert oder null>,
    "confidence": <0.0-1.0>,
    "status": "matched" | "partial" | "unmatched",
    "reason": "<kurze deutsche Begründung>",
    "match_criteria": [
      {{"kriterium": "Türtyp", "status": "ok", "detail": "Stahl = Stahl"}},
      {{"kriterium": "Brandschutz", "status": "ok", "detail": "T60 erfüllt T30"}},
      {{"kriterium": "Einbruchschutz", "status": "fehlt", "detail": "RC3 gefordert, nicht verfügbar"}}
    ],
    "alternative_ranks": []
  }}
]"""

    user_message = f"""Matche folgende {len(positions_data)} Positionen:\n{positions_block}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text.strip()

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        results = _repair_json(response_text)
        if not isinstance(results, list):
            results = [results]
    except json.JSONDecodeError:
        logger.warning(f"Batch AI match returned invalid JSON (after repair): {response_text[:300]}")
        # Return fallback for all positions
        return [
            {
                "best_match_index": pd["candidate_indices"][0] if pd["candidate_indices"] else None,
                "confidence": 0.3,
                "status": "partial",
                "reason": "KI-Batch-Antwort konnte nicht verarbeitet werden",
                "match_criteria": [],
                "alternative_indices": [],
            }
            for pd in positions_data
        ]

    # Map ranks back to DataFrame indices
    mapped_results = []
    for i, pos_data in enumerate(positions_data):
        # Find matching result (by position_index or by order)
        result = None
        for r in results:
            if r.get("position_index") == i:
                result = r
                break
        if result is None and i < len(results):
            result = results[i]
        if result is None:
            result = {"status": "unmatched", "confidence": 0.0, "reason": "Keine KI-Antwort"}

        candidates = pos_data["candidate_indices"]
        best_rank = result.get("best_match_rank")
        best_index = None
        if best_rank and 1 <= best_rank <= len(candidates):
            best_index = candidates[best_rank - 1]

        alt_indices = []
        for alt_rank in result.get("alternative_ranks", []):
            if isinstance(alt_rank, int) and 1 <= alt_rank <= len(candidates):
                alt_indices.append(candidates[alt_rank - 1])

        mapped_results.append({
            "best_match_index": best_index,
            "confidence": result.get("confidence", 0.0),
            "status": result.get("status", "unmatched"),
            "reason": result.get("reason", ""),
            "match_criteria": result.get("match_criteria", []),
            "alternative_indices": alt_indices,
        })

    return mapped_results


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

## CONFIDENCE-KALIBRIERUNG
- 0.9–1.0: ALLE Kriterien (Türtyp, Brandschutz, Einbruchschutz, Masse) exakt erfüllt
- 0.7–0.9: Hauptkriterien erfüllt, Nebenkriterien offen
- 0.5–0.7: Türtyp stimmt, aber Brand-/Einbruchschutz weicht ab
- 0.3–0.5: Nur grobe Ähnlichkeit
- 0.0–0.3: Kein sinnvoller Match
WICHTIG: Setze confidence NICHT höher als 0.6 wenn Brandschutz oder Einbruchschutz NICHT erfüllt sind.
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
        result = _repair_json(response_text)
    except json.JSONDecodeError:
        logger.warning(f"AI match returned invalid JSON (after repair): {response_text[:200]}")
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
