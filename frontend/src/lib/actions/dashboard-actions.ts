'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';

export type DashboardStats = {
  running: number;
  completed: number;
  failed: number;
  total: number;
};

export type ActivityEntry = {
  id: string;
  userId: string;
  action: string;
  details: string;
  targetId: string | null;
  targetType: string | null;
  createdAt: Date;
  user: { name: string | null; email: string };
};

export type MatchGapStatistics = {
  totalMatches: number;
  totalGaps: number;
  avgConfidence: number;
};

export async function getDashboardStats(): Promise<{
  stats: DashboardStats;
  recentActivity: ActivityEntry[];
}> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  // Get analysis counts grouped by status
  const statusGroups = await prisma.analysis.groupBy({
    by: ['status'],
    _count: { id: true },
  });

  const countByStatus: Record<string, number> = {};
  for (const group of statusGroups) {
    countByStatus[group.status] = group._count.id;
  }

  const stats: DashboardStats = {
    running: (countByStatus['running'] ?? 0) + (countByStatus['pending'] ?? 0),
    completed: countByStatus['completed'] ?? 0,
    failed: countByStatus['failed'] ?? 0,
    total: statusGroups.reduce((sum, g) => sum + g._count.id, 0),
  };

  // Get recent activity
  const recentActivity = await prisma.auditLog.findMany({
    take: 20,
    orderBy: { createdAt: 'desc' },
    include: {
      user: { select: { name: true, email: true } },
    },
  });

  return { stats, recentActivity };
}

export async function getMatchGapStatistics(): Promise<MatchGapStatistics> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const completedAnalyses = await prisma.analysis.findMany({
    where: {
      status: 'completed',
      result: { not: null },
    },
    select: { result: true },
    take: 100,
    orderBy: { endedAt: 'desc' },
  });

  let totalMatches = 0;
  let totalGaps = 0;
  let confidenceSum = 0;
  let confidenceCount = 0;

  for (const analysis of completedAnalyses) {
    if (!analysis.result || typeof analysis.result !== 'object') continue;

    const result = analysis.result as Record<string, unknown>;

    // Count matches
    const matchedItems = result.matched_items;
    if (Array.isArray(matchedItems)) {
      totalMatches += matchedItems.length;
      for (const item of matchedItems) {
        if (
          item &&
          typeof item === 'object' &&
          'confidence' in item &&
          typeof (item as Record<string, unknown>).confidence === 'number'
        ) {
          confidenceSum += (item as Record<string, unknown>).confidence as number;
          confidenceCount++;
        }
      }
    }

    // Count gaps
    const gapItems = result.gap_items;
    if (Array.isArray(gapItems)) {
      totalGaps += gapItems.length;
    }
  }

  const avgConfidence =
    confidenceCount > 0 ? Math.round((confidenceSum / confidenceCount) * 100) / 100 : 0;

  return { totalMatches, totalGaps, avgConfidence };
}
