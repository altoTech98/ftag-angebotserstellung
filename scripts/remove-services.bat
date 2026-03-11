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
