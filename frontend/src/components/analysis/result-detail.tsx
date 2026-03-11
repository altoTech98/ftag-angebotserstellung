'use client';

import { Bot } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { DimensionBars } from '@/components/analysis/dimension-bars';
import { ComparisonCard } from '@/components/analysis/comparison-card';
import type { MatchEntry, WizardState } from '@/components/analysis/types';

interface ResultDetailProps {
  entry: MatchEntry;
  config: WizardState['config'];
}

export function ResultDetail({ entry, config }: ResultDetailProps) {
  const isGap = entry.status === 'unmatched';

  return (
    <div
      className="border-t bg-muted/30 p-4 space-y-5"
      data-testid="result-detail"
      style={{
        animation: 'resultDetailExpand 200ms ease-out',
      }}
    >
      {/* AI Reasoning */}
      <section data-testid="ai-reasoning">
        <div className="mb-2 flex items-center gap-2">
          <Badge variant="secondary" className="gap-1">
            <Bot className="size-3" />
            KI
          </Badge>
          <h4 className="text-sm font-semibold">AI-Begruendung</h4>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {entry.reason || 'Keine Begruendung verfuegbar'}
        </p>
      </section>

      {/* Confidence Dimensions */}
      <section data-testid="confidence-dimensions">
        <h4 className="mb-3 text-sm font-semibold">Konfidenz-Dimensionen</h4>
        <DimensionBars
          entry={entry}
          highThreshold={config.highThreshold}
          lowThreshold={config.lowThreshold}
        />
      </section>

      {/* Comparison / Gap details */}
      <section data-testid="comparison-section">
        <h4 className="mb-3 text-sm font-semibold">
          {isGap ? 'Abgelehnte Produkte' : 'Vergleich'}
        </h4>
        <ComparisonCard entry={entry} />
      </section>
    </div>
  );
}
