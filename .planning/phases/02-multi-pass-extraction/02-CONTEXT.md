# Phase 2: Multi-Pass Extraction - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-file upload per tender with a 3-pass extraction pipeline that converts raw parsed text (from Phase 1 parsers) into structured `ExtractedDoorPosition` objects. Pass 1 is structural (regex/heuristic), Pass 2 is AI-semantic (Claude Opus, chunked), Pass 3 is cross-reference validation (gap check + adversarial review). Deduplication runs after each pass. Cross-document merging of positions from different files is included. The product matching itself is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Multi-Pass-Strategie
- Pass 1 (strukturell): Regex + Heuristik — Positionen aus Tabellenstruktur extrahieren (Spalten-Matching, Positions-Nummern per Regex, Dimensionen aus bekannten Mustern). Schnell, kostenlos, nur für klar strukturierte Daten.
- Pass 2 (AI-semantisch): Claude Opus mit Chunked-Overlap-Strategie. Dokument in seitenbasierte Chunks teilen (z.B. 30 Seiten pro Chunk, 5 Seiten Overlap). Jeder Chunk wird einzeln an Claude gesendet. Ergebnis: vollständige ExtractedDoorPosition-Objekte via messages.parse().
- Pass 3 (Cross-Reference-Validierung): Beides kombiniert — Lücken-Check UND Adversarial Review in einem Call. Pass 3 bekommt bisherige Ergebnisse + Originaltext und sucht: fehlende Positionen, unvollständige Felder, übersehene Details, falsche Zuordnungen, verwechselte Positionen, falsch gelesene Werte.
- Modell: Claude Opus für alle AI-Passes (Pass 2 + Pass 3). Genauigkeit hat Priorität vor Kosten.
- Chunking: Seitenbasiert — z.B. 30 Seiten pro Chunk, 5 Seiten Overlap. Natürliche Grenze, ParseResult hat bereits page_count.

### Deduplizierung
- Match-Key: AI-basiert — Claude entscheidet ob zwei Positionen die gleiche Tür meinen. Versteht Kontext: 'T1.01 EG links' und 'Position 1.01 Erdgeschoss' sind die gleiche.
- Timing: Nach jedem Pass. Pass 1 Ergebnis wird dedupliziert, dann an Pass 2 übergeben (so sieht Pass 2 was schon extrahiert wurde). Pass 3 bekommt das fusionierte Bild.
- Konflikte: Späterer Pass gewinnt (Pass 3 > Pass 2 > Pass 1). Originalwert wird in quellen-Tracking behalten.
- Provenienz: Vollständig — jedes Feld trackt welcher Pass, welches Dokument, welche Seite/Zelle via FieldSource. Bei Merge wird die Quelle des gewinnenden Werts gespeichert.

### Multi-File-Handling
- Upload-API: Session/Tender-ID basiert. POST /api/v2/upload gibt tender_id zurück (oder nimmt bestehende). Mehrere Uploads mit gleicher tender_id gehören zusammen. POST /api/v2/analyze nimmt tender_id.
- Reihenfolge: XLSX zuerst (strukturierteste Daten), dann PDF, dann DOCX. So hat Pass 1 (Regex) die besten Daten zuerst.
- Pass-Scope: Pro Datei Pass 1+2 einzeln. Pass 3 läuft über das fusionierte Ergebnis aller Dateien — der echte Cross-Document-Check.
- API-Koexistenz: Neuer /api/v2/upload Endpoint neben bestehendem /api/upload. Konsistent mit Phase 1: v1 und v2 koexistieren.

### Fehler & Teilresultate
- AI-Fehler: 3x Retry mit Backoff. Wenn alle fehlschlagen: Chunk überspringen, Warnung loggen, mit nächstem Chunk weitermachen. Am Ende: Bericht welche Teile nicht verarbeitet wurden.
- Unsicherheit: Immer extrahieren, aber FieldSource.konfidenz auf niedrigen Wert setzen. Downstream (Matching) entscheidet ob es den Wert verwendet. Lieber zu viel als zu wenig.
- Validierung: Minimal-Check — nur positions_nr ist Pflicht. Positionen mit nur positions_nr sind gültig aber bekommen Warnung 'wenig Daten extrahiert'.

### Claude's Discretion
- Genaue Chunk-Grösse und Overlap-Werte (30/5 als Richtwert, kann empirisch angepasst werden)
- Prompt-Design für Pass 2 und Pass 3
- Retry-Backoff-Strategie (exponentiell, konstant, etc.)
- Interne Dedup-Datenstrukturen
- Reihenfolge der Felder in AI-Prompts

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/v2/parsers/base.py`: ParseResult dataclass mit text, format, page_count, warnings, metadata, source_file, tables — direkte Input-Quelle für Pass 1
- `backend/v2/parsers/router.py`: Format-Detection-Router — kann für Multi-File-Dispatch wiederverwendet werden
- `backend/v2/schemas/extraction.py`: ExtractedDoorPosition (55 Felder) + ExtractionResult — Output-Schema für alle Passes
- `backend/v2/schemas/common.py`: FieldSource mit dokument, seite, zeile, zelle, sheet, konfidenz — bereit für Provenienz-Tracking
- `backend/v2/exceptions.py`: V2 Exception-Hierarchie — für Extraction-spezifische Errors erweitern
- `backend/v2/parsers/xlsx_parser.py`: KNOWN_FIELD_PATTERNS mit 23 Feldern und 200+ Aliases — nützlich für Pass 1 Regex-Extraktion

### Established Patterns
- `messages.parse()` mit Pydantic v2 für strukturierte AI-Outputs (Phase 1 getestet + kompatibel)
- Enum+Freitext-Pattern für alle Domain-Klassifikationen
- Structured logging mit python-json-logger
- ParseResult.tables Liste — separate Tabellen-Texte für gezieltes Chunking

### Integration Points
- `backend/v2/extraction/` — leeres Package aus Phase 1, hier kommt die Extraction-Logik rein
- v2-Router in main.py unter /api/v2/ — neuer Upload+Analyze Endpoint hier registrieren
- ParseResult → ExtractedDoorPosition ist die zentrale Transformation dieser Phase

</code_context>

<specifics>
## Specific Ideas

- Türlisten von verschiedenen Kunden haben 39-217 Spalten — Pass 1 Regex muss flexibel sein (KNOWN_FIELD_PATTERNS aus v1 XLSX-Parser als Basis)
- Pass 2 soll messages.parse(model="claude-opus-4-6", response_format=ExtractionResult) verwenden für typsichere Extraktion
- Pass 3 bekommt die bisherigen ExtractedDoorPosition-Objekte als JSON im Prompt + den Originaltext, und liefert korrigierte/ergänzte Positionen zurück
- Deduplizierung per AI: Batch von Positions-Nummern + Raum/Geschoss an Claude senden, Clustering zurückbekommen

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-multi-pass-extraction*
*Context gathered: 2026-03-10*
