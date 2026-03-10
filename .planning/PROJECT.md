# FTAG KI-Angebotserstellung v2

## What This Is

Ein KI-gestütztes System für Frank Türen AG, das Ausschreibungsunterlagen (PDF, DOCX, XLSX) analysiert, jede technische Anforderung gegen den FTAG-Produktkatalog (~891 Produkte) abgleicht, und ein vollständiges Excel-Angebot mit lückenloser Nachvollziehbarkeit generiert. Das Vertriebsteam kann daraus direkt ein Kundenangebot erstellen.

## Core Value

100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt — oder eine explizite, begründete Gap-Meldung. Keine "best guess" Matches. Genauigkeit vor Effizienz, Kosten irrelevant.

## Requirements

### Validated

<!-- Bestehende Funktionalität aus v1 die funktioniert und beibehalten wird -->

- ✓ Datei-Upload (PDF, DOCX, XLSX) — existing
- ✓ PDF-Textextraktion (PyMuPDF + pdfplumber) — existing
- ✓ Word-Parsing (python-docx) — existing
- ✓ Excel-Parsing (openpyxl/pandas) — existing
- ✓ Produktkatalog-Laden aus Excel (~891 Produkte) — existing
- ✓ FastAPI REST-API mit CORS — existing
- ✓ Feedback-System für Matching-Korrekturen — existing
- ✓ Hintergrund-Job-Verarbeitung mit SSE-Streaming — existing

### Active

- [ ] Mehrfach-Durchlauf Dokumentanalyse (jedes Dokument wird mehrmals geparst um nichts zu übersehen)
- [ ] Multi-Datei-Analyse (PDF + Excel + DOCX gemischt in einer Ausschreibung)
- [ ] Strukturierte Extraktion ALLER technischen Anforderungen als einzelne Datenpunkte
- [ ] Multi-dimensionaler Produktabgleich (Maße, Material, Normen, Leistungsdaten, Zertifizierungen, Preis)
- [ ] Konfidenz-Score pro Match (0-100%) mit Schwellenwert 95%+
- [ ] Adversarial Double-Check: Zweiter AI-Durchlauf versucht aktiv jeden Match zu widerlegen
- [ ] Triple-Check bei Unsicherheit (<95%): Dritter Durchlauf mit alternativem Prompt
- [ ] Detaillierte Gap-Analyse bei Nicht-Match (welche Eigenschaft weicht ab, Schweregrad, Vorschlag)
- [ ] Gap-Kategorisierung: Maße, Material, Norm, Zertifizierung, Leistung
- [ ] Alternative Produktvorschläge bei Gaps
- [ ] Excel-Output Sheet 1: Übersicht aller Anforderungen mit Match-Status
- [ ] Excel-Output Sheet 2: Detaillierte Match-Ergebnisse (Anforderung ↔ Produkt, Konfidenz, Begründung)
- [ ] Excel-Output Sheet 3: Gap-Analyse (Nicht-Matches mit Gründen, Abweichungen, Schweregrad)
- [ ] Excel-Output Sheet 4: Executive Summary
- [ ] Farbcodierung: Grün = Match, Gelb = teilweise, Rot = kein Match
- [ ] Nachvollziehbarkeit: Jede Zelle erklärt WARUM so entschieden wurde
- [ ] Chain-of-Thought: AI begründet jeden Schritt
- [ ] Logging jedes Analyseschritts
- [ ] Live-Fortschrittsanzeige im Frontend (welcher Schritt gerade läuft)
- [ ] Ergebnis-Plausibilitätsprüfung am Ende

### Out of Scope

- Neues Frontend-Design — Backend-Fokus, Frontend minimal (Upload + Download + Live-Log)
- Mobile App — Web-only
- ERP-Integration — nicht Teil von v2
- Benutzer-Authentifizierung — nicht im Scope des Neubaus
- Ollama/Local-LLM-Fallback — v2 nutzt ausschließlich Claude (bestes Modell, Kosten irrelevant)

## Context

**Brownfield-Projekt:** v1 existiert bereits mit funktionierender Pipeline (Upload → Analyse → Matching → Excel). Der Neubau nutzt v1 als Referenz, baut aber die Core-Engine komplett neu.

**Bekannte Probleme aus v1:**
1. Falsche Matches — Produkte wurden falsch zugeordnet
2. Übersehene Anforderungen — Dokument-Parsing hat Anforderungen verpasst
3. Fehlende Nachvollziehbarkeit — Nicht ersichtlich WARUM ein Match gemacht wurde

**Produktkatalog:** ~891 FTAG-Produkte, sehr detailliert (Maße, Materialien, Normen, Zertifizierungen, Leistungsdaten vorhanden).

**Typische Ausschreibung:** Mehrere Dateien gemischt (PDF + Excel + DOCX), 200-500+ technische Anforderungen pro Ausschreibung.

**Endnutzer:** Vertriebsteam erstellt aus dem Excel-Output direkt Kundenangebote — Excel muss so klar sein, dass keine Rückfragen nötig sind.

## Constraints

- **Tech Stack**: Python + FastAPI (Backend), Claude API als einziges AI-Modell (Opus/Sonnet)
- **AI-Strategie**: Mehrfach-Validierung zwingend — kein Single-Pass erlaubt
- **Genauigkeit**: Match-Schwellenwert 95%+ Konfidenz, darunter = Gap
- **Kosten**: Explizit irrelevant — Qualität hat absoluten Vorrang
- **Kompatibilität**: Bestehender Produktkatalog (produktuebersicht.xlsx) muss weiterhin funktionieren

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Komplett-Neubau statt Upgrade | v1-Architektur nicht für Mehrfach-Validierung ausgelegt | — Pending |
| Adversarial Double-Check | Zweiter AI-Durchlauf als Devil's Advocate erhöht Zuverlässigkeit | — Pending |
| Nur Claude API, kein Ollama | Genauigkeit vor Kosten, bestes Modell nötig | — Pending |
| Backend-Fokus, minimales Frontend | Vertrieb braucht Upload + Download + Live-Log, kein fancy UI | — Pending |
| 4-Sheet Excel-Output | Übersicht, Details, Gaps, Summary — alles auf einen Blick | — Pending |

---
*Last updated: 2026-03-10 after initialization*
