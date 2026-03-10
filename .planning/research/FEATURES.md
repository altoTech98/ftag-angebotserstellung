# Feature Landscape

**Domain:** AI-powered construction tender analysis with product catalog matching (door industry)
**Researched:** 2026-03-10
**Overall confidence:** HIGH (domain well-understood from existing codebase + industry research)

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-format document parsing (PDF, XLSX, DOCX) | Tenders always arrive as mixed file types | Low | Already exists in v1. PyMuPDF + pdfplumber + openpyxl + python-docx. Keep as-is. |
| Structured Excel Tuerliste parsing | 80%+ of Swiss construction tenders use Excel door lists with specific column layouts | Medium | Already exists. Column auto-detection for ~54 FTAG columns. Critical path. |
| Complete requirement extraction (zero missed positions) | v1 problem: missed requirements. A single missed door position = lost revenue or compliance failure | High | Multi-pass parsing needed. Single-pass is the #1 cause of missed positions. |
| Product catalog matching against ~891 FTAG products | Core value proposition. Without it, system has no purpose | High | Exists as 3-stage (TF-IDF + rules + feedback). Needs upgrade to multi-dimensional AI matching. |
| Confidence scoring per match (0-100%) | Sales team needs to know which matches are reliable vs. questionable. Without scores, every match needs manual review | Medium | v1 has implicit scoring via thresholds (60/35). Needs explicit per-match confidence with breakdown. |
| Gap analysis for unmatched requirements | Sales team must know WHAT cannot be fulfilled and WHY, to communicate to the customer | High | v1 has basic gap list. Needs detailed gap categorization (which dimension failed: size, fire rating, sound, material). |
| Color-coded Excel output (green/yellow/red) | Sales team works in Excel. Visual status at a glance is non-negotiable for 200-500 position tenders | Medium | Already exists with 2-sheet output. Needs expansion to 4 sheets per PROJECT.md. |
| Match traceability (WHY was this product chosen) | v1 problem: no explanation for matches. Sales team cannot trust opaque AI decisions | High | Chain-of-thought reasoning per match. Must be stored and displayed in Excel output. |
| SSE real-time progress streaming | Analyses take 2-10 minutes. Users abandon if they see no progress | Low | Already exists. Job system + SSE streaming with keepalive. Keep as-is. |
| Multi-file upload per tender | Real tenders have 3-15 files (door list + specs + plans). Single-file = unusable for real work | Medium | Already exists as project analysis. File classification (tuerliste/spezifikation/plan/sonstig). |
| Feedback/correction persistence | Corrections from past tenders must improve future matches. Without learning, same errors repeat | Low | Already exists. JSON-based feedback store. Corrections injected as few-shot examples. |

## Differentiators

Features that set the system apart from generic AI tender tools. Not expected by users upfront, but create significant competitive advantage once experienced.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-pass document analysis (2-3 passes per document) | Catches requirements missed by single-pass. v1's biggest weakness was missed positions. Each pass uses a different extraction strategy (structural, semantic, cross-reference) | High | PROJECT.md mandates this. Pass 1: structural column parsing. Pass 2: AI semantic extraction. Pass 3: cross-reference validation against spec documents. |
| Adversarial double-check (Devil's Advocate AI pass) | Second AI call actively tries to DISPROVE each match. If it succeeds, match is downgraded. Dramatically reduces false positives | High | Novel pattern for this domain. Send each match + product + requirement to a second prompt that argues why it is WRONG. If argument is convincing, flag for review. |
| Triple-check on low confidence (<95%) | Third AI pass with alternative prompt formulation when first two disagree. Majority voting on match quality | Medium | Only triggers when needed (estimated 10-20% of positions). Cost impact manageable since costs are explicitly irrelevant per PROJECT.md. |
| Multi-dimensional match scoring breakdown | Instead of one score, show: dimensions (pass/fail), fire rating (pass/fail), sound (pass/fail), material (pass/fail), certification (pass/fail), price (informational). Sales team sees exactly WHERE a product falls short | Medium | Enables targeted product substitution. If only sound rating fails, suggest product with higher dB. |
| Gap severity categorization | Not all gaps are equal. "Product is 5mm too narrow" vs "No fire-rated product exists" have very different business implications. Categorize: Critical (no solution exists), Major (significant deviation), Minor (close match, may be acceptable) | Medium | Enables prioritized action by sales team. Critical gaps get escalated, minor gaps may be accepted by customer. |
| Alternative product suggestions for gaps | When a match fails, suggest the closest alternatives with explanation of what would need to change. "Product X matches except fire rating is EI30 instead of required EI60" | Medium | Depends on gap analysis. Use same catalog search but relax the failing constraint. |
| 4-sheet Excel output (Overview + Details + Gaps + Executive Summary) | Single sheet is insufficient for 200-500 position tenders. Structured multi-sheet gives different stakeholders what they need: summary for managers, details for sales engineers, gaps for product managers | Medium | Sheet 1: Overview matrix (existing Tuermatrix-FTAG format). Sheet 2: Detail per match with confidence + reasoning. Sheet 3: Gap analysis with categories + severity. Sheet 4: Executive summary with statistics + recommendations. |
| Cross-document enrichment | Merge data from Excel door list + PDF specifications + Word requirements into unified position data. One document says "EI30", another specifies "Schallschutz 32dB" for the same door | High | Already partially implemented (scan_and_enrich). Needs to be more robust: map spec requirements to door positions by position number, room, or floor. |
| Chain-of-thought reasoning export | Every match decision includes the AI's step-by-step reasoning, stored and exportable. Audit trail for compliance-critical decisions | Medium | Use Claude structured output to enforce CoT format. Store reasoning alongside match result. Display in Excel "Hinweise" column. |
| Plausibility check at end | Final sanity check: Are all position numbers accounted for? Do match percentages add up? Any duplicate matches? Any position matched to same product suspiciously often? | Low | Simple algorithmic check after AI matching completes. Catches systematic errors. |

## Anti-Features

Features to explicitly NOT build. These would waste effort, add complexity, or actively harm the product.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Fancy frontend / SPA redesign | PROJECT.md explicitly scopes this as "Backend-Fokus, minimales Frontend". Sales team needs Upload + Download + Live-Log, not a dashboard | Keep minimal React frontend. Improve SSE progress display, add download buttons. No charts, no dashboards. |
| Automatic offer generation with pricing | Pricing requires business logic, customer relationships, volume discounts -- too much implicit knowledge to automate safely. Wrong prices = legal liability | Generate the match/gap Excel. Let sales team fill in prices manually in the FTAG format they already use. |
| Local LLM / Ollama fallback | PROJECT.md: "v2 nutzt ausschliesslich Claude (bestes Modell, Kosten irrelevant)". Multi-pass validation with local models would produce unreliable results | Remove Ollama code paths from v2. Single AI provider (Claude) simplifies testing and validation. |
| User authentication / role management | Explicitly out of scope per PROJECT.md. Small internal team, no external access | Skip auth entirely. Direct upload/download. |
| ERP integration | Out of scope per PROJECT.md. Would require understanding their specific ERP system | Export clean Excel that can be manually imported into ERP later. |
| Real-time collaborative editing of results | Sales team works individually on tenders. No need for multi-user concurrent editing | Generate Excel, download, edit locally in Excel. |
| Auto-retry on AI failures with degraded quality | Better to fail clearly than return bad results. "Genauigkeit vor Effizienz" | Retry same quality level 2-3 times. If Claude is down, fail with clear error message. Do not fall back to regex matching. |
| Embedding-based semantic search for catalog | TF-IDF + rule-based scoring already works well for structured catalog data. Embeddings add complexity without clear benefit for 891 structured products with known schemas | Keep TF-IDF pre-filter + rule-based scoring. Add AI verification on top. Embeddings would matter at 10K+ products. |
| PDF plan/drawing analysis | Construction plans require specialized CV models. Out of scope and unreliable with current LLM vision | Skip plan files during analysis. Classify as "plan" and ignore. Focus on text-based documents. |

## Feature Dependencies

```
Multi-format parsing (existing)
  |
  v
Multi-pass document analysis -----> Structured requirement extraction
  |                                    |
  v                                    v
Cross-document enrichment          Multi-dimensional product matching
  |                                    |
  v                                    v
Complete position list             Confidence score per match (0-100%)
                                       |
                                       +---> Adversarial double-check
                                       |        |
                                       |        v
                                       |     Triple-check (if <95%)
                                       |        |
                                       v        v
                                   Match results with confidence
                                       |
                                       +---> Gap analysis (categorized)
                                       |        |
                                       |        v
                                       |     Alternative product suggestions
                                       |        |
                                       v        v
                                   4-sheet Excel output
                                       |
                                       v
                                   Plausibility check
                                       |
                                       v
                                   Chain-of-thought export
```

Key dependency chains:
- Multi-pass parsing MUST come before matching (you cannot match what you did not extract)
- Confidence scoring MUST come before adversarial check (you need a baseline to challenge)
- Gap analysis MUST come after matching (gaps are the complement of matches)
- 4-sheet Excel is the final output -- depends on all upstream data being ready
- Plausibility check runs last, validates the entire pipeline output

## MVP Recommendation

**Phase 1 -- Foundation (must ship first):**
1. Multi-pass document analysis (2 passes minimum: structural + AI semantic)
2. Multi-dimensional product matching with explicit confidence scores
3. Basic gap analysis (matched/partial/unmatched with reason text)
4. 4-sheet Excel output structure

**Phase 2 -- Validation layer:**
5. Adversarial double-check (second AI pass)
6. Triple-check for low-confidence matches
7. Gap severity categorization (Critical/Major/Minor)
8. Alternative product suggestions

**Phase 3 -- Polish:**
9. Cross-document enrichment improvements
10. Chain-of-thought reasoning in Excel
11. Plausibility check
12. Live progress detail (which position is being processed)

**Defer indefinitely:**
- Embedding search (TF-IDF sufficient at current catalog size)
- Frontend redesign (minimal is fine)
- Pricing automation (too risky)

## Complexity Budget

| Feature Group | Estimated Effort | Risk |
|---------------|-----------------|------|
| Multi-pass parsing | 3-5 days | Medium -- prompt engineering intensive |
| Multi-dimensional matching + confidence | 3-5 days | Medium -- need to design scoring rubric |
| Adversarial double-check | 2-3 days | Low -- well-defined pattern, just a second prompt |
| Triple-check | 1-2 days | Low -- conditional extension of double-check |
| Gap analysis (categorized + alternatives) | 3-4 days | Medium -- requires good taxonomy |
| 4-sheet Excel output | 2-3 days | Low -- openpyxl work, extend existing generator |
| Cross-document enrichment | 2-3 days | High -- position-to-spec mapping is ambiguous |
| Chain-of-thought export | 1 day | Low -- store what Claude already generates |
| Plausibility check | 1 day | Low -- algorithmic, no AI needed |

**Total estimated: 18-27 days for full feature set**

## Sources

- [Tenderbolt - Best AI solutions for tenders 2025](https://www.tenderbolt.ai/en/post/les-meilleures-solutions-ia-de-reponse-aux-appels-doffres-en-2025)
- [Altura - AI in tender and RFP management 2025](https://altura.io/en/blog/ai-tendermanagement)
- [Altura - Document Analysis Feature](https://altura.io/en/feature/document-analysis)
- [iFieldSmart - AI Scope Gap Analysis for Construction](https://www.ifieldsmart.com/blogs/ai-scope-gap-analysis-for-construction-teams/)
- [TruBuild - AI-Powered Tender Evaluation in Construction](https://trubuild.io/blog/ai-powered-tender-evaluation-a-new-era-of-procurement-in-construction)
- [TenderStrike - AI Tender Documentation Analysis](https://www.tenderstrike.com/en/blog/AI-tender-documentation-analysis-construction-tool-over-ChatGPT/)
- [arXiv - Confidence alignment with correctness for LLM error detection](https://arxiv.org/html/2603.06604)
- [arXiv - Fact-checking with LLMs via probabilistic certainty](https://arxiv.org/html/2601.02574)
- [FastAPI SSE documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [openpyxl conditional formatting docs](https://openpyxl.readthedocs.io/en/3.1/formatting.html)
- Existing codebase analysis (HIGH confidence -- direct code review)
