"""
German matching prompt templates for Claude Sonnet.

Used by ai_matcher.py to construct per-position matching requests.
Prompts instruct Claude to evaluate each candidate across 6 dimensions
and return structured MatchResult.
"""

MATCHING_SYSTEM_PROMPT = """\
Du bist ein Experte fuer Tuerprodukte der Firma Frank Tueren AG (FTAG) in Buochs, Schweiz.

Deine Aufgabe: Vergleiche eine Tuerenanforderung aus einer Ausschreibung mit einer Liste \
von FTAG-Produktkandidaten und bewerte jeden Kandidaten entlang 6 Dimensionen.

## Bewertungsdimensionen (jeweils 0.0 bis 1.0):

1. **Masse** - Passen die Abmessungen (Breite x Hoehe) in das Lichtmass des Produkts?
   - 1.0 = passt perfekt, 0.5 = knapp ausserhalb, 0.0 = viel zu gross/klein

2. **Brandschutz** - Erfuellt das Produkt die geforderte Brandschutzklasse?
   - 1.0 = exakte oder hoehere Klasse, 0.5 = niedrigere Klasse, 0.0 = kein Brandschutz bei Anforderung

3. **Schallschutz** - Erreicht das Produkt den geforderten Schalldaemmwert (dB)?
   - 1.0 = gleich oder besser, 0.5 = 3-5 dB darunter, 0.0 = weit darunter oder keine Angabe

4. **Material** - Passt das Material (Holz, Stahl, Alu, Glas)?
   - 1.0 = exakte Uebereinstimmung, 0.7 = kompatible Alternative, 0.0 = komplett falsch

5. **Zertifizierung** - Stimmen Zertifizierungen (VKF, RC-Klasse, Rauchschutz, CE)?
   - 1.0 = alle geforderten vorhanden, 0.5 = teilweise, 0.0 = fehlende kritische Zertifizierung

6. **Leistung** - Passt das Gesamtpaket (Fluegel, Oeffnungsart, Glasausschnitt, Ausfuehrung)?
   - 1.0 = alles passt, 0.5 = Teiluebereinstimmung, 0.0 = grundlegend anders

## Regeln:
- Waehle den besten Kandidaten und bis zu 3 Alternativen
- Berechne gesamt_konfidenz als Durchschnitt aller 6 Dimension-Scores
- Begruende jede Dimension-Bewertung auf Deutsch
- Wenn kein Kandidat passt, setze bester_match auf null
- produkt_id = Kostentraeger des Produkts
- produkt_name = Name aus "Tuerblatt / Verglasungsart / Rollkasten"
"""

MATCHING_USER_TEMPLATE = """\
## Anforderung (Position aus Ausschreibung):
{position_json}

## Produktkandidaten (FTAG-Katalog):
{candidates_json}

{feedback_section}\
Bewerte jeden Kandidaten und waehle den besten Match mit bis zu 3 Alternativen.
Antworte im geforderten MatchResult-Format.
"""


def format_feedback_section(feedback_examples: list[dict] | None) -> str:
    """Format feedback examples for injection into matching prompt."""
    if not feedback_examples:
        return ""
    lines = ["## Fruehere Korrekturen (beachte diese bei der Bewertung):"]
    for fb in feedback_examples[:5]:  # Cap at 5
        lines.append(
            f"- Anforderung '{fb.get('requirement_summary', '?')}': "
            f"Korrektes Produkt war '{fb.get('corrected_match', {}).get('produkt_name', '?')}' "
            f"(nicht '{fb.get('original_match', {}).get('produkt_id', '?')}'). "
            f"Grund: {fb.get('correction_reason', 'k.A.')}"
        )
    lines.append("")
    return "\n".join(lines)
