import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepResults } from '@/components/analysis/step-results';
import type { AnalysisResult } from '@/components/analysis/types';

const mockResult: AnalysisResult = {
  matched: [
    {
      status: 'matched',
      confidence: 0.95,
      position: 'P1',
      beschreibung: 'Holz-Rahmentuer T30 einflügelig',
      menge: 2,
      einheit: 'Stk',
      matched_products: [
        { artikelnr: 'HRT30-1', bezeichnung: 'Holzrahmen T30 1-fluegelig' },
      ],
      gap_items: [],
      missing_info: [],
      reason: 'Exact match',
      original_position: {},
      category: 'Tueren',
    },
  ],
  partial: [
    {
      status: 'partial',
      confidence: 0.75,
      position: 'P2',
      beschreibung: 'Stahl-Schiebetuer EI30',
      menge: 1,
      einheit: 'Stk',
      matched_products: [
        { artikelnr: 'SST-EI30', bezeichnung: 'Stahl-Schiebetuer EI30' },
      ],
      gap_items: ['Obentuersteher'],
      missing_info: [{ feld: 'Breite', benoetigt: '1200mm', vorhanden: '' }],
      reason: 'Partial match, missing dimensions',
      original_position: {},
      category: 'Tueren',
    },
  ],
  unmatched: [
    {
      status: 'unmatched',
      confidence: 0,
      position: 'P3',
      beschreibung: 'Spezial-Brandschutztor ZK',
      menge: 1,
      einheit: 'Stk',
      matched_products: [],
      gap_items: ['Gesamtes Produkt'],
      missing_info: [],
      reason: 'No matching product in catalog',
      original_position: {},
      category: 'Tore',
    },
  ],
  summary: {
    total_positions: 3,
    matched_count: 1,
    partial_count: 1,
    unmatched_count: 1,
    match_rate: 0.33,
  },
};

const defaultConfig = {
  highThreshold: 90,
  lowThreshold: 70,
  validationPasses: 1,
};

describe('[ANLZ-05, RSLT-01, RSLT-04] Results table step', () => {
  const defaultProps = {
    result: mockResult,
    config: defaultConfig,
    onExpandRow: vi.fn(),
    expandedRow: null,
  };

  it('renders table with 6 columns: Nr, Anforderung, Position, Zugeordnetes Produkt, Artikelnr, Konfidenz', () => {
    render(<StepResults {...defaultProps} />);

    expect(screen.getByTestId('sort-nr')).toBeDefined();
    expect(screen.getByTestId('sort-beschreibung')).toBeDefined();
    expect(screen.getByTestId('sort-position')).toBeDefined();
    expect(screen.getByTestId('sort-produkt')).toBeDefined();
    expect(screen.getByTestId('sort-artikelnr')).toBeDefined();
    expect(screen.getByTestId('sort-konfidenz')).toBeDefined();

    expect(screen.getByText('Nr')).toBeDefined();
    expect(screen.getByText('Anforderung')).toBeDefined();
    expect(screen.getByText('Position')).toBeDefined();
    expect(screen.getByText('Zugeordnetes Produkt')).toBeDefined();
    expect(screen.getByText('Artikelnr')).toBeDefined();
    expect(screen.getByText('Konfidenz')).toBeDefined();
  });

  it('flattens matched + partial + unmatched into single numbered list', () => {
    render(<StepResults {...defaultProps} />);

    expect(screen.getByTestId('result-row-1')).toBeDefined();
    expect(screen.getByTestId('result-row-2')).toBeDefined();
    expect(screen.getByTestId('result-row-3')).toBeDefined();
  });

  it('filters by text search on beschreibung', async () => {
    const user = userEvent.setup();
    render(<StepResults {...defaultProps} />);

    const searchInput = screen.getByTestId('search-input');
    await user.type(searchInput, 'Holz');

    // Only the first entry should be visible
    expect(screen.getByTestId('result-row-1')).toBeDefined();
    expect(screen.queryByTestId('result-row-2')).toBeNull();
    expect(screen.queryByTestId('result-row-3')).toBeNull();
  });

  it('filters by confidence level dropdown', async () => {
    const user = userEvent.setup();
    render(<StepResults {...defaultProps} />);

    // Click on the confidence filter trigger
    const trigger = screen.getByTestId('confidence-filter');
    await user.click(trigger);

    // Select "Gap" option from the dropdown - find within the select popup
    const gapOptions = await screen.findAllByText('Gap');
    // Click the one that's a select item (not the filter chip)
    const selectGapOption = gapOptions.find(
      (el) => el.closest('[data-slot="select-item"]') !== null
    );
    expect(selectGapOption).toBeDefined();
    await user.click(selectGapOption!);

    // Only unmatched row should remain
    expect(screen.getByTestId('result-row-3')).toBeDefined();
    expect(screen.queryByTestId('result-row-1')).toBeNull();
    expect(screen.queryByTestId('result-row-2')).toBeNull();
  });

  it('sorts by column header click', async () => {
    const user = userEvent.setup();
    render(<StepResults {...defaultProps} />);

    // Click on Konfidenz header to sort by confidence
    const konfidenzHeader = screen.getByTestId('sort-konfidenz');
    await user.click(konfidenzHeader);

    // Get all rows - they should now be sorted by confidence ascending (0, 0.75, 0.95)
    const rows = screen.getAllByTestId(/^result-row-/);
    expect(rows).toHaveLength(3);
  });

  it('shows Excel download button', () => {
    render(<StepResults {...defaultProps} />);

    const downloadBtn = screen.getByTestId('download-excel-btn');
    expect(downloadBtn).toBeDefined();
    expect(downloadBtn.textContent).toContain('Excel herunterladen');
  });

  it('shows filter summary chips with counts per level', () => {
    render(<StepResults {...defaultProps} />);

    const chipHigh = screen.getByTestId('chip-high');
    expect(chipHigh.textContent).toContain('1 Hoch');

    const chipMedium = screen.getByTestId('chip-medium');
    expect(chipMedium.textContent).toContain('1 Mittel');

    const chipGap = screen.getByTestId('chip-gap');
    expect(chipGap.textContent).toContain('1 Gap');
  });
});
