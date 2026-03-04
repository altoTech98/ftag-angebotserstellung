@echo off
REM Quick Start für Ollama 24/7 Mode
REM Dieses Script setzt alles auf

echo ================================================
echo Frank Tueren AG - Ollama 24/7 Setup
echo ================================================
echo.

REM Check Admin Rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Dieses Script muss als Administrator laufen!
    echo Klicke mit Rechtsklick auf die BAT-Datei und waehle "Als Administrator ausfuehren"
    pause
    exit /b 1
)

echo [1/3] Setup Windows Auto-Start...
powershell -NoProfile -ExecutionPolicy Bypass -File "setup_ollama_autostart.ps1"
if errorlevel 1 (
    echo ERROR beim Auto-Start Setup!
    pause
    exit /b 1
)

echo.
echo [2/3] Starte Backend mit Watchdog...
echo.
cd backend
call .venv\Scripts\activate.bat
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

REM Falls Backend schliesst
pause
