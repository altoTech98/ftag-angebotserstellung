'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { MatchGapStatistics } from '@/lib/actions/dashboard-actions';

export function StatisticsWidget({ stats }: { stats: MatchGapStatistics }) {
  const total = stats.totalMatches + stats.totalGaps;
  const matchPercent = total > 0 ? Math.round((stats.totalMatches / total) * 100) : 0;
  const gapPercent = total > 0 ? 100 - matchPercent : 0;
  const hasData = total > 0 || stats.avgConfidence > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Statistik</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <p className="text-sm text-muted-foreground">Keine Analysedaten vorhanden</p>
        ) : (
          <div className="space-y-4">
            {/* Metric rows */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Matches</span>
                <span className="font-medium">{stats.totalMatches}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Gaps</span>
                <span className="font-medium">{stats.totalGaps}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Durchschnitts-Konfidenz</span>
                <span className="font-medium">
                  {Math.round(stats.avgConfidence * 100)}%
                </span>
              </div>
            </div>

            {/* Horizontal bar chart */}
            {total > 0 && (
              <div className="space-y-2">
                <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="bg-green-500 transition-all"
                    style={{ width: `${matchPercent}%` }}
                  />
                  <div
                    className="bg-red-500 transition-all"
                    style={{ width: `${gapPercent}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{matchPercent}% Matches</span>
                  <span>{gapPercent}% Gaps</span>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
