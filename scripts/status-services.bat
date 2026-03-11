@echo off
echo ============================================
echo  FTAG Service Status
echo ============================================
echo.

sc query FTAG-Backend  | findstr "STATE"
sc query FTAG-Frontend | findstr "STATE"
sc query FTAG-Tunnel   | findstr "STATE"

echo.
echo ─────────────────────────────────────────
echo Tunnel URL:
if exist "%~dp0..\logs\tunnel-service-error.log" (
    for /f "tokens=*" %%a in ('type "%~dp0..\logs\tunnel-service-error.log" ^| findstr "trycloudflare.com"') do set TUNNEL_LINE=%%a
    if defined TUNNEL_LINE (
        echo %TUNNEL_LINE%
    ) else (
        echo Keine Tunnel-URL gefunden.
    )
) else (
    echo Log-Datei nicht gefunden. Tunnel gestartet?
)
echo.
pause
