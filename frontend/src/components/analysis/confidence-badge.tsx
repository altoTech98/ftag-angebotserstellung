import { Badge } from '@/components/ui/badge';
import { getConfidenceLevel } from '@/components/analysis/types';

interface ConfidenceBadgeProps {
  confidence: number;
  highThreshold?: number;
  lowThreshold?: number;
}

const levelStyles: Record<string, string> = {
  high: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

export function ConfidenceBadge({
  confidence,
  highThreshold = 90,
  lowThreshold = 70,
}: ConfidenceBadgeProps) {
  // Show "Gap" for unmatched entries (confidence 0)
  if (confidence === 0) {
    return (
      <Badge className={levelStyles.low} data-testid="confidence-badge-gap">
        Gap
      </Badge>
    );
  }

  const level = getConfidenceLevel(confidence, highThreshold, lowThreshold);
  const pct = Math.round(confidence * 100);

  return (
    <Badge className={levelStyles[level]} data-testid={`confidence-badge-${level}`}>
      {pct}%
    </Badge>
  );
}
