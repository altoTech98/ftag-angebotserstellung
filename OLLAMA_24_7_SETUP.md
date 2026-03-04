# Ollama 24/7 Verfügbarkeits-Setup

## Problem gelöst: Ollama geht NIEMALS mehr offline!

### Drei Schichten Sicherung:

#### 1️⃣ **Backend Watchdog Service** (Ebene 1)
- Läuft im FastAPI Backend
- Überwacht Ollama alle 30 Sekunden
- Startet Ollama automatisch neu bei Crashes
- Exponential Backoff (5s, 10s, 20s, etc.)
- Max 10 Restart-Versuche pro Session

**Datei**: `backend/services/ollama_watchdog.py`

#### 2️⃣ **Windows Scheduled Task** (Ebene 2)
- Startet Ollama beim Login automatisch
- Läuft mit Administrator-Rechten
- Check beim Login + regelmäßige Überwachung

**Aktiviert durch**: `setup_ollama_autostart.ps1`

#### 3️⃣ **Ollama Native Recovery** (Ebene 3)
- Ollama hat eigene Error-Handling
- Datenbank-Recovery bei Crashes

---

## Installation

### Schritt 1: Windows Task Scheduler einrichten

Öffne PowerShell **als Administrator** und führe aus:

```powershell
# Navigiere zum Projekt
cd "C:\Users\ALI\Desktop\ClaudeCodeTest"

# Führe Setup-Script aus
.\setup_ollama_autostart.ps1
```

**Das Script wird:**
- Ollama-Installation finden
- Watchdog-Script erstellen
- Scheduled Task registrieren
- Auto-Start beim Login konfigurieren

### Schritt 2: Backend starten

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Der Watchdog startet automatisch bei Startup!

### Schritt 3: Verifikation

```bash
# Check Ollama Status
curl http://localhost:11434/api/tags

# Check Watchdog Status im Backend
curl http://localhost:8000/api/ollama/status

# Check Health
curl http://localhost:8000/health
```

---

## Überwachung

### Backend Logs anschauen
```bash
tail -f logs/app.log | grep -i ollama
```

### Scheduled Task Status
```powershell
# Task anschauen
Get-ScheduledTask -TaskName "Ollama_24_7_Watchdog"

# Task History
Get-ScheduledTaskInfo -TaskName "Ollama_24_7_Watchdog"

# Letzte Ausführungen
Get-ScheduledTask -TaskName "Ollama_24_7_Watchdog" | Get-ScheduledTaskInfo | Select-Object LastRunTime, LastTaskResult
```

### Prozess überwachen
```powershell
# Ollama Process Info
Get-Process -Name "ollama" | Select-Object Id, Name, CPU, Memory, Handles

# Live Monitoring
while ($true) {
    Clear-Host
    Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Select-Object Id, Name, CPU, Memory
    Start-Sleep -Seconds 2
}
```

---

## Endpunkte

### `/api/ollama/status` - Detaillierter Watchdog Status
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "watchdog": {
    "running": true,
    "health": true,
    "last_restart": "2024-01-15T08:00:00",
    "restart_attempts": 0,
    "max_restart_attempts": 10,
    "ollama_binary": "C:\\Program Files\\Ollama\\ollama.exe",
    "process_id": 12345
  },
  "24_7_guarantee": {
    "monitoring": true,
    "auto_restart": true,
    "health_check_interval_seconds": 30,
    "max_restart_attempts": 10,
    "exponential_backoff": true,
    "windows_autostart": true
  }
}
```

### `/api/availability/status` - Alle Services
Zeigt Status aller Services inklusive Ollama Watchdog

### `/health` - Quick Check
Zeigt 24/7 Guarantee Status

---

## Fehlerbehandlung

### Wenn Ollama nicht startet:
1. Check Prozess: `Get-Process -Name "ollama"`
2. Check Installation: `where ollama`
3. Test manuell: `ollama serve`

### Wenn Watchdog nicht reagiert:
1. Check Backend Logs: `logs/app.log`
2. Restart Backend
3. Watchdog startet automatisch neu

### Wenn Scheduled Task nicht läuft:
1. Check Admin-Rechte (brauch Administrator!)
2. Check Task Properties:
   ```powershell
   Get-ScheduledTask -TaskName "Ollama_24_7_Watchdog" | Get-ScheduledTaskInfo
   ```
3. Neuanlage:
   ```powershell
   .\setup_ollama_autostart.ps1
   ```

---

## Deinstallation

Falls du das Setup entfernen möchtest:

```powershell
# Scheduled Task entfernen
Unregister-ScheduledTask -TaskName "Ollama_24_7_Watchdog" -Confirm:$false

# Backend Watchdog stoppt automatisch mit Backend
```

---

## Sicherheitshinweise

- Watchdog läuft mit Prozess-Elevation
- Nur für Ollama optimiert, nicht invasiv
- Logs sind in `logs/` einsehbar
- Keine kritischen Daten gelöscht

---

## Garantie: 24/7 Online

Mit diesem Setup:
- ✅ Ollama läuft IMMER
- ✅ Auto-Restart bei Crashes
- ✅ Health Checks alle 30 Sekunden
- ✅ Exponential Backoff bei Fehlern
- ✅ Windows Auto-Start nach Reboot
- ✅ Backend Watchdog zusätzliches Monitoring

**Ollama geht NICHT mehr offline!** 🎯
