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

REM Telegram Bot – Tokens aus .env laden (NICHT hier hardcoden!)
REM set TELEGRAM_BOT_TOKEN=...   (in .env Datei setzen)
REM set TELEGRAM_CHAT_ID=...     (in .env Datei setzen)
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
)

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
python -m uvicorn main:app --host 0.0.0.0 --port 8000
