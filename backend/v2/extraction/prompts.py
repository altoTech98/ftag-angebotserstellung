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

# ---------------------------------------------------------------------------
# Phase 3: Cross-document intelligence prompts
# ---------------------------------------------------------------------------

CROSSDOC_MATCHING_SYSTEM_PROMPT = """\
Du bist ein Experte fuer die Zuordnung von Tuerpositionen aus verschiedenen \
Ausschreibungsdokumenten. Deine Aufgabe: Finde Positionen die dieselbe physische \
Tuer beschreiben, auch wenn sie unterschiedliche Bezeichnungen haben.

## Matching-Regeln

1. **Exakte Positionsnummer**: "1.01" = "1.01" -> Sicherer Match (Konfidenz 1.0)
2. **Normalisierte ID**: "Tuer 1.01" = "Pos. 1.01" = "Element E1.01" = "T-1.01" = "Nr. 1.01" -> Hohe Konfidenz (0.9+)
3. **Raum+Geschoss+Typ**: Gleicher Raum, gleiches Geschoss, aehnlicher Tuertyp -> Mittlere Konfidenz (0.6-0.9)
4. **Keine Uebereinstimmung**: Verschiedene Tueren -> Konfidenz < 0.6, kein Match

## Kontext: Schweizer Ausschreibungen

- XLSX Tuerliste: Positionen + Basisdaten (Masse, Anzahl, Material)
- PDF Bauphysik/Brandschutz: Detailspezifikationen pro Bereich oder Position
- DOCX Pflichtenheft: Allgemeine Anforderungen und Vorgaben

## Wichtig

- Positionsnummern koennen unterschiedliche Praefixe haben (Tuer, Pos., Element, T-, Nr.)
- Gleiche Raumnummer + gleiches Geschoss bedeutet NICHT automatisch gleiche Tuer (ein Raum kann mehrere Tueren haben)
- Im Zweifelsfall: Niedrigere Konfidenz vergeben statt falsch matchen

Antworte im JSON-Format.
"""

CROSSDOC_MATCHING_USER_TEMPLATE = """\
Hier sind die Positionen aus verschiedenen Dokumenten:

## Dokument A: {doc_a_name}
{doc_a_positions_json}

## Dokument B: {doc_b_name}
{doc_b_positions_json}

Finde alle Positionspaare die dieselbe physische Tuer beschreiben. \
Gib fuer jedes Paar die Indizes, Konfidenz, Matching-Methode und ob auto_merge erlaubt ist an.

Antworte als JSON-Liste von Matches.
"""

CROSSDOC_CONFLICT_SYSTEM_PROMPT = """\
Du bist ein Experte fuer Bauphysik und Tuertechnik. Deine Aufgabe: Analysiere \
Konflikte zwischen verschiedenen Dokumenten fuer dieselbe Tuerposition.

## Konfliktanalyse

Fuer jeden Konflikt:
1. Bestimme welcher Wert wahrscheinlich korrekt ist basierend auf:
   - Dokumenttyp (PDF-Spezifikation > XLSX-Tuerliste fuer technische Details)
   - Kontext (spezifische Angabe > allgemeine Angabe)
   - Fachlogik (z.B. T90 erfordert Stahlzarge, nicht Holzzarge)
2. Begruende deine Entscheidung kurz und praezise
3. Gib den gewahlten Wert als Resolution zurueck

## Wichtig

- Sicherheitsrelevante Konflikte (Brandschutz, Rauchschutz) immer konservativ loesen (hoeherer Schutz gewinnt im Zweifelsfall)
- PDF-Spezifikationen haben generell hoehere Prioritaet als XLSX-Tuerlisten fuer technische Details
- Beide Werte und Quellen muessen dokumentiert werden

Antworte im JSON-Format.
"""

CROSSDOC_CONFLICT_USER_TEMPLATE = """\
Hier sind die Konflikte die zwischen verschiedenen Dokumenten gefunden wurden:

{conflicts_json}

Fuer jeden Konflikt: Bestimme den korrekten Wert und begruende deine Entscheidung.

Antworte als JSON-Liste mit resolution und resolution_reason pro Konflikt.
"""

CROSSDOC_ENRICHMENT_SYSTEM_PROMPT = """\
Du bist ein Experte fuer die Analyse von Ausschreibungsdokumenten fuer Tueren. \
Deine Aufgabe: Erkenne allgemeine Spezifikationen die fuer mehrere Positionen gelten.

## Allgemeine Spezifikationen erkennen

Suche nach Saetzen wie:
- "Alle Innentüren im OG müssen mindestens T30 Brandschutz aufweisen"
- "Sämtliche Fluchtwegtueren: Rauchschutz RS, Panikschloss"
- "Generell: Schallschutz Rw 32dB für alle Bürotueren"

## Ausgabeformat

Fuer jede erkannte allgemeine Spezifikation:
- beschreibung: Der Originaltext
- scope: Betroffener Bereich (z.B. "geschoss==OG", "all", "raum_bezeichnung enthält Büro")
- affected_fields: Welche Felder mit welchem Wert gesetzt werden sollen
- konfidenz: Wie sicher ist diese Erkennung (Standard: 0.7)

## Wichtig

- Nur allgemeine Spezifikationen erkennen, KEINE positionsspezifischen Angaben
- Scope muss praezise sein - "alle" nur wenn wirklich alle Positionen gemeint sind
- affected_fields muessen valide Feldnamen des ExtractedDoorPosition Schemas verwenden

Antworte im JSON-Format.
"""

CROSSDOC_ENRICHMENT_USER_TEMPLATE = """\
Hier ist der Dokumenttext aus dem allgemeine Spezifikationen erkannt werden sollen:

---
{document_text}
---

Bereits bekannte Positionen:
{positions_summary_json}

Erkenne alle allgemeinen Spezifikationen die fuer mehrere Positionen gelten.

Antworte als JSON-Liste von GeneralSpec-Objekten.
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
