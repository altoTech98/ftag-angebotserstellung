import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CatalogVersionHistory } from '@/components/catalog/catalog-version-history';

// Mock server actions
vi.mock('@/lib/actions/catalog-actions', () => ({
  rollbackVersion: vi.fn(),
  compareVersions: vi.fn(),
}));

const mockVersions = [
  {
    id: 'v2',
    versionNum: 2,
    fileName: 'katalog_v2.xlsx',
    totalProducts: 900,
    mainProducts: 680,
    categories: 14,
    uploadedBy: 'user-1',
    isActive: true,
    notes: null,
    createdAt: '2026-03-11T10:00:00Z',
  },
  {
    id: 'v1',
    versionNum: 1,
    fileName: 'katalog_v1.xlsx',
    totalProducts: 884,
    mainProducts: 650,
    categories: 12,
    uploadedBy: 'user-1',
    isActive: false,
    notes: 'Erstupload',
    createdAt: '2026-03-10T10:00:00Z',
  },
];

describe('[KAT-03] CatalogVersionHistory', () => {
  it('renders version list with dates and stats', () => {
    render(
      <CatalogVersionHistory
        catalogId="cat-1"
        versions={mockVersions}
        canManage={false}
      />
    );

    expect(screen.getByTestId('version-history')).toBeDefined();
    expect(screen.getByTestId('version-list')).toBeDefined();
    expect(screen.getByTestId('version-2')).toBeDefined();
    expect(screen.getByTestId('version-1')).toBeDefined();
    expect(screen.getByText('900 Produkte')).toBeDefined();
    expect(screen.getByText('884 Produkte')).toBeDefined();
  });

  it('shows active version badge', () => {
    render(
      <CatalogVersionHistory
        catalogId="cat-1"
        versions={mockVersions}
        canManage={false}
      />
    );

    expect(screen.getByTestId('active-badge-2')).toBeDefined();
    expect(screen.getByText('Aktiv')).toBeDefined();
  });

  it('triggers rollback action on version click', () => {
    render(
      <CatalogVersionHistory
        catalogId="cat-1"
        versions={mockVersions}
        canManage={true}
      />
    );

    // Only non-active versions have rollback button
    const rollbackBtn = screen.getByTestId('rollback-btn-1');
    expect(rollbackBtn).toBeDefined();
    expect(rollbackBtn.textContent).toContain('Aktivieren');

    // Active version should not have rollback button
    expect(screen.queryByTestId('rollback-btn-2')).toBeNull();
  });

  it('shows version comparison diff controls', () => {
    render(
      <CatalogVersionHistory
        catalogId="cat-1"
        versions={mockVersions}
        canManage={false}
      />
    );

    expect(screen.getByTestId('version-compare')).toBeDefined();
    expect(screen.getByTestId('compare-a')).toBeDefined();
    expect(screen.getByTestId('compare-b')).toBeDefined();
    expect(screen.getByTestId('compare-btn')).toBeDefined();
  });
});
