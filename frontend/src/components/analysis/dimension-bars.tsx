'use client';

import type { MatchEntry } from '@/components/analysis/types';

interface DimensionBarsProps {
  entry: MatchEntry;
  highThreshold?: number;
  lowThreshold?: number;
}

const DIMENSION_PATTERNS: Record<string, RegExp> = {
  tuertyp: /Türtyp|tuertyp|Kategorie/i,
  material: /Material|Oberfläche|oberflaeche/i,
  brandschutz: /Brandschutz|EI\d+|Feuer/i,
  masse: /Masse|Dimension|Breite|Höhe|Lichtmass|zu gross|zu klein/i,
  ausfuehrung: /Ausführung|Flügel|Verglasung|fluegel/i,
  zubehoer: /Zubehör|Schloss|Band|Beschlag|zubehoer/i,
};

const DIMENSION_LABELS: Record<string, string> = {
  tuertyp: 'Tuertyp',
  material: 'Material',
  brandschutz: 'Brandschutz',
  masse: 'Masse',
  ausfuehrung: 'Ausfuehrung',
  zubehoer: 'Zubehoer',
};

function hasGapForDimension(entry: MatchEntry, pattern: RegExp): boolean {
  // Check gap_items
  for (const item of entry.gap_items) {
    if (pattern.test(item)) return true;
  }
  // Check missing_info fields
  for (const info of entry.missing_info) {
    if (pattern.test(info.feld)) return true;
  }
  return false;
}

function getBarColor(score: number, highThreshold: number, lowThreshold: number): string {
  if (score >= highThreshold) return 'bg-green-500';
  if (score >= lowThreshold) return 'bg-yellow-500';
  return 'bg-red-500';
}

export function DimensionBars({ entry, highThreshold = 90, lowThreshold = 70 }: DimensionBarsProps) {
  const baseScore = entry.confidence * 100;

  const dimensions = Object.entries(DIMENSION_PATTERNS).map(([key, pattern]) => {
    const hasGap = hasGapForDimension(entry, pattern);
    const score = hasGap
      ? Math.min(baseScore * 0.4, 40)
      : Math.min(baseScore * 1.1, 100);
    const roundedScore = Math.round(score);

    return {
      key,
      label: DIMENSION_LABELS[key],
      score: roundedScore,
      color: getBarColor(roundedScore, highThreshold, lowThreshold),
    };
  });

  return (
    <div
      className="grid grid-cols-1 gap-3 md:grid-cols-2"
      data-testid="dimension-bars"
    >
      {dimensions.map((dim) => (
        <div key={dim.key} className="flex items-center gap-3" data-testid={`dimension-${dim.key}`}>
          <span className="w-28 shrink-0 text-sm text-muted-foreground">
            {dim.label}
          </span>
          <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={`h-full rounded-full transition-all ${dim.color}`}
              style={{ width: `${dim.score}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right text-sm font-medium tabular-nums">
            {dim.score}%
          </span>
        </div>
      ))}
    </div>
  );
}
