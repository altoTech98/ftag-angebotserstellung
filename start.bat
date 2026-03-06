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

REM Check for ANTHROPIC_API_KEY
if "%ANTHROPIC_API_KEY%"=="" (
    echo WARNUNG: ANTHROPIC_API_KEY ist nicht gesetzt!
    echo Bitte setzen Sie den API-Key:
    echo   set ANTHROPIC_API_KEY=sk-ant-...
    echo.
    set /p ANTHROPIC_API_KEY="API Key eingeben: "
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

REM Start server
echo.
echo Starte Server auf http://localhost:8000
echo Drücken Sie CTRL+C zum Beenden
echo.
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
