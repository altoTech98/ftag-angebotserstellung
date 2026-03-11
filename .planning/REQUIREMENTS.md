# Requirements: AI Tender Matcher v2.0

**Defined:** 2026-03-10
**Core Value:** 100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt -- oder eine explizite, begruendete Gap-Meldung. Keine "best guess" Matches.

## v2.0 Requirements

Requirements for the SaaS platform milestone. Each maps to roadmap phases.

### Auth & Security

- [x] **AUTH-01**: User kann sich mit E-Mail und Passwort einloggen
- [x] **AUTH-02**: User kann Passwort per E-Mail-Link zuruecksetzen
- [x] **AUTH-03**: Session wird automatisch nach konfigurierbarer Inaktivitaet beendet (mit Warnung)
- [x] **AUTH-04**: System unterstuetzt 4 Rollen: Admin, Manager, Analyst, Viewer
- [x] **AUTH-05**: Routen und API-Endpoints sind rollenbasiert geschuetzt
- [x] **AUTH-06**: JWT-Token-Bridging zwischen Next.js und Python-Backend

### Design System & Layout

- [x] **UI-01**: Rot/Weiss Design-System (Tailwind CSS 4 + shadcn/ui) nach Spezifikation
- [x] **UI-02**: Responsive Layout (Desktop, Tablet, Mobil)
- [x] **UI-03**: Sidebar-Navigation mit rotem Akzent fuer aktives Item
- [x] **UI-04**: Breadcrumb-Navigation auf allen Seiten
- [ ] **UI-05**: Keyboard-Shortcuts fuer Power-User (N=Neue Analyse etc.)
- [ ] **UI-06**: Skeleton-Loader statt Spinner, benutzerfreundliche Fehlermeldungen

### Dashboard

- [ ] **DASH-01**: Status-Karten: Laufende / Abgeschlossene / Fehlerhafte Analysen
- [ ] **DASH-02**: Letzte Aktivitaeten Feed (wer hat was wann gemacht)
- [ ] **DASH-03**: Statistik-Widget: Gesamtzahl Matches, Gaps, Durchschnitts-Konfidenz
- [ ] **DASH-04**: Schnellzugriff-Button "Neue Analyse starten"

### Analyse-Wizard

- [ ] **ANLZ-01**: Schritt 1 -- Drag & Drop Upload (PDF/DOCX/XLSX) via Vercel Blob
- [ ] **ANLZ-02**: Schritt 2 -- Produktkatalog auswaehlen oder neu hochladen
- [ ] **ANLZ-03**: Schritt 3 -- Schwellenwerte und Validierungsdurchlaeufe konfigurieren
- [ ] **ANLZ-04**: Schritt 4 -- Analyse starten mit Echtzeit-Fortschrittsbalken (SSE direkt zu Python)
- [ ] **ANLZ-05**: Schritt 5 -- Ergebnis-Ansicht mit Tabs (Matches/Gaps/Zusammenfassung)

### Ergebnis-Ansicht

- [ ] **RSLT-01**: Tabellarische Darstellung aller Anforderungen mit Filter und Sortierung
- [ ] **RSLT-02**: Aufklappbare Detail-Ansicht pro Anforderung (AI-Begruendung, Dimensionen)
- [ ] **RSLT-03**: Vergleichsansicht: Anforderung links vs. Produkt rechts
- [ ] **RSLT-04**: Excel-Export (vollstaendige Ergebnis-Excel wie v1.0)

### Projektverwaltung

- [ ] **PROJ-01**: Projekte anlegen (Name, Kunde, Frist, Beschreibung)
- [ ] **PROJ-02**: Mehrere Analysen pro Projekt mit Historie
- [ ] **PROJ-03**: Projekte archivieren und loeschen
- [ ] **PROJ-04**: Projekte mit anderen Benutzern teilen

### Katalogverwaltung

- [ ] **KAT-01**: Kataloge hochladen (Excel/CSV) mit Import-Validierung
- [ ] **KAT-02**: Kataloge durchsuchen und filtern
- [ ] **KAT-03**: Katalog-Versionen verwalten (alt vs. neu)
- [ ] **KAT-04**: Einzelne Produkte bearbeiten/hinzufuegen/loeschen

### Admin-Bereich

- [ ] **ADMIN-01**: Benutzerverwaltung (anlegen, bearbeiten, deaktivieren, Rollen zuweisen)
- [ ] **ADMIN-02**: Aktivitaets-Log / Audit-Trail
- [ ] **ADMIN-03**: System-Einstellungen (Standard-Schwellenwerte, Max-Upload-Groesse, Session-Timeout)
- [ ] **ADMIN-04**: API-Key-Verwaltung (Claude API Key etc.)

### Infrastruktur

- [x] **INFRA-01**: Next.js 16 App Router + Prisma 7 + Neon Postgres (via Vercel)
- [x] **INFRA-02**: Python/FastAPI auf Railway deployen mit Service-Auth
- [ ] **INFRA-03**: BFF-Pattern: Next.js API Routes proxyen zu Python-Backend
- [ ] **INFRA-04**: Vercel Blob Storage fuer Datei-Uploads (signed URLs)
- [ ] **INFRA-05**: E-Mail-Versand (Passwort-Reset, Analyse-fertig-Benachrichtigung)

## v3.0+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Auth Enhancements

- **AUTH-07**: Zwei-Faktor-Authentifizierung (2FA) per E-Mail oder TOTP

### UI Enhancements

- **UI-07**: Dunkelmodus (Dunkelgrau-Hintergrund, Rot als Akzent)
- **UI-08**: Mehrsprachigkeit (Deutsch Standard, Englisch als Option)

### Export

- **EXPORT-01**: PDF-Export fuer Management-Zusammenfassung

### Platform

- **PLAT-01**: Multi-Tenancy (mehrere Firmen/Mandanten mit getrennten Daten)
- **PLAT-02**: Onboarding-Wizard beim ersten Login
- **PLAT-03**: Hilfe-Tooltips bei komplexen Einstellungen
- **PLAT-04**: DSGVO Datenexport (alle eigenen Daten exportierbar)
- **PLAT-05**: Impressum / Datenschutz-Seiten

## Out of Scope

| Feature | Reason |
|---------|--------|
| GAEB/LV-Format Unterstuetzung | Eigenes Parsing noetig, nicht im SaaS-Scope |
| PDF-Plan/Zeichnungs-Analyse | Erfordert spezialisierte CV-Modelle |
| ERP-Anbindung (Bohr System) | Separates Projekt |
| Automatische Preisfindung | Zu risikoreich, Vertrieb setzt Preise manuell |
| Echtzeit-Kollaboration | Vertrieb arbeitet einzeln |
| Ollama/Local-LLM | Nur Claude API |
| Mobile App | Web-only, Responsive reicht |
| Real-time Chat | High complexity, nicht core |
| Python-nach-TypeScript Portierung | Python-Backend bleibt, bewaehrt sich |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 10 | Complete |
| AUTH-02 | Phase 10 | Complete |
| AUTH-03 | Phase 10 | Complete |
| AUTH-04 | Phase 10 | Complete |
| AUTH-05 | Phase 10 | Complete |
| AUTH-06 | Phase 11 | Complete |
| UI-01 | Phase 10 | Complete |
| UI-02 | Phase 10 | Complete |
| UI-03 | Phase 10 | Complete |
| UI-04 | Phase 10 | Complete |
| UI-05 | Phase 15 | Pending |
| UI-06 | Phase 15 | Pending |
| DASH-01 | Phase 15 | Pending |
| DASH-02 | Phase 15 | Pending |
| DASH-03 | Phase 15 | Pending |
| DASH-04 | Phase 15 | Pending |
| ANLZ-01 | Phase 12 | Pending |
| ANLZ-02 | Phase 13 | Pending |
| ANLZ-03 | Phase 13 | Pending |
| ANLZ-04 | Phase 13 | Pending |
| ANLZ-05 | Phase 13 | Pending |
| RSLT-01 | Phase 13 | Pending |
| RSLT-02 | Phase 13 | Pending |
| RSLT-03 | Phase 13 | Pending |
| RSLT-04 | Phase 13 | Pending |
| PROJ-01 | Phase 12 | Pending |
| PROJ-02 | Phase 12 | Pending |
| PROJ-03 | Phase 12 | Pending |
| PROJ-04 | Phase 12 | Pending |
| KAT-01 | Phase 14 | Pending |
| KAT-02 | Phase 14 | Pending |
| KAT-03 | Phase 14 | Pending |
| KAT-04 | Phase 14 | Pending |
| ADMIN-01 | Phase 15 | Pending |
| ADMIN-02 | Phase 15 | Pending |
| ADMIN-03 | Phase 15 | Pending |
| ADMIN-04 | Phase 15 | Pending |
| INFRA-01 | Phase 10 | Complete |
| INFRA-02 | Phase 11 | Complete |
| INFRA-03 | Phase 11 | Pending |
| INFRA-04 | Phase 12 | Pending |
| INFRA-05 | Phase 15 | Pending |

**Coverage:**
- v2.0 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after roadmap creation*
