# Frontend Modernization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the 1546-line vanilla JS frontend to a React + Vite app with 1:1 feature parity.

**Architecture:** Separate `frontend-react/` Vite project with React Router for navigation, Context API for state management (auth + app state), CSS Modules migrated from the existing `style.css`. Dev server on port 5173 with proxy to FastAPI backend on port 8000. Production builds served by FastAPI as static files.

**Tech Stack:** React 18, Vite 5, React Router 6, CSS Modules

---

## Context for Implementer

The existing frontend is a single `frontend/app.js` (1546 lines) + `frontend/index.html` (504 lines) + `frontend/style.css` (1352 lines). All state is in global variables, DOM manipulation via `innerHTML` and `classList`. The backend is FastAPI on port 8000, all API endpoints are under `/api/`.

**Key API endpoints used by the frontend:**
- `POST /api/auth/login` → `{ token }`
- `GET /api/auth/me` → `{ email, role }`
- `POST /api/auth/logout`
- `GET /api/auth/users`, `POST /api/auth/users`, `DELETE /api/auth/users/{email}`
- `POST /api/upload` (FormData) → `{ file_id, filename, text_length }`
- `POST /api/upload/folder` (FormData) → `{ project_id, total_files, files, summary }`
- `POST /api/analyze` → `{ job_id }`
- `POST /api/analyze/project` → `{ job_id }`
- `GET /api/analyze/status/{job_id}` → `{ status, progress, result, error }`
- `GET /api/analyze/stream/{job_id}` → SSE stream
- `POST /api/result/generate` → `{ job_id }`
- `GET /api/result/status/{job_id}` → `{ status, result }`
- `GET /api/result/{result_id}/download` → Excel file
- `GET /api/catalog/info` → `{ total_products, categories, ... }`
- `POST /api/catalog/upload` (FormData)
- `GET /api/history` → `{ analyses: [...] }`
- `GET /api/history/{id}` → full analysis detail
- `POST /api/history/{id}/rematch`
- `DELETE /api/history/{id}`
- `POST /api/feedback` → save correction
- `GET /api/products/search?q=...&limit=15`
- `GET /health` → `{ ai: { engine } }` (NOT under /api)

---

### Task 1: Vite + React Project Scaffolding

**Files:**
- Create: `frontend-react/package.json`
- Create: `frontend-react/vite.config.js`
- Create: `frontend-react/index.html`
- Create: `frontend-react/src/main.jsx`
- Create: `frontend-react/src/App.jsx`
- Create: `frontend-react/.gitignore`

**Step 1: Initialize Vite project**

Run:
```bash
cd c:/Users/ALI/Desktop/ClaudeCodeTest && npm create vite@latest frontend-react -- --template react
```
Expected: Creates `frontend-react/` with Vite + React template files.

**Step 2: Install dependencies**

Run:
```bash
cd c:/Users/ALI/Desktop/ClaudeCodeTest/frontend-react && npm install && npm install react-router-dom
```
Expected: `node_modules/` created, `package-lock.json` written.

**Step 3: Configure Vite proxy**

Replace `frontend-react/vite.config.js` with:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 4: Create minimal App with router**

Replace `frontend-react/src/App.jsx` with:

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/analyse" replace />} />
        <Route path="/analyse" element={<div>Analyse</div>} />
        <Route path="/katalog" element={<div>Katalog</div>} />
        <Route path="/historie" element={<div>Historie</div>} />
        <Route path="/benutzer" element={<div>Benutzer</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

Replace `frontend-react/src/main.jsx` with:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**Step 5: Verify dev server starts**

Run:
```bash
cd c:/Users/ALI/Desktop/ClaudeCodeTest/frontend-react && npx vite --host 127.0.0.1 &
sleep 3 && curl -s http://127.0.0.1:5173/ | head -5
```
Expected: HTML output with `<div id="root">`.

Kill dev server after verification.

**Step 6: Add .gitignore**

Create `frontend-react/.gitignore`:
```
node_modules/
dist/
```

**Step 7: Commit**

```bash
git add frontend-react/
git commit -m "feat: scaffold React + Vite project with router"
```

---

### Task 2: CSS Migration (global.css + CSS Variables)

**Files:**
- Create: `frontend-react/src/styles/global.css`
- Modify: `frontend-react/src/main.jsx` (import global.css)

**Step 1: Extract global styles from style.css**

Create `frontend-react/src/styles/global.css` containing:
- The `:root` CSS variables block (lines 6-38 from `frontend/style.css`)
- The `*, *::before, *::after` reset (line 40)
- The `body` styles (lines 42-51)
- The `.hidden` utility (line 1246)
- The `@keyframes fadeIn` (lines 168-171)
- The `@keyframes spin` (line 581)
- The `@keyframes modalFade` and `@keyframes modalSlide` (lines 1000-1016)
- The `@keyframes toastIn` and `@keyframes toastOut` (lines 1197-1198)
- The Google Fonts import for Inter

Full file content:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg:         #ffffff;
  --bg-subtle:  #f9fafb;
  --bg-hover:   #f3f4f6;
  --border:     #e5e7eb;
  --border-light:#f3f4f6;
  --text:       #111827;
  --text-secondary: #374151;
  --text-muted: #6b7280;
  --text-faint: #9ca3af;
  --accent:     #2563eb;
  --accent-hover:#1d4ed8;
  --accent-light:#eff6ff;
  --accent-border:#bfdbfe;
  --success:    #059669;
  --success-light:#ecfdf5;
  --success-border:#a7f3d0;
  --warning:    #d97706;
  --warning-light:#fffbeb;
  --warning-border:#fde68a;
  --danger:     #dc2626;
  --danger-light:#fef2f2;
  --danger-border:#fecaca;

  --font: 'Inter', system-ui, -apple-system, sans-serif;
  --radius-sm:  6px;
  --radius:     8px;
  --radius-lg:  12px;

  --header-h:   56px;
  --max-w:      960px;
  --transition: 150ms ease;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 0.9375rem;
  line-height: 1.5;
}

.hidden { display: none !important; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes spin { to { transform: rotate(360deg); } }

@keyframes modalFade { from { opacity: 0; } to { opacity: 1; } }

@keyframes modalSlide {
  from { transform: translateY(12px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}

@keyframes toastIn { from { transform: translateY(12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes toastOut { from { opacity: 1; } to { opacity: 0; } }

@keyframes pulse-ring {
  0%,100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.3); }
  50%     { box-shadow: 0 0 0 6px rgba(37,99,235,0); }
}
```

**Step 2: Import in main.jsx**

Add to the top of `frontend-react/src/main.jsx`:
```jsx
import './styles/global.css'
```

**Step 3: Verify styles load**

Run dev server, open browser, confirm Inter font is applied and CSS variables work.

**Step 4: Commit**

```bash
git add frontend-react/src/styles/
git commit -m "feat: migrate CSS variables and global styles"
```

---

### Task 3: API Client Service

**Files:**
- Create: `frontend-react/src/services/api.js`

**Step 1: Create the API client**

This is a direct port of the `api()` function from `app.js` lines 1336-1380, but as a module with named exports per endpoint.

```js
const API_BASE = '/api'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function getToken() {
  return localStorage.getItem('auth_token')
}

async function request(path, opts = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const token = getToken()
  if (token) {
    opts.headers = opts.headers || {}
    opts.headers['Authorization'] = `Bearer ${token}`
  }

  let res
  try {
    res = await fetch(url, opts)
  } catch {
    throw new ApiError('Server nicht erreichbar. Ist der Server gestartet?', 0)
  }

  if (res.status === 401) {
    localStorage.removeItem('auth_token')
    throw new ApiError('Sitzung abgelaufen – bitte erneut anmelden.', 401)
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.detail || body.message || msg
    } catch {}
    if (res.status === 410) {
      msg = msg || 'Datei abgelaufen – bitte erneut hochladen.'
    }
    throw new ApiError(msg, res.status)
  }

  try {
    return await res.json()
  } catch {
    throw new ApiError('Ungueltige Server-Antwort', 0)
  }
}

// Auth
export const login = (email, password) =>
  request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

export const getMe = () => request('/auth/me')

export const getUsers = () => request('/auth/users')

export const createUser = (email, password, role) =>
  request('/auth/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, role }),
  })

export const deleteUser = (email) =>
  request(`/auth/users/${encodeURIComponent(email)}`, { method: 'DELETE' })

// Upload
export const uploadFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/upload', { method: 'POST', body: form })
}

export const uploadFolder = (files) => {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  return request('/upload/folder', { method: 'POST', body: form })
}

// Analysis
export const startAnalysis = (fileId) =>
  request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId }),
  })

export const startProjectAnalysis = (projectId) =>
  request('/analyze/project', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, file_overrides: {} }),
  })

export const getJobStatus = (jobId, statusPath = '/analyze/status/') =>
  request(`${statusPath}${jobId}`)

export function createSSE(jobId) {
  return new EventSource(`${API_BASE}/analyze/stream/${jobId}`)
}

// Result generation
export const generateResult = (requirements, matching) =>
  request('/result/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ requirements, matching }),
  })

export const getResultStatus = (jobId) =>
  request(`/result/status/${jobId}`)

export const getResultDownloadUrl = (resultId) =>
  `${API_BASE}/result/${resultId}/download`

// Catalog
export const getCatalogInfo = () => request('/catalog/info')

export const uploadCatalog = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/catalog/upload', { method: 'POST', body: form })
}

// History
export const getHistory = () => request('/history')
export const getHistoryDetail = (id) => request(`/history/${id}`)
export const rematchHistory = (id) => request(`/history/${id}/rematch`, { method: 'POST' })
export const deleteHistory = (id) => request(`/history/${id}`, { method: 'DELETE' })

// Feedback
export const saveFeedback = (body) =>
  request('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const searchProducts = (query, limit = 15) =>
  request(`/products/search?q=${encodeURIComponent(query)}&limit=${limit}`)

// Health
export const checkHealth = async () => {
  const res = await fetch('/health')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export { ApiError }
```

**Step 2: Commit**

```bash
git add frontend-react/src/services/
git commit -m "feat: add API client service with all endpoints"
```

---

### Task 4: Auth Context + useAuth Hook + LoginForm

**Files:**
- Create: `frontend-react/src/context/AuthContext.jsx`
- Create: `frontend-react/src/components/LoginForm.jsx`
- Create: `frontend-react/src/styles/LoginForm.module.css`
- Modify: `frontend-react/src/main.jsx` (wrap with AuthProvider)
- Modify: `frontend-react/src/App.jsx` (use auth, show login or app)

**Step 1: Create AuthContext**

```jsx
// frontend-react/src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import * as api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)       // { email, role } or null
  const [loading, setLoading] = useState(true)  // true while checking token

  // Check existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.getMe()
      .then(data => setUser(data))
      .catch(() => {
        localStorage.removeItem('auth_token')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await api.login(email, password)
    localStorage.setItem('auth_token', data.token)
    const me = await api.getMe()
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

**Step 2: Create LoginForm component**

Port the login form from `index.html` lines 15-32 and `app.js` lines 26-56.

```jsx
// frontend-react/src/components/LoginForm.jsx
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import styles from '../styles/LoginForm.module.css'

export default function LoginForm() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email.trim(), password)
    } catch (err) {
      setError(err.message || 'Login fehlgeschlagen')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.screen}>
      <div className={styles.card}>
        <div className={styles.brand}>Frank Tueren AG</div>
        <h2 className={styles.title}>Anmelden</h2>
        <form onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="login-email">E-Mail</label>
            <input
              type="email"
              id="login-email"
              className={styles.input}
              placeholder="admin@franktueren.ch"
              required
              autoComplete="username"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label} htmlFor="login-password">Passwort</label>
            <input
              type="password"
              id="login-password"
              className={styles.input}
              placeholder="Passwort"
              required
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <button type="submit" className={styles.button} disabled={submitting}>
            {submitting ? 'Anmelden...' : 'Anmelden'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

**Step 3: Create LoginForm CSS Module**

Extract login styles from `frontend/style.css` lines 1248-1319:

```css
/* frontend-react/src/styles/LoginForm.module.css */
.screen {
  position: fixed;
  inset: 0;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.card {
  width: 100%;
  max-width: 380px;
  padding: 2.5rem 2rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

.brand {
  font-weight: 700;
  font-size: 0.9375rem;
  color: var(--text);
  margin-bottom: 0.25rem;
  letter-spacing: -0.01em;
}

.title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 1.75rem;
  letter-spacing: -0.02em;
}

.formGroup {
  margin-bottom: 1rem;
}

.label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.375rem;
}

.input {
  width: 100%;
  padding: 0.5625rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 0.875rem;
  color: var(--text);
  background: var(--bg);
  outline: none;
  transition: border-color var(--transition);
}

.input:focus {
  border-color: var(--accent);
}

.input::placeholder {
  color: var(--text-faint);
}

.error {
  color: var(--danger);
  font-size: 0.8125rem;
  padding: 0.5rem 0.75rem;
  background: var(--danger-light);
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
  width: 100%;
}

.button:hover:not(:disabled) { background: var(--accent-hover); }
.button:disabled {
  background: var(--border);
  color: var(--text-faint);
  cursor: not-allowed;
}
```

**Step 4: Wire up App.jsx with auth**

```jsx
// frontend-react/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginForm from './components/LoginForm'

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return null

  if (!user) return <LoginForm />

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/analyse" replace />} />
      <Route path="/analyse" element={<div>Analyse (TODO)</div>} />
      <Route path="/katalog" element={<div>Katalog (TODO)</div>} />
      <Route path="/historie" element={<div>Historie (TODO)</div>} />
      <Route path="/benutzer" element={
        user.role === 'admin' ? <div>Benutzer (TODO)</div> : <Navigate to="/analyse" replace />
      } />
      <Route path="*" element={<Navigate to="/analyse" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
```

**Step 5: Wrap with AuthProvider in main.jsx**

```jsx
// frontend-react/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from './context/AuthContext'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
)
```

**Step 6: Verify login flow works**

Start backend (`start.bat`), start Vite dev server. Navigate to `http://localhost:5173/`. Should see login form. Login with valid credentials should show "Analyse (TODO)".

**Step 7: Commit**

```bash
git add frontend-react/src/
git commit -m "feat: add auth context, login form, and protected routes"
```

---

### Task 5: Header + Navigation + StatusBadge + Toast

**Files:**
- Create: `frontend-react/src/components/Header.jsx`
- Create: `frontend-react/src/styles/Header.module.css`
- Create: `frontend-react/src/components/StatusBadge.jsx`
- Create: `frontend-react/src/components/Toast.jsx`
- Create: `frontend-react/src/styles/Toast.module.css`
- Create: `frontend-react/src/context/AppContext.jsx`
- Modify: `frontend-react/src/App.jsx` (add Header + layout)

**Step 1: Create AppContext for global state + toast**

```jsx
// frontend-react/src/context/AppContext.jsx
import { createContext, useContext, useState, useCallback, useRef } from 'react'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timerRef = useRef(null)

  const showToast = useCallback((message) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setToast(message)
    timerRef.current = setTimeout(() => setToast(null), 3000)
  }, [])

  return (
    <AppContext.Provider value={{ toast, showToast }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
```

**Step 2: Create StatusBadge component**

Port the health check from `app.js` lines 1386-1432.

```jsx
// frontend-react/src/components/StatusBadge.jsx
import { useState, useEffect } from 'react'
import * as api from '../services/api'

export default function StatusBadge() {
  const [server, setServer] = useState({ online: false, text: 'Server' })
  const [ai, setAi] = useState({ online: false, text: 'KI' })

  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.checkHealth()
        setServer({ online: true, text: 'Server' })
        if (data.ai?.engine === 'claude') {
          setAi({ online: true, text: 'Claude AI' })
        } else if (data.ai?.engine === 'ollama') {
          setAi({ online: true, text: 'Ollama' })
        } else if (data.ai?.engine === 'regex') {
          setAi({ online: true, text: 'Basis-Modus', warn: true })
        } else {
          setAi({ online: true, text: 'KI' })
        }
      } catch {
        setServer({ online: false, text: 'Offline' })
        setAi({ online: false, text: 'KI' })
      }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  const dotStyle = (online, warn) => ({
    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
    background: online ? (warn ? '#d97706' : '#16a34a') : (server.online === false ? '#dc2626' : '#6b7280'),
  })

  return (
    <>
      <div className="status-badge" title="Server-Status">
        <span style={dotStyle(server.online)} />
        <span>{server.text}</span>
      </div>
      <div className="status-badge" title="KI-Engine">
        <span style={dotStyle(ai.online, ai.warn)} />
        <span>{ai.text}</span>
      </div>
    </>
  )
}
```

**Step 3: Create Header component**

Port from `index.html` lines 35-60.

```jsx
// frontend-react/src/components/Header.jsx
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import StatusBadge from './StatusBadge'
import styles from '../styles/Header.module.css'

export default function Header() {
  const { user, logout } = useAuth()

  const navItems = [
    { to: '/analyse', label: 'Analyse' },
    { to: '/katalog', label: 'Katalog' },
    { to: '/historie', label: 'Historie' },
  ]
  if (user?.role === 'admin') {
    navItems.push({ to: '/benutzer', label: 'Benutzer' })
  }

  return (
    <header className={styles.header}>
      <div className={styles.brand}>Frank Tueren AG</div>
      <nav className={styles.nav}>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.active : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className={styles.status}>
        <StatusBadge />
        <button className={styles.logoutBtn} onClick={logout} title="Abmelden">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </header>
  )
}
```

**Step 4: Create Header CSS Module**

Extract from `frontend/style.css` lines 53-149 + 1321-1339:

```css
/* frontend-react/src/styles/Header.module.css */
.header {
  height: var(--header-h);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 50;
  gap: 2rem;
}

.brand {
  font-weight: 700;
  font-size: 0.9375rem;
  color: var(--text);
  white-space: nowrap;
  letter-spacing: -0.01em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
}

.navItem {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  background: none;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius);
  transition: color var(--transition), background var(--transition);
  position: relative;
  white-space: nowrap;
  text-decoration: none;
}

.navItem:hover {
  color: var(--text);
  background: var(--bg-subtle);
}

.active {
  color: var(--text);
  font-weight: 600;
}

.active::after {
  content: '';
  position: absolute;
  bottom: -0.6875rem;
  left: 0.75rem;
  right: 0.75rem;
  height: 2px;
  background: var(--text);
  border-radius: 1px;
}

.status {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.logoutBtn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition);
  margin-left: 0.25rem;
}

.logoutBtn:hover {
  background: var(--danger-light);
  color: var(--danger);
  border-color: var(--danger-border);
}
```

**Step 5: Add status-badge styles to global.css**

Append to `global.css`:
```css
.status-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--text-muted);
  padding: 0.1875rem 0.5rem;
  border-radius: 9999px;
  background: var(--bg-subtle);
  border: 1px solid var(--border);
}
```

**Step 6: Create Toast component**

```jsx
// frontend-react/src/components/Toast.jsx
import { useApp } from '../context/AppContext'
import styles from '../styles/Toast.module.css'

export default function Toast() {
  const { toast } = useApp()
  if (!toast) return null
  return <div className={styles.toast}>{toast}</div>
}
```

```css
/* frontend-react/src/styles/Toast.module.css */
.toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  background: var(--text);
  color: white;
  padding: 0.625rem 1rem;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 200;
  animation: toastIn 0.2s ease;
}
```

**Step 7: Update App.jsx with Header + layout**

```jsx
// frontend-react/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { AppProvider } from './context/AppContext'
import LoginForm from './components/LoginForm'
import Header from './components/Header'
import Toast from './components/Toast'

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!user) return <LoginForm />

  return (
    <>
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/analyse" replace />} />
          <Route path="/analyse" element={<div>Analyse (TODO)</div>} />
          <Route path="/katalog" element={<div>Katalog (TODO)</div>} />
          <Route path="/historie" element={<div>Historie (TODO)</div>} />
          <Route path="/benutzer" element={
            user.role === 'admin' ? <div>Benutzer (TODO)</div> : <Navigate to="/analyse" replace />
          } />
          <Route path="*" element={<Navigate to="/analyse" replace />} />
        </Routes>
      </main>
      <Toast />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </BrowserRouter>
  )
}
```

**Step 8: Add main-content style to global.css**

```css
.main-content {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
}
```

**Step 9: Verify header renders, nav links work, status badges show**

Start backend + Vite dev server. Login. Confirm header shows with navigation tabs, status badges, and logout button. Click tabs to verify routing.

**Step 10: Commit**

```bash
git add frontend-react/src/
git commit -m "feat: add header, navigation, status badges, toast, and app layout"
```

---

### Task 6: FileUpload Component

**Files:**
- Create: `frontend-react/src/components/FileUpload.jsx`
- Create: `frontend-react/src/styles/FileUpload.module.css`

**Step 1: Create FileUpload component**

Port drag&drop + file/folder handling from `app.js` lines 107-265 and HTML from `index.html` lines 73-167. This is the most complex component. Key behaviors:
- Drag & drop zone (single files, multiple files, or folder)
- Single file → show file preview with name/size/icon
- Multiple files → show file list with count and total size
- Folder selection via hidden `webkitdirectory` input
- Allowed extensions filter
- `onFilesReady(files)` callback to parent (AnalysePage)

```jsx
// frontend-react/src/components/FileUpload.jsx
import { useState, useRef, useCallback } from 'react'
import styles from '../styles/FileUpload.module.css'

const ALLOWED_EXTS = ['xlsx','xls','xlsm','pdf','docx','doc','txt','jpg','jpeg','png','bmp','tif','tiff','dwg','dxf']
const FILE_ICONS = {
  pdf: '\u{1F4D5}', xlsx: '\u{1F4D7}', xls: '\u{1F4D7}', xlsm: '\u{1F4D7}',
  docx: '\u{1F4D8}', doc: '\u{1F4D8}', txt: '\u{1F4C4}',
  jpg: '\u{1F5BC}', jpeg: '\u{1F5BC}', png: '\u{1F5BC}', bmp: '\u{1F5BC}',
  tif: '\u{1F5BC}', tiff: '\u{1F5BC}', dwg: '\u{1F4D0}', dxf: '\u{1F4D0}',
}

function fmtSize(b) {
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

function getExt(name) {
  return name.split('.').pop().toLowerCase()
}

function getIcon(name) {
  return FILE_ICONS[getExt(name)] || '\u{1F4C4}'
}

function readDirectory(dirEntry) {
  return new Promise(resolve => {
    const files = []
    const reader = dirEntry.createReader()
    function readBatch() {
      reader.readEntries(entries => {
        if (entries.length === 0) { resolve(files); return }
        const promises = []
        for (const entry of entries) {
          if (entry.isFile) {
            promises.push(new Promise(res => entry.file(f => { files.push(f); res() })))
          } else if (entry.isDirectory) {
            promises.push(readDirectory(entry).then(sub => files.push(...sub)))
          }
        }
        Promise.all(promises).then(readBatch)
      })
    }
    readBatch()
  })
}

export default function FileUpload({ onFilesReady, disabled }) {
  const [singleFile, setSingleFile] = useState(null)
  const [multiFiles, setMultiFiles] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)

  const filterValid = (files) =>
    files.filter(f => ALLOWED_EXTS.includes(getExt(f.name)))

  const processFiles = useCallback((files) => {
    const valid = filterValid(files)
    if (valid.length === 0) return
    if (valid.length === 1) {
      setSingleFile(valid[0])
      setMultiFiles([])
      onFilesReady?.({ type: 'single', file: valid[0] })
    } else {
      setMultiFiles(valid)
      setSingleFile(null)
      onFilesReady?.({ type: 'multi', files: valid })
    }
  }, [onFilesReady])

  const handleDrop = useCallback(async (e) => {
    e.preventDefault()
    setDragOver(false)
    const items = e.dataTransfer.items
    const directFiles = []

    if (items && items.length > 0) {
      const folderPromises = []
      for (let i = 0; i < items.length; i++) {
        const entry = items[i].webkitGetAsEntry?.() || items[i].getAsEntry?.()
        if (entry?.isDirectory) {
          folderPromises.push(readDirectory(entry))
        } else if (items[i].kind === 'file') {
          const f = items[i].getAsFile()
          if (f) directFiles.push(f)
        }
      }
      if (folderPromises.length > 0) {
        const results = await Promise.all(folderPromises)
        processFiles(directFiles.concat(results.flat()))
        return
      }
    }

    if (directFiles.length === 0) {
      directFiles.push(...Array.from(e.dataTransfer.files))
    }
    processFiles(directFiles)
  }, [processFiles])

  const clearAll = () => {
    setSingleFile(null)
    setMultiFiles([])
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
    onFilesReady?.(null)
  }

  const hasFiles = singleFile || multiFiles.length > 0

  return (
    <div>
      <div
        className={`${styles.dropZone} ${dragOver ? styles.dragOver : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div className={styles.dropVisual}>
          <div className={styles.dropCircle}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p className={styles.dropMain}>Dateien oder Ordner hier ablegen</p>
          <p className={styles.dropHint}>Excel, PDF, Word &middot; max. 500 MB</p>
          <div className={styles.uploadButtons}>
            <button
              type="button"
              className={styles.uploadBtnFolder}
              onClick={e => { e.stopPropagation(); folderInputRef.current?.click() }}
            >
              Ordner auswaehlen
            </button>
            <button
              type="button"
              className={styles.uploadBtnFile}
              onClick={e => { e.stopPropagation(); fileInputRef.current?.click() }}
            >
              Dateien auswaehlen
            </button>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.xlsm,.pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tif,.tiff,.dwg,.dxf"
          multiple
          onChange={e => processFiles(Array.from(e.target.files))}
          hidden
        />
        <input
          ref={folderInputRef}
          type="file"
          webkitdirectory=""
          directory=""
          onChange={e => processFiles(Array.from(e.target.files))}
          hidden
        />
      </div>

      {/* Single file preview */}
      {singleFile && (
        <div className={styles.filePreview}>
          <span className={styles.fileIcon}>{getIcon(singleFile.name)}</span>
          <div className={styles.fileInfo}>
            <p className={styles.fileName}>{singleFile.name}</p>
            <p className={styles.fileSize}>{fmtSize(singleFile.size)}</p>
          </div>
          <button className={styles.removeBtn} onClick={clearAll} title="Entfernen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      )}

      {/* Multi-file preview */}
      {multiFiles.length > 0 && (
        <div className={styles.filesPreview}>
          <div className={styles.filesHeader}>
            <span className={styles.filesCount}>{multiFiles.length} Dateien</span>
            <span className={styles.filesTotalSize}>{fmtSize(multiFiles.reduce((s, f) => s + f.size, 0))}</span>
            <button className={styles.removeBtn} onClick={clearAll} title="Alle entfernen">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div className={styles.filesList}>
            {multiFiles.map((f, i) => (
              <div key={i} className={styles.fileItem}>
                <span className={styles.fileItemIcon}>{getIcon(f.name)}</span>
                <span className={styles.fileItemName} title={f.name}>{f.name}</span>
                <span className={styles.fileItemSize}>{fmtSize(f.size)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Create FileUpload CSS Module**

Extract from `frontend/style.css` the drop-zone (lines 281-371), file-preview (lines 373-406), multi-file (lines 408-449), and button styles:

```css
/* frontend-react/src/styles/FileUpload.module.css */
.dropZone {
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
  background: var(--bg);
  margin-bottom: 1.25rem;
}
.dropZone:hover { border-color: var(--accent); background: var(--accent-light); }
.dragOver { border-color: var(--accent); background: var(--accent-light); border-style: solid; }
.dropVisual { display: flex; flex-direction: column; align-items: center; }
.dropCircle { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; margin-bottom: 0.875rem; color: var(--text-muted); }
.dropZone:hover .dropCircle, .dragOver .dropCircle { color: var(--accent); }
.dropMain { font-size: 0.9375rem; font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
.dropHint { font-size: 0.8125rem; color: var(--text-muted); margin-bottom: 0.75rem; }
.uploadButtons { display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap; }
.uploadBtnFolder, .uploadBtnFile {
  display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5rem 1rem;
  border-radius: var(--radius); font-size: 0.8125rem; font-weight: 600; cursor: pointer;
  transition: all var(--transition); border: 1px solid;
}
.uploadBtnFolder { background: var(--accent); color: #fff; border-color: var(--accent); }
.uploadBtnFolder:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.uploadBtnFile { background: var(--bg); color: var(--text-secondary); border-color: var(--border); }
.uploadBtnFile:hover { background: var(--bg-hover); border-color: var(--text-muted); }

.filePreview {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
  background: var(--accent-light); border: 1px solid var(--accent-border); border-radius: var(--radius);
  margin-bottom: 1.25rem;
}
.fileIcon { font-size: 1.25rem; line-height: 1; flex-shrink: 0; }
.fileInfo { flex: 1; min-width: 0; }
.fileName { font-weight: 600; font-size: 0.875rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fileSize { font-size: 0.8125rem; color: var(--text-muted); }
.removeBtn {
  background: none; border: none; cursor: pointer; color: var(--text-faint);
  padding: 0.25rem; border-radius: var(--radius-sm); transition: all var(--transition); display: flex; align-items: center;
}
.removeBtn:hover { background: var(--danger-light); color: var(--danger); }

.filesPreview { margin-bottom: 1.25rem; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.filesHeader {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0.875rem;
  background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 0.8125rem;
}
.filesCount { font-weight: 600; color: var(--text-secondary); }
.filesTotalSize { color: var(--text-faint); font-size: 0.75rem; flex: 1; }
.filesList { max-height: 200px; overflow-y: auto; }
.fileItem {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.4375rem 0.875rem;
  border-bottom: 1px solid var(--border-light); font-size: 0.8125rem;
}
.fileItem:last-child { border-bottom: none; }
.fileItemIcon { font-size: 1rem; }
.fileItemName { flex: 1; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fileItemSize { color: var(--text-faint); font-size: 0.75rem; min-width: 50px; text-align: right; }
```

**Step 3: Commit**

```bash
git add frontend-react/src/components/FileUpload.jsx frontend-react/src/styles/FileUpload.module.css
git commit -m "feat: add FileUpload component with drag-and-drop"
```

---

### Task 7: AnalysePage (Upload + Processing + Results + Download)

**Files:**
- Create: `frontend-react/src/pages/AnalysePage.jsx`
- Create: `frontend-react/src/styles/AnalysePage.module.css`
- Create: `frontend-react/src/hooks/useSSE.js`
- Modify: `frontend-react/src/App.jsx` (import AnalysePage)

This is the biggest component. It manages the 3-step workflow: Upload → Processing → Results.

**Step 1: Create useSSE hook**

Port SSE logic from `app.js` lines 472-505:

```js
// frontend-react/src/hooks/useSSE.js
import { useRef, useCallback } from 'react'
import * as api from '../services/api'

export function useSSE() {
  const esRef = useRef(null)

  const pollSSE = useCallback((jobId, onProgress) => {
    return new Promise((resolve, reject) => {
      const es = api.createSSE(jobId)
      esRef.current = es
      let settled = false
      const settle = (fn, val) => {
        if (!settled) { settled = true; es.close(); fn(val) }
      }

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === 'keepalive') return
          if (data.progress && onProgress) onProgress(data.progress)
          if (data.status === 'completed') settle(resolve, data.result)
          if (data.status === 'failed') settle(reject, new Error(data.error || 'Analyse fehlgeschlagen'))
        } catch (err) {
          console.warn('SSE parse error:', err)
        }
      }
      es.onerror = () => settle(reject, new Error('SSE connection error'))
    })
  }, [])

  const pollFallback = useCallback(async (jobId, onProgress, statusPath = '/analyze/status/') => {
    const POLL_INTERVAL = 2000
    const MAX_POLLS = 450

    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL))
      const job = await api.getJobStatus(jobId, statusPath)
      if (job.progress && onProgress) onProgress(job.progress)
      if (job.status === 'completed') return job.result
      if (job.status === 'failed') throw new Error(job.error || 'Verarbeitung fehlgeschlagen')
    }
    throw new Error('Timeout: Bitte erneut versuchen.')
  }, [])

  const pollJob = useCallback(async (jobId, onProgress, statusPath = '/analyze/status/') => {
    if (statusPath === '/analyze/status/') {
      try {
        return await pollSSE(jobId, onProgress)
      } catch (e) {
        console.warn('SSE fallback to polling:', e.message)
      }
    }
    return await pollFallback(jobId, onProgress, statusPath)
  }, [pollSSE, pollFallback])

  const cleanup = useCallback(() => {
    if (esRef.current) { esRef.current.close(); esRef.current = null }
  }, [])

  return { pollJob, cleanup }
}
```

**Step 2: Create AnalysePage**

This is a large component that manages 4 panels: upload, processing, results, error.

```jsx
// frontend-react/src/pages/AnalysePage.jsx
import { useState, useCallback, useRef } from 'react'
import FileUpload from '../components/FileUpload'
import { useApp } from '../context/AppContext'
import { useSSE } from '../hooks/useSSE'
import * as api from '../services/api'
import styles from '../styles/AnalysePage.module.css'

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

function StepIndicator({ step }) {
  const pills = [
    { num: 1, label: 'Upload' },
    { num: 2, label: 'Analyse' },
    { num: 3, label: 'Ergebnis' },
  ]
  return (
    <div className={styles.stepsIndicator}>
      {pills.map((p, i) => (
        <div key={p.num}>
          {i > 0 && <div className={styles.pillConnector} />}
          <div className={`${styles.pill} ${step > p.num ? styles.pillDone : ''} ${step === p.num ? styles.pillActive : ''}`}>
            <span className={styles.pillNum}>{p.num}</span>
            <span className={styles.pillLabel}>{p.label}</span>
          </div>
        </div>
      )).reduce((acc, el, i) => {
        if (i > 0) acc.push(<div key={`conn-${i}`} className={styles.pillConnector} />)
        acc.push(el)
        return acc
      }, [])}
    </div>
  )
}

const STEP_IDS = ['upload', 'ai', 'match', 'gen']
const STEP_NAMES_SINGLE = ['Datei hochladen', 'Tuerliste parsen', 'Produkt-Matching', 'Machbarkeitsanalyse erstellen']
const STEP_NAMES_FOLDER = ['Dateien hochladen & klassifizieren', 'Tuerlisten parsen & zusammenfuehren', 'Produkt-Matching', 'Machbarkeitsanalyse erstellen']

function ProcessingPanel({ steps, subtitle }) {
  const DOT_SVG = {
    running: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><circle cx="12" cy="12" r="3" fill="white"/></svg>,
    done: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>,
    error: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
    pending: null,
  }

  return (
    <div className={styles.processingCard}>
      <div className={styles.processingHeader}>
        <div className={styles.processingSpinner} />
        <div>
          <h2 className={styles.cardTitle}>Verarbeitung laeuft</h2>
          <p className={styles.cardDesc}>{subtitle}</p>
        </div>
      </div>
      <div className={styles.stepsList}>
        {steps.map(s => (
          <div key={s.id} className={styles.stepItem}>
            <div className={`${styles.stepDot} ${styles[s.state]}`}>
              {DOT_SVG[s.state]}
            </div>
            <div>
              <p className={styles.stepName}>{s.name}</p>
              <p className={styles.stepStatus}>{s.status}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AnalysePage() {
  const { showToast } = useApp()
  const { pollJob, cleanup } = useSSE()
  const [panel, setPanel] = useState('upload') // upload | processing | results | error
  const [currentStep, setCurrentStep] = useState(1)
  const [subtitle, setSubtitle] = useState('Bitte warten...')
  const [errorMsg, setErrorMsg] = useState('')
  const [filesData, setFilesData] = useState(null) // { type, file/files }
  const [analysis, setAnalysis] = useState(null)
  const [offer, setOffer] = useState(null)
  const [steps, setSteps] = useState(
    STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' }))
  )

  const updateStep = useCallback((id, state, status) => {
    setSteps(prev => prev.map(s => s.id === id ? { ...s, state, status } : s))
  }, [])

  const handleFilesReady = useCallback((data) => {
    setFilesData(data)
  }, [])

  const startUpload = async () => {
    if (!filesData) return
    if (filesData.type === 'single') {
      if (filesData.file.size > MAX_FILE_SIZE_BYTES) {
        showToast('Datei ist zu gross (max. 100 MB)')
        return
      }
      await runSingleWorkflow(filesData.file)
    } else {
      const tooBig = filesData.files.find(f => f.size > MAX_FILE_SIZE_BYTES)
      if (tooBig) {
        showToast(`Datei "${tooBig.name}" ist zu gross (max. 100 MB)`)
        return
      }
      await runFolderWorkflow(filesData.files)
    }
  }

  const runSingleWorkflow = async (file) => {
    setPanel('processing')
    setCurrentStep(2)
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' })))
    updateStep('upload', 'running', 'Datei wird hochgeladen...')
    setSubtitle('Datei wird hochgeladen...')

    try {
      const up = await api.uploadFile(file)
      if (!up.file_id) throw new Error('Upload fehlgeschlagen: keine file_id erhalten')
      updateStep('upload', 'done', `${up.filename} hochgeladen (${up.text_length.toLocaleString('de-CH')} Zeichen)`)

      updateStep('ai', 'running', 'Tuerliste wird geparst...')
      setSubtitle('Tuerliste wird analysiert...')

      const { job_id } = await api.startAnalysis(up.file_id)
      const analysisResult = await pollJob(job_id, (progress) => {
        setSubtitle(progress || 'Analyse laeuft...')
      })
      setAnalysis(analysisResult)

      const pos = analysisResult.requirements?.positionen?.length || 0
      updateStep('ai', 'done', `${pos} Tuerpositionen erkannt`)

      const s = analysisResult.matching?.summary || {}
      updateStep('match', 'done', `${s.matched_count || 0} erfuellbar, ${s.partial_count || 0} teilweise, ${s.unmatched_count || 0} nicht erfuellbar`)

      setSubtitle('Machbarkeitsanalyse wird erstellt...')
      updateStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...')

      const { job_id: resultJobId } = await api.generateResult(analysisResult.requirements, analysisResult.matching)
      const result = await pollJob(resultJobId, (progress) => {
        setSubtitle(progress || 'Ergebnis wird erstellt...')
      }, '/result/status/')
      setOffer(result)
      updateStep('gen', 'done', result.message)

      setCurrentStep(3)
      setPanel('results')
    } catch (err) {
      console.error('[Workflow] Analysis failed:', err)
      setErrorMsg(err.message)
      setPanel('error')
      setCurrentStep(1)
    }
  }

  const runFolderWorkflow = async (files) => {
    setPanel('processing')
    setCurrentStep(2)
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_FOLDER[i], state: 'pending', status: 'Warte...' })))
    updateStep('upload', 'running', `${files.length} Dateien werden hochgeladen...`)
    setSubtitle('Dateien werden hochgeladen...')

    try {
      const uploadResult = await api.uploadFolder(files)
      const summary = uploadResult.summary || {}
      const classInfo = []
      if (summary.tuerliste_count) classInfo.push(`${summary.tuerliste_count} Tuerliste(n)`)
      if (summary.spezifikation_count) classInfo.push(`${summary.spezifikation_count} Spezifikation(en)`)
      if (summary.plan_count) classInfo.push(`${summary.plan_count} Plaene`)
      if (summary.foto_count) classInfo.push(`${summary.foto_count} Fotos`)
      if (summary.sonstig_count) classInfo.push(`${summary.sonstig_count} Sonstige`)
      updateStep('upload', 'done', `${uploadResult.total_files} Dateien: ${classInfo.join(', ')}`)

      if (!summary.tuerliste_count) {
        throw new Error('Keine Tuerliste erkannt. Bitte stellen Sie sicher, dass mindestens eine Excel-Datei mit Tuerlisten-Spalten enthalten ist.')
      }

      updateStep('ai', 'running', 'Tuerlisten werden geparst...')
      setSubtitle('Projekt wird analysiert...')

      const { job_id } = await api.startProjectAnalysis(uploadResult.project_id)
      const analysisResult = await pollJob(job_id, (progress) => {
        setSubtitle(progress || 'Analyse laeuft...')
        if (progress?.includes('Matching')) {
          updateStep('ai', 'done', 'Tuerlisten geparst')
          updateStep('match', 'running', progress)
        }
      })
      setAnalysis(analysisResult)

      const pos = analysisResult.requirements?.positionen?.length || 0
      updateStep('ai', 'done', `${pos} Tuerpositionen erkannt`)

      const s = analysisResult.matching?.summary || {}
      updateStep('match', 'done', `${s.matched_count || 0} erfuellbar, ${s.partial_count || 0} teilweise, ${s.unmatched_count || 0} nicht erfuellbar`)

      setSubtitle('Machbarkeitsanalyse wird erstellt...')
      updateStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...')

      const { job_id: resultJobId } = await api.generateResult(analysisResult.requirements, analysisResult.matching)
      const result = await pollJob(resultJobId, (progress) => {
        setSubtitle(progress || 'Ergebnis wird erstellt...')
      }, '/result/status/')
      setOffer(result)
      updateStep('gen', 'done', result.message)

      setCurrentStep(3)
      setPanel('results')
    } catch (err) {
      console.error('[FolderWorkflow] Failed:', err)
      setErrorMsg(err.message)
      setPanel('error')
      setCurrentStep(1)
    }
  }

  const resetAll = () => {
    cleanup()
    setPanel('upload')
    setCurrentStep(1)
    setFilesData(null)
    setAnalysis(null)
    setOffer(null)
    setErrorMsg('')
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' })))
  }

  return (
    <div>
      <StepIndicator step={currentStep} />

      {panel === 'upload' && (
        <div>
          <h1 className={styles.sectionTitle}>Tuerliste hochladen</h1>
          <p className={styles.sectionDesc}>Einzelne Datei oder kompletten Projektordner hochladen und automatisch analysieren lassen.</p>
          <FileUpload onFilesReady={handleFilesReady} />
          <button
            className={styles.ctaBtn}
            onClick={startUpload}
            disabled={!filesData}
          >
            Hochladen &amp; Analysieren
          </button>
        </div>
      )}

      {panel === 'processing' && (
        <ProcessingPanel steps={steps} subtitle={subtitle} />
      )}

      {panel === 'results' && analysis && (
        <ResultsPanel analysis={analysis} offer={offer} onReset={resetAll} />
      )}

      {panel === 'error' && (
        <div className={styles.errorCard}>
          <h2 className={styles.errorTitle}>Fehler aufgetreten</h2>
          <div className={styles.errorMsg}>{errorMsg}</div>
          <p className={styles.errorHint}>Browser-Konsole (F12) zeigt weitere Details.</p>
          <button className={`${styles.ctaBtn} ${styles.secondary}`} onClick={resetAll}>
            Erneut versuchen
          </button>
        </div>
      )}
    </div>
  )
}

// Inline ResultsPanel – displays stats, match rate, downloads, positions
function ResultsPanel({ analysis, offer, onReset }) {
  const [detailItem, setDetailItem] = useState(null)
  const match = analysis.matching || {}
  const summary = match.summary || {}

  const allItems = []
  const sections = [
    { items: match.matched || [], status: 'matched', label: 'Erfuellbare Positionen', cls: 'green', icon: '\u2713' },
    { items: match.partial || [], status: 'partial', label: 'Teilweise erfuellbare Positionen', cls: 'orange', icon: '\u26A0' },
    { items: match.unmatched || [], status: 'unmatched', label: 'Nicht erfuellbare Positionen', cls: 'red', icon: '\u2717' },
  ]
  sections.forEach(sec => {
    sec.items.forEach(item => allItems.push({ ...item, _status: sec.status }))
  })

  const stats = [
    { num: summary.total_positions || 0, label: 'Positionen gesamt', cls: 'blue' },
    { num: summary.matched_count || 0, label: 'Erfuellbar', cls: 'green' },
    { num: summary.partial_count || 0, label: 'Teilweise', cls: 'orange' },
    { num: summary.unmatched_count || 0, label: 'Nicht erfuellbar', cls: 'red' },
  ]

  const rate = summary.match_rate || 0

  return (
    <div>
      <div className={styles.resultsTopbar}>
        <button className={styles.resetBtn} onClick={onReset}>Neue Analyse starten</button>
      </div>

      <div className={styles.statGrid}>
        {stats.map((s, i) => (
          <div key={i} className={`${styles.statCard} ${styles[s.cls]}`}>
            <div className={styles.statNum}>{s.num}</div>
            <div className={styles.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className={styles.matchRateCard}>
        <div className={styles.matchRateHeader}>
          <span className={styles.matchRateLabel}>Erfuellungsrate</span>
          <span className={styles.matchRateValue}>{rate}%</span>
        </div>
        <div className={styles.matchBarBg}>
          <div className={styles.matchBarFill} style={{ width: `${rate}%` }} />
        </div>
      </div>

      {offer?.has_result && offer.result_id && (
        <div className={styles.downloadSection}>
          <p className={styles.downloadTitle}>Dokumente herunterladen</p>
          <a
            href={api.getResultDownloadUrl(offer.result_id)}
            className={styles.dlBtn}
            download
          >
            📗 Excel herunterladen
          </a>
        </div>
      )}

      {sections.map(({ items, status, label, cls, icon }) => {
        if (!items.length) return null
        return (
          <div key={status} className={styles.positionsSection}>
            <div className={`${styles.sectionHeader} ${styles[cls]}`}>
              <span>{icon}</span>
              <span>{label}</span>
              <span className={styles.sectionBadge}>{items.length}</span>
            </div>
            <div className={styles.tableWrap}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Pos.</th><th>Beschreibung</th><th>Menge</th>
                    <th>Brandschutz</th><th>FTAG Produkt</th><th>Kategorie</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => {
                    const pos = item.original_position || item
                    const products = item.matched_products || []
                    let ftag = '—'
                    if (products.length > 0) {
                      const names = products.map(p =>
                        p['Türblatt / Verglasungsart / Rollkasten'] ||
                        p['Tuerblatt / Verglasungsart / Rollkasten'] || ''
                      ).filter(n => n)
                      ftag = [...new Set(names)].join(' / ') || '—'
                    }
                    return (
                      <tr key={i} className={styles.clickableRow} onClick={() => setDetailItem(item)}>
                        <td><strong>{item.position || pos.position || '—'}</strong></td>
                        <td>{item.beschreibung || pos.beschreibung || pos.tuertyp || '—'}</td>
                        <td>{pos.menge || item.menge || 1}</td>
                        <td>{pos.brandschutz || '—'}</td>
                        <td title={ftag}>{ftag.substring(0, 60)}{ftag.length > 60 ? '...' : ''}</td>
                        <td>{item.category || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}

      {detailItem && (
        <PositionDetailModal item={detailItem} onClose={() => setDetailItem(null)} />
      )}
    </div>
  )
}

function PositionDetailModal({ item, onClose }) {
  const pos = item.original_position || item
  const statusMap = {
    matched: { label: 'Erfuellbar', cls: styles.tagGreen },
    partial: { label: 'Teilweise', cls: styles.tagOrange },
    unmatched: { label: 'Nicht erfuellbar', cls: styles.tagRed },
  }
  const st = statusMap[item._status] || { label: item._status, cls: '' }

  const fields = [
    ['Tuer-Nr', pos.position || item.position],
    ['Beschreibung', item.beschreibung || pos.beschreibung],
    ['Tuertyp', pos.tuertyp],
    ['Brandschutz', pos.brandschutz],
    ['Schallschutz', pos.schallschutz],
    ['Breite', pos.breite ? `${pos.breite} mm` : null],
    ['Hoehe', pos.hoehe ? `${pos.hoehe} mm` : null],
    ['Menge', pos.menge],
  ].filter(([, v]) => v != null && v !== '' && v !== '—')

  const products = item.matched_products || []

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h3>Position {item.position || pos.position || '—'}</h3>
          <button className={styles.modalClose} onClick={onClose}>×</button>
        </div>
        <div className={styles.modalBody}>
          <div style={{ marginBottom: '1rem' }}>
            <span className={`${styles.tag} ${st.cls}`}>{st.label}</span>
            {item.confidence && (
              <span style={{ color: 'var(--text-faint)', fontSize: '0.8125rem', marginLeft: '0.5rem' }}>
                Konfidenz: {(item.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>

          <h4 style={{ fontSize: '.875rem', fontWeight: 600, marginBottom: '.5rem' }}>Kundenanforderung</h4>
          <div className={styles.detailFields}>
            {fields.map(([label, value]) => (
              <div key={label} className={styles.detailField}>
                <span className={styles.detailFieldLabel}>{label}</span>
                <span className={styles.detailFieldValue}>{String(value)}</span>
              </div>
            ))}
          </div>

          <h4 style={{ fontSize: '.875rem', fontWeight: 600, margin: '1rem 0 .5rem' }}>FTAG Produkt</h4>
          {products.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>Kein passendes Produkt gefunden</p>
          ) : (
            products.map((p, i) => (
              <div key={i} className={styles.detailFields}>
                {Object.entries(p).filter(([k, v]) => v != null && v !== '' && !k.startsWith('_')).slice(0, 10).map(([k, v]) => (
                  <div key={k} className={styles.detailField}>
                    <span className={styles.detailFieldLabel}>{k}</span>
                    <span className={styles.detailFieldValue}>{String(v)}</span>
                  </div>
                ))}
              </div>
            ))
          )}

          {item.reason && (
            <div style={{ marginTop: '.75rem', padding: '.5rem .75rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius)', fontSize: '.8125rem', color: 'var(--text-muted)' }}>
              {item.reason}
            </div>
          )}
        </div>
        <div className={styles.modalFooter}>
          <button className={`${styles.ctaBtn} ${styles.secondary} ${styles.slim}`} onClick={onClose}>Schliessen</button>
        </div>
      </div>
    </div>
  )
}
```

**Note:** The `PositionDetailModal` uses `useEffect` – add `import { useEffect } from 'react'` at the top.

**Step 2: Create AnalysePage CSS Module**

This is large – extract processing, results, stat-grid, match-rate, download, positions, table, modal, and error styles from `frontend/style.css`. Due to size, create `frontend-react/src/styles/AnalysePage.module.css` with the relevant CSS blocks from the original `style.css` (lines 151-167, 233-245, 451-498, 564-655, 618-710, 712-768, 770-797, 799-827, 828-868, 870-900, 918-941, 988-1050, 1095-1180, 1182-1198, 1246, 1341-1352).

Key class mappings from global to module:
- `.section-title` → `.sectionTitle`
- `.section-desc` → `.sectionDesc`
- `.cta-btn` → `.ctaBtn`
- `.stat-grid` → `.statGrid`
- `.stat-card` → `.statCard`
- `.processing-card` → `.processingCard`
- `.modal-overlay` → `.modalOverlay`
- etc.

**Step 3: Update App.jsx**

```jsx
import AnalysePage from './pages/AnalysePage'
// ... in Routes:
<Route path="/analyse" element={<AnalysePage />} />
```

**Step 4: Verify full analysis workflow**

Start backend + Vite dev. Login, upload an Excel file, confirm the 3-step workflow runs and results display.

**Step 5: Commit**

```bash
git add frontend-react/src/
git commit -m "feat: add AnalysePage with upload, processing, results, and detail modal"
```

---

### Task 8: KatalogPage

**Files:**
- Create: `frontend-react/src/pages/KatalogPage.jsx`
- Create: `frontend-react/src/styles/KatalogPage.module.css`
- Modify: `frontend-react/src/App.jsx` (import KatalogPage)

**Step 1: Create KatalogPage**

Port catalog view from `app.js` lines 812-930 and HTML `index.html` lines 269-326.

```jsx
// frontend-react/src/pages/KatalogPage.jsx
import { useState, useEffect, useRef } from 'react'
import { useApp } from '../context/AppContext'
import * as api from '../services/api'
import styles from '../styles/KatalogPage.module.css'

export default function KatalogPage() {
  const { showToast } = useApp()
  const [catalogInfo, setCatalogInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  useEffect(() => { loadInfo() }, [])

  const loadInfo = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getCatalogInfo()
      setCatalogInfo(data)
    } catch (err) {
      setError(`Katalog konnte nicht geladen werden: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) return
    setUploading(true)
    try {
      const result = await api.uploadCatalog(uploadFile)
      showToast(result.message)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      loadInfo()
    } catch (err) {
      showToast(`Fehler: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const fmtSize = (b) => {
    if (b < 1024) return `${b} B`
    if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
    return `${(b / 1048576).toFixed(1)} MB`
  }

  return (
    <div>
      <h1 className={styles.sectionTitle}>Produktkatalog</h1>
      <p className={styles.sectionDesc}>FTAG-Produktkatalog verwalten</p>

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Aktueller Katalog</h2>
        {loading && <div className={styles.loadingState}><div className={styles.miniSpinner} /><span>Katalog wird geladen...</span></div>}
        {error && <p className={styles.errorInline}>{error}</p>}
        {catalogInfo && !loading && (
          <>
            <div className={styles.statGrid}>
              {[
                { num: catalogInfo.total_products, label: 'Produkte gesamt', cls: 'blue' },
                { num: catalogInfo.main_products, label: 'Hauptprodukte', cls: 'green' },
                { num: catalogInfo.accessory_products, label: 'Zubehoer', cls: 'orange' },
                { num: catalogInfo.categories, label: 'Kategorien', cls: '' },
              ].map((s, i) => (
                <div key={i} className={`${styles.statCard} ${styles[s.cls] || ''}`}>
                  <div className={styles.statNum}>{s.num}</div>
                  <div className={styles.statLabel}>{s.label}</div>
                </div>
              ))}
            </div>
            {catalogInfo.category_breakdown && (
              <div>
                <p className={styles.catLabel}>Kategorien</p>
                <div className={styles.catBadges}>
                  {Object.entries(catalogInfo.category_breakdown).sort((a, b) => b[1] - a[1]).map(([name, count]) => (
                    <span key={name} className={styles.tagBlue}>{name}: {count}</span>
                  ))}
                </div>
                <p className={styles.catMeta}>
                  Datei: {catalogInfo.filename} &middot; Letzte Aenderung: {catalogInfo.last_modified}
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Neuen Katalog hochladen</h2>
        <p className={styles.sectionDesc}>Excel-Datei (.xlsx) mit der aktuellen FTAG-Produktmatrix hochladen.</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          onChange={e => {
            const f = e.target.files[0]
            if (f && f.name.toLowerCase().endsWith('.xlsx')) setUploadFile(f)
          }}
          className={styles.fileInput}
        />
        {uploadFile && (
          <div className={styles.filePreview}>
            <span>📗</span>
            <span>{uploadFile.name} ({fmtSize(uploadFile.size)})</span>
          </div>
        )}
        <button className={styles.ctaBtn} onClick={handleUpload} disabled={!uploadFile || uploading}>
          {uploading ? 'Wird hochgeladen...' : 'Katalog hochladen'}
        </button>
      </div>
    </div>
  )
}
```

**Step 2: Create CSS Module** (reuse stat-grid patterns from AnalysePage but simplified)

**Step 3: Wire up in App.jsx**

**Step 4: Commit**

```bash
git add frontend-react/src/pages/KatalogPage.jsx frontend-react/src/styles/KatalogPage.module.css
git commit -m "feat: add KatalogPage with catalog info and upload"
```

---

### Task 9: HistoriePage

**Files:**
- Create: `frontend-react/src/pages/HistoriePage.jsx`
- Create: `frontend-react/src/styles/HistoriePage.module.css`
- Modify: `frontend-react/src/App.jsx` (import HistoriePage)

Port history view from `app.js` lines 1021-1187 and HTML `index.html` lines 328-366.

Key features:
- Load history on mount
- History table with date, filename, position counts (colored tags), match rate, action buttons
- Detail panel that shows full analysis when "Details" clicked
- Rematch and Delete buttons

**Step 1: Create HistoriePage** with table, detail panel, rematch/delete handlers.

**Step 2: Create CSS Module**

**Step 3: Wire up in App.jsx**

**Step 4: Commit**

```bash
git add frontend-react/src/pages/HistoriePage.jsx frontend-react/src/styles/HistoriePage.module.css
git commit -m "feat: add HistoriePage with history table and detail view"
```

---

### Task 10: BenutzerPage (Admin)

**Files:**
- Create: `frontend-react/src/pages/BenutzerPage.jsx`
- Create: `frontend-react/src/styles/BenutzerPage.module.css`
- Modify: `frontend-react/src/App.jsx` (import BenutzerPage)

Port user management from `app.js` lines 1438-1525 and HTML `index.html` lines 368-435.

Key features:
- Load users on mount
- Users table with email, role badge, created date, delete button
- "Add user" button → modal with email/password/role form
- Delete user with confirmation

**Step 1: Create BenutzerPage** with user table, add-user modal, delete handler.

**Step 2: Create CSS Module**

**Step 3: Wire up in App.jsx**

**Step 4: Commit**

```bash
git add frontend-react/src/pages/BenutzerPage.jsx frontend-react/src/styles/BenutzerPage.module.css
git commit -m "feat: add BenutzerPage with user management (admin only)"
```

---

### Task 11: CorrectionModal Component

**Files:**
- Create: `frontend-react/src/components/CorrectionModal.jsx`
- Create: `frontend-react/src/styles/CorrectionModal.module.css`
- Modify: `frontend-react/src/pages/AnalysePage.jsx` (integrate CorrectionModal into results)

Port correction system from `app.js` lines 1192-1330 and HTML `index.html` lines 455-500.

Key features:
- Shows current requirement and current product match
- Search input with debounce (350ms) calling `/api/products/search`
- Product results list with selection highlight
- Optional note field
- Save button calls `/api/feedback`

**Step 1: Create CorrectionModal**

**Step 2: Create CSS Module**

**Step 3: Add "Korrigieren" button to ResultsPanel** action column in AnalysePage

**Step 4: Commit**

```bash
git add frontend-react/src/components/CorrectionModal.jsx frontend-react/src/styles/CorrectionModal.module.css
git commit -m "feat: add CorrectionModal for product matching feedback"
```

---

### Task 12: FastAPI Integration + Build Config

**Files:**
- Modify: `frontend-react/vite.config.js` (build output path)
- Modify: `backend/main.py` (serve React build in production)
- Create: `frontend-react/src/styles/responsive.css` (responsive breakpoints)

**Step 1: Configure Vite build output**

Update `vite.config.js`:
```js
build: {
  outDir: '../frontend-react-dist',
  emptyOutDir: true,
}
```

**Step 2: Build the React app**

```bash
cd c:/Users/ALI/Desktop/ClaudeCodeTest/frontend-react && npm run build
```
Expected: Creates `frontend-react-dist/` with `index.html`, `assets/`.

**Step 3: Configure FastAPI to serve React build**

In `backend/main.py`, add a fallback route that serves the React SPA:
```python
# After all API routers, serve React build for non-API routes
from fastapi.staticfiles import StaticFiles
import os

react_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend-react-dist')
if os.path.isdir(react_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(react_dist, "assets")), name="react-assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(react_dist, "index.html"))
```

**Step 4: Add responsive CSS**

Port `@media (max-width: 640px)` block from `style.css` lines 1342-1352 into a `responsive.css` imported in `global.css`.

**Step 5: Test production build**

Build React app, start FastAPI server, navigate to `http://localhost:8000/`. Should serve the React app.

**Step 6: Commit**

```bash
git add frontend-react/vite.config.js backend/main.py frontend-react/src/styles/
git commit -m "feat: configure production build and FastAPI serving"
```

---

## Summary

| Task | Component | Estimated Complexity |
|------|-----------|---------------------|
| 1 | Vite + React scaffold | Low |
| 2 | CSS Migration | Low |
| 3 | API Client | Medium |
| 4 | Auth + Login | Medium |
| 5 | Header + Nav + Toast | Medium |
| 6 | FileUpload | High |
| 7 | AnalysePage (core) | High |
| 8 | KatalogPage | Low |
| 9 | HistoriePage | Medium |
| 10 | BenutzerPage | Low |
| 11 | CorrectionModal | Medium |
| 12 | Build + Integration | Low |

Total: 12 tasks, implementing 1:1 feature parity with the existing vanilla JS frontend.
