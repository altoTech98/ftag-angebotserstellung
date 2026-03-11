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
echo.
echo Tunnel-URL wird in logs\tunnel-service-error.log angezeigt.
echo Zum Anzeigen: scripts\show-tunnel-url.bat
echo.
pause
