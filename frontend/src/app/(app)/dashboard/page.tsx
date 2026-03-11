import { getDashboardStats, getMatchGapStatistics } from '@/lib/actions/dashboard-actions';
import { DashboardClient } from './client';

export default async function DashboardPage() {
  const [{ stats, recentActivity }, matchStats] = await Promise.all([
    getDashboardStats(),
    getMatchGapStatistics(),
  ]);

  return (
    <DashboardClient
      stats={stats}
      activity={recentActivity}
      matchStats={matchStats}
    />
  );
}
