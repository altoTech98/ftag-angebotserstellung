# Phase 1: Document Parsing & Pipeline Schemas - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Robust per-format parsers (PDF, DOCX, XLSX) that produce raw text output, plus Pydantic data contracts (schemas) for the entire v2 pipeline. Parsers deliver text; AI structuring happens in Phase 2. Schemas define the data contracts between all pipeline stages (extraction, matching, validation, gap analysis, output).

</domain>

<decisions>
## Implementation Decisions

### Pydantic-Schema-Design
- Maximale Feld-Tiefe: Jede Tür-Eigenschaft ein eigenes Feld (~50+ Felder: breite_mm, hoehe_mm, brandschutz_klasse, schallschutz_db, material_blatt, material_zarge, etc.)
- Feldnamen auf Deutsch (breite_mm, brandschutz_klasse, schallschutz_db) — konsistent mit Produktkatalog und Ausschreibungen
- Strikt + Freitext: Bekannte Werte als Enums (Brandschutz-Klassen, Schallschutz-Klassen, Materialien), aber mit Optional[str] Freitext-Feld für Unbekanntes/Unerwartetes
- Quellen-Tracking pro Feld: Jedes Feld hat source_document + source_location (Seite/Zeile/Zelle) — Provenienz auf Feld-Ebene, nicht nur pro Anforderung
- Schemas müssen mit `anthropic>=0.84.0` `messages.parse()` kompatibel sein (Pydantic v2)

### Parser-Strategie
- v1 excel_parser.py Logik (Header-Detect, Merged Cells, fuzzy Column Matching) übernehmen, aber sauber neu schreiben in v2-Struktur
- PDF: pymupdf4llm als Primär-Parser, pdfplumber nur als Fallback für spezielle Fälle
- Alle Parser liefern Roh-Text — AI macht die Strukturierung komplett (einheitlicher Ansatz, Strukturierung in Phase 2)
- OCR-Unterstützung mit Tesseract für gescannte PDFs (v1 hat bereits pytesseract-Integration)

### Datei-Organisation
- Neuer Ordner `backend/v2/` — saubere Trennung von v1
- Struktur nach Pipeline-Stufe: `v2/parsers/`, `v2/extraction/`, `v2/matching/`, `v2/validation/`, `v2/gaps/`, `v2/output/`
- v1 und v2 koexistieren während Entwicklung (verschiedene Endpoints), am Ende v1 entfernen
- Neue eigene Exception-Hierarchie in `backend/v2/` — keine Abhängigkeit von v1-Exceptions

### Fehlerbehandlung
- Bei teilweise lesbaren Dokumenten: Weitermachen + warnen (so viel wie möglich extrahieren, Fehler als Warnings loggen)
- Nur offensichtlich irrelevante Seiten filtern (leere Seiten, Deckblätter) — Rest geht an AI in Phase 2
- Parse-Warnungen nur im Logging, nicht im Pydantic-Schema
- Korrupte/passwortgeschützte Dateien: Versuchen zu parsen, bei Scheitern als Warning melden und mit anderen Dateien weitermachen

### Claude's Discretion
- Genaue Enum-Werte für Brandschutz/Schallschutz/Material (basierend auf Produktkatalog-Analyse)
- pymupdf4llm vs pdfplumber Fallback-Logik
- Interne Hilfsstrukturen und Utility-Funktionen
- Genaue Ordnerstruktur innerhalb der Pipeline-Stufen

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `excel_parser.py`: Header-Auto-Detect, Merged-Cell-Handling, fuzzy Column Matching — Logik übernehmen in neuer Struktur
- `document_parser.py`: Format-Detection, Byte-Parsing-Interface — als Referenz für v2 Parser-API
- `fast_matcher.py`: `_door_signature()` für Deduplizierung — nützlich für spätere Phasen
- `error_handler.py` + `exceptions.py`: Exception-Pattern als Vorlage für v2-Hierarchie

### Established Patterns
- Singleton-Pattern für Services (`get_ai_service()`) — v2 kann ähnlich machen
- Structured logging mit `python-json-logger` — beibehalten
- FastAPI Router-Pattern für Endpoints — konsistent halten

### Integration Points
- `backend/v2/` als neues Package neben `backend/services/`
- v2-Router registriert in `main.py` unter eigenem Prefix (z.B. `/api/v2/`)
- Produktkatalog (`data/produktuebersicht.xlsx`) wird von v2 genauso geladen — CatalogIndex oder neue Version davon
- Feedback-Store (`matching_feedback.json`) bleibt kompatibel

</code_context>

<specifics>
## Specific Ideas

- Produktkatalog hat ~318 Spalten — Schema muss die wichtigsten ~50+ Eigenschaften abdecken die für Matching relevant sind
- Türlisten von verschiedenen Kunden haben 39-217 Spalten — Parser muss flexibel sein
- Deutsch als Feldsprache wegen direkter Zuordnung zu Ausschreibungs- und Katalog-Begriffen

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-document-parsing-pipeline-schemas*
*Context gathered: 2026-03-10*
