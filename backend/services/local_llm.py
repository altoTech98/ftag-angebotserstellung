"""
Local LLM Service – Ollama-based AI functions replacing Claude API.

Provides:
- Project metadata extraction (Bauherr, Baustelle, etc.)
- Requirements extraction from tender documents
- Offer text generation
- Gap report text generation
- Document scanning for door data enrichment
- Ollama health check

All functions fall back to regex/template if Ollama is unavailable.
"""

import os
import re
import json
import logging
import time
import httpx

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

from config import settings as _settings
OLLAMA_TIMEOUT_SHORT = _settings.OLLAMA_TIMEOUT_SHORT
OLLAMA_TIMEOUT_MEDIUM = _settings.OLLAMA_TIMEOUT_MEDIUM
OLLAMA_TIMEOUT_LONG = _settings.OLLAMA_TIMEOUT_LONG

# Cache for status check
_status_cache = {"result": None, "timestamp": 0}
_STATUS_CACHE_TTL = 5  # seconds - reduced from 30s for faster status updates


# ─── Core Ollama Helper ─────────────────────────────────────

def _call_ollama(prompt: str, system: str = "", timeout: float = OLLAMA_TIMEOUT_SHORT) -> str | None:
    """
    Call Ollama generate API. Returns response text or None on failure.
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4096},
        }
        if system:
            payload["system"] = system

        response = httpx.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        response.raise_for_status()

        raw = response.json().get("response", "")
        if not raw.strip():
            logger.warning("Ollama returned empty response")
            return None

        return raw

    except httpx.ConnectError:
        logger.info("Ollama not reachable")
        return None
    except httpx.TimeoutException:
        logger.warning(f"Ollama timeout after {timeout}s")
        return None
    except Exception as e:
        logger.warning(f"Ollama call failed: {e}")
        return None


# ─── JSON Repair ─────────────────────────────────────────────

def _repair_json(text: str):
    """
    Attempt to repair common JSON issues from LLM responses.
    Handles trailing commas, truncated JSON, single-line comments.
    """
    # Remove single-line comments
    text = re.sub(r'//[^\n]*', '', text)
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to fix truncated JSON by closing brackets
    last_complete = text.rfind('}')
    if last_complete > 0:
        truncated = text[:last_complete + 1]
        truncated += ']' * max(0, truncated.count('[') - truncated.count(']'))
        truncated += '}' * max(0, truncated.count('{') - truncated.count('}'))
        truncated = re.sub(r',\s*([}\]])', r'\1', truncated)
        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

    # Last resort: add closing brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    fixed = text + '}' * max(0, open_braces) + ']' * max(0, open_brackets)
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
    return json.loads(fixed)


def _extract_json_from_response(text: str):
    """Extract and parse JSON from an LLM response that may contain markdown blocks."""
    if not text:
        return None

    # Try to extract from markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()

    try:
        return _repair_json(text)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"JSON extraction failed: {e}")

        # Last attempt: find any JSON object or array in text
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if json_match:
            try:
                return _repair_json(json_match.group(1))
            except (json.JSONDecodeError, Exception):
                pass

        return None


# ─── Ollama Status Check ────────────────────────────────────

def check_ollama_status() -> dict:
    """
    Check if Ollama is running and what models are available.
    Results are cached for 5 seconds for performance.
    """
    now = time.time()
    if _status_cache["result"] is not None and (now - _status_cache["timestamp"]) < _STATUS_CACHE_TTL:
        return _status_cache["result"]

    result = {"available": False, "models": [], "model_loaded": False}

    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        response.raise_for_status()
        data = response.json()

        models = [m.get("name", "") for m in data.get("models", [])]
        result["available"] = True
        result["models"] = models
        result["model_loaded"] = any(OLLAMA_MODEL in m for m in models)

    except Exception:
        pass

    _status_cache["result"] = result
    _status_cache["timestamp"] = now
    return result


def check_ollama_status_live() -> dict:
    """
    Live check for Ollama status WITHOUT caching.
    Used by health check endpoint for real-time status.
    """
    result = {"available": False, "models": [], "model_loaded": False}

    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        response.raise_for_status()
        data = response.json()

        models = [m.get("name", "") for m in data.get("models", [])]
        result["available"] = True
        result["models"] = models
        result["model_loaded"] = any(OLLAMA_MODEL in m for m in models)

    except Exception:
        pass

    return result


# ─── 1. Project Metadata Extraction ─────────────────────────

METADATA_PROMPT = """Extrahiere die folgenden Informationen aus dem Text. Antworte NUR mit einem JSON-Objekt, ohne zusaetzlichen Text.

Felder:
- bauherr: Name des Bauherrn / Auftraggebers / Bestellers
- bauort: Baustelle / Standort / Ort des Projekts
- architekt: Name des Architekten / Planers / Projektleiters
- projekt_name: Projektname / Projektbezeichnung / Objektbezeichnung
- datum: Projektdatum / Ausschreibungsdatum (Format: TT.MM.JJJJ)
- adresse: Vollstaendige Adresse des Projekts

Wenn ein Feld nicht gefunden wird, setze den Wert auf null.

Text:
{text}

JSON:"""


def _empty_metadata(source: str = "none") -> dict:
    return {
        "bauherr": None, "bauort": None, "architekt": None,
        "projekt_name": None, "datum": None, "adresse": None,
        "source": source,
    }


def _extract_metadata_regex(text: str) -> dict:
    """Extract metadata using regex patterns (fallback)."""
    result = _empty_metadata("regex")

    patterns = {
        "bauherr": [r'(?:Bauherr|Auftraggeber|Besteller|Bauherrschaft)\s*[:\-]?\s*(.+)'],
        "bauort": [r'(?:Baustelle|Bauort|Standort|Objekt\s*Standort)\s*[:\-]?\s*(.+)'],
        "architekt": [r'(?:Architekt|Planer|Projektleiter|Projektleitung|Bauleitung)\s*[:\-]?\s*(.+)'],
        "projekt_name": [r'(?:Projekt(?:name|bezeichnung)?|Objekt(?:bezeichnung)?|Vorhaben)\s*[:\-]?\s*(.+)'],
        "adresse": [r'(?:Adresse|Anschrift)\s*[:\-]?\s*(.+)'],
    }

    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = re.sub(r'[\s,;]+$', '', match.group(1).strip())[:200]
                if val and len(val) > 1:
                    result[field] = val
                    break

    date_match = re.search(r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b', text)
    if date_match:
        result["datum"] = date_match.group(1)

    has_data = any(result[k] for k in ("bauherr", "bauort", "architekt", "projekt_name", "datum", "adresse"))
    if not has_data:
        result["source"] = "none"

    return result


def extract_project_metadata(text: str) -> dict:
    """
    Extract project metadata from document text.
    Tries Ollama first, falls back to regex patterns.
    """
    if not text or not text.strip():
        return _empty_metadata()

    # Try Ollama
    truncated = text[:6000]
    prompt = METADATA_PROMPT.format(text=truncated)
    raw = _call_ollama(prompt, timeout=OLLAMA_TIMEOUT_SHORT)

    if raw:
        parsed = _extract_json_from_response(raw)
        if parsed and isinstance(parsed, dict):
            result = _empty_metadata("ollama")
            for key in ("bauherr", "bauort", "architekt", "projekt_name", "datum", "adresse"):
                val = parsed.get(key)
                if val and str(val).strip().lower() not in ("null", "none", "n/a", ""):
                    result[key] = str(val).strip()
            has_data = any(result[k] for k in ("bauherr", "bauort", "architekt", "projekt_name", "datum", "adresse"))
            if has_data:
                return result

    return _extract_metadata_regex(text)


# ─── 2. Requirements Extraction (replaces Claude) ───────────

_REQ_SYSTEM = """Du bist ein erfahrener Tueren-Fachberater der Frank Tueren AG in der Schweiz.
Deine Aufgabe ist es, Ausschreibungsdokumente zu analysieren und die genauen Tueranforderungen
strukturiert zu extrahieren.

Extrahiere alle Tuerpositionen mit folgenden Informationen (falls vorhanden):
- position: Positions-Nummer oder Bezeichnung
- menge: Anzahl der Tueren
- tuertyp: Art der Tuer (z.B. Stahltuer, Holztuer, Alutuer, Brandschutztuer, etc.)
- breite: Breite in mm
- hoehe: Hoehe in mm
- brandschutz: Brandschutzklasse (z.B. T30, T60, T90, EI30, EI60, EI90, EI120)
- schallschutz: Schalldaemmmass in dB (z.B. Rw=32dB)
- einbruchschutz: Widerstandsklasse (z.B. RC2, RC3, RC4, WK2, WK3)
- verglasung: Verglasungsanteil oder -typ
- oberflaechenbehandlung: Farbe/Beschichtung/Pulverbeschichtung
- zubehoer: Tuerbeschlaege, Schloesser, Schliesser, etc.
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
      "tuertyp": "Stahltuer",
      "breite": 900,
      "hoehe": 2100,
      "brandschutz": "T30",
      "schallschutz": null,
      "einbruchschutz": "RC2",
      "verglasung": null,
      "oberflaechenbehandlung": "RAL 7016",
      "zubehoer": "Tuerdruecker, Tuerschliesser",
      "besonderheiten": ""
    }
  ],
  "gesamtanzahl_tueren": 2,
  "hinweise": "Weitere Hinweise aus dem Dokument"
}"""


def _extract_requirements_regex(text: str) -> dict:
    """Fallback: extract door requirements using regex patterns."""
    positions = []
    pos_idx = 1

    # Find door-related paragraphs
    # Pattern: position numbers like "1.1", "Pos. 1", "Position 1"
    pos_pattern = r'(?:Pos(?:ition)?\.?\s*)?(\d+(?:\.\d+)?)\s*[:\-]?\s*(.*?)(?=(?:Pos(?:ition)?\.?\s*)?\d+(?:\.\d+)?\s*[:\-]|$)'
    blocks = re.findall(pos_pattern, text[:12000], re.DOTALL)

    for pos_nr, block in blocks:
        if len(block.strip()) < 10:
            continue

        door = {
            "position": pos_nr,
            "beschreibung": block.strip()[:200],
            "menge": 1,
            "einheit": "Stk",
            "tuertyp": None,
            "breite": None,
            "hoehe": None,
            "brandschutz": None,
            "schallschutz": None,
            "einbruchschutz": None,
            "verglasung": None,
            "oberflaechenbehandlung": None,
            "zubehoer": None,
            "besonderheiten": "",
        }

        # Door type
        for typ, label in [("stahl", "Stahltuer"), ("holz", "Holztuer"), ("alu", "Alutuer"), ("brand", "Brandschutztuer")]:
            if typ in block.lower():
                door["tuertyp"] = label
                break

        # Fire class
        fc = re.search(r'(EI|T)\s*(\d{2,3})', block, re.IGNORECASE)
        if fc:
            door["brandschutz"] = f"{fc.group(1).upper()}{fc.group(2)}"

        # Resistance
        rc = re.search(r'(RC|WK)\s*(\d)', block, re.IGNORECASE)
        if rc:
            door["einbruchschutz"] = f"{rc.group(1).upper()}{rc.group(2)}"

        # Sound
        snd = re.search(r'(?:Rw\s*=?\s*)?(\d{2,3})\s*dB', block, re.IGNORECASE)
        if snd:
            door["schallschutz"] = f"Rw={snd.group(1)}dB"

        # Dimensions (BxH)
        dim = re.search(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})', block)
        if dim:
            door["breite"] = int(dim.group(1))
            door["hoehe"] = int(dim.group(2))

        # Quantity
        qty = re.search(r'(\d+)\s*(?:Stk|Stueck|St\.)', block, re.IGNORECASE)
        if qty:
            door["menge"] = int(qty.group(1))

        # RAL color
        ral = re.search(r'RAL\s*(\d{4})', block, re.IGNORECASE)
        if ral:
            door["oberflaechenbehandlung"] = f"RAL {ral.group(1)}"

        # Only add if it seems door-related
        door_keywords = ["tuer", "tür", "door", "stahl", "holz", "alu", "brand", "EI", "RC", "WK"]
        if any(kw.lower() in block.lower() for kw in door_keywords):
            positions.append(door)
            pos_idx += 1

    # If no positions found via pattern, try simpler approach
    if not positions:
        # Look for fire class mentions as a hint of door-relevant content
        fire_matches = re.findall(r'(EI|T)\s*(\d{2,3})', text[:12000], re.IGNORECASE)
        for i, (prefix, val) in enumerate(fire_matches[:10]):
            positions.append({
                "position": str(i + 1),
                "beschreibung": f"Tuer {prefix.upper()}{val}",
                "menge": 1, "einheit": "Stk",
                "tuertyp": "Brandschutztuer",
                "breite": None, "hoehe": None,
                "brandschutz": f"{prefix.upper()}{val}",
                "schallschutz": None, "einbruchschutz": None,
                "verglasung": None, "oberflaechenbehandlung": None,
                "zubehoer": None, "besonderheiten": "",
            })

    return {
        "projekt": "",
        "auftraggeber": "",
        "positionen": positions,
        "gesamtanzahl_tueren": sum(p.get("menge", 1) for p in positions),
        "hinweise": "Regex-basierte Extraktion (Ollama nicht verfuegbar)",
    }


def extract_requirements_from_text(document_text: str) -> dict:
    """
    Extract structured door requirements from tender document text.
    Tries Ollama first, falls back to regex patterns.
    Replaces claude_client.extract_requirements_from_text().
    """
    if not document_text or not document_text.strip():
        return {"projekt": "", "auftraggeber": "", "positionen": [],
                "gesamtanzahl_tueren": 0, "hinweise": "Leeres Dokument"}

    prompt = f"""Analysiere folgendes Ausschreibungsdokument und extrahiere alle Tueranforderungen:

---DOKUMENT ANFANG---
{document_text[:12000]}
---DOKUMENT ENDE---

Extrahiere alle Tuerpositionen als strukturiertes JSON."""

    raw = _call_ollama(prompt, system=_REQ_SYSTEM, timeout=OLLAMA_TIMEOUT_MEDIUM)

    if raw:
        parsed = _extract_json_from_response(raw)
        if parsed and isinstance(parsed, dict) and "positionen" in parsed:
            logger.info(f"Requirements extracted via Ollama: {len(parsed.get('positionen', []))} positions")
            return parsed

    logger.info("Requirements extraction: falling back to regex")
    return _extract_requirements_regex(document_text)


# ─── 3. Offer Text Generation (replaces Claude) ─────────────

_OFFER_SYSTEM = """Du bist ein professioneller Angebotsverfasser der Frank Tueren AG, Buochs NW, Schweiz.
Erstelle formelle, professionelle Angebote auf Deutsch in schweizer Geschaeftsstil.
Frank Tueren AG fertigt hochwertige Stahl- und Metalltueren."""


def _generate_offer_template(requirements: dict, matched_products: list, project_info: dict) -> str:
    """Fallback: generate offer text using a template."""
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%d.%m.%Y")
    valid_until = (datetime.now() + timedelta(days=90)).strftime("%d.%m.%Y")

    lines = [
        "Frank Tueren AG",
        "Industriestrasse 12",
        "6374 Buochs NW",
        "",
        f"Angebotsdatum: {today}",
        f"Gueltig bis: {valid_until}",
        "",
        f"Betreff: Angebot Tueren",
        "",
        f"Sehr geehrte Damen und Herren,",
        "",
        f"Gerne unterbreiten wir Ihnen unser Angebot.",
        "",
        "Positionen:",
        "─" * 60,
    ]

    total = 0
    for i, pos in enumerate(matched_products, 1):
        beschr = pos.get("beschreibung", "Tuer")
        menge = pos.get("menge", 1)
        lines.append(f"Pos. {i}: {beschr} - Menge: {menge} Stk")
        lines.append(f"         Richtpreis auf Anfrage")
        lines.append("")

    lines.extend([
        "─" * 60,
        "",
        "Zahlungsbedingungen: 30 Tage netto",
        "Lieferfrist: 6-8 Wochen ab Auftragsbestaetigung",
        "Alle Preise verstehen sich exkl. MwSt. (8.1%) und exkl. Montage.",
        "",
        "Wir freuen uns auf Ihre Bestellung.",
        "",
        "Freundliche Gruesse",
        "Frank Tueren AG",
    ])

    return "\n".join(lines)


def generate_offer_text(
    requirements: dict,
    matched_products: list,
    project_info: dict,
) -> str:
    """
    Generate a formal offer text based on matched products.
    Replaces claude_client.generate_offer_text().
    """
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%d.%m.%Y")
    valid_until = (datetime.now() + timedelta(days=90)).strftime("%d.%m.%Y")

    prompt = f"""Erstelle ein formelles Angebot basierend auf folgenden Informationen:

PROJEKTINFO:
{json.dumps(project_info, ensure_ascii=False, indent=2)}

ANFORDERUNGEN AUS AUSSCHREIBUNG:
{json.dumps(requirements, ensure_ascii=False, indent=2)[:4000]}

GEMATCHTE PRODUKTE:
{json.dumps(matched_products[:30], ensure_ascii=False, indent=2)[:4000]}

ANGEBOTSDATEN:
- Angebotsdatum: {today}
- Gueltig bis: {valid_until}
- Zahlungsbedingungen: 30 Tage netto

Erstelle ein professionelles Angebot mit:
1. Kopfzeile (Frank Tueren AG, Angebotsnummer, Datum, Gueltigkeit)
2. Empfaengeradresse (aus Projektinfo)
3. Betreff mit Projektnamen
4. Einleitungstext
5. Positionsliste (Pos.-Nr., Beschreibung, Menge, Einheit, Einzelpreis CHF, Gesamtpreis CHF)
6. Zwischensumme, MwSt (8.1%), Gesamtbetrag
7. Konditionen und Schlusstext
8. Unterschrift Frank Tueren AG

Verwende realistische Preisangaben fuer Stahl/Metalltueren (Richtwerte: einfache Stahltuer CHF 800-1500, Brandschutztuer CHF 1200-3000, Sicherheitstuer RC2 CHF 1500-4000 je nach Groesse).
Markiere Preise als "Richtpreise exkl. Montage" wenn keine exakten Daten vorliegen."""

    raw = _call_ollama(prompt, system=_OFFER_SYSTEM, timeout=OLLAMA_TIMEOUT_LONG)

    if raw and len(raw.strip()) > 100:
        logger.info(f"Offer text generated via Ollama ({len(raw)} chars)")
        return raw

    logger.info("Offer text generation: falling back to template")
    return _generate_offer_template(requirements, matched_products, project_info)


# ─── 4. Gap Report Text Generation (replaces Claude) ────────

_GAP_SYSTEM = """Du bist ein technischer Berater der Frank Tueren AG.
Erstelle professionelle Gap-Reports auf Deutsch, die fehlende Produkte und moegliche Alternativen aufzeigen."""


def _generate_gap_template(requirements: dict, unmatched_positions: list, project_info: dict) -> str:
    """Fallback: generate gap report using a template."""
    total = requirements.get("gesamtanzahl_tueren", 0)

    lines = [
        "GAP-REPORT",
        "=" * 60,
        "",
        f"Zusammenfassung: {len(unmatched_positions)} von {total} Positionen nicht vollstaendig erfuellbar.",
        "",
        "Nicht erfuellbare Positionen:",
        "─" * 60,
    ]

    for i, pos in enumerate(unmatched_positions, 1):
        beschr = pos.get("beschreibung", "Tuer")
        status = pos.get("status", "unmatched")
        reason = pos.get("reason", "Kein passendes Produkt im Katalog")
        gaps = pos.get("gap_items", [])

        lines.append(f"\nPos. {i}: {beschr}")
        lines.append(f"  Status: {status}")
        lines.append(f"  Grund: {reason}")
        if gaps:
            for gap in gaps:
                lines.append(f"  - {gap}")
        lines.append(f"  Empfehlung: Sonderanfertigung pruefen oder alternative Spezifikation mit Bauherr besprechen")

    lines.extend([
        "",
        "─" * 60,
        "",
        "Naechste Schritte:",
        "1. Positionen mit Bauherr/Architekt besprechen",
        "2. Alternative Spezifikationen pruefen",
        "3. Sonderanfertigungen kalkulieren",
        "",
        "Frank Tueren AG",
    ])

    return "\n".join(lines)


def generate_gap_report_text(
    requirements: dict,
    unmatched_positions: list,
    project_info: dict,
) -> str:
    """
    Generate a gap report for positions that could not be matched.
    Replaces claude_client.generate_gap_report_text().
    """
    prompt = f"""Erstelle einen Gap-Report fuer nicht erfuellbare Anforderungen:

PROJEKT: {json.dumps(project_info, ensure_ascii=False, indent=2)}

NICHT ERFUELLBARE POSITIONEN:
{json.dumps(unmatched_positions[:30], ensure_ascii=False, indent=2)[:4000]}

ALLE ANFORDERUNGEN:
{json.dumps(requirements, ensure_ascii=False, indent=2)[:3000]}

Erstelle einen detaillierten Gap-Report mit:
1. Zusammenfassung: X von Y Positionen nicht erfuellbar
2. Fuer jede nicht erfuellbare Position:
   - Anforderung (was wurde gefordert)
   - Grund (warum nicht erfuellbar)
   - Empfehlung (Sonderanfertigung / alternative Spezifikation / Lieferantenpartner)
3. Handlungsempfehlungen
4. Naechste Schritte"""

    raw = _call_ollama(prompt, system=_GAP_SYSTEM, timeout=OLLAMA_TIMEOUT_LONG)

    if raw and len(raw.strip()) > 50:
        logger.info(f"Gap report generated via Ollama ({len(raw)} chars)")
        return raw

    logger.info("Gap report generation: falling back to template")
    return _generate_gap_template(requirements, unmatched_positions, project_info)


# ─── 5. Document Scanning for Door Data ─────────────────────

_SCAN_SYSTEM = """Du bist ein Experte fuer Tueren und Bau-Spezifikationen.
Analysiere das Dokument und extrahiere ALLE tuerbezogenen Daten.

Suche nach:
- Tuer-Nummern oder Positions-Nummern (z.B. T01.001, Pos. 1.1)
- Brandschutzanforderungen (EI30, EI60, T30, T60, etc.)
- Schallschutzanforderungen (dB-Werte)
- Einbruchschutz (RC2, RC3, WK2, WK3)
- Masse (Breite x Hoehe)
- Oberflaechen (RAL-Farben, Beschichtungen)
- Verglasung (Glasausschnitte, Verglasungsarten)
- Zubehoer (Beschlaege, Schliesser, Schloesser)
- Allgemeine Anforderungen die fuer alle Tueren gelten

Antworte NUR mit einem JSON-Objekt:
{
  "is_relevant": true/false,
  "door_properties": [
    {
      "tuer_nr": "T01.001 oder null",
      "brandschutz": "EI30 oder null",
      "schallschutz": "Rw=32dB oder null",
      "einbruchschutz": "RC2 oder null",
      "breite": 900,
      "hoehe": 2100,
      "verglasung": "Beschreibung oder null",
      "oberflaechenbehandlung": "RAL 7016 oder null",
      "zubehoer": "Tuerdruecker etc. oder null",
      "besonderheiten": "Zusatzinfos oder null"
    }
  ],
  "general_requirements": "Allgemeine Anforderungen die fuer alle Tueren gelten (z.B. alle Tueren RAL 9010)"
}"""


def _scan_document_regex(text: str) -> dict:
    """Fallback: scan document for door data using regex."""
    result = {
        "is_relevant": False,
        "door_properties": [],
        "general_requirements": "",
    }

    # Check relevance
    door_keywords = ["tuer", "tür", "door", "EI30", "EI60", "T30", "T60",
                     "brandschutz", "schallschutz", "RC2", "RC3", "WK2"]
    relevance_count = sum(1 for kw in door_keywords if kw.lower() in text.lower())
    if relevance_count < 2:
        return result

    result["is_relevant"] = True

    # Extract fire classes
    fire_classes = set()
    for m in re.finditer(r'(EI|T)\s*(\d{2,3})', text, re.IGNORECASE):
        fire_classes.add(f"{m.group(1).upper()}{m.group(2)}")

    # Extract resistance classes
    resistance = set()
    for m in re.finditer(r'(RC|WK)\s*(\d)', text, re.IGNORECASE):
        resistance.add(f"{m.group(1).upper()}{m.group(2)}")

    # Extract sound ratings
    sound = set()
    for m in re.finditer(r'(?:Rw\s*=?\s*)?(\d{2,3})\s*dB', text, re.IGNORECASE):
        sound.add(f"Rw={m.group(1)}dB")

    # Extract RAL colors
    ral_colors = set()
    for m in re.finditer(r'RAL\s*(\d{4})', text, re.IGNORECASE):
        ral_colors.add(f"RAL {m.group(1)}")

    # Extract dimensions (BxH)
    dimensions = []
    for m in re.finditer(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})', text):
        dimensions.append((int(m.group(1)), int(m.group(2))))

    # Extract door numbers
    door_nrs = set()
    for m in re.finditer(r'(?:T|Tuer|Tür)\s*(\d+(?:\.\d+)*)', text, re.IGNORECASE):
        door_nrs.add(m.group(0).strip())

    # Build properties
    if door_nrs:
        for nr in list(door_nrs)[:50]:
            prop = {"tuer_nr": nr}
            if fire_classes:
                prop["brandschutz"] = list(fire_classes)[0]
            if resistance:
                prop["einbruchschutz"] = list(resistance)[0]
            if sound:
                prop["schallschutz"] = list(sound)[0]
            if ral_colors:
                prop["oberflaechenbehandlung"] = list(ral_colors)[0]
            result["door_properties"].append(prop)
    else:
        # No specific door numbers - create general properties
        if fire_classes or resistance or sound:
            prop = {}
            if fire_classes:
                prop["brandschutz"] = ", ".join(sorted(fire_classes))
            if resistance:
                prop["einbruchschutz"] = ", ".join(sorted(resistance))
            if sound:
                prop["schallschutz"] = ", ".join(sorted(sound))
            if ral_colors:
                prop["oberflaechenbehandlung"] = ", ".join(sorted(ral_colors))
            result["door_properties"].append(prop)

    # General requirements
    general = []
    if ral_colors:
        general.append(f"Oberflaeche: {', '.join(sorted(ral_colors))}")
    if fire_classes:
        general.append(f"Brandschutz: {', '.join(sorted(fire_classes))}")
    if resistance:
        general.append(f"Einbruchschutz: {', '.join(sorted(resistance))}")
    if sound:
        general.append(f"Schallschutz: {', '.join(sorted(sound))}")
    result["general_requirements"] = "; ".join(general)

    return result


def scan_document_for_door_data(text: str, filename: str = "") -> dict:
    """
    Scan a document for door-related data using Ollama.
    Returns {is_relevant, door_properties[], general_requirements}.
    """
    if not text or not text.strip():
        return {"is_relevant": False, "door_properties": [], "general_requirements": ""}

    # Limit text for Ollama (longer than metadata, since we need more detail)
    truncated = text[:15000]

    prompt = f"""Analysiere folgendes Dokument ({filename}) und extrahiere ALLE tuerbezogenen Daten:

---DOKUMENT ANFANG---
{truncated}
---DOKUMENT ENDE---

Extrahiere alle tuerbezogenen Daten als JSON."""

    raw = _call_ollama(prompt, system=_SCAN_SYSTEM, timeout=OLLAMA_TIMEOUT_MEDIUM)

    if raw:
        parsed = _extract_json_from_response(raw)
        if parsed and isinstance(parsed, dict):
            logger.info(f"Document scan via Ollama ({filename}): "
                        f"relevant={parsed.get('is_relevant')}, "
                        f"properties={len(parsed.get('door_properties', []))}")
            return {
                "is_relevant": parsed.get("is_relevant", False),
                "door_properties": parsed.get("door_properties", []),
                "general_requirements": parsed.get("general_requirements", ""),
            }

    logger.info(f"Document scan: falling back to regex ({filename})")
    return _scan_document_regex(text)
