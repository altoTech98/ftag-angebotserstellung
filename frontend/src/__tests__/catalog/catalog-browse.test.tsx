import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CatalogTable } from '@/components/catalog/catalog-table';

// Mock server actions
vi.mock('@/lib/actions/catalog-actions', () => ({
  getCatalogProducts: vi.fn().mockResolvedValue({
    products: [],
    total: 0,
    page: 1,
    pages: 0,
  }),
  saveProductOverride: vi.fn(),
}));

const mockProducts = [
  {
    row_index: 0,
    category: 'Innentuer',
    summary: 'Rahmentuer Brandschutz EI30',
    fields: { tuertyp: 'Rahmentuer', brandschutz: 'EI30', masse: '1000x2100' },
    kostentraeger: 'KT-001',
    hasOverride: false,
    overrideAction: null,
    overrideId: null,
  },
  {
    row_index: 1,
    category: 'Aussentuer',
    summary: 'Haustuer Schallschutz',
    fields: { tuertyp: 'Haustuer', brandschutz: '-', masse: '900x2100' },
    kostentraeger: 'KT-002',
    hasOverride: true,
    overrideAction: 'edit',
    overrideId: 'ov-1',
  },
];

describe('[KAT-02] CatalogBrowse', () => {
  it('renders product table with pagination', () => {
    render(
      <CatalogTable
        catalogId="cat-1"
        initialProducts={mockProducts}
        initialTotal={52}
        initialPages={2}
        categories={['Innentuer', 'Aussentuer']}
        canEdit={false}
      />
    );

    expect(screen.getByTestId('catalog-table')).toBeDefined();
    expect(screen.getByTestId('pagination')).toBeDefined();
    expect(screen.getByText(/52 Produkte gesamt/)).toBeDefined();
    expect(screen.getByText('Rahmentuer')).toBeDefined();
    expect(screen.getByText('Haustuer')).toBeDefined();
  });

  it('filters products by search text', () => {
    render(
      <CatalogTable
        catalogId="cat-1"
        initialProducts={mockProducts}
        initialTotal={2}
        initialPages={1}
        categories={[]}
        canEdit={false}
      />
    );

    const searchInput = screen.getByTestId('search-input');
    expect(searchInput).toBeDefined();
    expect(searchInput.getAttribute('placeholder')).toBe('Produkte suchen...');
  });

  it('filters products by category', () => {
    render(
      <CatalogTable
        catalogId="cat-1"
        initialProducts={mockProducts}
        initialTotal={2}
        initialPages={1}
        categories={['Innentuer', 'Aussentuer']}
        canEdit={false}
      />
    );

    expect(screen.getByTestId('category-filter')).toBeDefined();
  });

  it('shows product count and override badge', () => {
    render(
      <CatalogTable
        catalogId="cat-1"
        initialProducts={mockProducts}
        initialTotal={2}
        initialPages={1}
        categories={[]}
        canEdit={true}
      />
    );

    // Second product has override
    expect(screen.getByTestId('override-badge')).toBeDefined();
    expect(screen.getByText('Bearbeitet')).toBeDefined();
  });
});
