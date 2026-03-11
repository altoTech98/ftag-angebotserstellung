'use client';

import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import type { WizardState } from './types';

interface StepConfigProps {
  config: WizardState['config'];
  onConfigChange: (config: Partial<WizardState['config']>) => void;
}

export function StepConfig({ config, onConfigChange }: StepConfigProps) {
  const { highThreshold, lowThreshold, validationPasses } = config;

  // Ensure lowThreshold < highThreshold
  function handleHighChange(value: number | readonly number[]) {
    const newHigh = Array.isArray(value) ? value[0] : value;
    if (newHigh > lowThreshold) {
      onConfigChange({ highThreshold: newHigh });
    }
  }

  function handleLowChange(value: number | readonly number[]) {
    const newLow = Array.isArray(value) ? value[0] : value;
    if (newLow < highThreshold) {
      onConfigChange({ lowThreshold: newLow });
    }
  }

  // Calculate zone percentages for the preview bar
  const greenWidth = 100 - highThreshold;
  const yellowWidth = highThreshold - lowThreshold;
  const redWidth = lowThreshold;

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-base font-medium">Analyse konfigurieren</h3>
        <p className="text-sm text-muted-foreground">
          Passen Sie die Schwellenwerte fuer die Konfidenz-Bewertung an.
        </p>
      </div>

      {/* High threshold slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="high-threshold">Hohe Konfidenz ab</Label>
          <span
            className="text-sm font-medium tabular-nums text-green-600"
            data-testid="high-threshold-value"
          >
            {highThreshold}%
          </span>
        </div>
        <Slider
          id="high-threshold"
          min={50}
          max={100}
          step={5}
          value={[highThreshold]}
          onValueChange={handleHighChange}
          aria-label="Hohe Konfidenz ab"
          data-testid="high-threshold-slider"
        />
        <p className="text-xs text-muted-foreground">
          Positionen ab diesem Wert gelten als sicher zugeordnet.
        </p>
      </div>

      {/* Low threshold slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="low-threshold">Niedrige Konfidenz unter</Label>
          <span
            className="text-sm font-medium tabular-nums text-red-600"
            data-testid="low-threshold-value"
          >
            {lowThreshold}%
          </span>
        </div>
        <Slider
          id="low-threshold"
          min={30}
          max={90}
          step={5}
          value={[lowThreshold]}
          onValueChange={handleLowChange}
          aria-label="Niedrige Konfidenz unter"
          data-testid="low-threshold-slider"
        />
        <p className="text-xs text-muted-foreground">
          Positionen unter diesem Wert gelten als nicht zugeordnet.
        </p>
      </div>

      {/* Confidence zone preview bar */}
      <div className="space-y-2">
        <Label>Konfidenz-Zonen Vorschau</Label>
        <div className="flex h-6 w-full overflow-hidden rounded-md text-xs font-medium">
          <div
            className="flex items-center justify-center bg-red-500/80 text-white"
            style={{ width: `${redWidth}%` }}
            data-testid="zone-red"
          >
            {redWidth > 15 && `<${lowThreshold}%`}
          </div>
          <div
            className="flex items-center justify-center bg-yellow-500/80 text-white"
            style={{ width: `${yellowWidth}%` }}
            data-testid="zone-yellow"
          >
            {yellowWidth > 15 && `${lowThreshold}-${highThreshold}%`}
          </div>
          <div
            className="flex items-center justify-center bg-green-500/80 text-white"
            style={{ width: `${greenWidth}%` }}
            data-testid="zone-green"
          >
            {greenWidth > 10 && `>${highThreshold}%`}
          </div>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Nicht zugeordnet</span>
          <span>Teilweise</span>
          <span>Zugeordnet</span>
        </div>
      </div>

      {/* Validation passes */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="validation-passes">Validierungsdurchlaeufe</Label>
          <span className="text-sm font-medium tabular-nums" data-testid="validation-passes-value">
            {validationPasses}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onConfigChange({ validationPasses: n })}
              className={`flex size-10 items-center justify-center rounded-md border text-sm font-medium transition-colors ${
                validationPasses === n
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border hover:bg-muted'
              }`}
              aria-label={`${n} Validierungsdurchlauf${n > 1 ? 'e' : ''}`}
              data-testid={`validation-pass-${n}`}
            >
              {n}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Mehrfache Durchlaeufe erhoehen die Genauigkeit, dauern aber laenger.
        </p>
      </div>
    </div>
  );
}
