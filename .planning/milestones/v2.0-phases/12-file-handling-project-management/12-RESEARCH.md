# Phase 12: File Handling + Project Management - Research

**Researched:** 2026-03-11
**Domain:** Vercel Blob file uploads, Prisma project/file schema, Next.js App Router CRUD
**Confidence:** HIGH

## Summary

Phase 12 adds two core capabilities to the FTAG platform: (1) persistent file storage via Vercel Blob with drag-and-drop upload supporting files over 4.5 MB, and (2) full project CRUD with sharing, archiving, and analysis history. The existing codebase already has a placeholder `projekte` page, a working Prisma 7 + Neon Postgres setup, Better Auth with RBAC permissions (including `project: ["create", "read", "update", "delete", "share"]`), and a BFF proxy layer.

The key technical challenge is the Vercel Blob client upload flow, which requires a two-step token exchange to bypass Vercel's 4.5 MB body limit. Files are uploaded directly from the browser to Vercel Blob, with a Next.js API route acting as the token issuer. The file metadata (blob URL, name, size, type) is then stored in Postgres via Prisma. For projects, this is standard CRUD with relational modeling -- projects own files and analyses, and a many-to-many sharing model connects projects to users.

**Primary recommendation:** Use `@vercel/blob` client uploads with `handleUpload` for all file uploads (bypasses 4.5 MB limit), store blob URLs in Prisma `File` model, and build project CRUD with Next.js Server Actions + Prisma queries. Use `access: 'private'` for all uploads since tender documents are confidential business data.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-04 | Vercel Blob Storage fuer Datei-Uploads (signed URLs) | `@vercel/blob` client upload flow with `handleUpload` token exchange; `access: 'private'` for confidential files; `del()` for cleanup |
| PROJ-01 | Projekte anlegen (Name, Kunde, Frist, Beschreibung) | Prisma `Project` model with fields: name, customer, deadline, description, status; Server Action for creation |
| PROJ-02 | Mehrere Analysen pro Projekt mit Historie | `Analysis` model with `projectId` FK, status enum, timestamps; project detail page with analysis list |
| PROJ-03 | Projekte archivieren und loeschen | `status` field on Project (active/archived); soft-delete via archive, hard-delete with cascade + blob cleanup |
| PROJ-04 | Projekte mit anderen Benutzern teilen | `ProjectShare` join table (projectId + userId + role); share dialog with user search |
| ANLZ-01 | Schritt 1 -- Drag & Drop Upload via Vercel Blob | Client-side drag-and-drop component using `upload()` from `@vercel/blob/client`; `handleUpload` route for token generation |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @vercel/blob | latest | File storage (upload, delete, list, get) | Official Vercel storage SDK; handles client uploads, token exchange, multipart for large files |
| prisma | 7.4.2 | Database ORM for project/file/analysis models | Already in use; Prisma 7 with PrismaPg adapter for Neon |
| next | 16.1.6 | App Router, Server Actions, API routes | Already in use; handles upload token route and server-side CRUD |
| better-auth | 1.5.4 | Auth + RBAC for permission checks | Already in use; project permissions already defined in permissions.ts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.577.0 | Icons for upload UI, project cards | Already installed; Upload, Folder, Archive, Share, Trash icons |
| sonner | 2.0.7 | Toast notifications for CRUD feedback | Already installed; success/error toasts |
| shadcn/ui dialog | 4.0.3 | Share dialog, delete confirmation, create project modal | Already available; extend with new dialogs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @vercel/blob | S3 + presigned URLs | More control but requires AWS setup; Vercel Blob is native to deployment platform |
| Server Actions | API routes for CRUD | Server Actions are simpler for form submissions; API routes needed only for blob token exchange |
| react-dropzone | Native drag-and-drop | react-dropzone adds dependency; native HTML5 DnD API is sufficient with `@vercel/blob/client` upload |

**Installation:**
```bash
cd frontend && npm install @vercel/blob
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   ├── api/
│   │   └── upload/
│   │       └── route.ts          # handleUpload token exchange for Vercel Blob
│   └── (app)/
│       └── projekte/
│           ├── page.tsx           # Project list (replace placeholder)
│           ├── neu/
│           │   └── page.tsx       # Create project form
│           └── [id]/
│               ├── page.tsx       # Project detail (files + analyses)
│               └── teilen/
│                   └── page.tsx   # Share management (or use dialog)
├── components/
│   ├── projects/
│   │   ├── project-list.tsx       # Project cards/table with status badges
│   │   ├── project-form.tsx       # Create/edit form (client component)
│   │   ├── project-card.tsx       # Single project card
│   │   ├── share-dialog.tsx       # Share project with users
│   │   └── archive-dialog.tsx     # Archive/delete confirmation
│   └── upload/
│       ├── file-dropzone.tsx      # Drag-and-drop upload zone (client component)
│       └── file-list.tsx          # Uploaded files with status
├── lib/
│   └── actions/
│       ├── project-actions.ts     # Server Actions: create, update, archive, delete, share
│       └── file-actions.ts        # Server Actions: record file metadata, delete file
└── generated/prisma/client/       # Prisma generated client (existing)
```

### Pattern 1: Vercel Blob Client Upload Flow
**What:** Two-step upload: browser gets token from your API route, then uploads directly to Vercel Blob
**When to use:** All file uploads (required to bypass 4.5 MB limit)
**Example:**
```typescript
// Source: https://vercel.com/docs/storage/vercel-blob/client-upload

// 1. API Route: frontend/src/app/api/upload/route.ts
import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';

export async function POST(request: Request): Promise<NextResponse> {
  // Authenticate first
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'Nicht authentifiziert' }, { status: 401 });
  }

  const body = (await request.json()) as HandleUploadBody;

  const jsonResponse = await handleUpload({
    body,
    request,
    onBeforeGenerateToken: async (pathname) => {
      return {
        allowedContentTypes: [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ],
        addRandomSuffix: true,
        tokenPayload: JSON.stringify({
          userId: session.user.id,
        }),
      };
    },
    onUploadCompleted: async ({ blob, tokenPayload }) => {
      // Save file metadata to DB (won't work locally without ngrok)
      // Use client-side DB save as primary path instead
    },
  });

  return NextResponse.json(jsonResponse);
}

// 2. Client Component: upload from browser
'use client';
import { upload } from '@vercel/blob/client';

const newBlob = await upload(file.name, file, {
  access: 'private',
  handleUploadUrl: '/api/upload',
  multipart: true, // for large files
  onUploadProgress: ({ loaded, total, percentage }) => {
    setProgress(percentage);
  },
});
// Then save newBlob.url to DB via Server Action
```

### Pattern 2: Server Actions for CRUD
**What:** Next.js Server Actions for all project mutations
**When to use:** Create, update, archive, delete, share operations
**Example:**
```typescript
// Source: Next.js App Router pattern

// frontend/src/lib/actions/project-actions.ts
'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';

export async function createProject(formData: FormData) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { project: ['create'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const project = await prisma.project.create({
    data: {
      name: formData.get('name') as string,
      customer: formData.get('customer') as string,
      deadline: formData.get('deadline') ? new Date(formData.get('deadline') as string) : null,
      description: formData.get('description') as string,
      ownerId: session.user.id,
    },
  });

  revalidatePath('/projekte');
  return project;
}
```

### Pattern 3: Project Sharing via Join Table
**What:** Many-to-many relationship between projects and users with role
**When to use:** PROJ-04 sharing requirement
**Example:**
```typescript
// Prisma schema pattern
model ProjectShare {
  id        String   @id @default(cuid())
  projectId String
  project   Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  role      String   @default("viewer") // viewer, editor
  createdAt DateTime @default(now())

  @@unique([projectId, userId])
  @@map("project_share")
}
```

### Anti-Patterns to Avoid
- **Storing files in Postgres:** Never store binary file data in the database. Store Vercel Blob URLs only.
- **Server-side upload for large files:** Never route file bytes through Next.js API routes. Use client upload to bypass 4.5 MB limit.
- **Forgetting blob cleanup on project delete:** When deleting a project, must also call `del()` on all associated blob URLs before removing DB records.
- **onUploadCompleted as primary save path:** This callback does not work in local development (requires public URL). Save file metadata via Server Action after `upload()` returns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File upload to cloud storage | Custom S3 presigned URL logic | `@vercel/blob` client upload with `handleUpload` | Handles token exchange, multipart, progress, retries automatically |
| Drag-and-drop file zone | Complex DnD library | Native HTML5 DnD events + `upload()` | Simple `onDrop` + `onDragOver` is sufficient; no need for react-dropzone |
| File type validation | Manual MIME checking | `allowedContentTypes` in `onBeforeGenerateToken` | Validated server-side by Vercel Blob before upload is allowed |
| Permission checking | Manual role checks | `auth.api.userHasPermission` from Better Auth | Already configured with project RBAC in permissions.ts |

**Key insight:** The Vercel Blob SDK handles ALL the complexity of secure client uploads (token generation, multipart chunking, progress tracking). The implementation is a thin API route + a client `upload()` call. Don't over-engineer.

## Common Pitfalls

### Pitfall 1: onUploadCompleted Not Working Locally
**What goes wrong:** The `onUploadCompleted` callback in `handleUpload` is called by Vercel's servers, which cannot reach `localhost`.
**Why it happens:** Vercel Blob sends a webhook to your server after upload completes; this requires a publicly accessible URL.
**How to avoid:** Do NOT rely on `onUploadCompleted` as the primary path to save file metadata. Instead, after `upload()` resolves on the client, call a Server Action to save the blob URL to the database. Use `onUploadCompleted` only as a backup/verification in production.
**Warning signs:** File metadata missing in DB after upload appears to succeed.

### Pitfall 2: Forgetting access: 'private' for Confidential Files
**What goes wrong:** Tender documents are publicly accessible via URL.
**Why it happens:** Default behavior or copy-paste from examples using `access: 'public'`.
**How to avoid:** Always use `access: 'private'`. Private blobs require server-side `get()` to stream content, which acts as an access control layer.
**Warning signs:** Blob URLs containing `.public.blob.vercel-storage.com`.

### Pitfall 3: Cascading Deletes Without Blob Cleanup
**What goes wrong:** Prisma cascade deletes remove DB records but orphan blobs in Vercel storage.
**Why it happens:** `onDelete: Cascade` only affects database rows, not external storage.
**How to avoid:** Before deleting a project, query all associated file blob URLs, call `del(urls)` on Vercel Blob, then delete the project in DB.
**Warning signs:** Growing Vercel Blob storage costs with no corresponding DB records.

### Pitfall 4: Missing Prisma Migration
**What goes wrong:** Schema changes not reflected in database.
**Why it happens:** Forgetting to run `npx prisma migrate dev` after adding new models.
**How to avoid:** Always create a migration after schema changes. Migration name should be descriptive (e.g., `add_project_and_file_models`).
**Warning signs:** Prisma client errors about missing tables/columns.

### Pitfall 5: BLOB_READ_WRITE_TOKEN Not Set
**What goes wrong:** Upload API route returns 500 errors.
**Why it happens:** Environment variable not configured locally or in Vercel deployment.
**How to avoid:** Add `BLOB_READ_WRITE_TOKEN` to `.env.local` for development. On Vercel, it's auto-set when you create a Blob store.
**Warning signs:** "BlobAccessError" or token-related errors in upload route.

## Code Examples

### Prisma Schema Addition (Project, File, Analysis, ProjectShare)
```prisma
// Source: Prisma 7 documentation + project patterns

model Project {
  id          String         @id @default(cuid())
  name        String
  customer    String?
  deadline    DateTime?
  description String?
  status      String         @default("active") // active, archived
  ownerId     String
  owner       User           @relation("OwnedProjects", fields: [ownerId], references: [id])
  files       File[]
  analyses    Analysis[]
  shares      ProjectShare[]
  createdAt   DateTime       @default(now())
  updatedAt   DateTime       @updatedAt

  @@map("project")
}

model File {
  id          String   @id @default(cuid())
  name        String   // original filename
  blobUrl     String   // Vercel Blob URL
  downloadUrl String   // Vercel Blob download URL
  size        Int      // file size in bytes
  contentType String   // MIME type
  projectId   String
  project     Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  uploadedBy  String
  uploader    User     @relation("UploadedFiles", fields: [uploadedBy], references: [id])
  createdAt   DateTime @default(now())

  @@map("file")
}

model Analysis {
  id        String   @id @default(cuid())
  projectId String
  project   Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  status    String   @default("pending") // pending, running, completed, failed
  result    Json?    // analysis result data
  startedAt DateTime?
  endedAt   DateTime?
  startedBy String
  user      User     @relation("UserAnalyses", fields: [startedBy], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("analysis")
}

model ProjectShare {
  id        String   @id @default(cuid())
  projectId String
  project   Project  @relation(fields: [projectId], references: [id], onDelete: Cascade)
  userId    String
  user      User     @relation("SharedProjects", fields: [userId], references: [id], onDelete: Cascade)
  role      String   @default("viewer") // viewer, editor
  createdAt DateTime @default(now())

  @@unique([projectId, userId])
  @@map("project_share")
}
```

**Note:** The `User` model needs additional relation fields:
```prisma
model User {
  // ... existing fields ...
  ownedProjects  Project[]      @relation("OwnedProjects")
  uploadedFiles  File[]         @relation("UploadedFiles")
  analyses       Analysis[]     @relation("UserAnalyses")
  sharedProjects ProjectShare[] @relation("SharedProjects")
}
```

### Drag-and-Drop Upload Component
```typescript
// Source: Vercel Blob client upload docs + HTML5 DnD API

'use client';

import { useState, useCallback } from 'react';
import { upload } from '@vercel/blob/client';
import { Upload, FileText, X } from 'lucide-react';

interface UploadedFile {
  name: string;
  url: string;
  downloadUrl: string;
  size: number;
  contentType: string;
}

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

export function FileDropzone({ projectId, onFileUploaded }: {
  projectId: string;
  onFileUploaded: (file: UploadedFile) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpload = useCallback(async (files: FileList) => {
    for (const file of Array.from(files)) {
      if (!ACCEPTED_TYPES.includes(file.type)) continue;
      setUploading(true);
      setProgress(0);

      const blob = await upload(file.name, file, {
        access: 'private',
        handleUploadUrl: '/api/upload',
        multipart: true,
        onUploadProgress: ({ percentage }) => setProgress(percentage),
      });

      onFileUploaded({
        name: file.name,
        url: blob.url,
        downloadUrl: blob.downloadUrl,
        size: file.size,
        contentType: file.type,
      });

      setUploading(false);
    }
  }, [onFileUploaded]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files);
      }}
      className={cn(
        'rounded-lg border-2 border-dashed p-8 text-center transition-colors',
        isDragging ? 'border-primary bg-primary/5' : 'border-border',
      )}
    >
      <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
      <p>PDF, DOCX oder XLSX hierher ziehen</p>
      {uploading && <progress value={progress} max={100} />}
    </div>
  );
}
```

### Project List Query with Sharing
```typescript
// Query pattern: show owned + shared projects
const projects = await prisma.project.findMany({
  where: {
    OR: [
      { ownerId: session.user.id },
      { shares: { some: { userId: session.user.id } } },
    ],
    status: showArchived ? undefined : 'active',
  },
  include: {
    owner: { select: { name: true, email: true } },
    _count: { select: { files: true, analyses: true } },
  },
  orderBy: { updatedAt: 'desc' },
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server upload (put from API route) | Client upload (upload from browser) | @vercel/blob client support | Files bypass 4.5 MB limit, upload directly to Blob |
| Public blob URLs | Private blobs with server-side get() | @vercel/blob >= 2.3 | Private storage requires streaming through your API for access control |
| Prisma @prisma/client import | Import from @/generated/prisma/client | Prisma 7 | Output path changed; already configured in this project |
| addRandomSuffix defaults to true | addRandomSuffix defaults to false | Recent @vercel/blob | Must explicitly set addRandomSuffix: true to avoid filename collisions |

**Important version note:** `addRandomSuffix` now defaults to `false` in recent versions of `@vercel/blob`. Always explicitly set `addRandomSuffix: true` when uploading user files to prevent collisions.

## Open Questions

1. **Private blob serving for downloads**
   - What we know: Private blobs require `get()` to stream content; public blobs are directly accessible via URL
   - What's unclear: Whether to use private or public storage -- tender docs are confidential, but private adds complexity for downloads
   - Recommendation: Use `access: 'private'` and create a download API route that authenticates + streams via `get()`. This ensures only authorized users can access files.

2. **Analysis model scope in this phase**
   - What we know: PROJ-02 requires "multiple analyses per project with history"; ANLZ-01 is "step 1 upload only"
   - What's unclear: How much Analysis model detail to build now vs. Phase 13
   - Recommendation: Create a minimal Analysis model (id, projectId, status, timestamps) now. Phase 13 will add the full wizard and result storage.

3. **onUploadCompleted local development**
   - What we know: This callback requires a public URL; won't work on localhost without ngrok
   - What's unclear: Whether to set up ngrok for development
   - Recommendation: Skip ngrok. Use client-side Server Action call after `upload()` resolves as the primary metadata save path. The `onUploadCompleted` callback is a nice-to-have for production resilience only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 + jsdom |
| Config file | frontend/vitest.config.ts |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-04 | Upload route authenticates and returns blob token | unit | `cd frontend && npx vitest run src/__tests__/upload/blob-upload.test.ts -x` | No - Wave 0 |
| PROJ-01 | Create project with required fields | unit | `cd frontend && npx vitest run src/__tests__/projects/project-crud.test.ts -x` | No - Wave 0 |
| PROJ-02 | Project detail shows analyses list | unit | `cd frontend && npx vitest run src/__tests__/projects/project-detail.test.ts -x` | No - Wave 0 |
| PROJ-03 | Archive and delete project | unit | `cd frontend && npx vitest run src/__tests__/projects/project-archive.test.ts -x` | No - Wave 0 |
| PROJ-04 | Share project with user | unit | `cd frontend && npx vitest run src/__tests__/projects/project-share.test.ts -x` | No - Wave 0 |
| ANLZ-01 | Drag-and-drop upload accepted file types | unit | `cd frontend && npx vitest run src/__tests__/upload/file-dropzone.test.ts -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/__tests__/upload/blob-upload.test.ts` -- covers INFRA-04
- [ ] `src/__tests__/upload/file-dropzone.test.ts` -- covers ANLZ-01
- [ ] `src/__tests__/projects/project-crud.test.ts` -- covers PROJ-01
- [ ] `src/__tests__/projects/project-detail.test.ts` -- covers PROJ-02
- [ ] `src/__tests__/projects/project-archive.test.ts` -- covers PROJ-03
- [ ] `src/__tests__/projects/project-share.test.ts` -- covers PROJ-04

## Sources

### Primary (HIGH confidence)
- [Vercel Blob SDK docs](https://vercel.com/docs/vercel-blob/using-blob-sdk) - `put()`, `del()`, `head()`, `list()`, `get()` API, `handleUpload`, client upload flow
- [Vercel Blob Client Upload docs](https://vercel.com/docs/storage/vercel-blob/client-upload) - Token exchange, `onBeforeGenerateToken`, `onUploadCompleted`, Next.js App Router examples
- [Vercel Blob Server Upload docs](https://vercel.com/docs/storage/vercel-blob/server-upload) - 4.5 MB limit explanation, server vs client upload guidance
- Existing codebase: `frontend/prisma/schema.prisma`, `frontend/src/lib/permissions.ts`, `frontend/src/lib/auth.ts` - Current schema, RBAC config, auth patterns

### Secondary (MEDIUM confidence)
- [Vercel 4.5 MB body limit KB](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions) - Confirmation that client uploads are the recommended bypass
- [@vercel/blob npm](https://www.npmjs.com/package/@vercel/blob) - Package availability and installation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `@vercel/blob` is official Vercel SDK, well documented; Prisma 7 already in use
- Architecture: HIGH - Client upload pattern is well-documented; CRUD with Server Actions is standard Next.js App Router
- Pitfalls: HIGH - Key pitfalls (onUploadCompleted local, 4.5 MB limit, blob cleanup) are documented in official sources

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable, well-documented stack)
