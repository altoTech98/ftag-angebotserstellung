@echo off
echo ============================================
echo  Frank Türen AG - Setup
echo ============================================
echo.

REM Check Python version
python --version
echo.

REM Create virtual environment
echo Erstelle virtuelles Environment in backend\.venv ...
python -m venv backend\.venv
if errorlevel 1 (
    echo FEHLER: Konnte venv nicht erstellen
    pause
    exit /b 1
)

REM Activate and install
echo Aktiviere venv und installiere Pakete...
call backend\.venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r backend\requirements.txt

echo.
echo ============================================
echo  Setup abgeschlossen!
echo ============================================
echo.
echo Nächste Schritte:
echo 1. API Key setzen:  set ANTHROPIC_API_KEY=sk-ant-...
echo 2. Server starten:  start.bat
echo 3. Browser öffnen:  http://localhost:8000
echo.
pause
