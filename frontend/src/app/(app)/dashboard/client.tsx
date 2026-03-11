'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { buttonVariants } from '@/components/ui/button';
import { StatCards } from './stat-cards';
import { ActivityFeed } from './activity-feed';
import { StatisticsWidget } from './statistics-widget';
import type {
  DashboardStats,
  ActivityEntry,
  MatchGapStatistics,
} from '@/lib/actions/dashboard-actions';

export function DashboardClient({
  stats,
  activity,
  matchStats,
}: {
  stats: DashboardStats;
  activity: ActivityEntry[];
  matchStats: MatchGapStatistics;
}) {
  return (
    <div className="space-y-6">
      {/* Page header with action button */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Willkommen bei FTAG Angebotserstellung
          </p>
        </div>
        <Link href="/neue-analyse" className={buttonVariants({ size: 'lg' })}>
          <Plus className="size-4" data-icon="inline-start" />
          Neue Analyse starten
        </Link>
      </div>

      {/* Stat cards row */}
      <StatCards stats={stats} matchStats={matchStats} />

      {/* Two-column layout: activity feed (wider) + statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <ActivityFeed entries={activity} />
        <StatisticsWidget stats={matchStats} />
      </div>
    </div>
  );
}
