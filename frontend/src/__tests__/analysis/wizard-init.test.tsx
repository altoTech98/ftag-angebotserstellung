import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { AnalysisResult } from '@/components/analysis/types';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

// Mock server actions
vi.mock('@/lib/actions/analysis-actions', () => ({
  prepareFilesForPython: vi.fn(),
  createAnalysis: vi.fn(),
  saveAnalysisResult: vi.fn(),
}));

// Import after mocks
import { AnalyseWizardClient } from '@/app/(app)/projekte/[id]/analyse/client';

const mockProject = {
  id: 'proj-1',
  name: 'Test Project',
  files: [
    {
      id: 'file-1',
      name: 'test.pdf',
      size: 1024,
      contentType: 'application/pdf',
      downloadUrl: 'https://example.com/test.pdf',
      createdAt: '2026-01-01T00:00:00Z',
    },
  ],
};

const mockResult: AnalysisResult = {
  matched: [
    {
      status: 'matched',
      confidence: 0.95,
      position: 'Pos 1',
      beschreibung: 'Brandschutztuer',
      menge: 1,
      einheit: 'Stk',
      matched_products: [{ artikelnr: 'FT-1', bezeichnung: 'T30' }],
      gap_items: [],
      missing_info: [],
      reason: 'Passt',
      original_position: {},
      category: 'Brandschutz',
    },
  ],
  partial: [],
  unmatched: [],
  summary: {
    total_positions: 1,
    matched_count: 1,
    partial_count: 0,
    unmatched_count: 0,
    match_rate: 1.0,
  },
};

describe('[ANLZ-05] Wizard initialization', () => {
  it('when initialResult is provided, wizard renders step 5 (results view) directly', () => {
    render(
      <AnalyseWizardClient project={mockProject} initialResult={mockResult} />
    );
    // Step 5 shows the results component
    expect(screen.getByTestId('step-results')).toBeTruthy();
  });

  it('when no initialResult, wizard renders step 1', () => {
    render(
      <AnalyseWizardClient project={mockProject} initialResult={null} />
    );
    // Step 1 shows file selection heading
    expect(screen.getByText('Dateien fuer die Analyse auswaehlen')).toBeTruthy();
  });

  it('when viewing past results (initialResult provided), back button is hidden', () => {
    render(
      <AnalyseWizardClient project={mockProject} initialResult={mockResult} />
    );
    // There should be no "Zurueck" button
    expect(screen.queryByText('Zurueck')).toBeNull();
  });
});
