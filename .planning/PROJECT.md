# FTAG KI-Angebotserstellung v2

## What This Is

Ein KI-gestuetztes System fuer Frank Tueren AG, das Ausschreibungsunterlagen (PDF, DOCX, XLSX) analysiert, jede technische Anforderung gegen den FTAG-Produktkatalog 6-dimensional abgleicht, und ein professionelles 4-Sheet Excel-Angebot generiert. Jetzt als professionelle SaaS-Web-Applikation mit Next.js Frontend, Rollen-System, Projektverwaltung, und Katalog-Management. Shipped als v2.0.

## Core Value

100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt — oder eine explizite, begruendete Gap-Meldung. Keine "best guess" Matches. Genauigkeit vor Effizienz, Kosten irrelevant.

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
- ✓ Chain-of-Thought Begruendung fuer jeden Match — v1.0
- ✓ Detaillierte Gap-Analyse mit Schweregrad und Alternativen — v1.0
- ✓ 4-Sheet Excel Output (Uebersicht, Details, Gap-Analyse, Executive Summary) — v1.0
- ✓ Farbcodierung (Gruen/Gelb/Rot) mit nachvollziehbarer Begruendung — v1.0
- ✓ Feedback-System fuer Matching-Korrekturen (Few-Shot Learning) — v1.0
- ✓ Live-Fortschrittsanzeige mit SSE Streaming — v1.0
- ✓ Plausibilitaetspruefung am Ende — v1.0
- ✓ FastAPI REST-API mit allen v2 Endpoints — v1.0
- ✓ React Frontend mit v2 Pipeline Integration — v1.0
- ✓ Next.js 16 App Router Frontend mit Tailwind CSS 4 (FTAG Rot/Weiss Design-System) — v2.0
- ✓ Better Auth Authentifizierung mit 4-Rollen RBAC (Admin/Manager/Analyst/Viewer) — v2.0
- ✓ Dashboard mit Status-Karten, Aktivitaeten-Feed, Match/Gap-Statistiken — v2.0
- ✓ 5-Schritt Analyse-Wizard (Upload → Katalog → Konfiguration → Start → Ergebnis) — v2.0
- ✓ Ergebnis-Ansicht mit Filter, Sortierung, Detail-Aufklappung, Excel-Export — v2.0
- ✓ Produktkatalog-Verwaltung (Upload, Suche, Versionen, CRUD) — v2.0
- ✓ Projektverwaltung (CRUD, Historie, Archivierung, Sharing) — v2.0
- ✓ Admin-Bereich (Benutzerverwaltung, Audit-Log, Systemeinstellungen, API-Keys) — v2.0
- ✓ Prisma 7 + Neon Postgres + Vercel Blob Storage — v2.0
- ✓ BFF-Pattern: Next.js API Routes proxyen zu Python/FastAPI Backend — v2.0
- ✓ E-Mail-Versand (Passwort-Reset, Analyse-fertig-Benachrichtigung) — v2.0

### Active

(None — define with `/gsd:new-milestone`)

### Out of Scope

- GAEB/LV-Format Unterstuetzung — standardisiertes Leistungsverzeichnis, eigenes Parsing noetig
- PDF-Plan/Zeichnungs-Analyse — erfordert spezialisierte CV-Modelle
- ERP-Anbindung (Bohr System) — separates Projekt, Excel reicht als Schnittstelle
- Automatische Preisfindung — zu risikoreich, Vertrieb setzt Preise manuell
- Ollama/Local-LLM Fallback — nur Claude API, Genauigkeit vor Kosten
- Mobile App — Web-only, Responsive reicht
- Echtzeit-Kollaboration — Vertrieb arbeitet einzeln
- 2FA — v3.0+, nicht kritisch fuer internen Einsatz
- PDF-Export — v3.0+, Excel reicht vorerst
- Dunkelmodus — v3.0+, Nice-to-Have
- Mehrsprachigkeit (DE/EN) — v3.0+, FTAG arbeitet auf Deutsch
- Multi-Tenancy — v3.0+, Architektur vorbereiten aber nicht implementieren
- Python-nach-TypeScript Portierung — Python-Backend bleibt, bewaehrt sich

## Context

**Shipped v2.0** with ~40,759 lines TypeScript (frontend) + Python backend, 9 phases, 26 plans, 42/42 requirements.
**Tech stack:** Next.js 16 + Tailwind CSS 4 + shadcn/ui (Frontend), Better Auth + Prisma 7 + Neon Postgres (Auth/DB), Vercel Blob (Storage), Python + FastAPI (AI Backend), Claude API (Sonnet), Resend (Email).
**Architecture:** Next.js BFF proxies to Python/FastAPI; SSE streams direct from Python to browser; Vercel Blob for file storage.
**Pipeline:** Upload → 3-Pass Extraction → Cross-Doc Intelligence → TF-IDF+AI Matching → Adversarial Validation → Gap Analysis → Excel Generation.
**Produktkatalog:** ~891 FTAG-Produkte mit Massen, Materialien, Normen, Zertifizierungen, Leistungsdaten.

**Known tech debt (v2.0):**
- 8 test stub files remain it.todo() with no real assertions
- Excel download payload sends wrong structure for requirements field (data quality)
- Config thresholds from wizard step 3 not forwarded to Python
- Session timeout not configurable via admin SystemSettings
- SSE polling fallback endpoint on Python side unverified
- compareVersions server action exported but never called from UI
- getActivityFeed exported but never imported (dead code)

## Constraints

- **Tech Stack**: Python + FastAPI (Backend), Next.js 16 (Frontend), Claude API als einziges AI-Modell
- **AI-Strategie**: Mehrfach-Validierung zwingend — kein Single-Pass erlaubt
- **Genauigkeit**: Match-Schwellenwert 95%+ Konfidenz, darunter = Gap
- **Kosten**: Explizit irrelevant — Qualitaet hat absoluten Vorrang
- **Kompatibilitaet**: Bestehender Produktkatalog (produktuebersicht.xlsx) muss weiterhin funktionieren
- **Deployment**: Vercel (Frontend) + Railway (Python Backend) + Neon (Postgres)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Komplett-Neubau statt Upgrade | v1-Architektur nicht fuer Mehrfach-Validierung ausgelegt | ✓ Good — v2 pipeline dramatically more reliable |
| Adversarial Double-Check | Zweiter AI-Durchlauf als Devil's Advocate | ✓ Good — catches false positives effectively |
| Nur Claude API, kein Ollama | Genauigkeit vor Kosten | ✓ Good — structured output via messages.parse() critical |
| 4-Sheet Excel-Output | Uebersicht, Details, Gaps, Summary | ✓ Good — sales team can use directly |
| Safety-critical dimension weighting | Brandschutz 2x, Masse/Schallschutz 1.5x | ✓ Good — prevents false confirmations on safety items |
| TF-IDF pre-filter (top_k=50) | Reduces 891 → ~50 candidates before Claude call | ✓ Good — efficient without missing matches |
| Better Auth (not NextAuth) | Official successor, built-in RBAC plugin | ✓ Good — clean 4-role system with invite-only flow |
| Prisma 7 + Neon Postgres | Pure TS engine, Better Auth adapter | ✓ Good — serverless-friendly, fast cold starts |
| BFF pattern with direct SSE | Next.js proxies CRUD; SSE direct to Python | ✓ Good — Vercel can't reliably proxy SSE |
| Vercel Blob for uploads | Presigned URLs bypass 4.5 MB body limit | ✓ Good — large tender docs upload cleanly |
| Tailwind CSS 4 with CSS-first config | No tailwind.config.js needed | ✓ Good — simpler setup, @theme directive |
| Railway for Python backend | No timeout limits unlike Vercel Functions | ✓ Good — long-running AI analysis works |

---
*Last updated: 2026-03-11 after v2.0 milestone completion*
