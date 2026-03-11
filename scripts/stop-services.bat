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
