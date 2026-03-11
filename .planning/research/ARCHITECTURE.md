# Architecture Patterns

**Domain:** SaaS web platform (Next.js) integrating with existing Python/FastAPI AI backend
**Researched:** 2026-03-10
**Focus:** Integration architecture, API proxying, shared auth, file handling, deployment

## Recommended Architecture

### High-Level System Topology

```
                        INTERNET
                           |
                    [Vercel Edge Network]
                           |
              +------------+------------+
              |                         |
      [Next.js App Router]      [Vercel Blob Storage]
      (Vercel Serverless)        (file persistence)
              |                         |
              |   +---------------------+
              |   |
              v   v
      [Next.js API Routes]  <-- Auth boundary (NextAuth.js)
         /api/pipeline/*         Server Actions
         /api/projects/*         Server Components
              |
              | HTTPS (internal, server-to-server)
              | Bearer token forwarding
              |
      [Python/FastAPI Backend]  <-- AI processing boundary
      (Railway.app)
         /api/upload
         /api/analyze
         /api/offer/*
         /api/products
         /api/feedback
              |
              +---> Claude API (Anthropic)
              +---> SQLite/PostgreSQL (analysis data)
              +---> Product Catalog (Excel, in-memory)
```

### Why This Topology

The system is a **BFF (Backend-for-Frontend) pattern** where Next.js API routes act as a thin orchestration layer between the browser and the Python AI backend. This is the correct choice because:

1. **Next.js on Vercel** handles auth, sessions, DB (Prisma/Postgres), UI rendering, and file storage
2. **Python on Railway** handles AI processing (Claude API, document parsing, product matching) -- these operations require long-running processes (2-10 min), large Python libraries (pdfplumber, openpyxl, pandas, scikit-learn), and persistent in-memory caches (TF-IDF index, product catalog)
3. **Vercel serverless functions have a 60s timeout** (even Pro plan: 300s). The Python backend processes tenders for 2-10 minutes. Running Python on Vercel is not viable for this workload.

### Component Boundaries

| Component | Responsibility | Runs On | Communicates With |
|-----------|---------------|---------|-------------------|
| Next.js App Router | UI rendering, page routing, server components | Vercel | Next.js API Routes |
| Next.js API Routes (BFF) | Auth enforcement, request validation, proxy to Python, DB writes | Vercel Serverless | Python Backend, Vercel Postgres, Vercel Blob |
| NextAuth.js | Session management, JWT issuance, role-based access | Vercel Serverless | Vercel Postgres (session/user store) |
| Prisma ORM | Database access for projects, users, audit log | Vercel Serverless | Vercel Postgres |
| Vercel Blob | Persistent file storage for uploaded documents | Vercel | Next.js API Routes |
| Python/FastAPI Backend | Document parsing, AI matching, Excel generation | Railway.app | Claude API, local SQLite/PostgreSQL |
| `fastapi-nextauth-jwt` | Validates NextAuth JWT tokens on Python side | Railway.app | Shared JWT_SECRET with NextAuth |

### Data Flow: Complete Analysis Pipeline

```
Browser                 Next.js (Vercel)              Python (Railway)
  |                          |                              |
  |-- Upload files --------->|                              |
  |                          |-- Store to Vercel Blob ----->|
  |                          |-- Save project to Prisma     |
  |                          |-- Return project_id -------->|
  |                          |                              |
  |-- Start analysis ------->|                              |
  |                          |-- POST /api/analyze/project  |
  |                          |   (with blob URLs + auth) -->|
  |                          |                              |-- Download files from Blob
  |                          |                              |-- Parse documents
  |                          |                              |-- AI matching pipeline
  |                          |                              |-- Generate Excel
  |                          |<-- Return job_id ------------|
  |<-- Return job_id --------|                              |
  |                          |                              |
  |-- SSE subscribe -------->|                              |
  |                          |-- SSE proxy to Python ------>|
  |<-- Progress events ------|<-- Progress events ----------|
  |                          |                              |
  |-- Download result ------>|                              |
  |                          |-- GET /api/result/download ->|
  |                          |<-- Excel bytes --------------|
  |<-- Excel file -----------|                              |
```

## Integration Patterns

### Pattern 1: Next.js API Route as BFF Proxy

**What:** Every Python backend call goes through a Next.js Route Handler that adds auth, validates input, and forwards the request.

**When:** All frontend-to-backend communication.

**Why:** The browser never talks directly to the Python backend. This centralizes auth, CORS, and rate limiting in one place. The Python backend only needs to trust requests from the Next.js server (verified by a shared API key).

**Confidence:** HIGH -- this is the standard pattern for Next.js + external API architectures.

```typescript
// app/api/pipeline/analyze/route.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL; // e.g. https://ftag-api.railway.app
const PYTHON_API_KEY = process.env.PYTHON_API_KEY;  // shared secret

export async function POST(request: Request) {
  // 1. Verify NextAuth session
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // 2. Validate role
  if (!["admin", "manager", "analyst"].includes(session.user.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  // 3. Forward to Python backend with internal auth
  const body = await request.json();
  const response = await fetch(`${PYTHON_API_URL}/api/analyze/project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${PYTHON_API_KEY}`,
      "X-User-Email": session.user.email,
    },
    body: JSON.stringify(body),
  });

  // 4. Return Python response
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
```

### Pattern 2: Shared Auth via JWT Secret

**What:** NextAuth.js issues JWTs. The Python backend validates them using the same `AUTH_SECRET` via `fastapi-nextauth-jwt`.

**When:** Python backend needs to know WHO is making a request (for audit logging, per-user feedback attribution).

**Why:** Avoids maintaining two separate auth systems. The existing Python auth (JWT + bcrypt in `auth_service.py`) gets replaced by NextAuth as the single source of truth.

**Confidence:** HIGH -- `fastapi-nextauth-jwt` is purpose-built for this exact integration.

```python
# Python backend: middleware or dependency
from fastapi_nextauth_jwt import NextAuthJWTv4
import os

JWT = NextAuthJWTv4(secret=os.getenv("AUTH_SECRET"))

@app.get("/api/analyze/status/{job_id}")
async def get_status(job_id: str, jwt: dict = Depends(JWT)):
    user_email = jwt.get("email")
    # ... use for audit logging
```

**Migration path from existing auth:**
1. Phase 1: Next.js API routes use `PYTHON_API_KEY` header (simple shared secret). Python backend trusts this key.
2. Phase 2: Optionally forward NextAuth JWT to Python. Python validates it for audit/attribution purposes.
3. The existing `auth_service.py` with bcrypt/jose remains as fallback for direct Python API access during development.

### Pattern 3: SSE Proxy for Real-Time Progress

**What:** Next.js Route Handler opens an SSE connection to Python and forwards events to the browser.

**When:** During analysis progress streaming (`/api/analyze/stream/{job_id}`).

**Why:** The browser cannot directly connect to the Python backend (different origin, auth boundary). The Next.js route handler acts as an SSE proxy.

**Confidence:** MEDIUM -- SSE proxying through Vercel serverless has known buffering issues. Requires specific headers.

```typescript
// app/api/pipeline/stream/[jobId]/route.ts
export async function GET(
  request: Request,
  { params }: { params: { jobId: string } }
) {
  const session = await auth();
  if (!session?.user) {
    return new Response("Unauthorized", { status: 401 });
  }

  const pythonStream = await fetch(
    `${PYTHON_API_URL}/api/analyze/stream/${params.jobId}`,
    {
      headers: {
        "Authorization": `Bearer ${PYTHON_API_KEY}`,
        "Accept": "text/event-stream",
      },
    }
  );

  // Forward the SSE stream with correct headers
  return new Response(pythonStream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
```

**Critical headers:** `X-Accel-Buffering: no` prevents Vercel/nginx from buffering the stream. Without this, SSE events arrive in bursts instead of real-time.

**Fallback:** If SSE proxying proves unreliable on Vercel, implement polling fallback:
- Client polls `GET /api/pipeline/status/{jobId}` every 3 seconds
- The existing Python backend already supports this pattern (`GET /api/analyze/status/{job_id}`)

### Pattern 4: File Upload Flow (Browser -> Vercel Blob -> Python)

**What:** Files upload to Vercel Blob first (persistent storage), then blob URLs are passed to Python for processing.

**When:** Every document upload in the analysis wizard.

**Why:** Vercel Blob provides persistent, CDN-backed storage. Python processes files by downloading from blob URLs. This decouples upload (fast, user-facing) from processing (slow, background).

**Confidence:** HIGH -- Vercel Blob supports files up to 5TB with multi-part uploads.

```
Upload Flow:
1. Browser -> Next.js API route -> Vercel Blob (client upload for files >4.5MB)
2. Next.js saves project record to Prisma with blob URLs
3. Next.js triggers Python: POST /api/analyze/project { blobUrls: [...] }
4. Python downloads files from blob URLs, processes them
```

**Changes to Python backend:**
- New parameter on `/api/analyze/project`: accept `blob_urls: list[str]` instead of expecting files in local cache
- Python downloads files from Vercel Blob URLs (simple HTTP GET, public or signed URLs)
- The existing `project_cache.set(f"project_{id}", file_bytes_dict)` pattern stays, but bytes come from Blob downloads instead of local upload

```python
# Python backend modification
import httpx

async def download_from_blob(blob_urls: list[dict]) -> dict:
    """Download files from Vercel Blob URLs."""
    file_bytes = {}
    async with httpx.AsyncClient() as client:
        for item in blob_urls:
            resp = await client.get(item["url"])
            resp.raise_for_status()
            file_bytes[item["file_id"]] = resp.content
    return file_bytes
```

### Pattern 5: Database Split (Prisma for SaaS, SQLAlchemy for AI)

**What:** Two databases serving different purposes. Vercel Postgres (via Prisma) for the SaaS layer. Python's existing SQLAlchemy/SQLite for AI processing state.

**When:** Always -- this is the fundamental data architecture.

**Why:** The Next.js app needs relational data for users, projects, permissions, audit logs. The Python backend needs fast local access for analysis state, job tracking, and feedback. Trying to share one database creates coupling, latency, and migration headaches.

**Confidence:** HIGH -- this is standard for polyglot architectures.

```
Vercel Postgres (Prisma):           Python DB (SQLAlchemy):
- User accounts & sessions          - Analysis jobs & progress
- Projects (metadata)               - Cached analysis results
- File references (blob URLs)       - Feedback corrections
- Audit log                         - Product catalog cache
- Role permissions                  - Match history
```

**Prisma schema for the SaaS layer:**

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      Role     @default(ANALYST)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  projects  Project[]
  auditLogs AuditLog[]
}

enum Role {
  ADMIN
  MANAGER
  ANALYST
  VIEWER
}

model Project {
  id          String   @id @default(cuid())
  name        String
  description String?
  status      ProjectStatus @default(CREATED)
  userId      String
  user        User     @relation(fields: [userId], references: [id])
  files       ProjectFile[]
  analyses    Analysis[]
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  archivedAt  DateTime?

  @@index([userId, status])
}

enum ProjectStatus {
  CREATED
  UPLOADING
  ANALYZING
  COMPLETED
  ARCHIVED
  ERROR
}

model ProjectFile {
  id          String   @id @default(cuid())
  projectId   String
  project     Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  filename    String
  blobUrl     String   // Vercel Blob URL
  fileSize    Int
  fileType    String
  category    String?  // tuerliste, spezifikation, plan, etc.
  createdAt   DateTime @default(now())

  @@index([projectId])
}

model Analysis {
  id             String   @id @default(cuid())
  projectId      String
  project        Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  pythonJobId    String?  // Job ID from Python backend
  status         AnalysisStatus @default(PENDING)
  totalPositions Int?
  matchedCount   Int?
  unmatchedCount Int?
  resultBlobUrl  String?  // Vercel Blob URL for result Excel
  startedAt      DateTime?
  completedAt    DateTime?
  createdAt      DateTime @default(now())

  @@index([projectId, status])
}

enum AnalysisStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
}

model AuditLog {
  id           String   @id @default(cuid())
  userId       String?
  user         User?    @relation(fields: [userId], references: [id])
  action       String
  resourceType String?
  resourceId   String?
  details      Json?
  createdAt    DateTime @default(now())

  @@index([userId, action])
  @@index([createdAt])
}
```

**Key decision:** The Python backend's existing SQLAlchemy models (`db/models.py` with User, Project, Analysis, etc.) continue to serve the Python side. The Prisma schema is the SaaS-layer view. Synchronization happens through the BFF layer: when an analysis completes, the Next.js API route updates the Prisma `Analysis` record with results from Python.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Python on Vercel Serverless

**What:** Deploying the FastAPI backend as Vercel serverless functions.
**Why bad:** Vercel serverless has a 60s timeout (Pro: 300s). Analysis runs 2-10 minutes. Python libraries (pandas, pdfplumber, scikit-learn) exceed Vercel's 250MB bundle size limit. The in-memory TF-IDF index and product catalog require persistent process memory.
**Instead:** Deploy Python on Railway.app as a long-running service with persistent memory.

### Anti-Pattern 2: Direct Browser-to-Python Communication

**What:** Having the React frontend call the Python API directly (different origin).
**Why bad:** Exposes the Python backend to the internet. Requires CORS configuration. Cannot leverage NextAuth sessions. Two separate auth systems to maintain.
**Instead:** All requests go through Next.js API routes (BFF pattern). Python backend only accepts requests from the Next.js server.

### Anti-Pattern 3: Single Shared Database

**What:** Having both Next.js and Python share one PostgreSQL database.
**Why bad:** Tight coupling between two deployment platforms. Schema migrations become dangerous (who owns the schema?). Prisma and SQLAlchemy model definitions diverge. Connection pooling across Vercel serverless + Railway is complex.
**Instead:** Each side owns its database. Data flows through the API boundary.

### Anti-Pattern 4: Storing Files in Python Backend Filesystem

**What:** Uploading files to Python backend's local filesystem (current pattern with `uploads/` directory).
**Why bad:** Railway containers can restart, losing files. No CDN. No backup. Files are trapped on one machine.
**Instead:** Upload to Vercel Blob (persistent, CDN-backed). Pass blob URLs to Python for processing.

### Anti-Pattern 5: Replacing Python Auth Without Migration

**What:** Removing the existing `auth_service.py` JWT auth from Python without a migration path.
**Why bad:** Python backend needs auth for direct API testing, development, and as a fallback. Removing it breaks the existing system.
**Instead:** Add NextAuth JWT validation alongside existing auth. Use `PYTHON_API_KEY` for service-to-service calls. Deprecate existing auth gradually.

## Deployment Architecture

### Vercel (Next.js Frontend + BFF)

```
Vercel Project:
  - Framework: Next.js App Router
  - Build: next build
  - Environment Variables:
    - AUTH_SECRET (shared with Python)
    - DATABASE_URL (Vercel Postgres)
    - BLOB_READ_WRITE_TOKEN (Vercel Blob)
    - PYTHON_API_URL (Railway URL)
    - PYTHON_API_KEY (shared secret for service auth)
  - Regions: fra1 (Frankfurt, closest to Switzerland)
```

### Railway.app (Python Backend)

```
Railway Service:
  - Runtime: Python 3.11+ (Dockerfile or Nixpacks)
  - Start: gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2
  - Environment Variables:
    - AUTH_SECRET (shared with NextAuth)
    - PYTHON_API_KEY (validates requests from Next.js)
    - ANTHROPIC_API_KEY (Claude API)
    - DATABASE_URL (Railway Postgres or SQLite volume)
  - Persistent Volume: /data (for SQLite, product catalog, feedback)
  - Health Check: /health
  - Region: EU (Frankfurt)
```

**Why Railway over Render:**
- Railway has persistent volumes (needed for SQLite + product catalog Excel file)
- Railway supports Docker natively (needed for system deps like tesseract for OCR)
- Railway has better cold start performance (important for SSE connections)
- Both are viable; Railway is the recommendation

### Network Security Between Services

```
Browser <--HTTPS--> Vercel (public)
Vercel  <--HTTPS--> Railway (private network or API key protected)

Python backend validation:
1. Check X-API-Key header matches PYTHON_API_KEY
2. Optionally validate forwarded NextAuth JWT for user attribution
3. Reject all requests without valid auth
```

```python
# Python backend: service-to-service auth middleware
@app.middleware("http")
async def service_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        expected = os.environ.get("PYTHON_API_KEY")
        if not api_key or api_key != expected:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)
```

## What Changes in the Python Backend

### New Endpoints/Modifications

| Endpoint | Change | Reason |
|----------|--------|--------|
| `POST /api/analyze/project` | Accept `blob_urls` parameter | Files come from Vercel Blob, not local cache |
| `POST /api/upload/folder` | May become unused | Uploads go to Vercel Blob directly |
| `GET /api/analyze/stream/{job_id}` | No change | SSE proxy from Next.js |
| `POST /api/result/generate` | Return blob URL option | Store result Excel in Vercel Blob for persistence |
| Auth middleware | Replace user JWT with API key check | Service-to-service auth |
| Health check | Add version, last-deploy info | Monitoring from Next.js |

### What Stays Untouched

- All AI pipeline services (ai_service.py, matching_pipeline, extraction, etc.)
- Product catalog loading (catalog_index.py)
- Excel generation (result_generator.py)
- Feedback store (feedback_store.py)
- Document parsing (document_parser.py, excel_parser.py)
- Job store and SSE streaming infrastructure

### Estimated Modifications

| File | Scope | Effort |
|------|-------|--------|
| `main.py` | Replace auth middleware with API key check | Small |
| `routers/upload.py` | Add blob URL download path | Medium |
| `routers/analyze.py` | Accept blob_urls in project analysis | Medium |
| `routers/offer.py` | Optionally upload result to Vercel Blob | Small |
| `config.py` | Add PYTHON_API_KEY, BLOB_DOWNLOAD_TIMEOUT | Small |

## Build Order (Phase Dependency Analysis)

Based on the integration architecture, the recommended build order:

1. **Next.js Project Setup + Auth** -- Foundation. Everything depends on auth working.
   - Next.js App Router, Tailwind, design system tokens
   - NextAuth.js with credentials provider (migrating from existing user list)
   - Prisma schema, Vercel Postgres connection
   - Role-based middleware

2. **Python Backend API Key Auth** -- Enables integration testing.
   - Add PYTHON_API_KEY middleware to Python
   - Add /health endpoint enhancements
   - Test service-to-service connectivity

3. **BFF Proxy Layer** -- Connects both systems.
   - Next.js API routes for each Python endpoint
   - SSE proxy with fallback to polling
   - Error handling and retry logic

4. **File Upload Flow** -- Required for analysis.
   - Vercel Blob integration
   - Python blob URL download capability
   - Upload wizard UI

5. **Dashboard + Analysis UI** -- Core user-facing features.
   - Dashboard with project list
   - Analysis wizard (multi-step)
   - Results viewer with SSE progress

6. **Admin + Catalog Management** -- Supporting features.
   - User management UI
   - Product catalog upload/version management
   - Audit log viewer

## Scalability Considerations

| Concern | Current (local) | SaaS (5 users) | SaaS (50 users) |
|---------|-----------------|-----------------|------------------|
| Auth | JWT + JSON file | NextAuth + Postgres | Same, add rate limiting |
| File storage | Local filesystem | Vercel Blob (free tier: 1GB) | Vercel Blob (Pro: 100GB) |
| Python backend | Single uvicorn process | Railway 1 instance, 2 workers | Railway 2 instances, auto-scale |
| Database | SQLite | Vercel Postgres free tier | Vercel Postgres Pro |
| SSE connections | Direct | Proxied through Vercel | May need WebSocket upgrade |
| Concurrent analyses | 1-2 | 3-5 (Railway CPU bound) | Queue system (Redis + worker) |

## Sources

- [Next.js API Routes as proxy layer](https://nextjs.org/blog/building-apis-with-nextjs) -- HIGH confidence
- [fastapi-nextauth-jwt PyPI](https://pypi.org/project/fastapi-nextauth-jwt/) -- HIGH confidence, purpose-built library
- [Vercel Blob documentation](https://vercel.com/docs/vercel-blob) -- HIGH confidence, official docs
- [FastAPI SSE documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- HIGH confidence
- [Fixing SSE streaming in Next.js on Vercel](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996) -- MEDIUM confidence
- [Combining Next.js and NextAuth with FastAPI](https://tom.catshoek.dev/posts/nextauth-fastapi/) -- HIGH confidence
- [Deploy FastAPI on Railway](https://docs.railway.com/guides/fastapi) -- HIGH confidence, official docs
- [Vercel Python + JS hybrid apps](https://vercel.com/kb/guide/how-to-use-python-and-javascript-in-the-same-application) -- HIGH confidence, explains limitations
- [Next.js + FastAPI discussion](https://github.com/vercel/next.js/discussions/43724) -- MEDIUM confidence
- [Prisma with Next.js guide](https://www.prisma.io/docs/guides/nextjs) -- HIGH confidence, official docs
- Existing codebase analysis: `backend/main.py`, `backend/routers/*.py`, `backend/services/auth_service.py`, `backend/db/models.py`, `backend/db/engine.py`, `backend/config.py`
