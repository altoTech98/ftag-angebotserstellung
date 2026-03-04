# Frank Türen AG – Projektjournal & Roadmap

## 📋 Projekt-Übersicht

**Projekt**: KI-gestützte Angebotserstellung für Frank Türen AG
**Status**: MVP aktiv (Desktop-basiert)
**Technologie**: FastAPI (Python) + Vanilla JS Frontend
**Zielgruppe**: Innendienst (Angebotserstellung), später: Kunden (Eigenservice)

---

## ✅ Bisher Umgesetzt

### Phase 1: Grundgerüst (✓ Abgeschlossen)
- **Frontend**: Single-Page App (Upload, Analyse, Historia, Katalog)
- **Backend**: FastAPI mit modularem Router-System
- **Dateiverarbeitung**: 
  - Excel (.xlsx) direkt parsbar
  - PDF/Word via Claude API (Textextraktion)
  - TXT-Import
- **Produktkatalog**: Statisch aus `produktuebersicht.xlsx` (~884 Produkte)

### Phase 2: Intelligentes Matching (✓ Abgeschlossen)
- **Regelbasiertes Matching**: 
  - Brandschutz (EI30=T30, Hierarchie)
  - Schallschutz (dB-Vergleich)
  - Einbruchschutz (RC2=WK2)
  - Abmessungen (Breite/Höhe)
  - Flügelanzahl
  - Verglasung
- **Score-System**: 60+ = erfüllbar, 35-59 = teilweise, <35 = nicht erfüllbar
- **Excel-Export**: Machbarkeitsanalyse + GAP-Report

### Phase 3: Nutzererlebnis (✓ Abgeschlossen)
- **Drag-Drop Upload**: Datei- und Ordner-Upload
- **Progressive Analyse**: Live-Status während Verarbeitung
- **Katalog-Editor**: Inline-Bearbeitung im Frontend
- **Feedback-System**: Korrektur von Fehlmatchings speichern
- **Analyse-Historie**: Vergangene Analysen abrufbar und neuerstellbar

### Phase 4: Infrastruktur (✓ Abgeschlossen)
- **Ollama-Integration**: Lokale LLM für Metadaten-Extraktion (optional)
- **Telegram-Bot**: Benachrichtigungen (optional)
- **Deployment-ready**: Dockerfile, Railway.toml, Render.yaml
- **Caching**: In-Memory-Cache (Text, Offers, Projects)

---

## 🚧 Aktueller Status – Bekannte Limitierungen

### 1. **Offline-Produktkatalog**
- ❌ Katalog ist **statisch** in Excel
- ❌ Preise müssen manuell gepflegt werden
- ❌ Keine automatische Sync mit ERP

### 2. **Keine ERP-Integration**
- ❌ Keine Verbindung zu "Bohr" ERP-System
- ❌ Preise/Verfügbarkeit nicht automatisch abgerufen
- ❌ Angebote werden mit Dummy-Preisen erstellt
- ❌ Manuelle Nachbearbeitung nötig

### 3. **Begrenzte Automatisierung**
- ❌ Projektmetadaten müssen oft manuell eingegeben werden
- ❌ Keine Kundenanbindung (self-service)
- ❌ Keine Email-Integration (PDF-Versand)

### 4. **Security & Compliance**
- ⚠️ Keine Benutzer-Authentifizierung
- ⚠️ Alle Uploads sichtbar für alle
- ⚠️ Keine Audit-Logs
- ⚠️ GDPR: Keine Datenregelung

---

## 🎯 ROADMAP – Nächste Schritte

### **Phase 5: ERP-Integration (PRIORITÄT 1)**
**Timeline**: 2-3 Wochen
**Nutzen**: Automatische Preisabzüge, Live-Verfügbarkeit, sichere Angebote

#### 5.1 Bohr-Schnittstelle
```
Anforderung:
- Bohr ERP-System (Hersteller, Hoster, API-Dokumentation?)
- Authentifizierung (API-Key, OAuth2, Basic Auth?)
- Endpoints für Preise, Verfügbarkeit, Materialverfügbarkeit

Implementierung:
1. Service: `services/erp_connector.py`
   - Bohr-Verbindung (REST/SOAP/Datei?)
   - Authentifizierung
   - Produktpreis-Abfrage
   - Verfügbarkeits-Check

2. Cache-Layer
   - Preise cachen (TTL: 1 Stunde)
   - Verfügbarkeit real-time

3. Offer-Generator Update
   - Automatische Preisabzüge
   - Verfügbarkeitsstatus
   - Gewinnmarge-Berechnung (falls Bohr das hat)

4. Frontend-Update
   - Preise live anzeigen
   - Verfügbarkeitsstatus pro Position
   - Gewinnmargen-Report
```

#### 5.2 Datenfluss-Diagramm
```
Hochgeladene Türliste
        ↓
Matching gegen Katalog
        ↓
Für jedes Match: ERP-Bohr abfragen
   ├─ Preis
   ├─ Verfügbarkeit
   └─ Lieferzeit
        ↓
Excel-Angebot mit Live-Preisen
```

---

### **Phase 6: Authentifizierung & Multi-User (PRIORITÄT 2)**
**Timeline**: 2 Wochen
**Nutzen**: Mehrere Nutzer, Datenschutz, Audit-Trail

#### 6.1 Benutzer-Management
```
Implementierung:
1. Backend:
   - JWT-Token-Auth (Python-jose)
   - User-Rollen: Admin, Sachbearbeiter, Kunde
   - Database: SQLite (simpel) oder PostgreSQL (produktiv)

2. Frontend:
   - Login-Seite
   - Rollenbasierte Sichtbarkeit
   - Nur eigene Analysen sehen

3. API-Protection:
   - JWT-Check auf allen Endpoints
   - Nur eigene Daten abrufbar
```

---

### **Phase 7: Email & Kundenanbindung (PRIORITÄT 3)**
**Timeline**: 1-2 Wochen
**Nutzen**: Automatischer PDF-Versand, Kundenselbstbedienung

#### 7.1 Email-Integration
```
Implementierung:
1. Service: `services/email_sender.py`
   - SMTP (Gmail, Outlook, Firmen-Mail)
   - PDF-Angebot versenden
   - HTML-Template für Angebote

2. Kunde-Portal (optional)
   - Angebots-Link teilen
   - PDF herunterladen
   - Status-Verfolgung
```

---

### **Phase 8: Advanced Analytics (PRIORITÄT 4)**
**Timeline**: 1 Woche
**Nutzen**: Geschäftseinblicke, KPI-Tracking

#### 8.1 Dashboard
```
Metriken:
- Anzahl Analysen/Tag
- Erfolgsquote (erfüllbar %)
- Durchschnittliche Bearbeitungszeit
- Häufigste Fehlmatchings
- Revenue-Report (wenn ERP-Preise)
```

---

## 💻 Technische Details – Was ist wo

### Backend-Struktur
```
backend/
├── main.py                          # FastAPI App + Lifespan
├── routers/
│   ├── upload.py                    # POST /api/upload
│   ├── analyze.py                   # POST /api/analyze + Status
│   ├── offer.py                     # POST /api/result/generate
│   ├── catalog.py                   # GET/POST /api/catalog
│   ├── history.py                   # GET/POST /api/history
│   ├── feedback.py                  # POST /api/feedback
│   └── [neu] erp.py                 # POST /api/erp/price (Phase 5)
│
├── services/
│   ├── document_parser.py           # PDF/Excel/Word → Text
│   ├── excel_parser.py              # Strukturiertes Parsing
│   ├── fast_matcher.py              # Regelbasiertes Matching
│   ├── catalog_index.py             # Produkt-Index (schnell)
│   ├── result_generator.py          # Excel-Erstellung
│   ├── offer_generator.py           # Angebots-Excel
│   ├── claude_client.py             # Claude API
│   ├── local_llm.py                 # Ollama/Regex
│   ├── feedback_store.py            # Korrektionen (JSON)
│   ├── history_store.py             # Historie (JSON)
│   ├── project_store.py             # Projekte
│   ├── job_store.py                 # Background-Jobs
│   ├── memory_cache.py              # TTL-Cache
│   └── [neu] erp_connector.py       # Bohr-Integration (Phase 5)
│
└── outputs/                         # Generierte Dateien
```

### Frontend-Struktur
```
frontend/
├── index.html                       # 3 Views: Offer, Catalog, History
├── app.js                           # Event-Handling, API-Calls
├── style.css                        # Design-System
└── [neu] components/
    └── [neu] erp-status.html       # Live-Preis-Anzeige (Phase 5)
```

---

## 🔧 Installation & Deployment für Frank Türen AG

### Lokal (Entwicklung)
```bash
# 1. Setup
setup.bat

# 2. Server starten
start.bat

# 3. Browser
http://localhost:8000
```

### Production (Ihr eigener Server)

#### Docker-Deployment (empfohlen)
```bash
# 1. Docker bauen
docker build -t frank-tueren-ag:1.0 .

# 2. Container starten
docker run -d \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -v /path/to/outputs:/app/outputs \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  frank-tueren-ag:1.0

# 3. Browser
http://your-server:8000
```

#### Umgebungsvariablen
```
# .env für Production
ANTHROPIC_API_KEY=sk-ant-...          # Falls Claude genutzt
OLLAMA_BASE_URL=http://localhost:11434  # Falls Ollama
ERP_BOHR_URL=https://bohr.example.com  # Phase 5
ERP_BOHR_API_KEY=xxx                    # Phase 5
ERP_BOHR_USERNAME=user                  # Phase 5
```

---

## 📊 Kosten-Nutzen-Analyse

| Feature | Aufwand | Nutzen | Priorität |
|---------|---------|--------|-----------|
| ERP-Integration | 40h | 🟢🟢🟢 Sehr hoch | 1 |
| Authentifizierung | 30h | 🟢🟢 Hoch | 2 |
| Email-Versand | 15h | 🟢🟢 Hoch | 3 |
| Analytics-Dashboard | 20h | 🟡 Mittel | 4 |
| Mobile-App | 80h | 🟢 Hoch | 5 |

---

## ⚠️ Bekannte Bugs & TODOs

- [ ] Beim Upload großer Dateien (>100MB) kann Timeout auftreten
- [ ] Produktkatalog-Editor: Keine Validierung von Abmessungen
- [ ] Historia: Löschen funktioniert nicht vollständig
- [ ] Feedback-System: Gelöschte Korrektionen hinterlassen Leichen

---

## 👥 Team & Kontakte

- **Entwicklung**: Claude (AI Agent)
- **Produkt**: Frank Türen AG (Innendienst)
- **ERP-Kontakt**: [Bohr-Hersteller/Hoster] (Phase 5)

---

**Letzte Aktualisierung**: 2025
**Nächster Meilenstein**: ERP-Integration (Phase 5)
