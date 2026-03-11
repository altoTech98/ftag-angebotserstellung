'use client';

import { Activity, CheckCircle, XCircle, Target } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { DashboardStats, MatchGapStatistics } from '@/lib/actions/dashboard-actions';

type StatCardProps = {
  label: string;
  value: number;
  icon: React.ReactNode;
  accentClass: string;
};

function StatCard({ label, value, icon, accentClass }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2">
        <div className={`flex items-center gap-2 ${accentClass}`}>
          {icon}
          <span className="text-sm text-muted-foreground">{label}</span>
        </div>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

export function StatCards({
  stats,
  matchStats,
}: {
  stats: DashboardStats;
  matchStats: MatchGapStatistics;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Laufende Analysen"
        value={stats.running}
        icon={<Activity className="size-5" />}
        accentClass="text-blue-500"
      />
      <StatCard
        label="Abgeschlossene Analysen"
        value={stats.completed}
        icon={<CheckCircle className="size-5" />}
        accentClass="text-green-500"
      />
      <StatCard
        label="Fehlerhafte Analysen"
        value={stats.failed}
        icon={<XCircle className="size-5" />}
        accentClass="text-red-500"
      />
      <StatCard
        label="Gesamt-Matches"
        value={matchStats.totalMatches}
        icon={<Target className="size-5" />}
        accentClass="text-[var(--ftag-rot,#c41230)]"
      />
    </div>
  );
}
