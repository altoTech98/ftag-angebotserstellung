import { describe, it, expect, vi, beforeEach } from 'vitest';

// Track the props passed to AnalysisCompleteEmail
let capturedEmailProps: Record<string, unknown> | null = null;

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  default: {
    analysis: {
      findUnique: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
  },
}));

// Mock auth
vi.mock('@/lib/auth', () => ({
  auth: {
    api: {
      getSession: vi.fn(),
      userHasPermission: vi.fn(),
    },
  },
}));

// Mock next/headers
vi.mock('next/headers', () => ({
  headers: vi.fn(() => Promise.resolve(new Headers())),
}));

// Mock next/cache
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

// Mock email
vi.mock('@/lib/email', () => ({
  resend: {
    emails: {
      send: vi.fn().mockResolvedValue({ id: 'email-1' }),
    },
  },
  EMAIL_FROM: 'test@ftag.ch',
}));

// Mock the email component to capture props
vi.mock('@/emails/analysis-complete', () => ({
  AnalysisCompleteEmail: vi.fn((props: Record<string, unknown>) => {
    capturedEmailProps = props;
    return null;
  }),
}));

import prisma from '@/lib/prisma';

describe('[INFRA-05] sendAnalysisCompleteEmail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedEmailProps = null;

    // Default: analysis with project and user
    vi.mocked(prisma.analysis.findUnique).mockResolvedValue({
      id: 'analysis-1',
      projectId: 'proj-1',
      startedBy: 'user-1',
      project: { name: 'Test Projekt' },
      result: null,
    } as any);

    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'user-1',
      name: 'Max Mustermann',
      email: 'max@ftag.ch',
    } as any);
  });

  it('includes partial entries in matchCount and calculates avgConfidence as percentage', async () => {
    vi.mocked(prisma.analysis.findUnique).mockResolvedValue({
      id: 'analysis-1',
      projectId: 'proj-1',
      startedBy: 'user-1',
      project: { name: 'Test Projekt' },
      result: {
        matched: [{ confidence: 0.9 }],
        partial: [{ confidence: 0.6 }],
        unmatched: [{}],
      },
    } as any);

    const { sendAnalysisCompleteEmail } = await import('@/lib/actions/analysis-actions');
    await sendAnalysisCompleteEmail('analysis-1');

    expect(capturedEmailProps).not.toBeNull();
    expect(capturedEmailProps!.matchCount).toBe(2);  // matched(1) + partial(1)
    expect(capturedEmailProps!.gapCount).toBe(1);     // unmatched(1)
    expect(capturedEmailProps!.avgConfidence).toBe(75); // ((0.9+0.6)/2)*100 = 75
  });

  it('counts only partial entries when no matched', async () => {
    vi.mocked(prisma.analysis.findUnique).mockResolvedValue({
      id: 'analysis-1',
      projectId: 'proj-1',
      startedBy: 'user-1',
      project: { name: 'Test Projekt' },
      result: {
        matched: [],
        partial: [{ confidence: 0.5 }, { confidence: 0.7 }],
        unmatched: [],
      },
    } as any);

    const { sendAnalysisCompleteEmail } = await import('@/lib/actions/analysis-actions');
    await sendAnalysisCompleteEmail('analysis-1');

    expect(capturedEmailProps).not.toBeNull();
    expect(capturedEmailProps!.matchCount).toBe(2);
    expect(capturedEmailProps!.avgConfidence).toBe(60); // ((0.5+0.7)/2)*100 = 60
  });

  it('returns zeros when no matches and no partial', async () => {
    vi.mocked(prisma.analysis.findUnique).mockResolvedValue({
      id: 'analysis-1',
      projectId: 'proj-1',
      startedBy: 'user-1',
      project: { name: 'Test Projekt' },
      result: {
        matched: [],
        partial: [],
        unmatched: [{}],
      },
    } as any);

    const { sendAnalysisCompleteEmail } = await import('@/lib/actions/analysis-actions');
    await sendAnalysisCompleteEmail('analysis-1');

    expect(capturedEmailProps).not.toBeNull();
    expect(capturedEmailProps!.matchCount).toBe(0);
    expect(capturedEmailProps!.gapCount).toBe(1);
    expect(capturedEmailProps!.avgConfidence).toBe(0);
  });

  it('handles null result gracefully', async () => {
    vi.mocked(prisma.analysis.findUnique).mockResolvedValue({
      id: 'analysis-1',
      projectId: 'proj-1',
      startedBy: 'user-1',
      project: { name: 'Test Projekt' },
      result: null,
    } as any);

    const { sendAnalysisCompleteEmail } = await import('@/lib/actions/analysis-actions');
    await sendAnalysisCompleteEmail('analysis-1');

    expect(capturedEmailProps).not.toBeNull();
    expect(capturedEmailProps!.matchCount).toBe(0);
    expect(capturedEmailProps!.gapCount).toBe(0);
    expect(capturedEmailProps!.avgConfidence).toBe(0);
  });
});
