@echo off
echo ============================================
echo  Frank Türen AG - KI Angebotserstellung
echo ============================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python nicht gefunden. Bitte Python 3.10+ installieren.
    pause
    exit /b 1
)

REM Check Ollama
curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo WARNUNG: Ollama laeuft nicht! Bitte Ollama starten.
    echo   Fallback-Modus aktiv (Regex statt KI).
    echo.
) else (
    echo Ollama verbunden.
)

REM Create virtual environment if not exists
if not exist "backend\.venv" (
    echo Erstelle virtuelles Environment...
    python -m venv backend\.venv
)

REM Activate venv and install requirements
echo Installiere Abhängigkeiten...
call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q

REM Telegram Bot (Token von @BotFather, Chat-ID vom User)
set TELEGRAM_BOT_TOKEN=8524632357:AAH3l0vI7gdACBXa7MEyEpFfGRy2CrchwBo
set TELEGRAM_CHAT_ID=8458317986

REM Start server
echo.
echo Starte Server auf http://localhost:8000
if defined TELEGRAM_BOT_TOKEN (
    echo Telegram Bot: AKTIV
) else (
    echo Telegram Bot: DEAKTIVIERT (TELEGRAM_BOT_TOKEN nicht gesetzt)
)
echo Druecken Sie CTRL+C zum Beenden
echo.
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
