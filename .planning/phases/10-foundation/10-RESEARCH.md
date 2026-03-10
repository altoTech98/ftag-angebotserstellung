# Phase 10: Foundation (Auth + Database + Design System) - Research

**Researched:** 2026-03-11
**Domain:** Authentication, Database ORM, Design System, Next.js App Shell
**Confidence:** HIGH

## Summary

Phase 10 establishes the v2.0 application shell: a Next.js 16 App Router project with Better Auth for authentication (email/password + RBAC), Prisma 7 with Neon Postgres for persistence, and a Tailwind CSS 4 + shadcn/ui design system themed to FTAG brand colors. This is a greenfield Next.js project -- the existing `frontend-react/` (Vite + React) is the v1.0 frontend and will not be reused.

The key architectural decisions are already locked: Better Auth with admin plugin for RBAC, email OTP plugin for 6-digit password reset codes, Prisma 7 adapter for Better Auth, and shadcn/ui v4 components themed with FTAG Rot/Weiss. The Next.js 16 release introduced `proxy.ts` (replacing `middleware.ts`), Turbopack as default bundler, and requires Node.js 20.9+.

**Primary recommendation:** Create the Next.js 16 app in a new `frontend/` directory (distinct from `frontend-react/`), wire Better Auth with Prisma + Neon Postgres, define the FTAG design tokens in CSS-first Tailwind 4, and build the authenticated shell layout with sidebar, breadcrumbs, and role-gated route protection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- FTAG Rot/Weiss: Classic FTAG Red (#C8102E) as primary, white backgrounds, dark gray text
- Visual style: Linear/Notion-style -- clean, minimal, lots of whitespace, subtle borders, flat design, professional B2B feel
- Dark charcoal sidebar with white text, red accent for active nav item
- Typography: Inter font family
- Components via shadcn/ui CLI v4, themed to FTAG brand
- Tailwind CSS 4 with CSS-first @theme config (no tailwind.config.js)
- Account creation: Invite-only -- Admin sends email invitations, user sets own password via signup link
- No public registration
- Login page: Centered card on clean background with FTAG logo above, email + password + submit
- Password reset: 6-digit code via email (not magic link), then set new password
- Session timeout: Configurable by Admin in settings (default 8 hours), warning modal 5 minutes before expiry with "Extend" button
- Sidebar items: Dashboard, Projekte, Neue Analyse, Katalog, Admin (role-gated) -- items appear as phases ship
- Mobile: Slide-out drawer (hamburger menu opens overlay drawer)
- Desktop: Collapsible sidebar (toggle to icon-only mode for more content space)
- Top header: Breadcrumbs on left, notification bell + user avatar dropdown (profile, logout) on right
- Responsive breakpoints: desktop (sidebar expanded), tablet (sidebar collapsed to icons), mobile (sidebar hidden, hamburger)
- Tiered access model (each role inherits permissions from the role below): Viewer < Analyst < Manager < Admin
- Default role for new invites: Set by Admin during invitation (no fixed default)
- Unauthorized access: Show page skeleton with "Keine Berechtigung" message and note to contact Admin
- All nav items visible to all roles (denied pages show permission message, not hidden)
- First Admin: Pre-seeded via environment variables (DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD)

### Claude's Discretion
- Exact red hex code refinement (start with #C8102E, adjust if needed)
- Button styles, card styling, spacing system details
- Breadcrumb separator and truncation behavior
- Error message styling and toast positioning
- Login form validation UX (inline vs. on-submit)
- Account lockout policy (if any)
- Notification bell placeholder behavior (empty state until Phase 15)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User kann sich mit E-Mail und Passwort einloggen | Better Auth emailAndPassword plugin with signIn.email/signUp.email client methods |
| AUTH-02 | User kann Passwort per E-Mail-Link zuruecksetzen | Better Auth emailOTP plugin -- 6-digit code flow (requestPasswordReset, resetPassword) per CONTEXT.md |
| AUTH-03 | Session wird automatisch nach konfigurierbarer Inaktivitaet beendet (mit Warnung) | Better Auth session config (expiresIn, updateAge) + client-side idle timer with warning modal |
| AUTH-04 | System unterstuetzt 4 Rollen: Admin, Manager, Analyst, Viewer | Better Auth admin plugin with createAccessControl for custom RBAC roles and permissions |
| AUTH-05 | Routen und API-Endpoints sind rollenbasiert geschuetzt | Next.js proxy.ts for route protection + server-side auth.api.userHasPermission checks |
| UI-01 | Rot/Weiss Design-System (Tailwind CSS 4 + shadcn/ui) nach Spezifikation | Tailwind CSS 4 @theme inline with FTAG color tokens, shadcn/ui v4 themed components |
| UI-02 | Responsive Layout (Desktop, Tablet, Mobil) | Tailwind responsive breakpoints (sm/md/lg/xl) with sidebar state management |
| UI-03 | Sidebar-Navigation mit rotem Akzent fuer aktives Item | Custom sidebar component with dark charcoal bg, collapsible, red active indicator |
| UI-04 | Breadcrumb-Navigation auf allen Seiten | shadcn/ui Breadcrumb component integrated with Next.js App Router pathname |
| INFRA-01 | Next.js 16 App Router + Prisma 7 + Neon Postgres (via Vercel) | Next.js 16 with Turbopack, Prisma 7 TS engine with Neon adapter, pooled connections |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.x | App framework (App Router) | Turbopack default, proxy.ts, React 19.2, cache components |
| React | 19.2.x | UI rendering | Ships with Next.js 16, includes View Transitions |
| Better Auth | 1.x (latest) | Authentication framework | Built-in RBAC via admin plugin, Prisma adapter, email OTP, TS-native |
| Prisma | 7.x | Database ORM | Pure TS engine (no Rust), 90% smaller bundles, 3x faster queries |
| Neon Postgres | - | Serverless database | Built-in connection pooling (PgBouncer), Vercel-native integration |
| Tailwind CSS | 4.x | Utility-first CSS | CSS-first @theme config, OKLCH colors, no config JS file |
| shadcn/ui | v4 (CLI) | Component library | Tailwind v4 native, React 19 support, data-slot attributes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @prisma/adapter-pg | latest | Neon Postgres adapter | Required for Prisma 7 + Neon connection |
| tw-animate-css | latest | Animations | Replaces deprecated tailwindcss-animate for shadcn/ui v4 |
| lucide-react | latest | Icons | Default icon set for shadcn/ui components |
| Inter (Google Fonts) | - | Typography | FTAG brand typeface via next/font/google |
| sonner | latest | Toast notifications | Replaces deprecated shadcn toast, used for error/success messages |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Better Auth | NextAuth/Auth.js | Better Auth has built-in RBAC plugin, simpler Prisma adapter -- decision locked |
| Neon Postgres | Vercel Postgres | Neon offers built-in pooling, better free tier -- decision locked |
| shadcn/ui | Radix + custom CSS | shadcn gives pre-built themed components with Tailwind -- decision locked |

**Installation:**
```bash
# Create Next.js 16 project
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir

# Auth + Database
npm install better-auth @better-auth/prisma-adapter prisma @prisma/client @prisma/adapter-pg

# UI
npx shadcn@latest init
npm install lucide-react sonner tw-animate-css
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── prisma/
│   ├── schema.prisma          # Better Auth models + custom models
│   └── migrations/            # Prisma migration files
├── prisma.config.ts           # Prisma 7 dynamic config
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout (Inter font, providers)
│   │   ├── proxy.ts           # Route protection (replaces middleware.ts)
│   │   ├── (auth)/            # Auth route group (no sidebar layout)
│   │   │   ├── login/page.tsx
│   │   │   ├── passwort-reset/page.tsx
│   │   │   └── einladung/[token]/page.tsx
│   │   ├── (app)/             # Authenticated route group (sidebar layout)
│   │   │   ├── layout.tsx     # Sidebar + header + breadcrumbs
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── projekte/page.tsx
│   │   │   ├── neue-analyse/page.tsx
│   │   │   ├── katalog/page.tsx
│   │   │   └── admin/page.tsx
│   │   └── api/
│   │       └── auth/[...all]/route.ts  # Better Auth handler
│   ├── components/
│   │   ├── ui/                # shadcn/ui generated components
│   │   ├── layout/
│   │   │   ├── sidebar.tsx    # Dark charcoal collapsible sidebar
│   │   │   ├── header.tsx     # Breadcrumbs + user menu
│   │   │   ├── breadcrumbs.tsx
│   │   │   └── user-menu.tsx  # Avatar dropdown (profile, logout)
│   │   └── auth/
│   │       ├── login-form.tsx
│   │       ├── password-reset-form.tsx
│   │       └── session-warning-modal.tsx
│   ├── lib/
│   │   ├── auth.ts            # Better Auth server config
│   │   ├── auth-client.ts     # Better Auth React client
│   │   ├── prisma.ts          # PrismaClient singleton
│   │   ├── permissions.ts     # RBAC role/permission definitions
│   │   └── utils.ts           # cn() helper from shadcn
│   ├── hooks/
│   │   ├── use-session-timeout.ts  # Client-side idle detection
│   │   └── use-breadcrumbs.ts      # Pathname-based breadcrumb generation
│   └── styles/
│       └── globals.css        # Tailwind 4 @theme inline + FTAG tokens
├── next.config.ts
├── package.json
└── .env.local
```

### Pattern 1: Better Auth Server Configuration with RBAC
**What:** Define auth instance with admin plugin, email OTP, and custom access control
**When to use:** Single auth.ts file imported by API routes and server components

```typescript
// src/lib/auth.ts
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { admin } from "better-auth/plugins";
import { emailOTP } from "better-auth/plugins";
import { nextCookies } from "better-auth/next-js";
import { createAccessControl } from "better-auth/plugins/access";
import prisma from "@/lib/prisma";

// Define resources and actions
const statement = {
  analysis: ["create", "read"],
  project: ["create", "read", "update", "delete", "share"],
  catalog: ["read", "update", "upload"],
  admin: ["access", "manage-users", "manage-settings"],
} as const;

const ac = createAccessControl(statement);

// Tiered roles (each inherits from below)
const viewerRole = ac.newRole({ analysis: ["read"], project: ["read"], catalog: ["read"] });
const analystRole = ac.newRole({ analysis: ["create", "read"], project: ["read"], catalog: ["read"] });
const managerRole = ac.newRole({ analysis: ["create", "read"], project: ["create", "read", "update", "delete", "share"], catalog: ["read", "update", "upload"] });
const adminRole = ac.newRole({ analysis: ["create", "read"], project: ["create", "read", "update", "delete", "share"], catalog: ["read", "update", "upload"], admin: ["access", "manage-users", "manage-settings"] });

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
    requireEmailVerification: false, // invite-only, admin creates users
  },
  session: {
    expiresIn: 60 * 60 * 8, // 8 hours default (configurable)
    updateAge: 60 * 15,     // refresh every 15 minutes
  },
  plugins: [
    admin({
      ac,
      roles: { viewer: viewerRole, analyst: analystRole, manager: managerRole, admin: adminRole },
      defaultRole: "viewer",
      adminRoles: ["admin"],
    }),
    emailOTP({
      otpLength: 6,
      expiresIn: 600, // 10 minutes
      async sendVerificationOTP({ email, otp, type }) {
        // Email sending -- placeholder until INFRA-05
        console.log(`[DEV] OTP for ${email}: ${otp} (type: ${type})`);
      },
    }),
    nextCookies(), // Must be last
  ],
  trustedOrigins: [process.env.BETTER_AUTH_URL!],
});
```

### Pattern 2: Route Protection with proxy.ts
**What:** Next.js 16 proxy (replaces middleware) for auth-gated routes
**When to use:** All requests to (app) routes check for session cookie

```typescript
// src/app/proxy.ts
import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

const PUBLIC_PATHS = ["/login", "/passwort-reset", "/einladung", "/api/auth"];

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check session cookie existence (lightweight, no DB call)
  const sessionCookie = getSessionCookie(request);
  if (!sessionCookie) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

### Pattern 3: Tailwind CSS 4 FTAG Theme
**What:** CSS-first theme configuration with FTAG brand tokens
**When to use:** globals.css, single source of truth for all design tokens

```css
/* src/styles/globals.css */
@import "tailwindcss";
@import "tw-animate-css";

:root {
  /* FTAG Brand Colors */
  --ftag-red: hsl(350 85% 42%);        /* #C8102E */
  --ftag-red-hover: hsl(350 85% 36%);
  --ftag-red-light: hsl(350 85% 95%);

  /* Sidebar */
  --sidebar-bg: hsl(220 13% 18%);       /* Dark charcoal */
  --sidebar-text: hsl(0 0% 95%);
  --sidebar-active: var(--ftag-red);
  --sidebar-hover: hsl(220 13% 24%);

  /* Semantic tokens */
  --background: hsl(0 0% 100%);
  --foreground: hsl(220 13% 18%);
  --card: hsl(0 0% 100%);
  --card-foreground: hsl(220 13% 18%);
  --primary: var(--ftag-red);
  --primary-foreground: hsl(0 0% 100%);
  --muted: hsl(220 10% 96%);
  --muted-foreground: hsl(220 10% 46%);
  --border: hsl(220 10% 90%);
  --input: hsl(220 10% 90%);
  --ring: var(--ftag-red);
  --destructive: hsl(0 84% 60%);
  --destructive-foreground: hsl(0 0% 100%);
  --radius: 0.5rem;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-sidebar-bg: var(--sidebar-bg);
  --color-sidebar-text: var(--sidebar-text);
  --color-sidebar-active: var(--sidebar-active);
  --color-sidebar-hover: var(--sidebar-hover);
  --color-ftag-red: var(--ftag-red);
  --color-ftag-red-hover: var(--ftag-red-hover);
  --color-ftag-red-light: var(--ftag-red-light);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);

  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}
```

### Pattern 4: Prisma 7 with Neon Postgres
**What:** Prisma 7 TypeScript engine with Neon connection pooling
**When to use:** Database access throughout the application

```typescript
// src/lib/prisma.ts
import { PrismaClient } from "@/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

const adapter = new PrismaPg({
  connectionString: process.env.DATABASE_URL!,
});

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient;
};

const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({ adapter });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}

export default prisma;
```

```env
# .env.local
# Pooled connection for application queries
DATABASE_URL="postgresql://user:pass@ep-xxx-pooler.region.neon.tech/dbname?sslmode=require"
# Direct connection for Prisma migrations
DIRECT_URL="postgresql://user:pass@ep-xxx.region.neon.tech/dbname?sslmode=require"

BETTER_AUTH_SECRET="generate-with-npx-auth-secret"
BETTER_AUTH_URL="http://localhost:3000"
DEFAULT_ADMIN_EMAIL="admin@franktueren.ch"
DEFAULT_ADMIN_PASSWORD="changeme-on-first-login"
```

### Pattern 5: First Admin Seeding
**What:** Create the initial admin user from environment variables on first startup
**When to use:** Application bootstrap, runs once when no admin exists

```typescript
// src/lib/seed-admin.ts
import { auth } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function seedAdmin() {
  const adminEmail = process.env.DEFAULT_ADMIN_EMAIL;
  const adminPassword = process.env.DEFAULT_ADMIN_PASSWORD;

  if (!adminEmail || !adminPassword) return;

  const existing = await prisma.user.findUnique({
    where: { email: adminEmail },
  });

  if (existing) return;

  // Use Better Auth server API to create user with hashed password
  await auth.api.createUser({
    body: {
      email: adminEmail,
      password: adminPassword,
      name: "Admin",
      role: "admin",
    },
  });

  console.log(`[SEED] Admin user created: ${adminEmail}`);
}
```

### Pattern 6: Session Timeout with Client-Side Idle Detection
**What:** Track user activity, show warning modal before session expires
**When to use:** All authenticated pages via the (app) layout

```typescript
// src/hooks/use-session-timeout.ts
"use client";
import { useState, useEffect, useCallback, useRef } from "react";

const ACTIVITY_EVENTS = ["mousedown", "keydown", "scroll", "touchstart"];
const WARNING_BEFORE_MS = 5 * 60 * 1000; // 5 minutes before expiry

export function useSessionTimeout(expiresIn: number) {
  const [showWarning, setShowWarning] = useState(false);
  const lastActivity = useRef(Date.now());
  const warningTimer = useRef<NodeJS.Timeout>();
  const expireTimer = useRef<NodeJS.Timeout>();

  const resetTimers = useCallback(() => {
    lastActivity.current = Date.now();
    setShowWarning(false);

    if (warningTimer.current) clearTimeout(warningTimer.current);
    if (expireTimer.current) clearTimeout(expireTimer.current);

    warningTimer.current = setTimeout(() => {
      setShowWarning(true);
    }, expiresIn - WARNING_BEFORE_MS);

    expireTimer.current = setTimeout(() => {
      // Force logout
      window.location.href = "/login?expired=true";
    }, expiresIn);
  }, [expiresIn]);

  const extendSession = useCallback(async () => {
    // Call Better Auth to refresh the session
    await fetch("/api/auth/session", { method: "GET", credentials: "include" });
    resetTimers();
  }, [resetTimers]);

  useEffect(() => {
    resetTimers();
    const handler = () => resetTimers();
    ACTIVITY_EVENTS.forEach(e => document.addEventListener(e, handler, { passive: true }));
    return () => {
      ACTIVITY_EVENTS.forEach(e => document.removeEventListener(e, handler));
      if (warningTimer.current) clearTimeout(warningTimer.current);
      if (expireTimer.current) clearTimeout(expireTimer.current);
    };
  }, [resetTimers]);

  return { showWarning, extendSession };
}
```

### Anti-Patterns to Avoid
- **Do NOT use middleware.ts:** Next.js 16 deprecates middleware.ts in favor of proxy.ts. Use `export default function proxy()` instead.
- **Do NOT make DB calls in proxy.ts:** Only check cookie existence for lightweight route protection. Validate sessions in server components/actions.
- **Do NOT store Prisma client in node_modules:** Prisma 7 generates output to project source by default. Import from `@/generated/prisma/client`.
- **Do NOT use tailwind.config.js:** Tailwind CSS 4 uses CSS-first config with @theme directive. All theming goes in globals.css.
- **Do NOT use tailwindcss-animate:** Deprecated in favor of tw-animate-css for shadcn/ui v4.
- **Do NOT use forwardRef in components:** React 19 + shadcn/ui v4 uses function components with data-slot attributes.
- **Do NOT hide nav items based on role:** All nav items visible to all roles; denied pages show "Keine Berechtigung" message.
- **Do NOT allow public registration:** emailAndPassword.disableSignUp should be true; only admins create users via admin.createUser.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authentication | Custom JWT/session logic | Better Auth emailAndPassword | Password hashing (scrypt), session management, CSRF protection built-in |
| Role-based access | Custom role checks | Better Auth admin plugin + createAccessControl | Permission inheritance, role assignment, hasPermission checks |
| Password reset | Custom token generation | Better Auth emailOTP plugin | OTP generation, expiry, attempt limiting, secure storage |
| Database ORM | Raw SQL queries | Prisma 7 | Type-safe queries, migrations, schema management |
| Connection pooling | Custom pool management | Neon built-in PgBouncer | Up to 10,000 connections, transaction mode, serverless-optimized |
| Component library | Custom form inputs, dialogs | shadcn/ui components | Accessible (Radix primitives), keyboard navigation, ARIA attributes |
| CSS design tokens | Custom CSS variable system | Tailwind CSS 4 @theme inline | Utility class generation, responsive variants, dark mode ready |
| Toast notifications | Custom notification system | sonner | Stacking, auto-dismiss, accessible announcements |

**Key insight:** Better Auth's plugin system (admin + emailOTP) provides 80% of the auth requirements out of the box. The remaining 20% is UI wiring (login form, session warning modal, permission error pages).

## Common Pitfalls

### Pitfall 1: Prisma 7 Output Location Changed
**What goes wrong:** Import from `@prisma/client` fails -- Prisma 7 generates to project source
**Why it happens:** Prisma 7 moved generated artifacts out of node_modules by default
**How to avoid:** Import from the configured output path (e.g., `@/generated/prisma/client`). Run `npx auth@latest generate` then `npx prisma generate` to ensure schema includes Better Auth models.
**Warning signs:** "Cannot find module '@prisma/client'" errors

### Pitfall 2: Better Auth Schema Generation Order
**What goes wrong:** Missing database tables for auth (user, session, account, verification)
**Why it happens:** Better Auth models must be added to Prisma schema before migration
**How to avoid:** Run `npx auth@latest generate` first (adds models to schema.prisma), then `npx prisma migrate dev`. Admin plugin adds extra fields (role, banned, banReason, banExpiresAt) to the user table.
**Warning signs:** "Table does not exist" errors on login

### Pitfall 3: Next.js 16 proxy.ts vs middleware.ts
**What goes wrong:** middleware.ts still works but is deprecated, may break in future
**Why it happens:** Next.js 16 renamed middleware to proxy for clarity
**How to avoid:** Use `proxy.ts` with `export default function proxy()`. Same matcher config, same NextRequest/NextResponse API.
**Warning signs:** Deprecation warnings in Next.js console

### Pitfall 4: Neon Connection Strings -- Pooled vs Direct
**What goes wrong:** Prisma migrations fail with "prepared statement already exists"
**Why it happens:** Migrations need direct connection, not pooled (PgBouncer transaction mode)
**How to avoid:** Set both DATABASE_URL (pooled, with -pooler suffix) and DIRECT_URL (direct, no -pooler) in .env. Prisma schema uses `directUrl` for migrations.
**Warning signs:** Migration commands hanging or erroring

### Pitfall 5: Session Timeout Not Actually Enforced
**What goes wrong:** Client shows warning but session stays valid server-side
**Why it happens:** Better Auth session.expiresIn is server-side; client idle detection is separate
**How to avoid:** Client-side idle timer must ALSO call server to invalidate/refresh session. Set Better Auth `session.expiresIn` to match the configured timeout. Use `session.updateAge` to refresh active sessions.
**Warning signs:** Users can still access API after client-side "timeout"

### Pitfall 6: Invite-Only Flow with Better Auth
**What goes wrong:** Public users can register via the /api/auth/sign-up endpoint
**Why it happens:** Better Auth email/password signup is enabled by default
**How to avoid:** Set `emailAndPassword.disableSignUp: true` to block public registration. Use `auth.api.createUser()` (admin plugin) for invite-only user creation. Build a custom invitation flow: admin creates user -> email with signup link -> user sets password.
**Warning signs:** Unknown users appearing in the database

### Pitfall 7: Tailwind CSS 4 Color Format
**What goes wrong:** Colors look wrong, opacity modifiers don't work
**Why it happens:** Tailwind 4 uses OKLCH internally; older HSL format syntax changed
**How to avoid:** Define CSS variables with full `hsl()` wrapper in :root. Use `@theme inline` to map to Tailwind utilities. Test with `bg-primary/50` to verify opacity modifiers work.
**Warning signs:** Color picker in VS Code not working, colors appearing different than expected

## Code Examples

### Better Auth Client Setup
```typescript
// src/lib/auth-client.ts
import { createAuthClient } from "better-auth/react";
import { adminClient } from "better-auth/client/plugins";
import { emailOTPClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [adminClient(), emailOTPClient()],
});

export const {
  signIn,
  signUp,
  signOut,
  useSession,
} = authClient;
```

### Server-Side Session Check in Server Component
```typescript
// src/app/(app)/layout.tsx
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/login");
  }

  return (
    <div className="flex h-screen">
      <Sidebar user={session.user} />
      <main className="flex-1 overflow-auto">
        <Header user={session.user} />
        {children}
      </main>
    </div>
  );
}
```

### Role-Gated Page Content
```typescript
// src/app/(app)/admin/page.tsx
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export default async function AdminPage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  const hasAccess = await auth.api.userHasPermission({
    body: {
      userId: session!.user.id,
      permissions: { admin: ["access"] },
    },
  });

  if (!hasAccess.data?.success) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">Keine Berechtigung</h1>
          <p className="text-muted-foreground">
            Sie haben keine Berechtigung fuer diese Seite.
            Bitte kontaktieren Sie Ihren Administrator.
          </p>
        </div>
      </div>
    );
  }

  return <div>Admin-Bereich</div>;
}
```

### Prisma Schema with Better Auth + Admin Plugin
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
  output   = "../src/generated/prisma/client"
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

model User {
  id            String    @id @default(cuid())
  name          String
  email         String    @unique
  emailVerified Boolean   @default(false)
  image         String?
  role          String    @default("viewer")
  banned        Boolean?
  banReason     String?
  banExpiresAt  DateTime?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  sessions      Session[]
  accounts      Account[]

  @@map("user")
}

model Session {
  id        String   @id @default(cuid())
  expiresAt DateTime
  token     String   @unique
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  ipAddress String?
  userAgent String?
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@map("session")
}

model Account {
  id                    String    @id @default(cuid())
  accountId             String
  providerId            String
  userId                String
  user                  User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  accessToken           String?
  refreshToken          String?
  idToken               String?
  accessTokenExpiresAt  DateTime?
  refreshTokenExpiresAt DateTime?
  scope                 String?
  password              String?
  createdAt             DateTime  @default(now())
  updatedAt             DateTime  @updatedAt

  @@map("account")
}

model Verification {
  id         String    @id @default(cuid())
  identifier String
  value      String
  expiresAt  DateTime
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt

  @@map("verification")
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| middleware.ts | proxy.ts | Next.js 16 (Oct 2025) | Clearer network boundary, Node.js runtime (not Edge) |
| tailwind.config.js | CSS-first @theme | Tailwind CSS 4 (2025) | No JS config file, @theme inline directive |
| tailwindcss-animate | tw-animate-css | shadcn/ui v4 (Mar 2025) | Must use new animation package |
| forwardRef components | Function components + data-slot | React 19 / shadcn v4 | Simpler component signatures |
| Prisma Rust engine | Prisma TS engine | Prisma 7 (Dec 2025) | 90% smaller bundles, 3x faster, output moved from node_modules |
| NextAuth/Auth.js | Better Auth | 2024-2025 | Built-in RBAC, simpler plugin system, TS-native |
| @prisma/client import | @/generated/prisma/client | Prisma 7 | Generated code in project source, not node_modules |

**Deprecated/outdated:**
- `middleware.ts`: Renamed to `proxy.ts` in Next.js 16 (still works but deprecated)
- `tailwindcss-animate`: Replaced by `tw-animate-css`
- `experimental.ppr`: Removed in favor of `cacheComponents` config
- `next lint` command: Removed, use ESLint directly
- `toast` component in shadcn/ui: Replaced by `sonner`

## Open Questions

1. **Email Sending in Development**
   - What we know: Better Auth emailOTP plugin needs a `sendVerificationOTP` function. INFRA-05 (email sending) is Phase 15.
   - What's unclear: How to handle email in development/staging before Phase 15
   - Recommendation: Log OTP codes to console in development. Optionally use Resend or Nodemailer with a test SMTP server (like Ethereal) for staging. Keep the email sending function easily swappable.

2. **Better Auth Invitation Flow**
   - What we know: `emailAndPassword.disableSignUp: true` blocks public signup. Admin can create users with `auth.api.createUser()`.
   - What's unclear: Better Auth does not have a built-in "invitation" plugin. Custom flow needed.
   - Recommendation: Admin creates user via `createUser` (with temporary password) -> send invite email with login link -> user logs in and changes password. Or: create user without password, send link to set-password page with a verification token.

3. **Session Timeout Admin Configuration**
   - What we know: Better Auth `session.expiresIn` is set at server startup. CONTEXT.md says "configurable by Admin in settings."
   - What's unclear: Changing session timeout requires server restart with Better Auth's current API.
   - Recommendation: Store timeout setting in database. On session creation, use the database value. May need to override Better Auth's session handling or use a custom session update hook. For Phase 10, hardcode 8-hour default; make it Admin-configurable in Phase 15 (ADMIN-03).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (ships with create-next-app) or Jest (Next.js default) |
| Config file | `vitest.config.ts` or `jest.config.ts` -- Wave 0 setup |
| Quick run command | `npx vitest run --reporter=verbose` |
| Full suite command | `npx vitest run` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Email/password login creates session | integration | `npx vitest run src/__tests__/auth/login.test.ts -t "login"` | Wave 0 |
| AUTH-02 | Password reset via 6-digit OTP | integration | `npx vitest run src/__tests__/auth/password-reset.test.ts` | Wave 0 |
| AUTH-03 | Session expiry after configured timeout | unit | `npx vitest run src/__tests__/hooks/session-timeout.test.ts` | Wave 0 |
| AUTH-04 | 4 roles with tiered permissions | unit | `npx vitest run src/__tests__/auth/permissions.test.ts` | Wave 0 |
| AUTH-05 | Route/API role enforcement | integration | `npx vitest run src/__tests__/auth/route-protection.test.ts` | Wave 0 |
| UI-01 | FTAG design tokens applied | smoke | `npx vitest run src/__tests__/ui/theme.test.ts` | Wave 0 |
| UI-02 | Responsive layout renders | smoke | Manual -- visual check at 3 breakpoints | manual-only |
| UI-03 | Sidebar with red active item | smoke | Manual -- visual check | manual-only |
| UI-04 | Breadcrumbs render on all pages | unit | `npx vitest run src/__tests__/ui/breadcrumbs.test.ts` | Wave 0 |
| INFRA-01 | Next.js + Prisma + Neon connected | smoke | `npx vitest run src/__tests__/infra/database.test.ts` | Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run --reporter=verbose`
- **Per wave merge:** `npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `vitest.config.ts` -- test framework configuration
- [ ] `src/__tests__/auth/login.test.ts` -- covers AUTH-01
- [ ] `src/__tests__/auth/password-reset.test.ts` -- covers AUTH-02
- [ ] `src/__tests__/hooks/session-timeout.test.ts` -- covers AUTH-03
- [ ] `src/__tests__/auth/permissions.test.ts` -- covers AUTH-04
- [ ] `src/__tests__/auth/route-protection.test.ts` -- covers AUTH-05
- [ ] `src/__tests__/ui/theme.test.ts` -- covers UI-01
- [ ] `src/__tests__/ui/breadcrumbs.test.ts` -- covers UI-04
- [ ] `src/__tests__/infra/database.test.ts` -- covers INFRA-01
- [ ] Framework install: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`

## Sources

### Primary (HIGH confidence)
- [Better Auth Email/Password docs](https://better-auth.com/docs/authentication/email-password) -- signup, signin, password reset configuration
- [Better Auth Admin Plugin docs](https://better-auth.com/docs/plugins/admin) -- RBAC, createAccessControl, user management
- [Better Auth Email OTP Plugin docs](https://better-auth.com/docs/plugins/email-otp) -- 6-digit OTP, password reset flow
- [Better Auth Next.js Integration](https://better-auth.com/docs/integrations/next) -- route handler, proxy.ts, server-side session
- [Better Auth Options/Session Config](https://better-auth.com/docs/reference/options) -- expiresIn, updateAge, cookie settings
- [Better Auth Prisma Adapter](https://better-auth.com/docs/adapters/prisma) -- schema generation, Prisma 7 support
- [Next.js 16 Blog Post](https://nextjs.org/blog/next-16) -- proxy.ts, Turbopack, breaking changes, React 19.2
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) -- CSS-first config, @theme inline, tw-animate-css
- [Prisma 7 Announcement](https://www.prisma.io/blog/announcing-prisma-orm-7-0-0) -- TS engine, output location, performance
- [Neon Prisma Guide](https://neon.com/docs/guides/prisma) -- connection pooling, DATABASE_URL vs DIRECT_URL
- [Prisma + Better Auth + Next.js Guide](https://www.prisma.io/docs/guides/betterauth-nextjs) -- complete integration setup

### Secondary (MEDIUM confidence)
- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16) -- migration steps
- [Neon Connection Pooling docs](https://neon.com/docs/connect/connection-pooling) -- PgBouncer, transaction mode

### Tertiary (LOW confidence)
- Better Auth invite-only flow -- assembled from multiple community discussions, no official "invitation" plugin documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via official docs and recent releases
- Architecture: HIGH -- patterns from official documentation and integration guides
- Pitfalls: HIGH -- documented in official migration guides and community issues
- Invitation flow: MEDIUM -- requires custom implementation, no official plugin
- Session timeout configurability: MEDIUM -- server-side config is static; dynamic config needs custom solution

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable ecosystem, 30-day window)
