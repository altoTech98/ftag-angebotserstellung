import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  default: {
    analysis: {
      findMany: vi.fn(),
    },
  },
}));

// Mock auth
vi.mock('@/lib/auth', () => ({
  auth: {
    api: {
      getSession: vi.fn(),
    },
  },
}));

// Mock next/headers
vi.mock('next/headers', () => ({
  headers: vi.fn(() => Promise.resolve(new Headers())),
}));

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';

describe('[DASH-03] getMatchGapStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
  });

  it('returns correct counts and avgConfidence for matched + partial + unmatched', async () => {
    vi.mocked(prisma.analysis.findMany).mockResolvedValue([
      {
        result: {
          matched: [{ confidence: 0.9 }],
          partial: [{ confidence: 0.7 }],
          unmatched: [{}],
        },
      },
    ] as any);

    const { getMatchGapStatistics } = await import('@/lib/actions/dashboard-actions');
    const stats = await getMatchGapStatistics();

    expect(stats.totalMatches).toBe(2); // matched(1) + partial(1)
    expect(stats.totalGaps).toBe(1);    // unmatched(1)
    expect(stats.avgConfidence).toBe(0.8); // (0.9+0.7)/2 = 0.8
  });

  it('returns zeros for empty arrays', async () => {
    vi.mocked(prisma.analysis.findMany).mockResolvedValue([
      {
        result: {
          matched: [],
          partial: [],
          unmatched: [],
        },
      },
    ] as any);

    const { getMatchGapStatistics } = await import('@/lib/actions/dashboard-actions');
    const stats = await getMatchGapStatistics();

    expect(stats.totalMatches).toBe(0);
    expect(stats.totalGaps).toBe(0);
    expect(stats.avgConfidence).toBe(0);
  });

  it('counts partial entries as matches with their confidence averaged', async () => {
    vi.mocked(prisma.analysis.findMany).mockResolvedValue([
      {
        result: {
          matched: [],
          partial: [{ confidence: 0.6 }, { confidence: 0.8 }],
          unmatched: [],
        },
      },
    ] as any);

    const { getMatchGapStatistics } = await import('@/lib/actions/dashboard-actions');
    const stats = await getMatchGapStatistics();

    expect(stats.totalMatches).toBe(2); // only partial entries
    expect(stats.totalGaps).toBe(0);
    expect(stats.avgConfidence).toBe(0.7); // (0.6+0.8)/2 = 0.7
  });

  it('gracefully returns zeros for null/missing result', async () => {
    vi.mocked(prisma.analysis.findMany).mockResolvedValue([
      { result: null },
      { result: 'not-an-object' },
    ] as any);

    const { getMatchGapStatistics } = await import('@/lib/actions/dashboard-actions');
    const stats = await getMatchGapStatistics();

    expect(stats.totalMatches).toBe(0);
    expect(stats.totalGaps).toBe(0);
    expect(stats.avgConfidence).toBe(0);
  });
});
