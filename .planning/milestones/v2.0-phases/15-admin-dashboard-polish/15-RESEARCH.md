# Phase 15: Admin + Dashboard + Polish - Research

**Researched:** 2026-03-11
**Domain:** Admin UI, Dashboard analytics, Email notifications, UX polish
**Confidence:** HIGH

## Summary

Phase 15 completes the v2.0 platform with four distinct domains: (1) admin user management using Better Auth's built-in admin plugin APIs, (2) dashboard with analysis statistics and activity feed, (3) email notifications via Resend + React Email, and (4) UX polish with keyboard shortcuts and skeleton loaders. The existing codebase already has the admin role-gate working, Better Auth admin plugin configured with RBAC, and placeholder pages ready for implementation.

The primary technical challenge is wiring together multiple independent features without introducing regressions. Each domain is relatively straightforward given the existing patterns (server actions, server/client component split, shadcn/ui components). The email integration requires a new dependency (Resend SDK + React Email) and environment variable. The audit log and system settings require new Prisma models and migrations.

**Primary recommendation:** Build admin user management first (leverages existing Better Auth admin APIs), then dashboard (new queries against existing data), then email (new dependency), then polish (keyboard shortcuts + skeletons) last as it touches many existing pages.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dashboard layout: Top row of 3-4 stat cards, below two-column (activity feed left/wider + statistics widget right), "Neue Analyse starten" button in page header top-right
- Admin user management: Full-width table (Name, Email, Rolle, Status, Erstellt am), actions column with edit/deactivate, "Benutzer einladen" button, edit dialog for name/role/status
- Audit log: Chronological table (Zeitpunkt, Benutzer, Aktion, Details), filter by user/action/date, newest first, paginated
- System settings: Tabbed sections (Analyse | Sicherheit | API-Schluessel), save button per tab
- Email provider: Resend with React Email templates
- Three email types: password reset OTP, user invitation, analysis complete
- Email design: minimal branded (FTAG logo, red accent line, white background, gray footer), German language
- Admin table follows same pattern as Phase 13 results table

### Claude's Discretion
- Keyboard shortcut selection and discoverability (help modal, tooltips, etc.)
- Skeleton loader design and placement
- Dashboard responsive breakpoints and mobile adaptation
- Audit log pagination strategy (cursor vs offset)
- Activity feed item design and grouping
- Invite email flow UX details
- Exact stat card icons and colors
- System settings validation and error handling

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMIN-01 | Benutzerverwaltung (anlegen, bearbeiten, deaktivieren, Rollen zuweisen) | Better Auth admin plugin provides createUser, setRole, banUser/unbanUser, listUsers APIs -- all already configured |
| ADMIN-02 | Aktivitaets-Log / Audit-Trail | New AuditLog Prisma model + server actions for logging; query with pagination/filtering |
| ADMIN-03 | System-Einstellungen (Standard-Schwellenwerte, Max-Upload-Groesse, Session-Timeout) | New SystemSettings Prisma model (single-row pattern); sync thresholds to Python backend |
| ADMIN-04 | API-Key-Verwaltung (Claude API Key etc.) | Store encrypted in SystemSettings; Python backend reads from env or settings endpoint |
| DASH-01 | Status-Karten: Laufende / Abgeschlossene / Fehlerhafte Analysen | Prisma aggregate queries on Analysis model (groupBy status) |
| DASH-02 | Letzte Aktivitaeten Feed | Query AuditLog model for recent entries across all users |
| DASH-03 | Statistik-Widget: Gesamtzahl Matches, Gaps, Durchschnitts-Konfidenz | Aggregate from Analysis.result JSON field |
| DASH-04 | Schnellzugriff-Button "Neue Analyse starten" | Link to /neue-analyse, visible on dashboard header |
| UI-05 | Keyboard-Shortcuts fuer Power-User | Custom useKeyboardShortcuts hook with native keydown listener |
| UI-06 | Skeleton-Loader statt Spinner | Tailwind animate-pulse skeleton components replacing existing loading states |
| INFRA-05 | E-Mail-Versand (Passwort-Reset, Analyse-fertig-Benachrichtigung) | Resend SDK + React Email templates, wire into Better Auth emailOTP sendVerificationOTP |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| better-auth | ^1.5.4 | Admin user CRUD (already installed) | Already configured with admin plugin, RBAC, 4 roles |
| resend | ^4.0 | Email sending API | CONTEXT.md locked decision; simple API, React Email integration |
| @react-email/components | ^1.0.8 | Email template components | Pairs with Resend; JSX-based email templates |
| prisma | ^7.4.2 | New models (AuditLog, SystemSettings) | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.577.0 | Icons for stat cards, actions | Already installed, use for dashboard icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Resend | Nodemailer + SMTP | Resend is simpler (API-based), React Email native; Nodemailer needs SMTP config |
| Custom keyboard hook | react-hotkeys-hook | Only ~5 shortcuts needed; custom hook avoids new dependency for trivial use case |
| Custom skeletons | react-loading-skeleton | Tailwind animate-pulse with div shapes is sufficient; no new dependency needed |

**Installation:**
```bash
cd frontend && npm install resend @react-email/components
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/(app)/
│   ├── admin/
│   │   ├── page.tsx              # Server: auth gate + data fetch
│   │   ├── client.tsx            # Client: tabs (Users, Audit, Settings)
│   │   ├── user-management.tsx   # Client: user table + CRUD dialogs
│   │   ├── audit-log.tsx         # Client: audit log table + filters
│   │   └── system-settings.tsx   # Client: tabbed settings form
│   └── dashboard/
│       ├── page.tsx              # Server: aggregate queries
│       ├── client.tsx            # Client: dashboard layout
│       ├── stat-cards.tsx        # Client: status card components
│       ├── activity-feed.tsx     # Client: recent activity list
│       └── statistics-widget.tsx # Client: match/gap stats
├── components/
│   ├── ui/
│   │   └── skeleton.tsx          # Reusable skeleton loader component
│   └── keyboard-shortcuts/
│       └── shortcut-provider.tsx # Global keyboard shortcut handler
├── emails/
│   ├── password-reset.tsx        # React Email: OTP template
│   ├── user-invitation.tsx       # React Email: invite template
│   └── analysis-complete.tsx     # React Email: results notification
└── lib/
    ├── actions/
    │   ├── admin-actions.ts      # Server actions: user CRUD, settings
    │   └── audit-actions.ts      # Server actions: log entry, query
    ├── email.ts                  # Resend client singleton
    └── hooks/
        └── use-keyboard-shortcuts.ts  # Custom keyboard shortcut hook
```

### Pattern 1: Better Auth Admin APIs via Server Actions
**What:** Wrap Better Auth admin plugin methods in Next.js Server Actions for type-safe client calls.
**When to use:** All user management operations (create, edit role, ban/unban, list).
**Example:**
```typescript
// Source: Better Auth admin plugin docs
'use server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';

export async function listUsers(searchValue?: string, offset = 0, limit = 50) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { admin: ['manage-users'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const result = await auth.api.listUsers({
    query: { searchValue, searchField: 'name', limit, offset },
  });
  return result;
}

export async function inviteUser(formData: FormData) {
  // ... auth check ...
  const newUser = await auth.api.createUser({
    body: {
      email: formData.get('email') as string,
      password: crypto.randomUUID(), // temporary, user resets via email
      name: formData.get('name') as string,
      role: formData.get('role') as string,
    },
  });
  // Send invitation email via Resend
  await sendInvitationEmail(newUser.email, newUser.name);
  revalidatePath('/admin');
  return newUser;
}
```

### Pattern 2: AuditLog Write Pattern
**What:** Record audit events in a central log table from server actions.
**When to use:** After every significant mutation (user CRUD, settings change, analysis start/complete).
**Example:**
```typescript
// Helper function called from server actions
async function logAuditEvent(params: {
  userId: string;
  action: string;
  details: string;
  targetId?: string;
  targetType?: string;
}) {
  await prisma.auditLog.create({
    data: {
      userId: params.userId,
      action: params.action,
      details: params.details,
      targetId: params.targetId,
      targetType: params.targetType,
    },
  });
}
```

### Pattern 3: Single-Row SystemSettings
**What:** Store system config in a single Prisma row, upsert on save.
**When to use:** System settings that apply globally (thresholds, limits, timeouts).
**Example:**
```typescript
// Prisma model
model SystemSettings {
  id                  String   @id @default("default")
  defaultConfidence   Float    @default(0.7)
  maxUploadSizeMB     Int      @default(50)
  sessionTimeoutMin   Int      @default(480)
  validationPasses    Int      @default(1)
  claudeApiKey        String?  // encrypted at rest
  updatedAt           DateTime @updatedAt
  updatedBy           String?
  @@map("system_settings")
}

// Server action
export async function updateSettings(section: string, formData: FormData) {
  // ... auth check for admin:manage-settings ...
  await prisma.systemSettings.upsert({
    where: { id: 'default' },
    create: { /* defaults */ },
    update: { /* form values */ },
  });
  // If thresholds changed, notify Python backend
  if (section === 'analyse') {
    await syncSettingsToPython();
  }
  revalidatePath('/admin');
}
```

### Pattern 4: Resend Email with React Email Templates
**What:** Send transactional emails using Resend SDK with JSX templates.
**When to use:** Password reset OTP, user invitation, analysis completion.
**Example:**
```typescript
// lib/email.ts
import { Resend } from 'resend';
export const resend = new Resend(process.env.RESEND_API_KEY);

// emails/password-reset.tsx
import { Html, Head, Body, Container, Text, Section, Hr } from '@react-email/components';

export function PasswordResetEmail({ otp, name }: { otp: string; name: string }) {
  return (
    <Html lang="de">
      <Head />
      <Body style={{ backgroundColor: '#ffffff', fontFamily: 'Arial, sans-serif' }}>
        <Container style={{ maxWidth: '480px', margin: '0 auto', padding: '20px' }}>
          {/* FTAG Logo + red accent line */}
          <Hr style={{ borderColor: '#dc2626', borderWidth: '2px' }} />
          <Text style={{ fontSize: '18px', fontWeight: 'bold' }}>
            Passwort zuruecksetzen
          </Text>
          <Text>Hallo {name},</Text>
          <Text>Ihr Verifizierungscode lautet:</Text>
          <Section style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f3f4f6' }}>
            <Text style={{ fontSize: '32px', fontWeight: 'bold', letterSpacing: '4px' }}>
              {otp}
            </Text>
          </Section>
          <Text style={{ color: '#6b7280', fontSize: '12px' }}>
            Dieser Code ist 10 Minuten gueltig.
          </Text>
        </Container>
      </Body>
    </Html>
  );
}

// Usage in auth.ts emailOTP plugin:
async sendVerificationOTP({ email, otp, type }) {
  const user = await prisma.user.findUnique({ where: { email } });
  await resend.emails.send({
    from: 'FTAG Angebotserstellung <noreply@ftag.ch>',
    to: [email],
    subject: 'Ihr Verifizierungscode',
    react: PasswordResetEmail({ otp, name: user?.name || email }),
  });
}
```

### Pattern 5: Custom Keyboard Shortcuts Hook
**What:** Global keyboard shortcut listener without external dependency.
**When to use:** Navigation shortcuts (N=new analysis, D=dashboard, etc.).
**Example:**
```typescript
// lib/hooks/use-keyboard-shortcuts.ts
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const SHORTCUTS: Record<string, string> = {
  n: '/neue-analyse',
  d: '/dashboard',
  p: '/projekte',
  k: '/katalog',
  '?': 'help', // opens help modal
};

export function useKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Skip when user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
      // Skip with modifier keys (except shift for ?)
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const route = SHORTCUTS[e.key.toLowerCase()];
      if (route === 'help') {
        // dispatch custom event for help modal
        window.dispatchEvent(new CustomEvent('toggle-shortcuts-help'));
      } else if (route) {
        router.push(route);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [router]);
}
```

### Pattern 6: Skeleton Loader Component
**What:** Tailwind-based skeleton placeholders matching content shape.
**When to use:** Replace spinners on all page loads and data fetches.
**Example:**
```typescript
// components/ui/skeleton.tsx
import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-muted', className)}
      {...props}
    />
  );
}

// Usage: Dashboard stat card skeleton
function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16" />
        <Skeleton className="mt-2 h-3 w-32" />
      </CardContent>
    </Card>
  );
}
```

### Anti-Patterns to Avoid
- **Calling Better Auth admin APIs from client components directly:** Always wrap in server actions for security. The admin plugin methods must run server-side.
- **Storing API keys in plain text:** Encrypt Claude API key before storing in DB. Never expose in client bundles.
- **Making audit log writes synchronous blockers:** Log audit events after the main operation succeeds. Consider fire-and-forget pattern (no await) for non-critical audit writes to avoid slowing mutations.
- **Hardcoding email sender address:** Use environment variable for Resend sender address; domain verification required.
- **Adding keyboard shortcuts that conflict with browser defaults:** Avoid Ctrl+N, Ctrl+T, etc. Use single letter keys only when no input is focused.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| User CRUD | Custom user table queries | Better Auth admin plugin (listUsers, createUser, banUser, setRole) | Already configured, handles password hashing, session revocation |
| Email HTML rendering | String templates or handlebars | React Email components (@react-email/components) | Cross-client compatibility, responsive, JSX authoring |
| Email delivery | SMTP client, nodemailer | Resend SDK | API-based, no SMTP config, delivery tracking, error handling |
| Role-based access control | Custom middleware | Better Auth RBAC + userHasPermission | Already configured with 4 roles and permission matrix |

**Key insight:** Better Auth admin plugin already provides 90% of ADMIN-01 functionality. The implementation is primarily UI work (table, dialogs, forms) wrapping existing API calls.

## Common Pitfalls

### Pitfall 1: Better Auth listUsers Returns Paginated Object
**What goes wrong:** Treating listUsers response as a plain array.
**Why it happens:** The response is `{ users: User[], total: number, limit: number, offset: number }`, not a flat array.
**How to avoid:** Destructure correctly: `const { users, total } = await auth.api.listUsers(...)`.
**Warning signs:** TypeError when trying to .map() on the response.

### Pitfall 2: Resend Domain Verification Required for Production
**What goes wrong:** Emails fail to send or land in spam.
**Why it happens:** Resend requires verified domain for production sending. Dev uses `onboarding@resend.dev`.
**How to avoid:** Use `onboarding@resend.dev` as sender during development. Add RESEND_API_KEY to env. Document domain verification as deployment step.
**Warning signs:** 403 errors from Resend API.

### Pitfall 3: Prisma Migration on Remote Neon DB
**What goes wrong:** `prisma migrate dev` hangs on remote Neon DB (known issue from Phase 12-01).
**Why it happens:** Interactive migration prompt + remote DB latency.
**How to avoid:** Create migration SQL manually as established in Phase 12-01 pattern.
**Warning signs:** Command hangs indefinitely.

### Pitfall 4: Keyboard Shortcuts Fire Inside Form Inputs
**What goes wrong:** Typing "n" in a form field triggers navigation to /neue-analyse.
**Why it happens:** Keydown listener does not check if user is typing in an input.
**How to avoid:** Always check `e.target.tagName` for INPUT/TEXTAREA/contentEditable before processing shortcuts.
**Warning signs:** Random navigation while filling forms.

### Pitfall 5: Analysis Result JSON Aggregation
**What goes wrong:** Dashboard statistics queries fail or return wrong numbers.
**Why it happens:** Analysis.result is a Json field; aggregation requires Prisma raw queries or post-processing.
**How to avoid:** For match/gap counts, either: (a) add denormalized count columns to Analysis model, or (b) fetch results and aggregate in JS. For a dashboard with moderate data volume, option (b) is simpler.
**Warning signs:** Prisma type errors when trying to filter/aggregate Json fields.

### Pitfall 6: Better Auth Server-Side Admin Calls Need Body Not Query
**What goes wrong:** 401 or parameter errors when calling admin APIs server-side.
**Why it happens:** Server-side calls use `body:` parameter, client-side uses direct parameters. Mixing them up causes failures.
**How to avoid:** Server-side: `auth.api.createUser({ body: { ... } })`. Client-side: `authClient.admin.createUser({ ... })`. Always use server actions (server-side pattern).
**Warning signs:** Unauthorized errors or missing parameter errors.

## Code Examples

### Dashboard Aggregate Query
```typescript
// Source: Prisma docs + existing Analysis model
export async function getDashboardStats() {
  const [analyses, recentActivity] = await Promise.all([
    prisma.analysis.groupBy({
      by: ['status'],
      _count: { id: true },
    }),
    prisma.auditLog.findMany({
      take: 20,
      orderBy: { createdAt: 'desc' },
      include: { user: { select: { name: true, email: true } } },
    }),
  ]);

  const statusMap = Object.fromEntries(
    analyses.map(a => [a.status, a._count.id])
  );

  return {
    running: statusMap['running'] || 0,
    completed: statusMap['completed'] || 0,
    failed: statusMap['failed'] || 0,
    recentActivity,
  };
}
```

### Audit Log Query with Filters
```typescript
export async function getAuditLog(params: {
  userId?: string;
  action?: string;
  from?: Date;
  to?: Date;
  offset?: number;
  limit?: number;
}) {
  const where: Record<string, unknown> = {};
  if (params.userId) where.userId = params.userId;
  if (params.action) where.action = params.action;
  if (params.from || params.to) {
    where.createdAt = {
      ...(params.from && { gte: params.from }),
      ...(params.to && { lte: params.to }),
    };
  }

  const [entries, total] = await Promise.all([
    prisma.auditLog.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      skip: params.offset || 0,
      take: params.limit || 50,
      include: { user: { select: { name: true, email: true } } },
    }),
    prisma.auditLog.count({ where }),
  ]);

  return { entries, total };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Nodemailer + SMTP | Resend API + React Email | 2023-2024 | No SMTP config, JSX templates, better DX |
| Custom user management tables | Better Auth admin plugin | 2024-2025 | Built-in CRUD, pagination, filtering |
| Loading spinners | Skeleton loaders | 2022+ (mainstream) | Better perceived performance, less layout shift |
| Library-based hotkeys (Mousetrap) | Custom hooks or react-hotkeys-hook | 2023+ | Simpler for small shortcut sets |

## Open Questions

1. **Python Backend Settings Sync**
   - What we know: System settings (thresholds, API key) need to reach Python backend
   - What's unclear: Whether Python should poll settings or receive push notification
   - Recommendation: Add a `/api/settings/sync` endpoint on Python that Next.js calls after settings save. Python stores in memory/env. Simple and reliable.

2. **Audit Log for Python-Initiated Events**
   - What we know: Analysis start/complete/fail happens in Python backend
   - What's unclear: How Python writes audit entries (direct DB or callback to Next.js)
   - Recommendation: Python calls Next.js API route `/api/audit` with service key to log events. Alternatively, Next.js creates audit entry when it receives SSE completion event.

3. **Claude API Key Encryption**
   - What we know: API key must not be stored in plain text
   - What's unclear: Encryption approach for single-tenant deployment
   - Recommendation: Use Node.js crypto (AES-256-GCM) with a server-side encryption key from env vars. Simple and sufficient for single-tenant.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.0.18 + jsdom |
| Config file | frontend/vitest.config.ts |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run --reporter=verbose` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADMIN-01 | User management CRUD via admin actions | unit | `cd frontend && npx vitest run src/__tests__/admin/user-management.test.ts -x` | Wave 0 |
| ADMIN-02 | Audit log write and query | unit | `cd frontend && npx vitest run src/__tests__/admin/audit-log.test.ts -x` | Wave 0 |
| ADMIN-03 | System settings save and read | unit | `cd frontend && npx vitest run src/__tests__/admin/system-settings.test.ts -x` | Wave 0 |
| ADMIN-04 | API key storage | unit | `cd frontend && npx vitest run src/__tests__/admin/api-key.test.ts -x` | Wave 0 |
| DASH-01 | Dashboard stat cards render correct counts | unit | `cd frontend && npx vitest run src/__tests__/dashboard/stat-cards.test.tsx -x` | Wave 0 |
| DASH-02 | Activity feed renders recent entries | unit | `cd frontend && npx vitest run src/__tests__/dashboard/activity-feed.test.tsx -x` | Wave 0 |
| DASH-03 | Statistics widget shows aggregates | unit | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx -x` | Wave 0 |
| DASH-04 | Quick-action button navigates to wizard | unit | `cd frontend && npx vitest run src/__tests__/dashboard/quick-action.test.tsx -x` | Wave 0 |
| UI-05 | Keyboard shortcuts trigger navigation | unit | `cd frontend && npx vitest run src/__tests__/ui/keyboard-shortcuts.test.ts -x` | Wave 0 |
| UI-06 | Skeleton loaders render during loading | unit | `cd frontend && npx vitest run src/__tests__/ui/skeleton-loader.test.tsx -x` | Wave 0 |
| INFRA-05 | Email sending with Resend | unit | `cd frontend && npx vitest run src/__tests__/infra/email.test.ts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run --reporter=verbose`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/__tests__/admin/user-management.test.ts` -- covers ADMIN-01
- [ ] `src/__tests__/admin/audit-log.test.ts` -- covers ADMIN-02
- [ ] `src/__tests__/admin/system-settings.test.ts` -- covers ADMIN-03
- [ ] `src/__tests__/admin/api-key.test.ts` -- covers ADMIN-04
- [ ] `src/__tests__/dashboard/stat-cards.test.tsx` -- covers DASH-01
- [ ] `src/__tests__/dashboard/activity-feed.test.tsx` -- covers DASH-02
- [ ] `src/__tests__/dashboard/statistics.test.tsx` -- covers DASH-03
- [ ] `src/__tests__/dashboard/quick-action.test.tsx` -- covers DASH-04
- [ ] `src/__tests__/ui/keyboard-shortcuts.test.ts` -- covers UI-05
- [ ] `src/__tests__/ui/skeleton-loader.test.tsx` -- covers UI-06
- [ ] `src/__tests__/infra/email.test.ts` -- covers INFRA-05

## Sources

### Primary (HIGH confidence)
- Better Auth admin plugin docs (https://better-auth.com/docs/plugins/admin) -- createUser, listUsers, banUser, setRole, removeUser APIs
- Resend official docs (https://resend.com/docs/send-with-nextjs) -- Next.js integration, API route pattern, React Email rendering
- Existing codebase -- auth.ts, permissions.ts, auth-client.ts, project-actions.ts patterns
- Prisma schema -- existing models, migration patterns

### Secondary (MEDIUM confidence)
- React Email components (https://react.email/components) -- template component library
- react-hotkeys-hook docs -- alternative keyboard shortcut approach (decided against for simplicity)

### Tertiary (LOW confidence)
- None -- all critical findings verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries either already installed or well-documented with official Next.js integration
- Architecture: HIGH -- follows established project patterns (server actions, server/client split, Prisma models)
- Pitfalls: HIGH -- based on project-specific decisions documented in STATE.md and verified API behaviors
- Email integration: HIGH -- Resend docs are comprehensive with Next.js examples

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable libraries, established patterns)
