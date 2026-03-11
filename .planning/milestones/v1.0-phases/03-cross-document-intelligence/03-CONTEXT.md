# Phase 3: Cross-Document Intelligence - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Enriching door positions with data from all uploaded documents and surfacing contradictions between documents before matching begins. This phase adds a post-pipeline cross-document layer on top of Phase 2's per-file 3-pass extraction. Product matching itself is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Position Matching Across Documents
- Dedicated cross-doc matcher module — separate from Phase 2's intra-doc dedup. Different rules: also match by room+floor+door-type when positions_nr is missing in one document.
- Tiered confidence approach: auto-merge at 90%+ confidence, flag as 'possible match' at 60-90% for user review, ignore below 60%.
- General spec paragraphs (e.g., 'Alle Türen im OG müssen T30 sein') are detected, scoped, and applied to all matching positions. Tagged with 'general spec' source.
- AI handles cross-doc position identifier normalization (e.g., 'Tür 1.01' = 'Pos. 1.01' = 'Element E1.01'). Same approach as Phase 2 dedup but across document boundaries.

### Conflict Handling
- AI resolution: Send both conflicting values + context to Claude to determine which is more likely correct based on document type, surrounding context, and domain knowledge.
- Full transparency: AI picks the best value but the rejected alternative is stored and visible. Output shows e.g. 'T90 (aus PDF-Spec, bestätigt durch AI) — Konflikt mit T30 aus Excel'.
- Detect both exact field contradictions AND semantic conflicts (e.g., 'Holzrahmen' in Excel but 'Stahlzarge' implied by PDF fire spec). AI should catch logical inconsistencies.
- Conflict severity: Critical (safety-relevant: fire rating, emergency exit), Major (spec-relevant: dimensions, material), Minor (cosmetic: color, surface). Matches Phase 6 Gap Analysis severity pattern.

### Enrichment Scope & Depth
- Fill gaps + upgrade low confidence: If a field is empty, fill from other doc. If a field has konfidenz <0.7 but another doc has a higher-confidence value, upgrade. FieldSource provenance preserved.
- Extract and apply implicit specs from general document sections (e.g., 'Alle Innentüren: Holzzarge, 40dB Schallschutz'). Apply to all matching positions with 'implicit spec' source and lower konfidenz (e.g., 0.7).
- Extend FieldSource with enrichment_source metadata — explicitly mark 'this field was enriched from document X' beyond the existing dokument field. More explicit cross-doc provenance.
- Generate enrichment report: per document, how many positions matched, how many fields enriched, how many conflicts found. Gives sales team confidence in cross-doc analysis.

### Pipeline Integration
- Post-pipeline step: Run existing 3-pass pipeline per file first (Phase 2 code untouched), then run cross-doc intelligence as a separate layer over all results. Clean separation.
- Automatic when multi-file: If tender has 2+ files, cross-doc runs automatically after the 3-pass pipeline. Single file: skip. No extra API call needed.
- Same /api/v2/analyze response, extended with enrichment_report and conflicts fields. One API call, one result object.
- Separate Claude call(s) for cross-doc matching, enrichment, and conflict resolution. Dedicated prompts per task. Uses same asyncio.to_thread + messages.parse() pattern from Phase 2.

### Claude's Discretion
- Exact prompt design for cross-doc matching, enrichment, and conflict resolution
- Batching strategy for AI calls (how many positions per call)
- enrichment_source schema extension details
- Enrichment report format and structure
- Internal data structures for cross-doc matching

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/v2/extraction/dedup.py`: merge_positions() with field-level conflict resolution — pattern to follow for cross-doc merge
- `backend/v2/extraction/prompts.py`: German prompt templates — extend with cross-doc prompts
- `backend/v2/extraction/pipeline.py`: Pipeline orchestrator — add post-pipeline hook for cross-doc step
- `backend/v2/schemas/common.py`: FieldSource with dokument, seite, zeile, zelle, konfidenz — extend with enrichment_source
- `backend/v2/schemas/extraction.py`: ExtractedDoorPosition (55 fields) + ExtractionResult — extend ExtractionResult with enrichment_report and conflicts

### Established Patterns
- asyncio.to_thread wrapping sync Anthropic for messages.parse() async compat
- Later-pass-wins conflict resolution (Pass 3 > Pass 2 > Pass 1)
- Position batching at 25 per batch for context limits
- Compact position summaries for AI prompts
- In-memory dict for tender storage (single-process dev)

### Integration Points
- `backend/v2/extraction/` — new modules: cross_doc_matcher.py, enrichment.py, conflict_detector.py
- `backend/v2/routers/analyze_v2.py` — trigger cross-doc step after pipeline, extend response
- ExtractionResult schema — add enrichment_report and conflicts fields

</code_context>

<specifics>
## Specific Ideas

- Cross-doc matcher should understand that Swiss tenders often have: XLSX Türliste (positions + basic specs), PDF Bauphysik/Brandschutz (detailed specs per area), DOCX Pflichtenheft (general requirements). Each doc type contributes different field types.
- Conflict severity should align with Phase 6's Gap Analysis severity (Critical/Major/Minor) to maintain consistent UX across the pipeline.
- Enrichment report is visible to the sales team and should build confidence: "PDF-Spezifikation hat 45 Felder bei 12 Positionen ergänzt, 3 Konflikte gefunden."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-cross-document-intelligence*
*Context gathered: 2026-03-10*
