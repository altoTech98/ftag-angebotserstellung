@echo off
echo ============================================
echo  Cloudflared Installation
echo ============================================
echo.

REM Check if already installed
where cloudflared >nul 2>&1
if not errorlevel 1 (
    echo cloudflared ist bereits installiert.
    cloudflared --version
    goto :end
)

REM Check if already in scripts directory
if exist "%~dp0cloudflared.exe" (
    echo cloudflared.exe gefunden in %~dp0
    goto :end
)

echo Lade cloudflared herunter...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"

if exist "%~dp0cloudflared.exe" (
    echo [OK] cloudflared erfolgreich heruntergeladen.
    "%~dp0cloudflared.exe" --version
) else (
    echo [FEHLER] Download fehlgeschlagen.
    echo Bitte manuell herunterladen von:
    echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
    pause
    exit /b 1
)

:end
echo.
pause
