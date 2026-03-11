# On-Premise 24/7 Deployment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Frank Tueren AG app (Next.js + FastAPI) accessible 24/7 from the internet, running on the existing Windows 10 PC with auto-start on boot.

**Architecture:** Cloudflare Quick Tunnel exposes localhost:3000 to the internet with free HTTPS. NSSM registers Backend, Frontend, and Tunnel as Windows services that auto-start and auto-restart. Frontend proxies API calls to localhost:8000 server-side, so only port 3000 is tunneled.

**Tech Stack:** cloudflared, NSSM, Windows Services, Batch scripts

---

## Chunk 1: CORS and Config Changes

### Task 1: Update CORS to allow Cloudflare tunnel origins

**Files:**
- Modify: `backend/config.py:159-171`
- Modify: `backend/main.py:252-267`

- [ ] **Step 1: Add trycloudflare.com support to CORS config**

In `backend/config.py`, update the CORS_ORIGINS section to include a `CLOUDFLARE_TUNNEL_URL` setting:

```python
# After line 156 (NEXTJS_ORIGIN)
CLOUDFLARE_TUNNEL_URL: Optional[str] = os.environ.get("CLOUDFLARE_TUNNEL_URL")
```

- [ ] **Step 2: Update CORS middleware in main.py to accept tunnel origins**

In `backend/main.py`, after the existing CORS origins logic (line 258), add:

```python
# Add Cloudflare tunnel URL if configured
_tunnel_url = _os.environ.get("CLOUDFLARE_TUNNEL_URL", "")
if _tunnel_url:
    _cors_origins.append(_tunnel_url)
```

- [ ] **Step 3: Verify backend starts without errors**

Run: `cd backend && python -c "from config import settings; print('OK:', settings.ENVIRONMENT.value)"`
Expected: `OK: development`

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/main.py
git commit -m "feat: add Cloudflare tunnel URL to CORS config"
```

---

## Chunk 2: Install Tools and Create Service Scripts

### Task 2: Create cloudflared download/install script

**Files:**
- Create: `scripts/install-cloudflared.bat`

- [ ] **Step 1: Create the install script**

```bat
@echo off
echo ============================================
echo  Cloudflared Installation
echo ============================================
echo.

REM Check if already installed
where cloudflared >nul 2>&1
if not errorlevel 1 (
    echo cloudflared ist bereits installiert.
    cloudflared --version
    goto :end
)

REM Check if already in scripts directory
if exist "%~dp0cloudflared.exe" (
    echo cloudflared.exe gefunden in %~dp0
    goto :end
)

echo Lade cloudflared herunter...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"

if exist "%~dp0cloudflared.exe" (
    echo [OK] cloudflared erfolgreich heruntergeladen.
    "%~dp0cloudflared.exe" --version
) else (
    echo [FEHLER] Download fehlgeschlagen.
    echo Bitte manuell herunterladen von:
    echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
    pause
    exit /b 1
)

:end
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add scripts/install-cloudflared.bat
git commit -m "feat: add cloudflared install script"
```

### Task 3: Create NSSM download/install script

**Files:**
- Create: `scripts/install-nssm.bat`

- [ ] **Step 1: Create the install script**

```bat
@echo off
echo ============================================
echo  NSSM Installation
echo ============================================
echo.

REM Check if already in scripts directory
if exist "%~dp0nssm.exe" (
    echo nssm.exe gefunden in %~dp0
    goto :end
)

REM Check if in PATH
where nssm >nul 2>&1
if not errorlevel 1 (
    echo nssm ist bereits installiert.
    goto :end
)

echo Lade NSSM herunter...
powershell -Command ^
    "$url = 'https://nssm.cc/release/nssm-2.24.zip'; " ^
    "$zip = '%TEMP%\nssm.zip'; " ^
    "$extract = '%TEMP%\nssm-extract'; " ^
    "Invoke-WebRequest -Uri $url -OutFile $zip; " ^
    "Expand-Archive -Path $zip -DestinationPath $extract -Force; " ^
    "Copy-Item (Get-ChildItem -Path $extract -Recurse -Filter 'nssm.exe' | Where-Object { $_.Directory.Name -eq 'win64' } | Select-Object -First 1).FullName -Destination '%~dp0nssm.exe'; " ^
    "Remove-Item $zip -Force; " ^
    "Remove-Item $extract -Recurse -Force"

if exist "%~dp0nssm.exe" (
    echo [OK] NSSM erfolgreich heruntergeladen.
) else (
    echo [FEHLER] Download fehlgeschlagen.
    echo Bitte manuell herunterladen von: https://nssm.cc/release/nssm-2.24.zip
    echo Die nssm.exe (win64) in den scripts/ Ordner kopieren.
    pause
    exit /b 1
)

:end
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add scripts/install-nssm.bat
git commit -m "feat: add NSSM install script"
```

### Task 4: Create Windows service registration script

**Files:**
- Create: `scripts/setup-services.bat`

- [ ] **Step 1: Create the service setup script**

This script registers three Windows services using NSSM. Must be run as Administrator.

```bat
@echo off
echo ============================================
echo  FTAG Windows Services Setup
echo  (Als Administrator ausfuehren!)
echo ============================================
echo.

REM Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Dieses Script muss als Administrator ausgefuehrt werden!
    echo Rechtsklick auf die Datei ^> "Als Administrator ausfuehren"
    pause
    exit /b 1
)

set NSSM=%~dp0nssm.exe
set PROJECT_DIR=%~dp0..
set BACKEND_DIR=%PROJECT_DIR%\backend
set FRONTEND_DIR=%PROJECT_DIR%\frontend
set VENV_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe

REM Check prerequisites
if not exist "%NSSM%" (
    echo FEHLER: nssm.exe nicht gefunden. Bitte zuerst install-nssm.bat ausfuehren.
    pause
    exit /b 1
)
if not exist "%VENV_PYTHON%" (
    echo FEHLER: Python venv nicht gefunden. Bitte zuerst setup.bat ausfuehren.
    pause
    exit /b 1
)
if not exist "%~dp0cloudflared.exe" (
    echo FEHLER: cloudflared.exe nicht gefunden. Bitte zuerst install-cloudflared.bat ausfuehren.
    pause
    exit /b 1
)

REM ─────────────────────────────────────────
REM Service 1: FTAG-Backend (FastAPI)
REM ─────────────────────────────────────────
echo.
echo [1/3] Registriere FTAG-Backend Service...
"%NSSM%" stop FTAG-Backend >nul 2>&1
"%NSSM%" remove FTAG-Backend confirm >nul 2>&1
"%NSSM%" install FTAG-Backend "%VENV_PYTHON%"
"%NSSM%" set FTAG-Backend AppParameters "-m uvicorn main:app --host 0.0.0.0 --port 8000"
"%NSSM%" set FTAG-Backend AppDirectory "%BACKEND_DIR%"
"%NSSM%" set FTAG-Backend DisplayName "Frank Tueren AG - Backend"
"%NSSM%" set FTAG-Backend Description "FastAPI Backend fuer KI-Angebotserstellung"
"%NSSM%" set FTAG-Backend Start SERVICE_AUTO_START
"%NSSM%" set FTAG-Backend AppStdout "%PROJECT_DIR%\logs\backend-service.log"
"%NSSM%" set FTAG-Backend AppStderr "%PROJECT_DIR%\logs\backend-service-error.log"
"%NSSM%" set FTAG-Backend AppRotateFiles 1
"%NSSM%" set FTAG-Backend AppRotateBytes 10485760
"%NSSM%" set FTAG-Backend AppRestartDelay 5000
"%NSSM%" set FTAG-Backend AppExit Default Restart
echo [OK] FTAG-Backend registriert

REM ─────────────────────────────────────────
REM Service 2: FTAG-Frontend (Next.js)
REM ─────────────────────────────────────────
echo.
echo [2/3] Registriere FTAG-Frontend Service...

REM Find node.exe path
for /f "tokens=*" %%i in ('where node 2^>nul') do set NODE_PATH=%%i
if "%NODE_PATH%"=="" (
    echo FEHLER: Node.js nicht gefunden. Bitte Node.js installieren.
    pause
    exit /b 1
)

REM Find npm path (use npx to run next start)
for /f "tokens=*" %%i in ('where npx 2^>nul') do set NPX_PATH=%%i

"%NSSM%" stop FTAG-Frontend >nul 2>&1
"%NSSM%" remove FTAG-Frontend confirm >nul 2>&1
"%NSSM%" install FTAG-Frontend "%NPX_PATH%"
"%NSSM%" set FTAG-Frontend AppParameters "next start --port 3000"
"%NSSM%" set FTAG-Frontend AppDirectory "%FRONTEND_DIR%"
"%NSSM%" set FTAG-Frontend DisplayName "Frank Tueren AG - Frontend"
"%NSSM%" set FTAG-Frontend Description "Next.js Frontend fuer KI-Angebotserstellung"
"%NSSM%" set FTAG-Frontend Start SERVICE_AUTO_START
"%NSSM%" set FTAG-Frontend AppStdout "%PROJECT_DIR%\logs\frontend-service.log"
"%NSSM%" set FTAG-Frontend AppStderr "%PROJECT_DIR%\logs\frontend-service-error.log"
"%NSSM%" set FTAG-Frontend AppRotateFiles 1
"%NSSM%" set FTAG-Frontend AppRotateBytes 10485760
"%NSSM%" set FTAG-Frontend AppRestartDelay 5000
"%NSSM%" set FTAG-Frontend AppExit Default Restart
echo [OK] FTAG-Frontend registriert

REM ─────────────────────────────────────────
REM Service 3: FTAG-Tunnel (Cloudflared)
REM ─────────────────────────────────────────
echo.
echo [3/3] Registriere FTAG-Tunnel Service...
"%NSSM%" stop FTAG-Tunnel >nul 2>&1
"%NSSM%" remove FTAG-Tunnel confirm >nul 2>&1
"%NSSM%" install FTAG-Tunnel "%~dp0cloudflared.exe"
"%NSSM%" set FTAG-Tunnel AppParameters "tunnel --url http://localhost:3000"
"%NSSM%" set FTAG-Tunnel AppDirectory "%~dp0"
"%NSSM%" set FTAG-Tunnel DisplayName "Frank Tueren AG - Cloudflare Tunnel"
"%NSSM%" set FTAG-Tunnel Description "Cloudflare Tunnel fuer externen Zugriff"
"%NSSM%" set FTAG-Tunnel Start SERVICE_AUTO_START
"%NSSM%" set FTAG-Tunnel AppStdout "%PROJECT_DIR%\logs\tunnel-service.log"
"%NSSM%" set FTAG-Tunnel AppStderr "%PROJECT_DIR%\logs\tunnel-service-error.log"
"%NSSM%" set FTAG-Tunnel AppRotateFiles 1
"%NSSM%" set FTAG-Tunnel AppRotateBytes 10485760
"%NSSM%" set FTAG-Tunnel AppRestartDelay 5000
"%NSSM%" set FTAG-Tunnel AppExit Default Restart
echo [OK] FTAG-Tunnel registriert

echo.
echo ============================================
echo  Alle Services registriert!
echo ============================================
echo.
echo Services starten mit: scripts\start-services.bat
echo Services Status:      scripts\status-services.bat
echo Services entfernen:   scripts\remove-services.bat
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add scripts/setup-services.bat
git commit -m "feat: add Windows service registration script via NSSM"
```

### Task 5: Create service management scripts (start, stop, status, remove)

**Files:**
- Create: `scripts/start-services.bat`
- Create: `scripts/stop-services.bat`
- Create: `scripts/status-services.bat`
- Create: `scripts/remove-services.bat`

- [ ] **Step 1: Create start-services.bat**

```bat
@echo off
echo Starte FTAG Services...
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Als Administrator ausfuehren!
    pause
    exit /b 1
)

net start FTAG-Backend
echo Warte 10 Sekunden bis Backend bereit ist...
timeout /t 10 /nobreak >nul

net start FTAG-Frontend
echo Warte 5 Sekunden bis Frontend bereit ist...
timeout /t 5 /nobreak >nul

net start FTAG-Tunnel

echo.
echo Alle Services gestartet!
echo Tunnel-URL wird in logs\tunnel-service.log angezeigt.
echo.
echo Log anzeigen:
echo   type "%~dp0..\logs\tunnel-service.log" ^| findstr "trycloudflare.com"
echo.
pause
```

- [ ] **Step 2: Create stop-services.bat**

```bat
@echo off
echo Stoppe FTAG Services...
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Als Administrator ausfuehren!
    pause
    exit /b 1
)

net stop FTAG-Tunnel
net stop FTAG-Frontend
net stop FTAG-Backend

echo.
echo Alle Services gestoppt.
pause
```

- [ ] **Step 3: Create status-services.bat**

```bat
@echo off
echo ============================================
echo  FTAG Service Status
echo ============================================
echo.

sc query FTAG-Backend  | findstr "STATE"
sc query FTAG-Frontend | findstr "STATE"
sc query FTAG-Tunnel   | findstr "STATE"

echo.
echo ─────────────────────────────────────────
echo Tunnel URL:
if exist "%~dp0..\logs\tunnel-service.log" (
    type "%~dp0..\logs\tunnel-service.log" | findstr "trycloudflare.com" | findstr /V "INF"
    if errorlevel 1 (
        type "%~dp0..\logs\tunnel-service-error.log" | findstr "trycloudflare.com"
    )
)
echo.
pause
```

- [ ] **Step 4: Create remove-services.bat**

```bat
@echo off
echo ============================================
echo  FTAG Services entfernen
echo ============================================
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Als Administrator ausfuehren!
    pause
    exit /b 1
)

echo Stoppe und entferne Services...
set NSSM=%~dp0nssm.exe

"%NSSM%" stop FTAG-Tunnel >nul 2>&1
"%NSSM%" remove FTAG-Tunnel confirm
"%NSSM%" stop FTAG-Frontend >nul 2>&1
"%NSSM%" remove FTAG-Frontend confirm
"%NSSM%" stop FTAG-Backend >nul 2>&1
"%NSSM%" remove FTAG-Backend confirm

echo.
echo Alle Services entfernt.
pause
```

- [ ] **Step 5: Commit**

```bash
git add scripts/start-services.bat scripts/stop-services.bat scripts/status-services.bat scripts/remove-services.bat
git commit -m "feat: add service management scripts (start/stop/status/remove)"
```

---

## Chunk 3: Master Deploy Script and Frontend Build

### Task 6: Create the master deploy-local.bat script

**Files:**
- Create: `deploy-local.bat`

- [ ] **Step 1: Create deploy-local.bat**

This is the one-click setup script that does everything.

```bat
@echo off
echo ============================================
echo  Frank Tueren AG - 24/7 On-Premise Deploy
echo ============================================
echo.
echo Dieses Script:
echo  1. Installiert cloudflared und NSSM
echo  2. Erstellt das Python venv und installiert Abhaengigkeiten
echo  3. Baut das Next.js Frontend
echo  4. Registriert Windows-Dienste
echo  5. Startet alles
echo.
echo WICHTIG: Als Administrator ausfuehren!
echo.
pause

REM Check admin
net session >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Bitte als Administrator ausfuehren!
    pause
    exit /b 1
)

set PROJECT_DIR=%~dp0
set SCRIPTS_DIR=%PROJECT_DIR%scripts

REM ─────────────────────────────────────────
echo.
echo [1/5] Tools installieren...
echo ─────────────────────────────────────────

if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"

if not exist "%SCRIPTS_DIR%\cloudflared.exe" (
    echo Lade cloudflared herunter...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%SCRIPTS_DIR%\cloudflared.exe'"
)

if not exist "%SCRIPTS_DIR%\nssm.exe" (
    echo Lade NSSM herunter...
    powershell -Command ^
        "$zip = '%TEMP%\nssm.zip'; " ^
        "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip; " ^
        "Expand-Archive -Path $zip -DestinationPath '%TEMP%\nssm-extract' -Force; " ^
        "Copy-Item (Get-ChildItem '%TEMP%\nssm-extract' -Recurse -Filter 'nssm.exe' | Where-Object { $_.Directory.Name -eq 'win64' } | Select-Object -First 1).FullName '%SCRIPTS_DIR%\nssm.exe'; " ^
        "Remove-Item $zip -Force; Remove-Item '%TEMP%\nssm-extract' -Recurse -Force"
)

echo [OK] Tools bereit

REM ─────────────────────────────────────────
echo.
echo [2/5] Backend Setup...
echo ─────────────────────────────────────────

if not exist "%PROJECT_DIR%backend\.venv" (
    echo Erstelle Python venv...
    python -m venv "%PROJECT_DIR%backend\.venv"
)

echo Installiere Python-Abhaengigkeiten...
call "%PROJECT_DIR%backend\.venv\Scripts\activate.bat"
pip install -r "%PROJECT_DIR%backend\requirements.txt" -q
echo [OK] Backend bereit

REM ─────────────────────────────────────────
echo.
echo [3/5] Frontend Build...
echo ─────────────────────────────────────────

cd /d "%PROJECT_DIR%frontend"

echo Installiere Node-Abhaengigkeiten...
call npm install --silent

echo Baue Next.js fuer Production...
call npm run build
if errorlevel 1 (
    echo FEHLER: Frontend Build fehlgeschlagen!
    pause
    exit /b 1
)
echo [OK] Frontend gebaut

cd /d "%PROJECT_DIR%"

REM ─────────────────────────────────────────
echo.
echo [4/5] Windows Services registrieren...
echo ─────────────────────────────────────────

call "%SCRIPTS_DIR%\setup-services.bat"

REM ─────────────────────────────────────────
echo.
echo [5/5] Services starten...
echo ─────────────────────────────────────────

call "%SCRIPTS_DIR%\start-services.bat"

echo.
echo ============================================
echo  DEPLOYMENT ABGESCHLOSSEN!
echo ============================================
echo.
echo Die Tunnel-URL finden Sie in:
echo   logs\tunnel-service-error.log
echo.
echo   type logs\tunnel-service-error.log ^| findstr "trycloudflare.com"
echo.
echo Service-Status pruefen:
echo   scripts\status-services.bat
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add deploy-local.bat
git commit -m "feat: add one-click on-premise deployment script"
```

### Task 7: Create show-tunnel-url helper script

**Files:**
- Create: `scripts/show-tunnel-url.bat`

- [ ] **Step 1: Create the script**

```bat
@echo off
echo.
echo Aktuelle Tunnel-URL:
echo ─────────────────────────────────────────
echo.
if exist "%~dp0..\logs\tunnel-service-error.log" (
    for /f "tokens=*" %%a in ('type "%~dp0..\logs\tunnel-service-error.log" ^| findstr "https://.*trycloudflare.com"') do (
        set LAST_URL=%%a
    )
    if defined LAST_URL (
        echo %LAST_URL%
    ) else (
        echo Keine Tunnel-URL gefunden. Ist der FTAG-Tunnel Service gestartet?
    )
) else (
    echo Log-Datei nicht gefunden. Ist der FTAG-Tunnel Service gestartet?
)
echo.
pause
```

- [ ] **Step 2: Commit**

```bash
git add scripts/show-tunnel-url.bat
git commit -m "feat: add tunnel URL display helper script"
```

### Task 8: Add scripts/ to .gitignore for binaries

**Files:**
- Modify: `.gitignore` (root)

- [ ] **Step 1: Add binary exclusions**

Add to the root `.gitignore`:

```
# Deployment binaries (downloaded at runtime)
scripts/*.exe
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: exclude deployment binaries from git"
```
