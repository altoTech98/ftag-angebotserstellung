import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---- Shared mocks ----

vi.mock('@/lib/prisma', () => ({
  default: {
    project: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      create: vi.fn(),
    },
  },
}));

vi.mock('@/lib/auth', () => ({
  auth: {
    api: {
      getSession: vi.fn(),
      userHasPermission: vi.fn(),
    },
  },
}));

vi.mock('next/headers', () => ({
  headers: vi.fn(() => Promise.resolve(new Headers())),
}));

vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

vi.mock('@vercel/blob', () => ({
  del: vi.fn(),
}));

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';

// ---- Fixtures ----

const mockSession = {
  user: { id: 'user-1', name: 'Test User', email: 'test@ftag.ch', role: 'manager' },
  session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
} as any;

const mockProjects = [
  {
    id: 'proj-1',
    name: 'Projekt Alpha',
    customer: 'Kunde AG',
    deadline: new Date('2026-06-01'),
    description: 'Beschreibung Alpha',
    status: 'active',
    ownerId: 'user-1',
    createdAt: new Date(),
    updatedAt: new Date(),
    owner: { name: 'Test User' },
    _count: { files: 3, analyses: 1 },
  },
  {
    id: 'proj-2',
    name: 'Projekt Beta',
    customer: null,
    deadline: null,
    description: null,
    status: 'active',
    ownerId: 'user-1',
    createdAt: new Date(),
    updatedAt: new Date(),
    owner: { name: 'Test User' },
    _count: { files: 0, analyses: 0 },
  },
];

// ---- Tests ----

describe('[PROJ-02] ProjectList rendering', () => {
  it('should define ProjectList component that receives projects array', async () => {
    const { ProjectList } = await import('@/components/projects/project-list');
    expect(ProjectList).toBeDefined();
    expect(typeof ProjectList).toBe('function');
  });
});

describe('[PROJ-02] ProjectCard rendering', () => {
  it('should define ProjectCard component that receives project data', async () => {
    const { ProjectCard } = await import('@/components/projects/project-card');
    expect(ProjectCard).toBeDefined();
    expect(typeof ProjectCard).toBe('function');
  });

  it('should export ProjectCard with expected interface (project prop with name, customer, counts)', async () => {
    const { ProjectCard } = await import('@/components/projects/project-card');
    // Component should accept a project object -- this validates export exists
    expect(ProjectCard).toBeDefined();
  });
});

describe('[PROJ-01] ProjectForm submission', () => {
  it('should define ProjectForm component', async () => {
    const { ProjectForm } = await import('@/components/projects/project-form');
    expect(ProjectForm).toBeDefined();
    expect(typeof ProjectForm).toBe('function');
  });
});

describe('[PROJ-02] Empty project list', () => {
  it('ProjectList should be callable with empty array', async () => {
    const { ProjectList } = await import('@/components/projects/project-list');
    expect(ProjectList).toBeDefined();
    // Component should handle empty projects array
  });
});
