/**
 * V2 Result Mapper
 *
 * Transforms the v2 pipeline analysis response into the display structure
 * expected by ResultsPanel (matched/partial/unmatched arrays with summary).
 */

export function mapV2ResultToDisplay(v2Result) {
  const { positionen, match_results, adversarial_results, gap_results, analysis_id } = v2Result

  // Build lookups by positions_nr
  const matchLookup = Object.fromEntries(
    (match_results || []).map(mr => [mr.positions_nr, mr])
  )
  const advLookup = Object.fromEntries(
    (adversarial_results || []).map(ar => [ar.positions_nr, ar])
  )
  const gapLookup = Object.fromEntries(
    (gap_results || []).map(gr => [gr.positions_nr, gr])
  )

  const matched = []
  const partial = []
  const unmatched = []

  for (const pos of (positionen || [])) {
    const nr = pos.positions_nr
    const adv = advLookup[nr]
    const match = matchLookup[nr]
    const gaps = gapLookup[nr]

    // Determine confidence from adversarial (preferred) or match
    const confidence = adv
      ? adv.adjusted_confidence
      : (match?.bester_match?.gesamt_konfidenz || 0)

    // Map to display item matching ResultsPanel shape
    const item = {
      position: nr,
      beschreibung: pos.positions_bezeichnung || pos.tuertyp || '-',
      original_position: pos,
      confidence,
      category: match?.bester_match?.produkt_kategorie || '-',
      reason: adv?.resolution_reasoning || match?.bester_match?.begruendung || '',
      matched_products: match?.bester_match ? [{
        'Tuerblatt / Verglasungsart / Rollkasten': match.bester_match.produkt_name,
        _row_index: null,
        _produkt_id: match.bester_match.produkt_id,
      }] : [],
      // V2-specific data for detail modal + correction modal
      _v2: {
        adversarial: adv,
        match: match,
        gaps: gaps,
        dimension_scores: match?.bester_match?.dimension_scores || [],
      },
      // Gap items for detail modal
      gap_items: gaps?.gaps?.map(g => ({
        field: g.dimension,
        detail: g.abweichung_beschreibung,
        severity: g.schweregrad,
      })) || [],
      // Match criteria for detail modal
      match_criteria: (match?.bester_match?.dimension_scores || []).map(ds => ({
        kriterium: ds.dimension,
        status: ds.score >= 0.95 ? 'ok' : ds.score >= 0.6 ? 'teilweise' : 'fehlt',
        detail: `${(ds.score * 100).toFixed(0)}% - ${ds.begruendung || ''}`,
      })),
    }

    // Classify by adjusted_confidence thresholds
    if (confidence >= 0.95) {
      matched.push(item)
    } else if (confidence >= 0.60) {
      partial.push(item)
    } else {
      unmatched.push(item)
    }
  }

  const total = (positionen || []).length
  return {
    analysis_id,
    requirements: { positionen },
    matching: {
      matched,
      partial,
      unmatched,
      summary: {
        total_positions: total,
        matched_count: matched.length,
        partial_count: partial.length,
        unmatched_count: unmatched.length,
        match_rate: total > 0 ? Math.round((matched.length / total) * 100) : 0,
      },
    },
  }
}
