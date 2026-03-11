@echo off
echo.
echo Aktuelle Tunnel-URL:
echo ─────────────────────────────────────────
echo.
set TUNNEL_LINE=
if exist "%~dp0..\logs\tunnel-service-error.log" (
    for /f "tokens=*" %%a in ('type "%~dp0..\logs\tunnel-service-error.log" ^| findstr "https://.*trycloudflare.com"') do set TUNNEL_LINE=%%a
    if defined TUNNEL_LINE (
        echo %TUNNEL_LINE%
    ) else (
        echo Keine Tunnel-URL gefunden. Ist der FTAG-Tunnel Service gestartet?
    )
) else (
    echo Log-Datei nicht gefunden. Ist der FTAG-Tunnel Service gestartet?
)
echo.
pause
