import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepConfig } from '@/components/analysis/step-config';

const defaultConfig = {
  highThreshold: 90,
  lowThreshold: 70,
  validationPasses: 1,
};

describe('[ANLZ-03] Configuration step', () => {
  it('renders high threshold slider with default 90', () => {
    const onChange = vi.fn();
    render(<StepConfig config={defaultConfig} onConfigChange={onChange} />);

    const value = screen.getByTestId('high-threshold-value');
    expect(value.textContent).toBe('90%');
    expect(screen.getByText('Hohe Konfidenz ab')).toBeDefined();
  });

  it('renders low threshold slider with default 70', () => {
    const onChange = vi.fn();
    render(<StepConfig config={defaultConfig} onConfigChange={onChange} />);

    const value = screen.getByTestId('low-threshold-value');
    expect(value.textContent).toBe('70%');
    expect(screen.getByText('Niedrige Konfidenz unter')).toBeDefined();
  });

  it('validates lowThreshold < highThreshold via zone preview', () => {
    const onChange = vi.fn();
    // Render with high=80 low=70 -- valid config
    render(
      <StepConfig
        config={{ highThreshold: 80, lowThreshold: 70, validationPasses: 1 }}
        onConfigChange={onChange}
      />
    );

    // The zone preview should show three zones
    const redZone = screen.getByTestId('zone-red');
    const yellowZone = screen.getByTestId('zone-yellow');
    const greenZone = screen.getByTestId('zone-green');

    expect(redZone).toBeDefined();
    expect(yellowZone).toBeDefined();
    expect(greenZone).toBeDefined();

    // Red zone width should be 70%, yellow 10%, green 20%
    expect(redZone.style.width).toBe('70%');
    expect(yellowZone.style.width).toBe('10%');
    expect(greenZone.style.width).toBe('20%');
  });

  it('renders validation passes selector defaulting to 1', async () => {
    const onChange = vi.fn();
    render(<StepConfig config={defaultConfig} onConfigChange={onChange} />);

    expect(screen.getByTestId('validation-passes-value').textContent).toBe('1');

    // The button for pass 1 should be styled as selected (primary bg)
    const btn1 = screen.getByTestId('validation-pass-1');
    expect(btn1.className).toContain('bg-primary');

    // Click button 2
    const user = userEvent.setup();
    const btn2 = screen.getByTestId('validation-pass-2');
    await user.click(btn2);

    expect(onChange).toHaveBeenCalledWith({ validationPasses: 2 });
  });

  it('renders confidence zone preview bar', () => {
    const onChange = vi.fn();
    render(<StepConfig config={defaultConfig} onConfigChange={onChange} />);

    expect(screen.getByText('Konfidenz-Zonen Vorschau')).toBeDefined();
    expect(screen.getByText('Nicht zugeordnet')).toBeDefined();
    expect(screen.getByText('Teilweise')).toBeDefined();
    expect(screen.getByText('Zugeordnet')).toBeDefined();
  });
});
