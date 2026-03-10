# Requirements: FTAG KI-Angebotserstellung v2

**Defined:** 2026-03-10
**Core Value:** 100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt — oder eine explizite, begründete Gap-Meldung.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Dokument-Analyse

- [x] **DOKA-01**: System parst PDF-Dateien und extrahiert vollständigen Text mit Tabellenstruktur
- [x] **DOKA-02**: System parst DOCX-Dateien und extrahiert Text mit Formatierung
- [x] **DOKA-03**: System parst XLSX-Dateien und erkennt Türlisten-Spaltenstruktur automatisch
- [x] **DOKA-04**: System akzeptiert mehrere Dateien pro Ausschreibung (PDF + Excel + DOCX gemischt)
- [x] **DOKA-05**: System führt Multi-Pass-Analyse durch (Pass 1: strukturell, Pass 2: AI-semantisch, Pass 3: Cross-Reference-Validierung)
- [x] **DOKA-06**: System extrahiert ALLE technischen Anforderungen als einzelne Datenpunkte (Maße, Material, Normen, Zertifizierungen, Leistungsdaten)
- [x] **DOKA-07**: System reichert Positionen mit Daten aus verschiedenen Dokumenten an (Cross-Document Enrichment: Excel-Türliste + PDF-Spezifikation + DOCX-Anforderungen)
- [x] **DOKA-08**: System erkennt und meldet Konflikte zwischen Dokumenten (z.B. unterschiedliche Brandschutzklassen in verschiedenen Dateien)

### Produkt-Matching

- [x] **MATC-01**: System gleicht jede extrahierte Anforderung gegen den FTAG-Produktkatalog (~891 Produkte) ab
- [x] **MATC-02**: System bewertet jedes Match multi-dimensional (Maße, Brandschutz, Schallschutz, Material, Zertifizierung, Leistungsdaten)
- [x] **MATC-03**: System berechnet Konfidenz-Score (0-100%) pro Match mit Aufschlüsselung nach Dimension
- [x] **MATC-04**: System setzt Match-Schwellenwert bei 95%+ Konfidenz
- [x] **MATC-05**: System führt Adversarial Double-Check durch (zweiter AI-Call versucht aktiv jeden Match zu widerlegen)
- [x] **MATC-06**: System führt Triple-Check durch bei Konfidenz <95% (dritter AI-Durchlauf mit alternativem Prompt)
- [x] **MATC-07**: System begründet jeden Match mit Chain-of-Thought (Schritt-für-Schritt-Argumentation)
- [x] **MATC-08**: System listet bei mehreren möglichen Produkten alle auf mit Begründung
- [x] **MATC-09**: System integriert Feedback/Korrekturen aus früheren Analysen als Few-Shot-Examples

### Gap-Analyse

- [x] **GAPA-01**: System erstellt detaillierte Gap-Analyse für jeden Nicht-Match (welche Eigenschaft weicht ab)
- [x] **GAPA-02**: System kategorisiert Gaps nach Dimension: Maße, Material, Norm, Zertifizierung, Leistung
- [x] **GAPA-03**: System bewertet Gap-Schweregrad: Kritisch (keine Lösung), Major (signifikante Abweichung), Minor (nahe am Match)
- [x] **GAPA-04**: System generiert AI-Vorschlag was sich ändern müsste damit ein Produkt passt
- [x] **GAPA-05**: System schlägt alternative Produkte vor die den Gap schließen könnten (mit Erklärung was noch abweicht)

### Excel-Output

- [ ] **EXEL-01**: System generiert Excel mit Sheet 1 "Übersicht" — alle Anforderungen mit Match-Status (Grün/Gelb/Rot)
- [ ] **EXEL-02**: System generiert Excel mit Sheet 2 "Details" — Anforderung ↔ Produkt, Konfidenz, dimensionale Aufschlüsselung, Begründung
- [ ] **EXEL-03**: System generiert Excel mit Sheet 3 "Gap-Analyse" — alle Nicht-Matches mit Gründen, Abweichungen, Schweregrad, Alternativen
- [ ] **EXEL-04**: System generiert Excel mit Sheet 4 "Executive Summary" — Statistiken, Zusammenfassung, Empfehlungen
- [ ] **EXEL-05**: System verwendet Farbcodierung: Grün = Match (95%+), Gelb = teilweise (60-95%), Rot = kein Match (<60%)
- [ ] **EXEL-06**: Jede Entscheidungszelle enthält nachvollziehbare Begründung (WARUM so entschieden)

### Qualitätssicherung

- [ ] **QUAL-01**: System führt Ergebnis-Plausibilitätsprüfung am Ende durch (alle Positionen abgedeckt, keine Duplikate, keine verdächtigen Muster)
- [ ] **QUAL-02**: System loggt jeden Analyseschritt (welche Anforderung, welcher Pass, welches Ergebnis)
- [ ] **QUAL-03**: System zeigt Live-Fortschritt im Frontend (welcher Schritt läuft, welche Position wird verarbeitet)
- [ ] **QUAL-04**: System gibt bei AI-Ausfall klare Fehlermeldung statt degradierter Ergebnisse

### API & Integration

- [x] **APII-01**: POST /api/upload akzeptiert mehrere Dateien pro Ausschreibung
- [ ] **APII-02**: POST /api/analyze startet Multi-Pass-Analyse mit SSE-Streaming für Fortschritt
- [ ] **APII-03**: GET /api/analyze/status/{job_id} liefert detaillierten Fortschritt (Position X von Y, aktueller Pass)
- [ ] **APII-04**: POST /api/offer/generate erstellt 4-Sheet Excel-Output
- [ ] **APII-05**: GET /api/offer/{id}/download liefert generierte Excel-Datei
- [x] **APII-06**: POST /api/feedback speichert Matching-Korrekturen für zukünftige Analysen

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Erweiterte Dokument-Analyse

- **DOKA-09**: GAEB/LV-Format Unterstützung (standardisiertes Leistungsverzeichnis)
- **DOKA-10**: PDF-Plan/Zeichnungs-Analyse mit Computer Vision

### Erweiterte Integration

- **APII-07**: ERP-Anbindung (Bohr System) für Live-Preise
- **APII-08**: Automatische Angebotserstellung mit Preiskalkulation

### Frontend

- **FRNT-01**: Modernes Dashboard mit Analyse-Historie
- **FRNT-02**: Interaktive Ergebnis-Bearbeitung im Browser

## Out of Scope

| Feature | Reason |
|---------|--------|
| Ollama/Local-LLM Fallback | Nur Claude API — Genauigkeit vor Kosten |
| Frontend-Redesign | Backend-Fokus, minimales UI reicht für Vertrieb |
| Benutzer-Authentifizierung | Kleine interne Nutzung, kein externer Zugriff |
| ERP-Integration | Separates Projekt, Excel reicht als Schnittstelle |
| Embedding-basierte Suche | TF-IDF ausreichend bei 891 Produkten |
| Automatische Preisfindung | Zu risikoreich, Vertrieb setzt Preise manuell |
| Echtzeit-Kollaboration | Vertrieb arbeitet einzeln an Ausschreibungen |
| PDF-Plan-Analyse | Erfordert spezialisierte CV-Modelle, unzuverlässig |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOKA-01 | Phase 1 | Complete |
| DOKA-02 | Phase 1 | Complete |
| DOKA-03 | Phase 1 | Complete |
| DOKA-04 | Phase 2 | Complete |
| DOKA-05 | Phase 2 | Complete |
| DOKA-06 | Phase 2 | Complete |
| DOKA-07 | Phase 3 | Complete |
| DOKA-08 | Phase 3 | Complete |
| MATC-01 | Phase 4 | Complete |
| MATC-02 | Phase 4 | Complete |
| MATC-03 | Phase 4 | Complete |
| MATC-04 | Phase 4 | Complete |
| MATC-05 | Phase 5 | Complete |
| MATC-06 | Phase 5 | Complete |
| MATC-07 | Phase 5 | Complete |
| MATC-08 | Phase 5 | Complete |
| MATC-09 | Phase 4 | Complete |
| GAPA-01 | Phase 6 | Complete |
| GAPA-02 | Phase 6 | Complete |
| GAPA-03 | Phase 6 | Complete |
| GAPA-04 | Phase 6 | Complete |
| GAPA-05 | Phase 6 | Complete |
| EXEL-01 | Phase 7 | Pending |
| EXEL-02 | Phase 7 | Pending |
| EXEL-03 | Phase 7 | Pending |
| EXEL-04 | Phase 7 | Pending |
| EXEL-05 | Phase 7 | Pending |
| EXEL-06 | Phase 7 | Pending |
| QUAL-01 | Phase 8 | Pending |
| QUAL-02 | Phase 8 | Pending |
| QUAL-03 | Phase 8 | Pending |
| QUAL-04 | Phase 8 | Pending |
| APII-01 | Phase 2 | Complete |
| APII-02 | Phase 8 | Pending |
| APII-03 | Phase 8 | Pending |
| APII-04 | Phase 7 | Pending |
| APII-05 | Phase 7 | Pending |
| APII-06 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after roadmap creation*
