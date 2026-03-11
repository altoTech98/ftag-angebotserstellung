import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepCatalog } from '@/components/analysis/step-catalog';
import type { CatalogInfo } from '@/components/analysis/step-catalog';

const mockCatalogs: CatalogInfo[] = [
  {
    id: 'cat-1',
    name: 'FTAG Produktuebersicht',
    productCount: 884,
    updatedAt: new Date('2026-03-10'),
    isActive: true,
  },
];

const twoCatalogs: CatalogInfo[] = [
  ...mockCatalogs,
  {
    id: 'cat-2',
    name: 'Testkatalog',
    productCount: 100,
    updatedAt: new Date('2026-03-11'),
    isActive: false,
  },
];

describe('[ANLZ-02] Catalog selection step', () => {
  it('renders catalog cards from real data', () => {
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId="cat-1" onCatalogChange={onChange} catalogs={mockCatalogs} />
    );

    expect(screen.getByText('FTAG Produktuebersicht')).toBeDefined();
    expect(screen.getByText(/884 Produkte/)).toBeDefined();
  });

  it('shows pre-selected catalog with badge', () => {
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId="cat-1" onCatalogChange={onChange} catalogs={mockCatalogs} />
    );

    const badge = screen.getByTestId('catalog-selected-badge');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('Ausgewaehlt');

    const card = screen.getByTestId('catalog-card');
    expect(card.className).toContain('ring-primary');
  });

  it('shows upload button as link to /katalog', () => {
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId="cat-1" onCatalogChange={onChange} catalogs={mockCatalogs} />
    );

    const uploadBtn = screen.getByTestId('upload-catalog-btn');
    expect(uploadBtn).toBeDefined();
    // Should not be disabled (it is now a link)
    expect(uploadBtn.hasAttribute('disabled')).toBe(false);
  });

  it('auto-selects single catalog when catalogId is null', () => {
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId={null} onCatalogChange={onChange} catalogs={mockCatalogs} />
    );

    expect(onChange).toHaveBeenCalledWith('cat-1');
  });

  it('shows empty state when no catalogs exist', () => {
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId={null} onCatalogChange={onChange} catalogs={[]} />
    );

    expect(screen.getByTestId('no-catalogs')).toBeDefined();
    expect(screen.getByText(/Noch keine Kataloge vorhanden/)).toBeDefined();
  });

  it('allows selecting between multiple catalogs', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <StepCatalog catalogId={null} onCatalogChange={onChange} catalogs={twoCatalogs} />
    );

    // Should not auto-select (more than one catalog)
    // Click on second catalog
    const cards = screen.getAllByTestId('catalog-card');
    expect(cards).toHaveLength(2);
    await user.click(cards[1]);
    expect(onChange).toHaveBeenCalledWith('cat-2');
  });
});
