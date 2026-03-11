# Retrospective

## Milestone: v1.0 — KI-Angebotserstellung v2 Pipeline

**Shipped:** 2026-03-10
**Phases:** 9 | **Plans:** 21

### What Was Built
- Multi-format document parsing (PDF/DOCX/XLSX) with Pydantic pipeline schemas
- 3-pass extraction (structural + AI semantic + cross-reference validation) with deduplication
- Cross-document intelligence with enrichment and AI conflict resolution
- TF-IDF + Claude AI product matching against 891-product catalog (6 dimensions)
- Adversarial FOR/AGAINST debate with triple-check ensemble
- Categorized gap analysis with severity ratings and alternative suggestions
- Professional 4-sheet Excel output with color coding and chain-of-thought reasoning
- End-to-end pipeline with plausibility checks, SSE streaming, and React frontend

### What Worked
- Phase-by-phase approach allowed verifiable incremental progress
- Pydantic schemas defined upfront (Phase 1) prevented integration issues later
- Adversarial validation architecture caught real false positives
- German-language prompts matched domain language, improving extraction quality
- Safety-critical dimension weighting (Brandschutz 2x) prevented dangerous false confirms
- TF-IDF pre-filter kept API costs manageable while maintaining recall

### What Was Inefficient
- Phase 9 (frontend wiring) was essentially gap closure for v1.0 audit — should have been planned from the start
- Phase 3 human verification items remain pending (need live API key testing)
- SSE cross-thread issue discovered late in integration — caught by audit, not by phase verification
- ROADMAP.md plan checkboxes not consistently updated by executors (cosmetic issue)

### Patterns Established
- Enum+Freitext pattern for all domain classifications
- Safety cap pipeline: apply_safety_caps → set_hat_match → limit_alternatives
- Three-track processing: bestaetigt (filtered), unsicher (full), abgelehnt (text only)
- Deterministic resolution via weighted average instead of additional AI calls
- Lazy try/except imports for optional dependencies (graceful degradation)
- 500ms progress throttle to prevent SSE flooding

### Key Lessons
- Define frontend wiring as explicit phase in initial roadmap (not gap closure)
- asyncio.Queue is not thread-safe for cross-thread communication — use loop.call_soon_threadsafe
- messages.parse() structured output eliminates manual JSON parsing but requires Pydantic v2 compatibility
- TF-IDF top_k=50 is sufficient for 891-product catalog; top_k=80 for triple-check wider pool

### Cost Observations
- Model mix: Opus for adversarial debate only, Sonnet for all other AI calls
- Sessions: 9 execution sessions + 2 gap closure + 1 audit
- Notable: Deterministic adversarial resolution saved ~33% on Opus calls vs. third-call approach

---

## Milestone: v2.0 — AI Tender Matcher — Web-Oberflaeche & Platform

**Shipped:** 2026-03-11
**Phases:** 9 | **Plans:** 26

### What Was Built
- Next.js 16 SaaS app with Better Auth RBAC (4 roles), Prisma 7/Neon DB, FTAG Rot/Weiss design system
- BFF proxy layer connecting Next.js to Python/FastAPI with service auth and SSE streaming
- Vercel Blob file uploads with presigned URLs, project CRUD with history/archiving/sharing
- 5-step analysis wizard with SSE progress and full results view (filtering, detail expansion, Excel export)
- Product catalog upload, browse, search, versioning, and individual product CRUD
- Admin panel: user management, audit log, system settings, dashboard KPIs, keyboard shortcuts, email notifications
- 3 gap closure phases (16, 17, 18) fixing cross-phase integration issues found by audit

### What Worked
- Yolo mode with fine granularity enabled rapid execution (88 min for 26 plans, 3.9 min avg)
- Phase-by-phase approach continued to allow verifiable incremental progress
- Better Auth RBAC plugin gave clean 4-role system out of the box
- BFF pattern cleanly separated concerns (CRUD via proxy, SSE direct)
- Milestone audit caught 6 integration gaps across 2 rounds — all fixed before completion
- Gap closure phases (16-18) were quick and surgical (1 plan each, 2-3 min)

### What Was Inefficient
- 3 gap closure phases needed post-audit — ideally integration wiring should be verified during execution
- 8 test stub files (it.todo) never got real assertions — testing deferred to hypothetical future
- Excel download payload structure issue (RSLT-04) not caught until second audit
- Config thresholds from wizard not forwarded to Python — wizard step 3 is cosmetic only
- Phase 14 compareVersions action and Phase 15 getActivityFeed are dead code

### Patterns Established
- Server Actions pattern: auth.api.getSession -> userHasPermission -> prisma query -> revalidatePath
- Split page into server (page.tsx) + client (client.tsx) for optimal hydration
- base-ui component API quirks documented (onValueChange unions, render prop vs asChild)
- Manual migration SQL for Neon DB (prisma migrate dev hangs on remote DB)
- it.todo() pattern for test stubs (Vitest marks as skipped)
- Shared helper pattern for code deduplication (e.g., _build_catalog_index_from_df)

### Key Lessons
- Milestone audit is essential — caught 6 real integration gaps that would have been production bugs
- base-ui (shadcn v4 foundation) has different API patterns than Radix — must check docs
- Prisma 7 has stricter JSON typing (Prisma.InputJsonValue cast needed)
- Better Auth userHasPermission uses 'permissions' (plural) key, not 'permission'
- SSE cannot be reliably proxied through Vercel — direct browser-to-Python connection is the right architecture

### Cost Observations
- Model mix: 100% Sonnet for all AI calls (quality profile)
- Sessions: ~12 execution sessions + 3 gap closure + 2 audits
- Notable: 88 min total execution for full SaaS platform — excellent velocity at 3.9 min/plan

---

## Cross-Milestone Trends

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Phases | 9 | 9 |
| Plans | 21 | 26 |
| Timeline | 8 days | 10 days |
| Requirements | 38/38 | 42/42 |
| Gap closures | 2 phases | 3 phases (16, 17, 18) |
| Audit status | tech_debt | tech_debt |
| Execution time | N/A | 88 min |
| Avg plan time | N/A | 3.9 min |
