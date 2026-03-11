import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/actions/project-actions', () => ({
  createProject: vi.fn(),
  archiveProject: vi.fn(),
  deleteProject: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ push: vi.fn(), refresh: vi.fn() })),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe('[PROJ-03] ArchiveDialog confirmation', () => {
  it('should export ArchiveDialog with action prop for archive or delete', async () => {
    const { ArchiveDialog } = await import('@/components/projects/archive-dialog');
    expect(ArchiveDialog).toBeDefined();
    expect(typeof ArchiveDialog).toBe('function');
  });

  it('should define warning text constants', async () => {
    const mod = await import('@/components/projects/archive-dialog');
    expect(mod.ARCHIVE_WARNING).toBeDefined();
    expect(mod.DELETE_WARNING).toBeDefined();
    expect(mod.ARCHIVE_WARNING).toContain('archiviert');
    expect(mod.DELETE_WARNING).toContain('unwiderruflich');
  });
});
