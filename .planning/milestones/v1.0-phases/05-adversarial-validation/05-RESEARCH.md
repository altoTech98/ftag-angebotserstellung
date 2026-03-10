# Phase 5: Adversarial Validation - Research

**Researched:** 2026-03-10
**Domain:** AI adversarial debate pattern, Claude Opus structured outputs, concurrent API orchestration
**Confidence:** HIGH

## Summary

Phase 5 adds an adversarial validation layer on top of Phase 4's product matching. Every match undergoes a debate-format challenge (FOR/AGAINST arguments via two separate Opus API calls), followed by a resolution step. Matches falling below 95% confidence after adversarial review trigger a triple-check ensemble with wider candidate pool and inverted prompt strategy.

The technical challenge is primarily prompt engineering and pipeline orchestration -- the infrastructure patterns (asyncio.Semaphore, messages.parse with Pydantic, German prompts) are already established in Phase 4. The key risks are API cost (2-4 Opus calls per position) and rate limit management (Opus shares rate limits across all 4.x versions).

**Primary recommendation:** Build adversarial validation as a separate module (`adversarial.py` + `adversarial_prompts.py`) with its own Pydantic schemas, called inline after Phase 4 matching in the analyze endpoint. Use `asyncio.Semaphore(3)` for Opus calls (lower than Phase 4's 5 due to Opus being more expensive and sharing rate limits).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Debate format: two separate Opus API calls per position -- one argues FOR the match, one argues AGAINST
- A third lightweight resolution step determines the final verdict with adjusted confidence
- Input: same candidates + Phase 4 match result (no fresh TF-IDF search)
- Scope: ALL positions go through adversarial validation (per MATC-05: "every match")
- Model: Claude Opus for both FOR and AGAINST calls
- Full adversarial debate on best match AND up to 3 alternatives -- each candidate gets its own FOR/AGAINST reasoning (per MATC-08)
- Trigger for triple-check: post-adversarial confidence drops below 95%
- Triple-check strategy: ensemble of BOTH approaches -- wider candidate pool (top 80 instead of 30-50 via relaxed TF-IDF) AND inverted prompt (requirement-centric instead of product-centric)
- Model: Opus for both ensemble passes
- Take the higher-confidence result from the two approaches
- If still below 95% after triple-check: flag as 'unsicher' (uncertain match), keep best match found across all passes
- Language: German (consistent with all prompts and domain vocabulary)
- Structure: per-dimension reasoning step + final summary synthesis
- Verbosity: adaptive -- brief (1 sentence) for high-confidence dimensions (>90%), detailed (2-3 sentences) for low-confidence or mismatched dimensions
- Adversarial debate reasoning (FOR/AGAINST arguments) fully stored and visible in output
- Separate AdversarialResult schema linked to MatchResult by positions_nr (MatchResult stays untouched)
- Pipeline position: inline after Phase 4 matching in analyze endpoint -- single call returns fully validated results
- Concurrency: asyncio.Semaphore pattern (like Phase 4) for parallel Opus calls across positions

### Claude's Discretion
- Exact prompt design for FOR/AGAINST debate calls
- Resolution logic for combining FOR/AGAINST into final verdict
- Semaphore limit for Opus calls (likely lower than Phase 4's 5 due to Opus rate limits)
- Exact TF-IDF relaxation parameters for wider-pool triple-check
- Internal data structures for AdversarialResult schema
- How to structure the inverted (requirement-centric) prompt for triple-check

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MATC-05 | System fuehrt Adversarial Double-Check durch (zweiter AI-Call versucht aktiv jeden Match zu widerlegen) | Debate pattern: FOR call validates, AGAINST call challenges. Opus 4.6 with messages.parse() for structured output. asyncio.Semaphore(3) for concurrent Opus calls. |
| MATC-06 | System fuehrt Triple-Check durch bei Konfidenz <95% (dritter AI-Durchlauf mit alternativem Prompt) | Ensemble of wider-pool (top_k=80 TF-IDF) + inverted requirement-centric prompt. Take higher-confidence result. Flag 'unsicher' if still <95%. |
| MATC-07 | System begruendet jeden Match mit Chain-of-Thought (Schritt-fuer-Schritt-Argumentation) | Per-dimension CoT in AdversarialResult schema with adaptive verbosity. FOR/AGAINST debate arguments fully stored. German language throughout. |
| MATC-08 | System listet bei mehreren moeglichen Produkten alle auf mit Begruendung | Full debate (FOR/AGAINST) on best match AND up to 3 alternatives. Each candidate gets individual confidence scores and reasoning in AdversarialResult. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.49.0 (project uses 0.42.0) | Claude Opus API calls via messages.parse() | Already in use for Phase 4 Sonnet calls; same pattern works for Opus |
| pydantic | v2 | AdversarialResult schema with structured output | Already used for all Phase 1-4 schemas; messages.parse() requires it |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Semaphore-based concurrency for parallel Opus calls | Every adversarial validation run (all positions in parallel) |
| logging | stdlib | API call counting and cost visibility | Track Opus call volume per analysis run |

### No New Dependencies Required
Phase 5 uses exclusively libraries already in the project. No new pip installs needed.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/
  matching/
    adversarial.py            # Core adversarial validation logic
    adversarial_prompts.py    # FOR/AGAINST/resolution/triple-check prompts
    ai_matcher.py             # Existing Phase 4 (untouched)
    tfidf_index.py            # Existing (reused for wider-pool triple-check)
  schemas/
    adversarial.py            # AdversarialResult, DebateArgument, etc.
    matching.py               # Existing Phase 4 (untouched)
  routers/
    analyze_v2.py             # Extended to call adversarial after matching
```

### Pattern 1: Debate-Format Adversarial Validation
**What:** Two independent Opus calls per position -- one argues FOR, one AGAINST the match. A resolution step synthesizes the verdict.
**When to use:** Every matched position (MATC-05 requires "every match").
**Structure:**

```python
# Pseudocode for the adversarial pipeline per position
async def validate_single_position(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    position: ExtractedDoorPosition,
    candidates: list[dict],
    semaphore: asyncio.Semaphore,
) -> AdversarialResult:
    async with semaphore:
        # Step 1: FOR argument (argues match is correct)
        for_result = await asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=FOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": for_user_content}],
            output_format=ForArgument,
        )

        # Step 2: AGAINST argument (actively tries to disprove)
        against_result = await asyncio.to_thread(
            client.messages.parse,
            model="claude-opus-4-6",
            max_tokens=4096,
            system=AGAINST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": against_user_content}],
            output_format=AgainstArgument,
        )

        # Step 3: Resolution (lightweight -- can use Sonnet or Opus)
        resolution = resolve_debate(for_result, against_result, match_result)

        # Step 4: Triple-check if confidence < 0.95
        if resolution.adjusted_confidence < 0.95:
            resolution = await triple_check(...)

        return build_adversarial_result(resolution, for_result, against_result)
```

### Pattern 2: Triple-Check Ensemble
**What:** When post-adversarial confidence < 95%, run two independent recovery strategies and take the better result.
**When to use:** Only for positions that fail the adversarial review.
**Approach:**
1. **Wider pool:** Re-run TF-IDF with `top_k=80` (instead of 50) and send to Opus for fresh matching
2. **Inverted prompt:** Requirement-centric matching (start from requirement dimensions, search for matching products instead of product-centric evaluation)
3. Take the higher-confidence result from both approaches
4. If still below 95%: flag as `validation_status="unsicher"`, keep best result found

### Pattern 3: Adaptive Chain-of-Thought
**What:** Per-dimension reasoning that adapts verbosity based on confidence.
**When to use:** All adversarial results (MATC-07).
**Logic:**
- Dimension score > 0.9: 1 sentence brief reasoning
- Dimension score <= 0.9: 2-3 sentences detailed reasoning explaining gaps/concerns
- Final synthesis summarizes across all dimensions

### Pattern 4: AdversarialResult Linked by positions_nr
**What:** Separate schema that references MatchResult without modifying it.
**When to use:** Pipeline output -- MatchResult remains Phase 4's output, AdversarialResult is Phase 5's addition.

```python
class AdversarialResult(BaseModel):
    positions_nr: str  # Links to MatchResult.positions_nr
    validation_status: Literal["bestaetigt", "unsicher", "abgelehnt"]
    adjusted_confidence: float  # Post-adversarial confidence
    bester_match_produkt_id: Optional[str]  # May differ from Phase 4
    for_arguments: list[CandidateDebate]
    against_arguments: list[CandidateDebate]
    resolution_reasoning: str
    per_dimension_cot: list[DimensionCoT]
    alternative_candidates: list[AdversarialCandidate]
    triple_check_used: bool
    triple_check_reasoning: Optional[str]
    api_calls_count: int  # Cost visibility
```

### Anti-Patterns to Avoid
- **Modifying MatchResult schema:** Phase 4 output must remain untouched. AdversarialResult is a separate parallel structure.
- **Running FOR and AGAINST sequentially per position:** Both can run in parallel within the semaphore slot since they are independent.
- **Using Sonnet for adversarial calls:** CONTEXT.md locks Opus for debate. Only resolution step could potentially use Sonnet.
- **Skipping positions without a match:** Even `hat_match=False` positions need adversarial review to potentially find better candidates.
- **Unbounded concurrency on Opus calls:** Opus shares rate limits across all 4.x versions. Must use semaphore.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured Opus output | Manual JSON parsing from Opus response | `messages.parse(output_format=PydanticModel)` | Guaranteed schema compliance, no parse errors |
| Rate limit handling | Custom retry logic | `asyncio.Semaphore(3)` + let SDK handle 429 retries | SDK has built-in retry with exponential backoff |
| TF-IDF wider search | New search index for triple-check | `tfidf_index.search(position, top_k=80)` | Existing index supports any top_k value |
| Confidence calculation | Custom weighted average | Let Opus calculate in structured output | AI can reason about multi-dimensional confidence holistically |

## Common Pitfalls

### Pitfall 1: Opus Rate Limit Exhaustion
**What goes wrong:** With 2 Opus calls per position and potentially 20+ positions, that is 40+ Opus calls in rapid succession, easily exceeding Tier 1-2 RPM limits.
**Why it happens:** Opus 4.x shares a combined rate limit (50 RPM at Tier 1, 1000 RPM at Tier 2). Phase 4 Sonnet calls don't consume the Opus quota, but adversarial calls do.
**How to avoid:** Use `asyncio.Semaphore(3)` to limit parallel Opus calls. At 3 concurrent, with ~5-10 seconds per call, throughput is ~18-36 calls/minute -- safe for Tier 2+.
**Warning signs:** 429 errors from Anthropic API, `retry-after` headers in responses.

### Pitfall 2: AGAINST Prompt Too Aggressive
**What goes wrong:** The AGAINST argument finds flaws in everything, causing all matches to fail adversarial review and trigger triple-check for every position.
**Why it happens:** An overly aggressive AGAINST prompt that penalizes minor mismatches.
**How to avoid:** Calibrate AGAINST prompt to focus on safety-critical dimensions (Brandschutz, Schallschutz, Masse) and only penalize genuine specification mismatches, not cosmetic differences. Include explicit instruction: "Minor differences in Leistung or Oberflaechenausfuehrung should NOT lead to rejection."
**Warning signs:** >50% of positions triggering triple-check.

### Pitfall 3: Resolution Step Ignoring Domain Knowledge
**What goes wrong:** Resolution always sides with AGAINST because it sounds more authoritative, or always sides with FOR because confidence was initially high.
**Why it happens:** Resolution prompt lacks domain-specific weighting rules.
**How to avoid:** Resolution prompt must reference domain knowledge: Brandschutz hierarchy (EI30 < EI60 < EI90), measurement tolerances (+-10mm for Masse), and that higher fire class always satisfies lower requirement.
**Warning signs:** Resolution consistently produces same verdict regardless of debate quality.

### Pitfall 4: Token Budget Overflow for Large Position Sets
**What goes wrong:** With 30+ positions, each generating 4+ Opus calls with detailed CoT, total token usage explodes (potentially >1M output tokens per analysis).
**Why it happens:** Opus output at $25/MTok, detailed reasoning for each candidate across all dimensions.
**How to avoid:** Monitor and log API call counts + token usage per run. Cap max_tokens appropriately (4096 for debate, 2048 for resolution). Budget estimate: ~3K output tokens per debate call x 2 calls x 20 positions = 120K output tokens = ~$3 per analysis run for debate alone.
**Warning signs:** Analysis cost exceeding $10 per run.

### Pitfall 5: Triple-Check Creating Infinite Loops
**What goes wrong:** Triple-check finds a different best match, which then also fails adversarial review if re-validated.
**Why it happens:** Not having a clear "one-shot" triple-check policy.
**How to avoid:** Triple-check is exactly one additional pass (no recursive validation). Take the best result across all passes, flag as 'unsicher' if still below 95%.
**Warning signs:** N/A -- prevent by design.

## Code Examples

### AdversarialResult Schema Design

```python
# Source: Project convention (Pydantic v2 with messages.parse)
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field

class ValidationStatus(str, Enum):
    BESTAETIGT = "bestaetigt"      # Confirmed at 95%+
    UNSICHER = "unsicher"           # Best effort but <95%
    ABGELEHNT = "abgelehnt"        # No viable match found

class DimensionCoT(BaseModel):
    dimension: str = Field(description="Dimension name (Masse, Brandschutz, etc.)")
    score: float = Field(description="Adjusted score after adversarial review")
    reasoning: str = Field(description="Chain-of-thought reasoning for this dimension")
    confidence_level: str = Field(description="'hoch' or 'niedrig' for adaptive verbosity")

class CandidateDebate(BaseModel):
    produkt_id: str
    produkt_name: str
    for_argument: str = Field(description="Arguments supporting this match")
    against_argument: str = Field(description="Arguments challenging this match")
    for_confidence: float
    against_confidence: float

class AdversarialCandidate(BaseModel):
    produkt_id: str
    produkt_name: str
    adjusted_confidence: float
    dimension_scores: list[DimensionCoT]
    reasoning_summary: str

class AdversarialResult(BaseModel):
    positions_nr: str
    validation_status: ValidationStatus
    adjusted_confidence: float
    bester_match: Optional[AdversarialCandidate] = None
    alternative_candidates: list[AdversarialCandidate] = Field(default_factory=list)
    debate: list[CandidateDebate] = Field(default_factory=list)
    resolution_reasoning: str = Field(description="Final synthesis explaining the verdict")
    triple_check_used: bool = False
    triple_check_method: Optional[str] = None
    triple_check_reasoning: Optional[str] = None
    api_calls_count: int = Field(default=2, description="Number of Opus API calls used")
```

### FOR Prompt Structure (German)

```python
FOR_SYSTEM_PROMPT = """\
Du bist ein Experte fuer FTAG-Tuereprodukte und argumentierst FUER die vorgeschlagene Produktzuordnung.

Deine Aufgabe: Finde alle Gruende, warum das zugeordnete Produkt die richtige Wahl ist.

## Argumentation pro Dimension:
Fuer jede der 6 Dimensionen (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung):
- Score > 0.9: Kurze Bestaetigung (1 Satz)
- Score <= 0.9: Detaillierte Argumentation (2-3 Saetze) warum das Produkt trotzdem passt

## Regeln:
- Beruecksichtige Brandschutz-Hierarchie: hoehere Klasse erfuellt niedrigere (EI60 erfuellt EI30)
- Masse-Toleranz: +-10mm ist akzeptabel
- Schallschutz: hoeherer dB-Wert erfuellt niedrigeren
- Argumentiere ehrlich -- wenn eine Dimension schlecht passt, sage es
"""
```

### AGAINST Prompt Structure (German)

```python
AGAINST_SYSTEM_PROMPT = """\
Du bist ein kritischer Pruefer fuer FTAG-Produktzuordnungen und versuchst aktiv, die vorgeschlagene Zuordnung zu widerlegen.

Deine Aufgabe: Finde alle Gruende, warum das zugeordnete Produkt NICHT die richtige Wahl sein koennte.

## Pruefung pro Dimension:
Fuer jede der 6 Dimensionen (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung):
- Suche nach konkreten Spezifikations-Abweichungen
- Pruefe ob bessere Kandidaten uebersehen wurden
- Identifiziere fehlende oder unvollstaendige Informationen

## Schwerpunkte (sicherheitskritisch):
- Brandschutz: Stimmt die Klasse exakt? Ist VKF-Nummer vorhanden?
- Masse: Passt das Lichtmass wirklich? Keine Ueberschreitung?
- Schallschutz: Wird der geforderte dB-Wert erreicht?

## Regeln:
- Kleinere Abweichungen bei Leistung/Oberflaeche sind KEIN Ablehnungsgrund
- Fokus auf sicherheitskritische und normative Abweichungen
- Schlage konkret bessere Alternativen vor wenn vorhanden
"""
```

### Concurrent Adversarial Execution

```python
# Source: Phase 4 pattern (ai_matcher.py) adapted for Opus
ADVERSARIAL_MAX_CONCURRENT = 3  # Lower than Phase 4's 5 for Opus

async def validate_positions(
    client: anthropic.Anthropic,
    match_results: list[MatchResult],
    positions: list[ExtractedDoorPosition],
    candidates_map: dict[str, list[dict]],
) -> list[AdversarialResult]:
    semaphore = asyncio.Semaphore(ADVERSARIAL_MAX_CONCURRENT)

    async def _validate_one(mr: MatchResult, pos: ExtractedDoorPosition):
        async with semaphore:
            # FOR and AGAINST can run in parallel within the slot
            for_task = asyncio.to_thread(
                client.messages.parse,
                model="claude-opus-4-6",
                # ... FOR prompt
            )
            against_task = asyncio.to_thread(
                client.messages.parse,
                model="claude-opus-4-6",
                # ... AGAINST prompt
            )
            for_result, against_result = await asyncio.gather(for_task, against_task)
            # Resolution + potential triple-check
            return resolve_and_build_result(for_result, against_result, mr, pos)

    tasks = [
        _validate_one(mr, pos)
        for mr, pos in zip(match_results, positions)
    ]
    return list(await asyncio.gather(*tasks))
```

### Analyze Endpoint Integration

```python
# In analyze_v2.py, after matching block:
if _ADVERSARIAL_AVAILABLE and match_results:
    adversarial_results = await validate_positions(
        client=client,
        match_results=match_results,
        positions=result.positionen,
        candidates_map=candidates_map,
    )
    response["adversarial_results"] = [
        ar.model_dump() for ar in adversarial_results
    ]
    response["total_confirmed"] = sum(
        1 for ar in adversarial_results
        if ar.validation_status == ValidationStatus.BESTAETIGT
    )
    response["total_uncertain"] = sum(
        1 for ar in adversarial_results
        if ar.validation_status == ValidationStatus.UNSICHER
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude Opus 4 ($15/$75 per MTok) | Claude Opus 4.6 ($5/$25 per MTok) | Feb 2026 | 3x cheaper -- makes adversarial viable for production |
| `client.beta.messages.parse()` | `client.messages.parse()` | Late 2025 | No longer beta; stable API for structured outputs |
| `response.parsed` | `response.parsed_output` | SDK update | Note: project uses SDK 0.42.0 with `.parsed` -- verify compatibility |

**Model ID for Opus:** `claude-opus-4-6` (alias), full ID `claude-opus-4-6-20260205`

**Pricing for Phase 5 workload estimate:**
- Per position: ~2 Opus calls (debate) + 1 resolution = ~6K input + ~6K output tokens
- 20 positions: ~120K input + ~120K output tokens
- Cost: ~$0.60 input + ~$3.00 output = ~$3.60 per analysis
- With triple-check (assume 30% trigger): add ~$2.00 = ~$5.60 per analysis
- Prompt caching can reduce input cost by 90% for system prompts

**Rate Limits (Opus 4.x combined):**

| Tier | RPM | ITPM | OTPM |
|------|-----|------|------|
| 1 | 50 | 30,000 | 8,000 |
| 2 | 1,000 | 450,000 | 90,000 |
| 3 | 2,000 | 800,000 | 160,000 |
| 4 | 4,000 | 2,000,000 | 400,000 |

At Tier 1 (50 RPM), 40+ Opus calls per analysis is tight. Semaphore(3) with ~5s per call = ~36 calls/min, which fits.
At Tier 2+, no concern.

## Open Questions

1. **SDK Version Compatibility**
   - What we know: Project uses anthropic SDK 0.42.0, which works with `messages.parse()` and `response.parsed` for Sonnet
   - What's unclear: Whether 0.42.0 supports Opus 4.6 model ID or if an upgrade is needed
   - Recommendation: Test with current SDK first; upgrade to >=0.49.0 only if model ID is rejected. The `response.parsed` vs `response.parsed_output` attribute may also differ by version.

2. **AGAINST Prompt Calibration**
   - What we know: Over-aggressive AGAINST prompts will cause excessive triple-checks
   - What's unclear: Exact threshold for what counts as a "real" flaw vs cosmetic difference
   - Recommendation: Start conservative (focus on safety-critical dimensions), tune based on real tender data. Blocker flag in STATE.md already notes this.

3. **Resolution Step Model Choice**
   - What we know: CONTEXT.md says "lightweight resolution step" but also "Opus for both FOR and AGAINST"
   - What's unclear: Whether resolution must also use Opus or can use Sonnet to save cost
   - Recommendation: Use Sonnet for resolution (it only synthesizes two existing arguments, doesn't need Opus reasoning depth). If user insists on Opus, easy to swap model ID.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | backend/tests/ (existing conftest.py + conftest_v2.py) |
| Quick run command | `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v2_adversarial.py -x` |
| Full suite command | `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MATC-05 | Every match undergoes adversarial double-check | unit | `pytest tests/test_v2_adversarial.py::TestAdversarialDebate -x` | Wave 0 |
| MATC-06 | Triple-check triggered at <95% confidence | unit | `pytest tests/test_v2_adversarial.py::TestTripleCheck -x` | Wave 0 |
| MATC-07 | Chain-of-thought reasoning in output | unit | `pytest tests/test_v2_adversarial.py::TestChainOfThought -x` | Wave 0 |
| MATC-08 | Multiple candidates listed with individual scores | unit | `pytest tests/test_v2_adversarial.py::TestMultipleCandidates -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v2_adversarial.py -x`
- **Per wave merge:** `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_v2_adversarial.py` -- covers MATC-05, MATC-06, MATC-07, MATC-08
- [ ] Mock fixtures for MatchResult -> AdversarialResult pipeline (reuse `_make_match_result` from test_v2_matching.py)
- [ ] Mock Opus responses for FOR/AGAINST/resolution structured outputs

## Sources

### Primary (HIGH confidence)
- [Anthropic Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview) -- Opus 4.6 model ID `claude-opus-4-6`, pricing $5/$25 per MTok
- [Anthropic Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) -- Opus 4.x combined rate limits per tier
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- `messages.parse()` with `output_format` parameter, `response.parsed_output`
- [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) -- Opus 4.6 pricing, prompt caching multipliers

### Secondary (MEDIUM confidence)
- Phase 4 codebase (`ai_matcher.py`, `prompts.py`, `matching.py` schemas) -- established patterns for structured AI outputs
- Phase 4 test suite (`test_v2_matching.py`) -- mock patterns for Claude API calls

### Tertiary (LOW confidence)
- AGAINST prompt calibration effectiveness -- needs empirical testing with real tender data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- same libraries as Phase 4, no new dependencies
- Architecture: HIGH -- follows Phase 4 patterns exactly (asyncio.Semaphore, messages.parse, Pydantic v2)
- Pitfalls: MEDIUM -- rate limit analysis is verified from official docs; prompt calibration is theoretical
- Cost estimates: MEDIUM -- based on official pricing, actual token usage depends on prompt length

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- Opus 4.6 pricing/API unlikely to change within 30 days)
