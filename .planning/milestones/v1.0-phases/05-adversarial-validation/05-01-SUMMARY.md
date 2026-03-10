---
phase: 05-adversarial-validation
plan: 01
subsystem: matching
tags: [adversarial, debate, opus, chain-of-thought, pydantic, asyncio]

# Dependency graph
requires:
  - phase: 04-product-matching-engine
    provides: MatchResult, MatchCandidate, DimensionScore schemas and matching pipeline
provides:
  - AdversarialResult schema with debate, CoT, and adjusted confidence
  - FOR/AGAINST German prompt templates for Opus debate calls
  - validate_single_position and validate_positions concurrent pipeline
  - Deterministic resolution with weighted dimension scoring
affects: [05-adversarial-validation, 06-gap-analysis]

# Tech tracking
tech-stack:
  added: []
  patterns: [adversarial-debate-pattern, deterministic-resolution, adaptive-verbosity-cot]

key-files:
  created:
    - backend/v2/schemas/adversarial.py
    - backend/v2/matching/adversarial_prompts.py
    - backend/v2/matching/adversarial.py
    - backend/tests/test_v2_adversarial.py
  modified:
    - backend/v2/matching/__init__.py

key-decisions:
  - "Deterministic resolution (weighted average) instead of third Opus API call for cost efficiency"
  - "Safety-critical dimension weighting: Brandschutz 2x, Masse 1.5x, Schallschutz 1.5x, Leistung 0.8x"
  - "FOR and AGAINST calls run in parallel within semaphore slot for throughput"
  - "Alternatives scored proportionally to Phase 4 confidence ratio vs best match"

patterns-established:
  - "Adversarial debate: FOR+AGAINST parallel Opus calls with deterministic resolution"
  - "Adaptive verbosity CoT: hoch (>0.9 score, 1 sentence) vs niedrig (<=0.9, detailed reasoning)"
  - "Semaphore(3) for Opus rate limit safety (lower than Phase 4 Sonnet Semaphore(5))"

requirements-completed: [MATC-05, MATC-07, MATC-08]

# Metrics
duration: 7min
completed: 2026-03-10
---

# Phase 5 Plan 01: Adversarial Debate Engine Summary

**FOR/AGAINST debate validation with Opus structured output, deterministic weighted resolution, and per-dimension chain-of-thought with adaptive verbosity**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-10T17:57:23Z
- **Completed:** 2026-03-10T18:04:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- AdversarialResult schema with ValidationStatus (bestaetigt/unsicher/abgelehnt), CandidateDebate, DimensionCoT, and ForArgument/AgainstArgument models for messages.parse structured output
- German adversarial prompts (FOR defends match, AGAINST challenges with safety-critical focus, resolution synthesizes verdict)
- Concurrent validation pipeline with asyncio.Semaphore(3) and parallel FOR+AGAINST per position
- 24 tests covering schema construction, prompt content, debate logic, resolution thresholds, adaptive verbosity, and concurrent processing

## Task Commits

Each task was committed atomically:

1. **Task 1: AdversarialResult schema and test scaffold** - `c79773f` (test)
2. **Task 2: Adversarial debate prompts and validation engine** - `195ded8` (feat)

## Files Created/Modified
- `backend/v2/schemas/adversarial.py` - ValidationStatus, DimensionCoT, CandidateDebate, AdversarialCandidate, AdversarialResult, ForArgument, AgainstArgument schemas
- `backend/v2/matching/adversarial_prompts.py` - FOR_SYSTEM_PROMPT, AGAINST_SYSTEM_PROMPT, FOR/AGAINST_USER_TEMPLATE, RESOLUTION_PROMPT
- `backend/v2/matching/adversarial.py` - validate_single_position, validate_positions, resolve_debate with weighted dimension scoring
- `backend/v2/matching/__init__.py` - Added adversarial exports
- `backend/tests/test_v2_adversarial.py` - 24 tests for schemas, prompts, debate, resolution, concurrency

## Decisions Made
- Deterministic resolution via weighted average of FOR/AGAINST dimension scores instead of a third API call (saves cost, sufficient for synthesizing two structured arguments)
- Safety-critical dimension weighting: Brandschutz 2x, Masse/Schallschutz 1.5x, Leistung 0.8x (reflects domain priority of fire safety over cosmetic features)
- FOR and AGAINST Opus calls run in parallel within same semaphore slot (2 calls but 1 slot since they're for the same position)
- Alternative candidates scored proportionally to their Phase 4 confidence relative to best match

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted test mock data for bestaetigt/unsicher thresholds**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Default mock dimension scores (0.85-0.95) averaged to ~0.89 after weighted resolution, never reaching 0.95 bestaetigt threshold
- **Fix:** Created parameterized mock helpers with explicit high/low dimension scores for threshold tests
- **Files modified:** backend/tests/test_v2_adversarial.py
- **Verification:** All 24 tests pass including bestaetigt (0.95+) and unsicher (<0.95) threshold tests
- **Committed in:** 195ded8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test data calibration fix, no scope change.

## Issues Encountered
- Pre-existing broken tests (test_offer.py, test_product_matcher.py) due to deleted v1 modules; out of scope, not related to Phase 5 changes
- .gitignore `test_*` pattern catches backend/tests/test_* files; used `git add -f` as established pattern

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AdversarialResult schema ready for Plan 02 (triple-check ensemble at <95% confidence)
- validate_single_position returns unsicher status for low confidence, ready for triple-check extension
- Pipeline integration into analyze endpoint planned for Plan 02

---
*Phase: 05-adversarial-validation*
*Completed: 2026-03-10*
