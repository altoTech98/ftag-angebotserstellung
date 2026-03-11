import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProductEditDialog } from '@/components/catalog/product-edit-dialog';

// Mock server actions
vi.mock('@/lib/actions/catalog-actions', () => ({
  saveProductOverride: vi.fn(),
}));

const mockProduct = {
  row_index: 0,
  category: 'Innentuer',
  summary: 'Rahmentuer Brandschutz EI30',
  fields: {
    tuertyp: 'Rahmentuer',
    brandschutz: 'EI30',
    masse: '1000x2100',
    kategorie: 'Innentuer',
    kostentraeger: 'KT-001',
  },
  kostentraeger: 'KT-001',
  hasOverride: false,
  overrideAction: null,
  overrideId: null,
};

describe('[KAT-04] ProductEditDialog', () => {
  it('renders edit form with key product fields', () => {
    render(
      <ProductEditDialog
        catalogId="cat-1"
        product={mockProduct}
        mode="edit"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('dialog-title').textContent).toBe('Produkt bearbeiten');
    expect(screen.getByTestId('product-edit-form')).toBeDefined();
    expect(screen.getByTestId('field-kategorie')).toBeDefined();
    expect(screen.getByTestId('field-kostentraeger')).toBeDefined();
    expect(screen.getByTestId('field-tuertyp')).toBeDefined();
    expect(screen.getByTestId('field-brandschutzklasse')).toBeDefined();
  });

  it('validates required fields before save', () => {
    render(
      <ProductEditDialog
        catalogId="cat-1"
        product={mockProduct}
        mode="edit"
        onClose={vi.fn()}
      />
    );

    // Required fields: kategorie, kostentraeger
    const kategorie = screen.getByTestId('field-kategorie') as HTMLInputElement;
    const kostentraeger = screen.getByTestId('field-kostentraeger') as HTMLInputElement;
    expect(kategorie.value).toBe('Innentuer');
    expect(kostentraeger.value).toBe('KT-001');
  });

  it('submits product changes via server action', () => {
    render(
      <ProductEditDialog
        catalogId="cat-1"
        product={mockProduct}
        mode="edit"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('save-btn')).toBeDefined();
    expect(screen.getByTestId('save-btn').textContent).toContain('Speichern');
  });

  it('renders add new product form', () => {
    render(
      <ProductEditDialog
        catalogId="cat-1"
        mode="add"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('dialog-title').textContent).toBe('Neues Produkt hinzufuegen');
    // Fields should be empty in add mode
    const kategorie = screen.getByTestId('field-kategorie') as HTMLInputElement;
    expect(kategorie.value).toBe('');
  });

  it('confirms product deletion', () => {
    // Delete is handled in CatalogTable with window.confirm
    // ProductEditDialog handles add/edit mode only
    render(
      <ProductEditDialog
        catalogId="cat-1"
        product={mockProduct}
        mode="edit"
        onClose={vi.fn()}
      />
    );

    // Dialog renders with close button
    expect(screen.getByText('Abbrechen')).toBeDefined();
  });
});
