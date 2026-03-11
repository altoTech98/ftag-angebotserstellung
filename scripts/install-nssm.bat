@echo off
echo ============================================
echo  NSSM Installation
echo ============================================
echo.

REM Check if already in scripts directory
if exist "%~dp0nssm.exe" (
    echo nssm.exe gefunden in %~dp0
    goto :end
)

REM Check if in PATH
where nssm >nul 2>&1
if not errorlevel 1 (
    echo nssm ist bereits installiert.
    goto :end
)

echo Lade NSSM herunter...
powershell -Command ^
    "$url = 'https://nssm.cc/release/nssm-2.24.zip'; " ^
    "$zip = '%TEMP%\nssm.zip'; " ^
    "$extract = '%TEMP%\nssm-extract'; " ^
    "Invoke-WebRequest -Uri $url -OutFile $zip; " ^
    "Expand-Archive -Path $zip -DestinationPath $extract -Force; " ^
    "Copy-Item (Get-ChildItem -Path $extract -Recurse -Filter 'nssm.exe' | Where-Object { $_.Directory.Name -eq 'win64' } | Select-Object -First 1).FullName -Destination '%~dp0nssm.exe'; " ^
    "Remove-Item $zip -Force; " ^
    "Remove-Item $extract -Recurse -Force"

if exist "%~dp0nssm.exe" (
    echo [OK] NSSM erfolgreich heruntergeladen.
) else (
    echo [FEHLER] Download fehlgeschlagen.
    echo Bitte manuell herunterladen von: https://nssm.cc/release/nssm-2.24.zip
    echo Die nssm.exe (win64) in den scripts/ Ordner kopieren.
    pause
    exit /b 1
)

:end
echo.
pause
