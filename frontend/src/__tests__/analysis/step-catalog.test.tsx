import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StepCatalog } from '@/components/analysis/step-catalog';

describe('[ANLZ-02] Catalog selection step', () => {
  it('renders default catalog info card', () => {
    const onChange = vi.fn();
    render(<StepCatalog catalogId="ftag-default" onCatalogChange={onChange} />);

    expect(screen.getByText('FTAG Produktuebersicht')).toBeDefined();
    expect(screen.getByText(/~891 Produkte/)).toBeDefined();
    expect(screen.getByText(/Standard-Produktkatalog/)).toBeDefined();
  });

  it('shows pre-selected FTAG Produktuebersicht', () => {
    const onChange = vi.fn();
    render(<StepCatalog catalogId="ftag-default" onCatalogChange={onChange} />);

    const badge = screen.getByTestId('catalog-selected-badge');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('Ausgewaehlt');

    const card = screen.getByTestId('catalog-card');
    expect(card.className).toContain('ring-primary');
  });

  it('disables upload button with phase 14 tooltip', () => {
    const onChange = vi.fn();
    render(<StepCatalog catalogId="ftag-default" onCatalogChange={onChange} />);

    const uploadBtn = screen.getByTestId('upload-catalog-btn');
    expect(uploadBtn).toBeDefined();
    expect(uploadBtn.hasAttribute('disabled')).toBe(true);
    expect(screen.getByText(/Verfuegbar in Phase 14/)).toBeDefined();
  });

  it('auto-selects default catalog when catalogId is null', () => {
    const onChange = vi.fn();
    render(<StepCatalog catalogId={null} onCatalogChange={onChange} />);

    expect(onChange).toHaveBeenCalledWith('ftag-default');
  });
});
