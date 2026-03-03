# Frank Tueren AG – KI-Machbarkeitsanalyse

Webbasiertes Tool zur automatischen Analyse von Tuerlisten und Ausschreibungen.
Vergleicht Kundenanforderungen mit dem FTAG-Produktkatalog und erstellt eine
Machbarkeitsanalyse mit GAP-Report als Excel-Download.

## Features

- **Datei-Upload**: Excel-Tuerlisten (.xlsx), PDF, Word (.docx), TXT
- **Automatisches Matching**: Regelbasierter Abgleich mit dem FTAG-Produktkatalog
- **Machbarkeitsanalyse**: Erfuellbar / teilweise / nicht erfuellbar pro Position
- **Excel-Export**: Machbarkeitsanalyse + GAP-Report als formatierte Excel-Datei
- **Katalog-Verwaltung**: Produktkatalog direkt im Browser aktualisieren
- **Analyse-Historie**: Vergangene Analysen einsehen und neu matchen

## Tech Stack

| Komponente | Technologie |
|-----------|-------------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Vanilla HTML / CSS / JS |
| AI (optional) | Claude API (fuer PDF/Word-Textanalyse) |
| Excel | openpyxl, pandas, xlsxwriter |
| PDF | pdfplumber |
| Word | python-docx |

## Setup

```bash
# 1. Setup (erstellt venv, installiert Dependencies)
setup.bat

# 2. API Key setzen (nur fuer PDF/Word-Analyse noetig)
set ANTHROPIC_API_KEY=sk-ant-...

# 3. Server starten
start.bat

# 4. Browser oeffnen
http://localhost:8000
```

### Voraussetzungen

- Python 3.10+
- Windows (setup.bat / start.bat)
- ANTHROPIC_API_KEY (optional, nur fuer PDF/Word-Dokumente)

### Ollama (optional – Metadaten-Extraktion)

Ollama ermoeglicht die automatische Extraktion von Projektmetadaten
(Bauherr, Baustelle, Architekt, Datum) aus hochgeladenen Dokumenten.
Ohne Ollama wird ein Regex-Fallback verwendet.

```bash
# 1. Ollama installieren: https://ollama.com
# 2. Modell herunterladen
ollama pull llama3.2

# 3. Ollama-Server starten (laeuft im Hintergrund)
ollama serve
```

## Projektstruktur

```
ClaudeCodeTest/
├── backend/
│   ├── main.py                    # FastAPI Entry Point, CORS, Router
│   ├── requirements.txt           # Python Dependencies
│   ├── routers/
│   │   ├── upload.py              # POST /api/upload (Datei-Upload)
│   │   ├── analyze.py             # POST /api/analyze (Analyse starten)
│   │   ├── offer.py               # POST /api/result/generate (Excel erstellen)
│   │   ├── catalog.py             # GET/POST /api/catalog (Katalog verwalten)
│   │   ├── history.py             # GET /api/history (Analyse-Historie)
│   │   └── feedback.py            # POST /api/feedback (Korrekturen)
│   └── services/
│       ├── document_parser.py     # PDF/Excel/Word → Text
│       ├── excel_parser.py        # Strukturiertes Tuerlisten-Parsing
│       ├── fast_matcher.py        # Regelbasiertes Produkt-Matching
│       ├── catalog_index.py       # Produktkatalog-Index (kategorisiert)
│       ├── result_generator.py    # Machbarkeitsanalyse Excel-Generator
│       ├── offer_generator.py     # Angebots-Excel-Generator
│       ├── claude_client.py       # Claude API (Text-Extraktion)
│       ├── local_llm.py          # Ollama/Regex Metadaten-Extraktion
│       ├── product_matcher.py     # KI-gestuetztes Matching (Legacy)
│       ├── feedback_store.py      # Korrektur-Speicher (JSON)
│       ├── history_store.py       # Analyse-Historie (JSON)
│       ├── file_classifier.py     # Datei-Klassifikation
│       ├── project_store.py       # Projekt-Verwaltung
│       ├── job_store.py           # Background-Job-Verwaltung
│       └── memory_cache.py        # In-Memory-Cache (TTL)
├── frontend/
│   ├── index.html                 # Single-Page UI
│   ├── app.js                     # Frontend-Logik
│   └── style.css                  # Styling
├── data/
│   └── produktuebersicht.xlsx     # FTAG-Produktkatalog (~884 Produkte)
├── uploads/                       # Hochgeladene Dateien (Runtime)
├── outputs/                       # Generierte Excel-Dateien (Runtime)
├── Dockerfile                     # Docker-Deployment
├── railway.toml                   # Railway-Konfiguration
├── render.yaml                    # Render-Konfiguration
├── setup.bat                      # Erstinstallation (Windows)
└── start.bat                      # Server starten (Windows)
```

## API Endpunkte

### Upload
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/upload` | Datei hochladen (Excel, PDF, Word, TXT) |

### Analyse
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/analyze` | Analyse starten (Background-Job) |
| GET | `/api/analyze/status/{job_id}` | Job-Status abfragen |

### Ergebnis
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/result/generate` | Excel-Machbarkeitsanalyse erstellen |
| GET | `/api/result/status/{job_id}` | Generator-Status abfragen |
| GET | `/api/result/{id}/download` | Excel herunterladen |

### Katalog
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/catalog/info` | Katalog-Metadaten |
| POST | `/api/catalog/upload` | Neuen Katalog hochladen |

### Historie
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/history` | Alle Analysen |
| GET | `/api/history/{id}` | Analyse-Details |
| POST | `/api/history/{id}/rematch` | Analyse neu matchen |
| DELETE | `/api/history/{id}` | Analyse loeschen |

### Feedback
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/feedback` | Korrektur speichern |
| GET | `/api/feedback/stats` | Feedback-Statistiken |

## Matching-Logik

Das Produkt-Matching ist regelbasiert (kein AI noetig) und prueft:

| Kriterium | Gewichtung | Logik |
|-----------|-----------|-------|
| Brandschutz | 30 Punkte | Hierarchie: EI30 = T30, hoehere Klasse erfuellt niedrigere |
| Schallschutz | 20 Punkte | dB-Vergleich (Produkt >= Anforderung) |
| Einbruchschutz | 15 Punkte | RC2 = WK2, hoehere Klasse erfuellt niedrigere |
| Abmessungen | 20 Punkte | Breite/Hoehe-Vergleich mit Auto-Normalisierung (cm→mm) |
| Fluegelanzahl | 10 Punkte | 1-flueglig / 2-flueglig Erkennung |
| Verglasung | 5 Punkte | Glasausschnitt-Erkennung |

**Schwellwerte**: >= 60 Punkte = erfuellbar, 35-59 = teilweise, < 35 = nicht erfuellbar

Fuer PDF/Word-Dateien wird zusaetzlich Claude AI zur Textextraktion verwendet.
