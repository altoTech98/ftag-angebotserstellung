import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  default: {
    project: {
      findUnique: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
    projectShare: {
      create: vi.fn(),
      delete: vi.fn(),
      findUnique: vi.fn(),
      findMany: vi.fn(),
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

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';

const mockSession = {
  user: { id: 'user-1', name: 'Owner', email: 'owner@ftag.ch', role: 'manager' },
  session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
};

describe('[PROJ-04] shareProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    vi.mocked(auth.api.getSession).mockResolvedValue(mockSession as any);
    vi.mocked(auth.api.userHasPermission).mockResolvedValue({ success: true } as any);
    vi.mocked(prisma.project.findUnique).mockResolvedValue({
      id: 'proj-1',
      ownerId: 'user-1',
    } as any);
  });

  it('should create ProjectShare record for valid email', async () => {
    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'user-2',
      name: 'Target User',
      email: 'target@ftag.ch',
    } as any);
    vi.mocked(prisma.projectShare.findUnique).mockResolvedValue(null);
    const mockShare = {
      id: 'share-1',
      projectId: 'proj-1',
      userId: 'user-2',
      role: 'viewer',
    };
    vi.mocked(prisma.projectShare.create).mockResolvedValue(mockShare as any);

    const { shareProject } = await import('@/lib/actions/project-actions');
    const result = await shareProject('proj-1', 'target@ftag.ch');

    expect(prisma.projectShare.create).toHaveBeenCalledWith({
      data: { projectId: 'proj-1', userId: 'user-2', role: 'viewer' },
    });
    expect(result).toEqual({ success: true, share: mockShare });
  });

  it('should reject if user email not found', async () => {
    vi.mocked(prisma.user.findUnique).mockResolvedValue(null);

    const { shareProject } = await import('@/lib/actions/project-actions');
    const result = await shareProject('proj-1', 'nobody@ftag.ch');

    expect(result).toEqual({ error: 'Benutzer nicht gefunden' });
    expect(prisma.projectShare.create).not.toHaveBeenCalled();
  });

  it('should reject if already shared with that user', async () => {
    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'user-2',
      name: 'Target',
      email: 'target@ftag.ch',
    } as any);
    vi.mocked(prisma.projectShare.findUnique).mockResolvedValue({
      id: 'share-existing',
    } as any);

    const { shareProject } = await import('@/lib/actions/project-actions');
    const result = await shareProject('proj-1', 'target@ftag.ch');

    expect(result).toEqual({ error: 'Projekt bereits geteilt' });
    expect(prisma.projectShare.create).not.toHaveBeenCalled();
  });

  it('should reject if user lacks project:share permission', async () => {
    vi.mocked(auth.api.userHasPermission).mockResolvedValue({ success: false } as any);

    const { shareProject } = await import('@/lib/actions/project-actions');
    await expect(shareProject('proj-1', 'target@ftag.ch')).rejects.toThrow('Keine Berechtigung');
  });
});

describe('[PROJ-04] removeShare', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    vi.mocked(auth.api.getSession).mockResolvedValue(mockSession as any);
  });

  it('should delete ProjectShare record', async () => {
    vi.mocked(prisma.projectShare.findUnique).mockResolvedValue({
      id: 'share-1',
      projectId: 'proj-1',
      userId: 'user-2',
      project: { ownerId: 'user-1' },
    } as any);
    vi.mocked(prisma.projectShare.delete).mockResolvedValue({ id: 'share-1' } as any);

    const { removeShare } = await import('@/lib/actions/project-actions');
    await removeShare('share-1');

    expect(prisma.projectShare.delete).toHaveBeenCalledWith({
      where: { id: 'share-1' },
    });
  });
});

describe('[PROJ-04] getProjectShares', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    vi.mocked(auth.api.getSession).mockResolvedValue(mockSession as any);
  });

  it('should return shares with user details', async () => {
    const mockShares = [
      {
        id: 'share-1',
        projectId: 'proj-1',
        userId: 'user-2',
        role: 'viewer',
        user: { id: 'user-2', name: 'User Two', email: 'user2@ftag.ch' },
      },
    ];
    vi.mocked(prisma.projectShare.findMany).mockResolvedValue(mockShares as any);

    const { getProjectShares } = await import('@/lib/actions/project-actions');
    const result = await getProjectShares('proj-1');

    expect(prisma.projectShare.findMany).toHaveBeenCalledWith({
      where: { projectId: 'proj-1' },
      include: { user: { select: { id: true, name: true, email: true } } },
    });
    expect(result).toEqual(mockShares);
  });
});
