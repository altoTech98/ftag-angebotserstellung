import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComparisonCard } from '@/components/analysis/comparison-card';
import type { MatchEntry } from '@/components/analysis/types';

const matchedEntry: MatchEntry = {
  status: 'matched',
  confidence: 0.88,
  position: 'Pos 1.01',
  beschreibung: 'Brandschutztuer T30',
  menge: 2,
  einheit: 'Stk',
  matched_products: [
    { artikelnr: 'FT-1001', bezeichnung: 'Brandschutztuer T30-1', breite: '900mm', material: 'Stahl' },
  ],
  gap_items: [],
  missing_info: [],
  reason: 'Gute Uebereinstimmung',
  original_position: { breite: '900mm', hoehe: '2100mm', material: 'Stahl' },
  category: 'Brandschutz',
};

const gapEntry: MatchEntry = {
  status: 'unmatched',
  confidence: 0.1,
  position: 'Pos 3.02',
  beschreibung: 'Sondertuer XXL',
  menge: 1,
  einheit: 'Stk',
  matched_products: [],
  gap_items: [
    'FT-3001: Breite 1600mm uebersteigt Maximum',
    'FT-3002: Sonderhoehe nicht lieferbar',
  ],
  missing_info: [],
  reason: 'Keine passende Tuer im Sortiment',
  original_position: { breite: '1600mm', hoehe: '2800mm' },
  category: 'Sonder',
};

describe('[RSLT-03] Comparison card', () => {
  it('renders two-column layout: Anforderung vs Produkt', () => {
    render(<ComparisonCard entry={matchedEntry} />);
    const card = screen.getByTestId('comparison-card');
    expect(card).toBeTruthy();
    expect(screen.getByText('Anforderung')).toBeTruthy();
    expect(screen.getByText('Produkt')).toBeTruthy();
  });

  it('shows field match indicators', () => {
    render(<ComparisonCard entry={matchedEntry} />);
    // "breite" matches "900mm" on both sides -> should show check indicator
    const checkIcons = screen.queryAllByTestId('match-indicator-check');
    expect(checkIcons.length).toBeGreaterThan(0);
  });

  it('shows rejection reasons for gap entries', () => {
    render(<ComparisonCard entry={gapEntry} />);
    const gapCard = screen.getByTestId('comparison-card-gap');
    expect(gapCard).toBeTruthy();
    expect(screen.getByText(/Breite 1600mm uebersteigt Maximum/)).toBeTruthy();
    expect(screen.getByText(/Sonderhoehe nicht lieferbar/)).toBeTruthy();
  });
});
