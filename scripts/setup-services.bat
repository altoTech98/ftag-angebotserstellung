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

REM Find npx path
for /f "tokens=*" %%i in ('where npx 2^>nul') do set NPX_PATH=%%i
if "%NPX_PATH%"=="" (
    echo FEHLER: Node.js/npx nicht gefunden. Bitte Node.js installieren.
    pause
    exit /b 1
)

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
