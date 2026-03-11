# Phase 17: Fix Dashboard & Email Data Access - Research

**Researched:** 2026-03-11
**Domain:** Data key mismatch between Python backend result shape and Next.js consumers
**Confidence:** HIGH

## Summary

Phase 17 fixes two data access bugs where Next.js code reads incorrect JSON keys from the analysis result stored in Prisma. The Python backend (via `product_matcher.py`) returns results with top-level keys `matched`, `partial`, `unmatched`, and `summary`. This is the exact shape saved to the Prisma `Analysis.result` JSON column via `saveAnalysisResult()`. However, two consumers read wrong keys:

1. **Dashboard `getMatchGapStatistics`** reads `result.matched_items` and `result.gap_items` -- these keys do not exist. It should read `result.matched` (+ `result.partial`) for match count and confidence, and `result.unmatched` for gap count.

2. **Email `sendAnalysisCompleteEmail`** was already fixed in Phase 16-01 to read `result.matched` and `result.unmatched` (correct keys). However, it currently only counts `matched` and `unmatched`, ignoring `partial` entries entirely. The `partial` entries should be included in the match count (they have matched products, just with gaps). Also, confidence calculation uses `Math.round((totalConfidence / matchCount) * 100)` which converts the 0-1 scale to a percentage, but the email template displays `{avgConfidence}%` -- so it would show e.g. "85%" which is correct. But the dashboard widget shows `Math.round(stats.avgConfidence * 100)%` -- meaning it expects a 0-1 scale value. This inconsistency needs alignment.

**Primary recommendation:** Fix `getMatchGapStatistics` to read `matched`/`partial`/`unmatched` keys; align confidence format between dashboard (0-1 scale) and email (percentage); include `partial` entries appropriately in both consumers.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-03 | Statistik-Widget: Gesamtzahl Matches, Gaps, Durchschnitts-Konfidenz | Fix `getMatchGapStatistics` to read correct keys (`matched`/`partial`/`unmatched` instead of `matched_items`/`gap_items`). Include `partial` entries in match count. Confidence is on 0-1 scale in source data. |
| INFRA-05 | E-Mail-Versand (Analyse-fertig-Benachrichtigung) | Fix `sendAnalysisCompleteEmail` to include `partial` entries in stats; align confidence format with the email template's `{avgConfidence}%` display. |
</phase_requirements>

## Architecture Patterns

### Data Flow: Python Backend -> Prisma -> Next.js Consumers

```
Python product_matcher.py
  returns: { matched: [], partial: [], unmatched: [], summary: {...} }
       |
       v  (SSE stream -> browser -> saveAnalysisResult server action)
Prisma Analysis.result (JSON column)
  stores: { matched: [...], partial: [...], unmatched: [...], summary: {...} }
       |
       +--> getMatchGapStatistics() reads from Prisma     [BROKEN - wrong keys]
       +--> sendAnalysisCompleteEmail() reads from Prisma  [PARTIAL FIX - missing partial]
       +--> StepResults component reads from state         [WORKS - uses correct keys]
```

### Exact Key Mapping (Verified from Source)

| Python key | TS AnalysisResult key | What it contains |
|------------|----------------------|------------------|
| `matched` | `matched` | Array of MatchEntry with status="matched", confidence 0-1 |
| `partial` | `partial` | Array of MatchEntry with status="partial", confidence 0-1 |
| `unmatched` | `unmatched` | Array of MatchEntry with status="unmatched", confidence=0 |
| `summary` | `summary` | Object with total_positions, matched_count, partial_count, unmatched_count, match_rate |

### Bug 1: getMatchGapStatistics (dashboard-actions.ts lines 88-119)

**Current (broken):**
```typescript
const matchedItems = result.matched_items;  // WRONG KEY - does not exist
// ...
const gapItems = result.gap_items;           // WRONG KEY - does not exist
```

**Correct:**
```typescript
const matched = result.matched;     // Array of MatchEntry (status=matched)
const partial = result.partial;     // Array of MatchEntry (status=partial)
const unmatched = result.unmatched; // Array of MatchEntry (status=unmatched)

// Matches = matched + partial (both have products assigned)
// Gaps = unmatched (no products found)
// Confidence: each entry has .confidence on 0-1 scale
```

**Decision needed:** Should `partial` entries count as matches or gaps?
- In the result_generator.py, partial entries have `matched_products` but also `gap_items`
- Recommendation: Count partial as a separate stat or include in matches (they DO have products), but also count their gap_items in total gaps. Simplest: matched + partial = "matches", unmatched = "gaps" (aligns with summary.matched_count + summary.partial_count).

### Bug 2: sendAnalysisCompleteEmail (analysis-actions.ts lines 160-176)

**Current (partially fixed in Phase 16-01):**
```typescript
const matchItems = Array.isArray(result?.matched) ? result.matched : [];
const gapItems = Array.isArray(result?.unmatched) ? result.unmatched : [];
// Missing: partial entries are ignored entirely
```

**Fix needed:**
- Include `partial` in match count (or add separate stat)
- Ensure confidence calculation matches what the email template expects

### Confidence Scale Inconsistency

| Consumer | Source confidence | Transformation | Display |
|----------|-----------------|----------------|---------|
| Dashboard StatisticsWidget | 0-1 (from MatchEntry) | `Math.round(stats.avgConfidence * 100)%` | Expects 0-1 input |
| Dashboard getMatchGapStatistics | 0-1 (from MatchEntry) | `Math.round((sum / count) * 100) / 100` | Returns 0-1 (e.g. 0.85) |
| Email sendAnalysisCompleteEmail | 0-1 (from MatchEntry) | `Math.round((total / count) * 100)` | Returns percentage (e.g. 85) |
| Email template | percentage | `{avgConfidence}%` | Displays "85%" |

The dashboard path is consistent (0-1 throughout). The email path correctly converts to percentage for display. Both are fine -- they just need to be using the right source keys.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statistics aggregation | Custom SQL aggregation | Read from result JSON + summary sub-object | Summary already has counts; confidence needs per-entry scan |

**Key insight:** The `summary` sub-object in the result already contains `matched_count`, `partial_count`, `unmatched_count`, and `match_rate`. The `getMatchGapStatistics` function could use these directly for counts instead of re-counting array lengths. However, confidence still requires iterating entries.

## Common Pitfalls

### Pitfall 1: Missing partial entries
**What goes wrong:** Only counting `matched` and `unmatched`, ignoring `partial` entries
**Why it happens:** The email fix in Phase 16-01 only addressed `matched`/`unmatched` keys
**How to avoid:** Always consider all three arrays: `matched`, `partial`, `unmatched`
**Warning signs:** Gap count too low, match count too low, total does not add up

### Pitfall 2: Null/undefined result field
**What goes wrong:** `analysis.result` can be null for running/failed analyses
**Why it happens:** result is only populated when analysis completes
**How to avoid:** Already handled -- `getMatchGapStatistics` filters for `status: 'completed', result: { not: null }`
**Warning signs:** TypeError on null access

### Pitfall 3: Prisma JSON type casting
**What goes wrong:** Prisma Json field returns `Prisma.JsonValue` which needs casting
**Why it happens:** Prisma 7 stricter JSON typing
**How to avoid:** Cast to `Record<string, unknown>` as currently done; check Array.isArray before accessing

### Pitfall 4: Confidence scale mismatch between consumers
**What goes wrong:** Dashboard expects 0-1, email expects percentage -- mixing them up
**Why it happens:** Two separate implementations with different conventions
**How to avoid:** Keep dashboard returning 0-1 (widget multiplies by 100), keep email returning percentage (template displays directly)

## Code Examples

### Corrected getMatchGapStatistics

```typescript
// Source: analysis of current codebase
export async function getMatchGapStatistics(): Promise<MatchGapStatistics> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const completedAnalyses = await prisma.analysis.findMany({
    where: { status: 'completed', result: { not: null } },
    select: { result: true },
    take: 100,
    orderBy: { endedAt: 'desc' },
  });

  let totalMatches = 0;
  let totalGaps = 0;
  let confidenceSum = 0;
  let confidenceCount = 0;

  for (const analysis of completedAnalyses) {
    if (!analysis.result || typeof analysis.result !== 'object') continue;
    const result = analysis.result as Record<string, unknown>;

    // Count matched entries (fully matched products)
    const matched = Array.isArray(result.matched) ? result.matched : [];
    totalMatches += matched.length;
    for (const item of matched) {
      if (item && typeof item === 'object' && 'confidence' in item) {
        const conf = (item as Record<string, unknown>).confidence;
        if (typeof conf === 'number') {
          confidenceSum += conf;
          confidenceCount++;
        }
      }
    }

    // Count partial entries (have products but also gaps)
    const partial = Array.isArray(result.partial) ? result.partial : [];
    totalMatches += partial.length;
    for (const item of partial) {
      if (item && typeof item === 'object' && 'confidence' in item) {
        const conf = (item as Record<string, unknown>).confidence;
        if (typeof conf === 'number') {
          confidenceSum += conf;
          confidenceCount++;
        }
      }
    }

    // Count unmatched entries (gaps)
    const unmatched = Array.isArray(result.unmatched) ? result.unmatched : [];
    totalGaps += unmatched.length;
  }

  const avgConfidence =
    confidenceCount > 0 ? Math.round((confidenceSum / confidenceCount) * 100) / 100 : 0;

  return { totalMatches, totalGaps, avgConfidence };
}
```

### Corrected sendAnalysisCompleteEmail stats extraction

```typescript
// Source: analysis of current codebase
const result = analysis.result as Record<string, unknown> | null;
const matched = Array.isArray(result?.matched) ? result.matched : [];
const partial = Array.isArray(result?.partial) ? result.partial : [];
const unmatched = Array.isArray(result?.unmatched) ? result.unmatched : [];

const matchCount = matched.length + partial.length;
const gapCount = unmatched.length;

let avgConfidence = 0;
const allMatchedItems = [...matched, ...partial];
if (allMatchedItems.length > 0) {
  const totalConfidence = allMatchedItems.reduce(
    (sum: number, item: Record<string, unknown>) =>
      sum + (typeof item.confidence === 'number' ? item.confidence : 0),
    0
  );
  avgConfidence = Math.round((totalConfidence / allMatchedItems.length) * 100);
}
```

## Files to Modify

| File | What to Change | Lines |
|------|---------------|-------|
| `frontend/src/lib/actions/dashboard-actions.ts` | Fix `getMatchGapStatistics`: change `matched_items`->`matched`, `gap_items`->`unmatched`, add `partial` | 88-119 |
| `frontend/src/lib/actions/analysis-actions.ts` | Fix `sendAnalysisCompleteEmail`: add `partial` to stats | 160-176 |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.x |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-03 | getMatchGapStatistics reads correct keys and produces correct counts/confidence | unit | `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx -x` | Stub only (it.todo) |
| INFRA-05 | sendAnalysisCompleteEmail includes partial entries and correct stats | unit | `cd frontend && npx vitest run src/__tests__/email/analysis-complete.test.tsx -x` | No |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run src/__tests__/dashboard/statistics.test.tsx src/__tests__/email/analysis-complete.test.tsx -x`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/__tests__/dashboard/statistics.test.tsx` -- implement tests (currently stubs with it.todo)
- [ ] `frontend/src/__tests__/email/analysis-complete.test.tsx` -- covers INFRA-05 email stats

## Sources

### Primary (HIGH confidence)
- Direct source code analysis of:
  - `backend/services/product_matcher.py` lines 86-94, 114-117 -- confirmed result shape `{matched, partial, unmatched, summary}`
  - `frontend/src/lib/actions/dashboard-actions.ts` lines 88-119 -- confirmed wrong keys `matched_items`, `gap_items`
  - `frontend/src/lib/actions/analysis-actions.ts` lines 147-196 -- confirmed email reads `matched`/`unmatched` (fixed in Phase 16-01) but misses `partial`
  - `frontend/src/components/analysis/types.ts` lines 32-64 -- confirmed MatchEntry.confidence is 0-1 scale, AnalysisResult has matched/partial/unmatched/summary
  - `frontend/src/app/(app)/dashboard/statistics-widget.tsx` lines 7-35 -- confirmed widget expects 0-1 confidence value
  - `frontend/src/components/analysis/step-progress.tsx` line 65 -- confirmed SSE result is saved directly to Prisma

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all relevant files read and verified
- Architecture: HIGH - data flow traced end-to-end from Python through SSE to Prisma to consumers
- Pitfalls: HIGH - bugs are clear key mismatches, verified by reading actual source

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- this is a bug fix, not dependent on external libraries)
