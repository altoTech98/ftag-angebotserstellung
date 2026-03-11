import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResultDetail } from '@/components/analysis/result-detail';
import type { MatchEntry, WizardState } from '@/components/analysis/types';

const defaultConfig: WizardState['config'] = {
  highThreshold: 90,
  lowThreshold: 70,
  validationPasses: 1,
};

const matchedEntry: MatchEntry = {
  status: 'matched',
  confidence: 0.92,
  position: 'Pos 1.01',
  beschreibung: 'Brandschutztuer T30 einflügelig',
  menge: 2,
  einheit: 'Stk',
  matched_products: [
    { artikelnr: 'FT-1001', bezeichnung: 'Brandschutztuer T30-1' },
  ],
  gap_items: [],
  missing_info: [],
  reason: 'Die Anforderung passt gut zum Produkt FT-1001 aufgrund der uebereinstimmenden Brandschutzklasse T30.',
  original_position: { breite: '900mm', hoehe: '2100mm', material: 'Stahl' },
  category: 'Brandschutz',
};

const unmatchedEntry: MatchEntry = {
  status: 'unmatched',
  confidence: 0.15,
  position: 'Pos 2.05',
  beschreibung: 'Schiebetuer mit Glasfuellung',
  menge: 1,
  einheit: 'Stk',
  matched_products: [],
  gap_items: [
    'FT-2001: Masse zu gross fuer Standardrahmen',
    'FT-2002: Material nicht verfuegbar in Glasausfuehrung',
  ],
  missing_info: [
    { feld: 'Verglasung', benoetigt: 'ESG 8mm', vorhanden: '' },
  ],
  reason: 'Keine passende Schiebetuer mit Glasfuellung im Sortiment.',
  original_position: { breite: '1200mm', hoehe: '2400mm' },
  category: 'Schiebetuer',
};

describe('[RSLT-02] Result detail expansion', () => {
  it('renders AI reasoning text from entry.reason', () => {
    render(<ResultDetail entry={matchedEntry} config={defaultConfig} />);
    expect(screen.getByTestId('ai-reasoning')).toBeTruthy();
    expect(screen.getByText(/Die Anforderung passt gut zum Produkt FT-1001/)).toBeTruthy();
  });

  it('renders 6 dimension bars', () => {
    render(<ResultDetail entry={matchedEntry} config={defaultConfig} />);
    const bars = screen.getByTestId('dimension-bars');
    expect(bars).toBeTruthy();
    // Check all 6 labels present
    expect(screen.getByTestId('dimension-tuertyp')).toBeTruthy();
    expect(screen.getByTestId('dimension-material')).toBeTruthy();
    expect(screen.getByTestId('dimension-brandschutz')).toBeTruthy();
    expect(screen.getByTestId('dimension-masse')).toBeTruthy();
    expect(screen.getByTestId('dimension-ausfuehrung')).toBeTruthy();
    expect(screen.getByTestId('dimension-zubehoer')).toBeTruthy();
  });

  it('renders comparison card for matched entries', () => {
    render(<ResultDetail entry={matchedEntry} config={defaultConfig} />);
    expect(screen.getByTestId('comparison-card')).toBeTruthy();
    // Should show "Vergleich" heading
    expect(screen.getByText('Vergleich')).toBeTruthy();
  });

  it('renders rejection list for gap entries', () => {
    render(<ResultDetail entry={unmatchedEntry} config={defaultConfig} />);
    expect(screen.getByTestId('comparison-card-gap')).toBeTruthy();
    // Should show gap items
    expect(screen.getByText(/Masse zu gross fuer Standardrahmen/)).toBeTruthy();
    expect(screen.getByText(/Material nicht verfuegbar/)).toBeTruthy();
    // Section heading should say "Abgelehnte Produkte"
    const sectionHeadings = screen.getAllByText('Abgelehnte Produkte');
    expect(sectionHeadings.length).toBeGreaterThanOrEqual(1);
  });
});
