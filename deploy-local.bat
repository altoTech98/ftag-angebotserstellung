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
    if not exist "%SCRIPTS_DIR%\cloudflared.exe" (
        echo FEHLER: cloudflared Download fehlgeschlagen!
        pause
        exit /b 1
    )
)
echo [OK] cloudflared bereit

if not exist "%SCRIPTS_DIR%\nssm.exe" (
    echo Lade NSSM herunter...
    powershell -Command ^
        "$zip = '%TEMP%\nssm.zip'; " ^
        "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip; " ^
        "Expand-Archive -Path $zip -DestinationPath '%TEMP%\nssm-extract' -Force; " ^
        "Copy-Item (Get-ChildItem '%TEMP%\nssm-extract' -Recurse -Filter 'nssm.exe' | Where-Object { $_.Directory.Name -eq 'win64' } | Select-Object -First 1).FullName '%SCRIPTS_DIR%\nssm.exe'; " ^
        "Remove-Item $zip -Force; Remove-Item '%TEMP%\nssm-extract' -Recurse -Force"
    if not exist "%SCRIPTS_DIR%\nssm.exe" (
        echo FEHLER: NSSM Download fehlgeschlagen!
        pause
        exit /b 1
    )
)
echo [OK] NSSM bereit

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
call npm install --silent 2>nul

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
echo Die Tunnel-URL finden Sie mit:
echo   scripts\show-tunnel-url.bat
echo.
echo Service-Status pruefen:
echo   scripts\status-services.bat
echo.
echo Services stoppen:
echo   scripts\stop-services.bat
echo.
pause
