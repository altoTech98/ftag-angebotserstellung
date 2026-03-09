# Frontend Modernization Design – Frank Türen AG

## Zusammenfassung

Migration des bestehenden Vanilla JS Frontends (1546 Zeilen `app.js`) zu einer React-App mit Vite. 1:1 Feature-Parität, keine UX-Änderungen. Bestehende CSS-Styles werden als CSS Modules übernommen.

## Entscheidungen

| Bereich | Entscheidung | Begründung |
|---------|-------------|------------|
| Framework | React + Vite | User kennt React, Vite ist schnell |
| Projekt-Setup | Separates `frontend-react/` Verzeichnis | Dev: Port 5173, Prod: FastAPI served built files |
| CSS | Bestehendes CSS → CSS Modules | Kein visueller Unterschied, saubere Trennung |
| State Management | useState + useContext | Überschaubarer State, keine Extra-Dependency |
| Migration | Big Bang | 2-5 User, 4 Views – Parallel-Betrieb lohnt nicht |
| Architektur | 1:1 Feature-Parität | Erst migrieren, dann verbessern |

## Projektstruktur

```
frontend-react/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.jsx                 # Entry point, Router
│   ├── App.jsx                  # Layout (Header, Nav, Content)
│   ├── context/
│   │   ├── AuthContext.jsx       # Login-State, JWT-Token, User-Rolle
│   │   └── AppContext.jsx        # Globaler App-State (aktive Analyse, etc.)
│   ├── hooks/
│   │   ├── useAuth.js            # Login/Logout, Token-Refresh
│   │   ├── useApi.js             # Fetch-Wrapper mit Auth-Header
│   │   └── useSSE.js             # Server-Sent Events für Analyse-Progress
│   ├── pages/
│   │   ├── AnalysePage.jsx       # Upload + Analyse + Ergebnisse
│   │   ├── KatalogPage.jsx       # Produktkatalog durchsuchen
│   │   ├── HistoriePage.jsx      # Vergangene Analysen
│   │   └── BenutzerPage.jsx      # User-Management (Admin only)
│   ├── components/
│   │   ├── Header.jsx            # Logo, Nav-Tabs, Status-Badges
│   │   ├── LoginForm.jsx         # Login-Screen
│   │   ├── FileUpload.jsx        # Drag&Drop, single + folder
│   │   ├── AnalysisProgress.jsx  # Fortschrittsanzeige mit SSE
│   │   ├── ResultsTable.jsx      # Matching-Ergebnisse Tabelle
│   │   ├── PositionDetail.jsx    # Detail-Modal für eine Position
│   │   ├── CorrectionModal.jsx   # Produkt-Korrektur mit Suche
│   │   ├── ProductCard.jsx       # Produkt-Anzeige im Katalog
│   │   └── StatusBadge.jsx       # Server/AI Online-Status
│   ├── services/
│   │   └── api.js                # API-Client (alle Endpoints)
│   └── styles/
│       ├── global.css            # Reset, Variablen, Basis-Styles
│       └── *.module.css          # Pro Komponente ein CSS Module
├── index.html
├── vite.config.js
└── package.json
```

## Routing

```
/           → Redirect zu /analyse (wenn eingeloggt) oder LoginForm
/analyse    → AnalysePage
/katalog    → KatalogPage
/historie   → HistoriePage
/benutzer   → BenutzerPage (nur Admin)
```

## Auth-Flow

1. `AuthContext` speichert JWT-Token + User-Info im State + `localStorage`
2. App-Start: Token aus `localStorage` lesen, validieren via `GET /api/auth/me`
3. Ungültiger Token → Login-Screen
4. `useApi` Hook hängt automatisch `Authorization: Bearer <token>` an jeden Request
5. 401-Response → Token löschen, zurück zum Login
6. Admin-Routen (`/benutzer`) prüfen `user.role === 'admin'`

## Analyse-Flow (Kernfeature)

### 1. Upload
- Drag & Drop Zone + File-Input
- Einzeldatei → `POST /api/upload` → file_id + text_preview
- Ordner/Multi → `POST /api/upload/folder` → project_id + Datei-Liste

### 2. Analyse starten
- `POST /api/analyze` mit file_id oder project_id → job_id

### 3. Progress via SSE
- `EventSource` auf `/api/analyze/{job_id}/stream`
- Events: `progress`, `complete`, `error`
- Automatischer Reconnect (3 Versuche)

### 4. Ergebnisse
- ResultsTable: Positionen mit Anforderung, Match, Konfidenz, Status
- PositionDetail Modal: Details + Alternativen
- CorrectionModal: Produktsuche + Feedback speichern

### 5. Download
- Angebot: `GET /api/offer/{id}/download`
- Lückenbericht: `GET /api/report/{id}/download`

## Neben-Views

- **Katalog**: Suchfeld mit Debounce → ProductCards, client-side Pagination
- **Historie**: Tabelle vergangener Analysen
- **Benutzer**: User CRUD (Admin only)

## CSS-Migration

- `frontend/style.css` (1352 Zeilen) aufteilen in `global.css` + `*.module.css`
- CSS-Variablen beibehalten (`--primary`, `--bg`, etc.)
- Keine visuellen Änderungen

## API-Client

- Zentraler Fetch-Wrapper in `services/api.js`
- Base-URL aus `VITE_API_URL` Environment Variable
- Auth-Header automatisch aus AuthContext
- Dev: Vite Proxy `/api` → `http://localhost:8000`
- Prod: `VITE_API_URL=/api`

## Vite Config

- Dev-Server: Port 5173 mit Proxy zu Backend
- Build-Output: Konfigurierbar (FastAPI served)
