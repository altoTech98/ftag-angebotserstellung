# FTAG KI-Angebotserstellung v2

## What This Is

Ein KI-gestütztes System für Frank Türen AG, das Ausschreibungsunterlagen (PDF, DOCX, XLSX) mit Multi-Pass-Analyse und Adversarial Validation analysiert, jede technische Anforderung gegen den FTAG-Produktkatalog (~891 Produkte) 6-dimensional abgleicht, und ein professionelles 4-Sheet Excel-Angebot mit lückenloser Nachvollziehbarkeit generiert. Shipped als v1.0.

## Core Value

100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt — oder eine explizite, begründete Gap-Meldung. Keine "best guess" Matches. Genauigkeit vor Effizienz, Kosten irrelevant.

## Requirements

### Validated

- ✓ PDF/DOCX/XLSX Parsing mit Format-Autoerkennung — v1.0
- ✓ Multi-Pass Extraktion (strukturell + AI semantisch + Cross-Reference) — v1.0
- ✓ Multi-Datei Upload (PDF + Excel + DOCX gemischt) — v1.0
- ✓ Cross-Document Intelligence (Enrichment + Konflikterkennung) — v1.0
- ✓ TF-IDF + Claude AI Product Matching (891 Produkte, 6 Dimensionen) — v1.0
- ✓ Konfidenz-Score 0-100% mit 95% Schwellenwert — v1.0
- ✓ Adversarial Double-Check (FOR/AGAINST Debate) — v1.0
- ✓ Triple-Check Ensemble bei <95% Konfidenz — v1.0
- ✓ Chain-of-Thought Begründung für jeden Match — v1.0
- ✓ Detaillierte Gap-Analyse mit Schweregrad und Alternativen — v1.0
- ✓ 4-Sheet Excel Output (Übersicht, Details, Gap-Analyse, Executive Summary) — v1.0
- ✓ Farbcodierung (Grün/Gelb/Rot) mit nachvollziehbarer Begründung — v1.0
- ✓ Feedback-System für Matching-Korrekturen (Few-Shot Learning) — v1.0
- ✓ Live-Fortschrittsanzeige mit SSE Streaming — v1.0
- ✓ Plausibilitätsprüfung am Ende — v1.0
- ✓ FastAPI REST-API mit allen v2 Endpoints — v1.0
- ✓ React Frontend mit v2 Pipeline Integration — v1.0

### Active

(No active requirements — start next milestone with `/gsd:new-milestone`)

### Out of Scope

- GAEB/LV-Format Unterstützung — standardisiertes Leistungsverzeichnis, eigenes Parsing nötig
- PDF-Plan/Zeichnungs-Analyse — erfordert spezialisierte CV-Modelle
- ERP-Anbindung (Bohr System) — separates Projekt, Excel reicht als Schnittstelle
- Automatische Preisfindung — zu risikoreich, Vertrieb setzt Preise manuell
- Benutzer-Authentifizierung — kleine interne Nutzung, kein externer Zugriff
- Ollama/Local-LLM Fallback — nur Claude API, Genauigkeit vor Kosten
- Mobile App — Web-only
- Echtzeit-Kollaboration — Vertrieb arbeitet einzeln

## Context

**Shipped v1.0** with ~11,070 lines v2 code (Python + React), 9 phases, 21 plans, 38/38 requirements.
**Tech stack:** Python + FastAPI (Backend), Claude API (Opus + Sonnet), React (Frontend), openpyxl (Excel).
**Pipeline:** Upload → 3-Pass Extraction → Cross-Doc Intelligence → TF-IDF+AI Matching → Adversarial Validation → Gap Analysis → Excel Generation.
**Produktkatalog:** ~891 FTAG-Produkte mit Maßen, Materialien, Normen, Zertifizierungen, Leistungsdaten.

**Known tech debt:**
- SSE progress events use `asyncio.Queue.put_nowait()` cross-thread (not thread-safe); fallback polling compensates
- 2 human verification items pending in Phase 3 (live API key testing for cross-doc features)

## Constraints

- **Tech Stack**: Python + FastAPI (Backend), Claude API als einziges AI-Modell (Opus/Sonnet)
- **AI-Strategie**: Mehrfach-Validierung zwingend — kein Single-Pass erlaubt
- **Genauigkeit**: Match-Schwellenwert 95%+ Konfidenz, darunter = Gap
- **Kosten**: Explizit irrelevant — Qualität hat absoluten Vorrang
- **Kompatibilität**: Bestehender Produktkatalog (produktuebersicht.xlsx) muss weiterhin funktionieren

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Komplett-Neubau statt Upgrade | v1-Architektur nicht für Mehrfach-Validierung ausgelegt | ✓ Good — v2 pipeline dramatically more reliable |
| Adversarial Double-Check | Zweiter AI-Durchlauf als Devil's Advocate erhöht Zuverlässigkeit | ✓ Good — catches false positives effectively |
| Nur Claude API, kein Ollama | Genauigkeit vor Kosten, bestes Modell nötig | ✓ Good — structured output via messages.parse() critical |
| Backend-Fokus, minimales Frontend | Vertrieb braucht Upload + Download + Live-Log, kein fancy UI | ✓ Good — React frontend sufficient for workflow |
| 4-Sheet Excel-Output | Übersicht, Details, Gaps, Summary — alles auf einen Blick | ✓ Good — sales team can use directly |
| Deterministic adversarial resolution | Weighted avg statt dritter Opus-Call für Cost Efficiency | ✓ Good — consistent results, lower cost |
| Safety-critical dimension weighting | Brandschutz 2x, Masse/Schallschutz 1.5x | ✓ Good — prevents false confirmations on safety items |
| TF-IDF pre-filter (top_k=50) | Reduces 891 → ~50 candidates before Claude call | ✓ Good — efficient without missing matches |
| Enum+Freitext pattern | All domain classifications have enum + freetext fallback | ✓ Good — handles non-standard values gracefully |

---
*Last updated: 2026-03-10 after v1.0 milestone*
