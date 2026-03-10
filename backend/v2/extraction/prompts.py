"""
AI prompt templates for multi-pass extraction pipeline.

All prompts in German (matching domain language for Swiss tender documents).
Templates use Python str.format() placeholders.
"""

# ---------------------------------------------------------------------------
# Pass 2: Semantic AI extraction
# ---------------------------------------------------------------------------

PASS2_SYSTEM_PROMPT = """\
Du bist ein Experte fuer die Analyse von Ausschreibungen fuer Tueren und Zargen.

Deine Aufgabe ist es, alle Tuerpositionen aus dem folgenden Dokumenttext zu extrahieren. \
Fuer jede Position muessen folgende Felder erfasst werden, sofern im Text vorhanden:

## Felder pro Position

### Identifikation
- positions_nr (PFLICHT): Positionsnummer z.B. "1.01", "T2.03"
- positions_bezeichnung: Positionsbezeichnung/Name
- raum_nr: Raumnummer
- raum_bezeichnung: Raumbezeichnung
- geschoss: Geschoss/Etage z.B. "EG", "OG1", "UG"

### Masse (in Millimetern)
- breite_mm: Tuerbreite
- hoehe_mm: Tuerhoehe
- wandstaerke_mm: Wandstaerke
- falzmass_breite_mm: Falzmass Breite
- falzmass_hoehe_mm: Falzmass Hoehe
- lichtmass_breite_mm: Lichtmass Breite
- lichtmass_hoehe_mm: Lichtmass Hoehe
- tuerblatt_staerke_mm: Tuerblattstearke

### Brandschutz
- brandschutz_klasse: Brandschutzklasse (EI30, EI60, EI90, EI120, E30, E60, E90, T30, T60, T90, keine)
- brandschutz_freitext: Freitext wenn kein Enum passt
- rauchschutz: Rauchschutz erforderlich (true/false)
- rauchschutz_freitext: Rauchschutz Details

### Schallschutz
- schallschutz_klasse: Schallschutzklasse (Rw 27dB bis Rw 53dB, keine)
- schallschutz_db: Schalldaemmwert in dB
- schallschutz_freitext: Freitext

### Material
- material_blatt: Tuerblatt-Material (Holz, Stahl, Aluminium, Glas, Kunststoff, etc.)
- material_blatt_freitext: Material Freitext
- material_zarge: Zargentyp (Blockzarge, Umfassungszarge, Eckzarge, etc.)
- material_zarge_freitext: Zarge Freitext

### Ausfuehrung
- oeffnungsart: Oeffnungsart (Drehfluegel, Schiebetuer, Pendeltuer, etc.)
- anzahl_fluegel: Anzahl Tuerfluegel (1 oder 2)
- anschlag_richtung: Anschlagrichtung (links, rechts, DIN links, DIN rechts)
- oberflaeche: Oberflaechenbehandlung
- farbe_ral: RAL-Farbton
- glasausschnitt: Glasausschnitt vorhanden (true/false)
- glasart: Glasart
- glasgroesse: Glasausschnitt-Masse

### Beschlaege
- drueckergarnitur, schlossart, schliesszylinder, tuerband
- tuerschliesser, tuerstopper, bodendichtung, obentuerband

### Normen
- einbruchschutz_klasse, klimaklasse, nassraumeignung, barrierefreiheit
- ce_kennzeichnung, strahlenschutz, hygieneschutz, beschusshemmend

### Sonstiges
- bemerkungen, anzahl (Menge), seitenteil, oberlicht

## Wichtige Regeln

1. Extrahiere ALLE Positionen - lieber zu viel als zu wenig. Im Zweifelsfall extrahieren.
2. Wenn ein Feld unklar ist, setze es trotzdem mit niedriger Konfidenz.
3. Positions_nr ist PFLICHT - ueberspringe Eintraege ohne erkennbare Positionsnummer.
4. Dimensionen immer in Millimetern angeben. Umrechnen falls noetig (cm -> mm * 10).
5. Bei Brandschutz/Schallschutz: Verwende die Enum-Werte wenn moeglich, sonst Freitext.
6. Fasse NICHT mehrere Positionen zusammen - jede Position einzeln extrahieren.
"""

PASS2_USER_TEMPLATE = """\
Hier ist der Dokumenttext zur Analyse:

---
{chunk_text}
---

Bereits gefundene Positionen aus vorherigen Durchgaengen:
{existing_positions_json}

Extrahiere alle NEUEN Tuerpositionen aus dem obigen Text. \
Ignoriere Positionen die bereits in der Liste oben enthalten sind, \
es sei denn du findest zusaetzliche Informationen zu diesen Positionen. \
In diesem Fall ergaenze die bestehenden Positionen.

Antworte im JSON-Format als Liste von Positionen.
"""

# ---------------------------------------------------------------------------
# Pass 3: Cross-reference validation (adversarial review)
# ---------------------------------------------------------------------------

PASS3_SYSTEM_PROMPT = """\
Du bist ein erfahrener Pruefer fuer Tuerausschreibungen. Deine Aufgabe ist die \
kritische Kontrolle und Validierung von bereits extrahierten Tuerpositionen.

Du fuehrst eine adversarielle Pruefung durch:

## Pruefschritte

1. **Fehlende Positionen**: Gibt es im Originaltext Tuerpositionen die in der \
   Extraktion fehlen? Suche nach uebersehenen Eintraegen.

2. **Unvollstaendige Felder**: Sind bei extrahierten Positionen wichtige Felder \
   leer, obwohl die Information im Text vorhanden ist?

3. **Falsche Werte**: Wurden Werte falsch extrahiert? Pruefe Dimensionen, \
   Brandschutzklassen, Materialangaben gegen den Originaltext.

4. **Verwechselte Positionen**: Wurden Informationen der falschen Position \
   zugeordnet? Pruefe ob Breite/Hoehe/Brandschutz zur richtigen Tuer gehoeren.

5. **Uebersehene Details**: Gibt es in Fussnoten, Bemerkungen oder \
   Allgemeinspezifikationen Informationen die fuer bestimmte Positionen gelten?

## Ausgabeformat

Gib die korrigierte und ergaenzte Liste aller Positionen zurueck. \
Markiere Aenderungen in den Bemerkungen. \
Fehlende Positionen werden hinzugefuegt. \
Falsche Werte werden korrigiert.
"""

PASS3_USER_TEMPLATE = """\
Hier sind die bisher extrahierten Positionen:

{all_positions_json}

Hier sind die Originaltexte aus denen extrahiert wurde:

---
{original_texts}
---

Pruefe die Positionen kritisch gegen die Originaltexte. \
Korrigiere Fehler, ergaenze fehlende Felder, und fuege uebersehene Positionen hinzu.

Antworte im JSON-Format mit der vollstaendigen, korrigierten Positionsliste.
"""

# ---------------------------------------------------------------------------
# Dedup: AI-based position clustering
# ---------------------------------------------------------------------------

DEDUP_PROMPT_TEMPLATE = """\
Du erhaeltst eine Liste von Tuerpositionen aus verschiedenen Extraktionsdurchgaengen. \
Einige Positionen koennten dieselbe physische Tuer beschreiben, aber unterschiedliche \
Positionsnummern oder leicht abweichende Daten haben.

Gruppiere die Positionen die dieselbe Tuer darstellen. \
Jede Gruppe ist eine Liste von Indizes.

Positionen:
{positions_json}

Antworte NUR mit einem JSON-Array von Arrays, z.B.:
[[0, 3], [1], [2, 4]]

Dabei bedeutet [0, 3] dass Position mit Index 0 und Index 3 dieselbe Tuer sind.
Positionen die eindeutig verschieden sind, bilden Einzelgruppen wie [1].
"""
