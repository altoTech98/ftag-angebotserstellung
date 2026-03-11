import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  default: {
    project: {
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      findUnique: vi.fn(),
    },
    file: {
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

// Mock @vercel/blob
vi.mock('@vercel/blob', () => ({
  del: vi.fn(),
}));

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';

describe('[PROJ-01] createProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
    vi.mocked(auth.api.userHasPermission).mockResolvedValue({ success: true } as any);
  });

  it('should create a project with name, customer, deadline, description, ownerId', async () => {
    const mockProject = {
      id: 'proj-1',
      name: 'Test Project',
      customer: 'Kunde AG',
      deadline: new Date('2026-06-01'),
      description: 'Test description',
      status: 'active',
      ownerId: 'user-1',
    };
    vi.mocked(prisma.project.create).mockResolvedValue(mockProject as any);

    const { createProject } = await import('@/lib/actions/project-actions');

    const formData = new FormData();
    formData.set('name', 'Test Project');
    formData.set('customer', 'Kunde AG');
    formData.set('deadline', '2026-06-01');
    formData.set('description', 'Test description');

    const result = await createProject(formData);

    expect(prisma.project.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        name: 'Test Project',
        customer: 'Kunde AG',
        ownerId: 'user-1',
      }),
    });
    expect(result).toEqual(mockProject);
  });
});

describe('[PROJ-03] archiveProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
  });

  it('should set project status to archived', async () => {
    vi.mocked(prisma.project.findUnique).mockResolvedValue({
      id: 'proj-1',
      ownerId: 'user-1',
    } as any);
    vi.mocked(prisma.project.update).mockResolvedValue({
      id: 'proj-1',
      status: 'archived',
    } as any);

    const { archiveProject } = await import('@/lib/actions/project-actions');
    await archiveProject('proj-1');

    expect(prisma.project.update).toHaveBeenCalledWith({
      where: { id: 'proj-1' },
      data: { status: 'archived' },
    });
  });
});

describe('[PROJ-03] deleteProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'admin' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
  });

  it('should delete project and associated blob files', async () => {
    const { del } = await import('@vercel/blob');

    vi.mocked(prisma.project.findUnique).mockResolvedValue({
      id: 'proj-1',
      ownerId: 'user-1',
    } as any);
    vi.mocked(prisma.file.findMany).mockResolvedValue([
      { blobUrl: 'https://blob.vercel-storage.com/file1' },
      { blobUrl: 'https://blob.vercel-storage.com/file2' },
    ] as any);
    vi.mocked(prisma.project.delete).mockResolvedValue({ id: 'proj-1' } as any);

    const { deleteProject } = await import('@/lib/actions/project-actions');
    await deleteProject('proj-1');

    expect(del).toHaveBeenCalledWith([
      'https://blob.vercel-storage.com/file1',
      'https://blob.vercel-storage.com/file2',
    ]);
    expect(prisma.project.delete).toHaveBeenCalledWith({
      where: { id: 'proj-1' },
    });
  });
});
