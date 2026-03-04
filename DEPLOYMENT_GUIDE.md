# Frank Türen AG - Deployment & Setup Guide
## Production-Ready Application

---

## 1. VORAUSSETZUNGEN

### System-Anforderungen
- **Python 3.12+**
- **Ollama** (LLM Server, optional)
- **Node.js** (für Frontend-Build, optional)
- **4GB RAM** minimum
- **2GB freier Speicher** für Uploads & Cache

### Software-Stack
```
Backend: FastAPI + uvicorn + Python 3.12
Frontend: HTML5 + CSS3 + Vanilla JavaScript
LLM: Ollama (lokal) oder Claude API (Remote)
Database: In-Memory Cache (SQLite optional)
```

---

## 2. INSTALLATION

### 2.1 Repository klonen
```bash
cd C:\Users\ALI\Desktop
git clone https://github.com/franktueren/angebotserstellung.git
cd angebotserstellung
```

### 2.2 Backend Setup
```bash
cd backend

# Virtual Environment erstellen
python -m venv .venv

# Aktivieren (Windows)
.venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt

# Optional: Ollama installieren
# https://ollama.ai/download
```

### 2.3 Environment-Variablen konfigurieren
```bash
# Erstelle backend/.env (oder setze System-Variablen)
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Optional
ANTHROPIC_API_KEY=sk-...
TELEGRAM_TOKEN=...
```

### 2.4 Datenverzeichnisse prüfen
```bash
# Folgende Verzeichnisse werden automatisch erstellt:
# - data/              (Produktkatalog)
# - uploads/           (Hochgeladene Dateien)
# - outputs/           (Generierte Angebote)
# - logs/              (Log-Dateien)
```

---

## 3. OLLAMA SETUP (Lokal)

### 3.1 Ollama installieren
```bash
# https://ollama.ai/download
# Oder: Chocolatey (Windows)
choco install ollama
```

### 3.2 Modell pullen
```bash
# Starte Ollama Server
ollama serve

# In neuer Konsole:
ollama pull llama3.2
ollama pull neural-chat  # (Optional, schneller)

# Status prüfen
ollama list
```

### 3.3 Ollama testen
```bash
# Server läuft auf: http://localhost:11434
curl http://localhost:11434/api/tags
```

---

## 4. BACKEND STARTEN

### 4.1 Development-Modus
```bash
cd backend
.venv\Scripts\activate
python main.py

# Oder mit uvicorn direkt:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Production-Modus
```bash
# Mit Gunicorn (empfohlen)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Oder mit uvicorn (ohne reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.3 Health Check
```bash
# API sollte auf http://localhost:8000 erreichbar sein
curl http://localhost:8000/health

# Response:
{
  "status": "ok",
  "service": "Frank Türen AG – Angebotserstellung",
  "version": "2.0.0",
  "catalog": {...},
  "ollama": {...}
}
```

---

## 5. FRONTEND

### 5.1 Automatisch serviert
- Frontend wird automatisch von FastAPI unter `/` serviert
- Zugriff: `http://localhost:8000`

### 5.2 Statische Dateien
```
frontend/
├── index.html      (Hauptseite)
├── app.js          (Logik)
├── style.css       (Styling)
└── lib/
    └── api-client.js  (HTTP Client)
```

### 5.3 Development
```bash
# Frontend-Datei ändern → automatisch im Browser laden
# (Cache-Control Header in main.py deaktiviert Cache)
```

---

## 6. TESTING

### 6.1 Unit-Tests
```bash
cd backend
pytest tests/ -v --cov=services

# Spezifische Tests
pytest tests/test_validators.py -v
```

### 6.2 API-Tests
```bash
# Mit curl
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test.pdf"

# Mit Postman/Insomnia
# Importiere: API_COLLECTION.postman_json
```

### 6.3 Load-Tests
```bash
# Mit locust (optional installieren)
pip install locust
locust -f loadtest.py -u 100 -r 10 --headless
```

---

## 7. MONITORING & LOGS

### 7.1 Log-Dateien
```bash
# Lokation: backend/logs/app.log
# Format: JSON (strukturierte Logs)

# Lesen
tail -f logs/app.log
```

### 7.2 Health-Endpoints
```bash
# API Health
GET /health

# App Info
GET /info

# Upload Service Health
GET /api/upload/health
```

### 7.3 Performance-Monitoring
```bash
# Cache-Statistiken im Health-Endpoint enthalten
# - text_cache: {size, hits, misses, items}
# - offer_cache: {...}
# - project_cache: {...}
```

---

## 8. DATABASE & PERSISTENCE

### 8.1 In-Memory Cache
- Text-Cache: 1 Stunde TTL (3600s)
- Project-Cache: 30 Minuten TTL (1800s)
- Offer-Cache: 30 Minuten TTL (1800s)
- Max-Size: 500MB (konfigurierbar)

### 8.2 Datei-Speicherung
```
uploads/           (Hochgeladene Dateien, 24h TTL)
outputs/           (Generierte Angebote)
data/              (Produktkatalog & Feedback)
```

### 8.3 Optional: SQLite
```python
# Für zukünftige Persistierung:
# - Feedback-Speicherung
# - Projekt-Historie
# - User-Management

# Siehe: backend/services/database.py (TODO)
```

---

## 9. SICHERHEIT

### 9.1 CORS-Konfiguration
```python
# config.py
CORS_ORIGINS = ["*"]  # Dev-Mode
# Production: nur whitelisted origins
```

### 9.2 Input-Validierung
```
- File Size Limits (100MB max)
- File Type Whitelist
- Filename Sanitization
- Text Length Limits
```

### 9.3 Security Headers
```
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
```

---

## 10. FEHLERBEHEBUNG

### 10.1 Ollama nicht erreichbar
```
Symptom: "Ollama not reachable" in Logs

Lösung:
1. Ollama Server starten: ollama serve
2. URL überprüfen: OLLAMA_URL env var
3. Port 11434 nicht blockiert?
```

### 10.2 Zu wenig Memory
```
Symptom: Crashes bei großen Dateien

Lösung:
1. Cache-Size reduzieren: CACHE_MAX_SIZE_MB
2. Worker-Prozesse reduzieren
3. Datei-Größe-Limit senken: MAX_FILE_SIZE_MB
```

### 10.3 Langsame Responses
```
Symptom: API-Responses > 5 Sekunden

Lösung:
1. Ollama Model ist zu groß → llama3.2 nutzen
2. Network-Latenz prüfen
3. Load-Tests durchführen
4. Cache-Hit-Rate überprüfen
```

---

## 11. MAINTENANCE

### 11.1 Logs archivieren
```bash
# Logs werden nach 5x10MB rotiert (RotatingFileHandler)
# Alte Logs: logs/app.log.1, app.log.2, etc.
```

### 11.2 Cache leeren
```bash
# API Endpoint
POST /api/clear-cache

# Oder: Code
from services.memory_cache import text_cache, offer_cache, project_cache
text_cache.clear()
offer_cache.clear()
project_cache.clear()
```

### 11.3 Uploads bereinigen
```bash
# Automatisch täglich (UPLOAD_CLEANUP_HOURS=24)
# Oder manuell:
python -c "from services.file_cleanup import cleanup_old_files; cleanup_old_files()"
```

---

## 12. DEPLOYMENT ZU PRODUCTION

### 12.1 Environment-Variablen
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
WORKERS=4
CACHE_MAX_SIZE_MB=1000
RATE_LIMIT_ENABLED=true
CSRF_PROTECTION_ENABLED=true
```

### 12.2 Server-Setup (Linux/Docker empfohlen)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["gunicorn", "main:app", "--workers", "4", "--bind", "0.0.0.0:8000"]
```

### 12.3 Reverse Proxy (Nginx)
```nginx
upstream frank_tueren {
    server localhost:8000;
}

server {
    listen 80;
    server_name franktueren.ch;
    
    location / {
        proxy_pass http://frank_tueren;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 12.4 SSL/HTTPS
```bash
# Let's Encrypt mit Certbot
certbot certonly --standalone -d franktueren.ch
# Update nginx config mit certificate paths
```

---

## CHECKLISTE FÜR PRODUCTION

- [ ] ENVIRONMENT=production gesetzt
- [ ] DEBUG=false
- [ ] OLLAMA_URL & MODEL konfiguriert
- [ ] ANTHROPIC_API_KEY (falls Claude-Fallback nötig)
- [ ] TELEGRAM_TOKEN (optional)
- [ ] SSL/HTTPS aktiviert
- [ ] Rate-Limiting aktiviert
- [ ] CSRF-Protection aktiviert
- [ ] Logging auf INFO-Level
- [ ] Backups für Katalog-Datei
- [ ] Monitoring & Alerting setup
- [ ] Load-Tests durchgeführt
- [ ] Security-Audit durchgeführt

---

## SUPPORT & KONTAKT

Bei Fragen oder Problemen:
- Logs überprüfen: `logs/app.log`
- Health-Endpoint nutzen: `/health`
- GitHub Issues: [Repository]
- E-Mail: support@franktueren.ch
