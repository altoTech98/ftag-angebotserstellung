# On-Premise 24/7 Deployment Design

## Problem
The Frank Tueren AG application (Next.js frontend + FastAPI backend) runs locally but is not accessible from the internet and does not auto-start after reboots.

## Solution
Deploy on-premise on the existing Windows 10 PC with Cloudflare Quick Tunnel for internet access and NSSM for Windows service management.

## Architecture

```
Internet (HTTPS)
    |
    v
Cloudflare Quick Tunnel (*.trycloudflare.com)
    |
    v
Windows 10 PC (24/7)
    +-- FTAG-Frontend  (Next.js on :3000)
    +-- FTAG-Backend   (FastAPI on :8000)
    +-- FTAG-Tunnel    (cloudflared)
    +-- Neon DB        (external, already provisioned)
```

## Components

### 1. Cloudflare Quick Tunnel
- **Tool**: `cloudflared` CLI
- **Mode**: Quick Tunnel (no account/domain required initially, upgradeable to named tunnel with custom domain later)
- **Routing**: Exposes localhost:3000 (frontend) to a random `*.trycloudflare.com` URL
- **Backend access**: Frontend proxies API calls to localhost:8000 server-side, so only the frontend port needs to be tunneled
- **HTTPS**: Provided automatically by Cloudflare

### 2. Windows Services via NSSM
Three services registered with NSSM (Non-Sucking Service Manager):

| Service Name | Process | Start Type | Restart |
|-------------|---------|------------|---------|
| FTAG-Backend | `uvicorn main:app --host 0.0.0.0 --port 8000` | Automatic | On failure |
| FTAG-Frontend | `npm start` (Next.js production) | Automatic | On failure |
| FTAG-Tunnel | `cloudflared tunnel --url http://localhost:3000` | Automatic | On failure |

### 3. Frontend Build
- `npm run build` must be run before starting the production server
- The `npm start` command serves the pre-built Next.js app

### 4. Configuration Changes
- **CORS**: Backend must allow the Cloudflare tunnel URL as origin
- **CORS wildcard option**: Allow `*.trycloudflare.com` since the URL changes on restart
- **Environment**: Set `ENVIRONMENT=production` for backend

## Implementation Plan

### Step 1: Install cloudflared
- Download `cloudflared` for Windows
- Place in project directory or system PATH

### Step 2: Install NSSM
- Download NSSM (nssm.cc)
- Place in project directory or system PATH

### Step 3: Create service setup scripts
- `setup-services.bat` — registers all 3 Windows services via NSSM
- `remove-services.bat` — unregisters services (cleanup)
- `status-services.bat` — checks service status

### Step 4: Build frontend for production
- Run `npm run build` in frontend directory
- Ensure `.env.local` has correct production values

### Step 5: CORS adjustment
- Update `backend/config.py` to allow `*.trycloudflare.com` origins in production mode

### Step 6: Startup script
- `deploy-local.bat` — one-click setup: installs tools, builds frontend, registers services, starts everything

## Environment Variables (Production)

### Backend
```
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
ANTHROPIC_API_KEY=<existing key>
DATABASE_URL=<neon direct URL>
PYTHON_SERVICE_KEY=<generate strong key>
SSE_TOKEN_SECRET=<generate strong key>
NEXTJS_ORIGIN=*.trycloudflare.com
```

### Frontend (.env.local)
```
DATABASE_URL=<neon pooler URL>
DIRECT_URL=<neon direct URL>
BETTER_AUTH_SECRET=<generate>
BETTER_AUTH_URL=https://<tunnel-url>.trycloudflare.com
PYTHON_BACKEND_URL=http://localhost:8000
PYTHON_SERVICE_KEY=<same as backend>
SSE_TOKEN_SECRET=<same as backend>
NEXT_PUBLIC_PYTHON_SSE_URL=https://<tunnel-url>.trycloudflare.com/api/sse
```

## Upgrade Path
When ready for a custom domain:
1. Create Cloudflare account
2. Register/transfer domain to Cloudflare
3. Create a named tunnel (fixed URL) instead of quick tunnel
4. Update CORS and environment variables with the fixed domain
5. Update NSSM service to use named tunnel config

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| PC power loss | UPS recommended; services auto-start on boot |
| Quick tunnel URL changes on restart | Accept for now; upgrade to named tunnel later |
| Windows updates force restart | Configure active hours to avoid auto-restart |
| Neon DB free tier limits | Monitor usage; upgrade if needed |

## Prerequisites
- Windows 10 PC stays powered on 24/7
- Internet connection stable
- ANTHROPIC_API_KEY set
- Neon DB credentials available
