"""
ERP Integration Config Example

Dies ist eine Beispielkonfiguration für die Bohr-ERP Integration.
Verwende dies als Referenz für deine eigene ERP-Instanz.
"""

# ─────────────────────────────────────────────────────────────────────────────
# BOHR ERP API ENDPOINTS (Beispiel)
# ─────────────────────────────────────────────────────────────────────────────

"""
WICHTIG: Passe diese Endpoints an dein echtes Bohr-System an!

Standard Bohr REST API Endpoints (typisch):

1. PRICING ENDPOINT:
   GET /api/v1/products/{product_id}/pricing?quantity={qty}
   
   Response:
   {
     "netto": 1250.00,
     "brutto": 1500.00,
     "currency": "CHF",
     "rabatt": 0,
     "bestand": 5,
     "lieferzeit_tage": 14
   }

2. AVAILABILITY ENDPOINT:
   GET /api/v1/products/{product_id}/availability
   
   Response:
   {
     "verfuegbar": true,
     "menge": 5,
     "lagerort": "A-15-3",
     "lieferzeit_tage": 14,
     "naechste_lieferung": "2025-02-15"
   }

3. HEALTH CHECK:
   GET /api/v1/health
   
   Response:
   {
     "status": "ok"
   }
"""


# ─────────────────────────────────────────────────────────────────────────────
# UMGEBUNGSVARIABLEN (.env)
# ─────────────────────────────────────────────────────────────────────────────

"""
Setze diese Variablen in deiner .env Datei:

# ERP Integration
ERP_ENABLED=true
ERP_BOHR_URL=https://bohr.frank-tueren.de
ERP_BOHR_API_KEY=sk-bohr-xyzabc123...
ERP_BOHR_USERNAME=api_user
ERP_BOHR_PASSWORD=secure_password
ERP_REQUEST_TIMEOUT=10.0
ERP_USE_CACHE=true
ERP_FALLBACK_TO_ESTIMATE=true

# Cache TTL (in Sekunden)
ERP_PRICE_CACHE_TTL_SECONDS=3600  # 1 Stunde

# Falls mit Basic Auth:
# Nutze nur ERP_BOHR_USERNAME und ERP_BOHR_PASSWORD

# Falls mit Bearer Token:
# Nutze nur ERP_BOHR_API_KEY
"""


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTIFIZIERUNG OPTIONEN
# ─────────────────────────────────────────────────────────────────────────────

"""
Der ERP Connector unterstützt:

1. API KEY (Bearer Token):
   Header: Authorization: Bearer {ERP_BOHR_API_KEY}

2. BASIC AUTH (Username + Password):
   Header: Authorization: Basic {base64(username:password)}

Wähle eine Methode und setze die entsprechenden Variablen.
"""


# ─────────────────────────────────────────────────────────────────────────────
# SCHNELLSTART SCHRITTE
# ─────────────────────────────────────────────────────────────────────────────

"""
1. Bohr-ERP Verbindungsdaten sammeln:
   - Base URL (z.B. https://bohr.deine-domain.de)
   - API Key oder Username/Password
   - Zu testender Product-ID

2. .env Datei aktualisieren mit ERP-Credentials

3. Test durchführen:
   curl http://localhost:8000/api/erp/health
   
   Response sollte:
   {
     "status": "ok",
     "enabled": true,
     "connected": true
   }

4. Einzelnen Preis testen:
   curl http://localhost:8000/api/erp/price/AG-001?quantity=1
   
   Response:
   {
     "product_id": "AG-001",
     "quantity": 1,
     "unit_price_net": 1250.00,
     "unit_price_gross": 1500.00,
     ...
   }

5. Bulk Preise testen:
   curl -X POST http://localhost:8000/api/erp/prices \
     -H "Content-Type: application/json" \
     -d '{"product_ids": ["AG-001", "AG-002"]}'
"""


# ─────────────────────────────────────────────────────────────────────────────
# ANGEBOT GENERATION MIT ERP-PREISEN
# ─────────────────────────────────────────────────────────────────────────────

"""
Workflow:

1. Benutzer lädt Türliste hoch

2. Matching findet Produkte

3. Angebotserstellung (POST /api/offer/generate):
   - Für jedes Match: ERP-Preis laden
   - Mit Caching um Performance zu optimieren
   - Fallback auf Schätzpreise wenn ERP ausfällt

4. Preistotale berechnen und speichern

5. Excel-Angebot mit aktuellen Preisen erstellen

6. Kundendownload: GET /api/offer/{id}/download
   - Excel enthält Live-Preise
   - Quellangabe (ERP vs. Schätzung)
   - Lieferzeitangabe
"""


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK-PREISE (wenn ERP nicht verfügbar)
# ─────────────────────────────────────────────────────────────────────────────

"""
Wenn ERP_FALLBACK_TO_ESTIMATE=true (Standard):
- Falls ERP ausfällt, wird Schätzpreis verwendet
- Im Angebot wird notiert: "Geschätzter Preis"
- Kein Fehler, Geschäft wird nicht unterbrochen

Wenn ERP_FALLBACK_TO_ESTIMATE=false:
- Falls ERP ausfällt, wird Error geworfen
- Kunde kann kein Angebot erstellen
- Nur sinnvoll wenn ERP 100% verfügbar ist
"""


# ─────────────────────────────────────────────────────────────────────────────
# BOHR API ENDPOINTS - DETAILLIERTE DOKUMENTATION
# ─────────────────────────────────────────────────────────────────────────────

"""
FALLS DEIN BOHR-SYSTEM ANDERE ENDPOINTS NUTZT:

1. Überprüfe die Bohr-API Dokumentation für dein System
2. Passe die Endpoints in erp_connector.py an:
   - _query_bohr_price() Methode
   - _query_bohr_availability() Methode

3. Beispiel: SOAP-basierte API
   Falls Bohr SOAP statt REST nutzt, erstelle einen SOAP-Adapter:
   - services/erp_soap_adapter.py
   - Nutze zeep-Library: pip install zeep

4. Beispiel: CSV/Excel Export
   Falls Bohr nur CSV-Exports anbietet:
   - Implementiere Datei-Import statt API
   - Polling-Interval konfigurierbar machen
"""


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE-TIPPS
# ─────────────────────────────────────────────────────────────────────────────

"""
1. CACHING:
   - Preise werden 1 Stunde gecacht
   - Verhindert zu viele ERP-Abfragen
   - Konfigurierbar via ERP_PRICE_CACHE_TTL_SECONDS

2. BULK QUERIES:
   - Nutze POST /api/erp/prices für mehrere Produkte
   - Effizienter als einzelne GET-Requests

3. TIMEOUT:
   - Standard: 10 Sekunden
   - Für langsame Netzwerke erhöhen: ERP_REQUEST_TIMEOUT=30.0

4. CONNECTION POOLING:
   - Requests Session wird wiederverwendet
   - Automatische Verbindungsverwaltung
"""


# ─────────────────────────────────────────────────────────────────────────────
# DEBUGGING & TROUBLESHOOTING
# ─────────────────────────────────────────────────────────────────────────────

"""
Logs überprüfen (im Docker oder lokal):
   tail -f logs/app.log | grep ERP

Häufige Fehler:

1. "ERP health check failed: Connection refused"
   → ERP URL prüfen, ERP läuft?

2. "ERP price query failed: 401 Unauthorized"
   → API-Key oder Username/Password falsch

3. "ERP price query failed: 404 Not Found"
   → Product-ID existiert nicht in ERP
   → Endpunkt-Format überprüfen

4. "Using fallback price"
   → ERP nicht erreichbar, aber Fallback aktiv
   → Ist OK für unkritische Szenarien
   → Prüfe ERP-Verfügbarkeit für Production
"""
