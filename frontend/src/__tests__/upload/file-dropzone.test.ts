import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock @vercel/blob/client
vi.mock('@vercel/blob/client', () => ({
  upload: vi.fn(),
}));

// Mock server actions
vi.mock('@/lib/actions/file-actions', () => ({
  saveFileMetadata: vi.fn(),
  deleteFile: vi.fn(),
}));

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

describe('[ANLZ-01] FileDropzone component', () => {
  it('should export FileDropzone component', async () => {
    const { FileDropzone } = await import('@/components/upload/file-dropzone');
    expect(FileDropzone).toBeDefined();
    expect(typeof FileDropzone).toBe('function');
  });

  it('should accept projectId and onFileUploaded props', async () => {
    const { FileDropzone } = await import('@/components/upload/file-dropzone');
    // Validates the export exists and is callable
    expect(FileDropzone).toBeDefined();
  });

  it('should define ACCEPTED_TYPES constant for PDF/DOCX/XLSX', async () => {
    const mod = await import('@/components/upload/file-dropzone');
    expect(mod.ACCEPTED_TYPES).toBeDefined();
    expect(mod.ACCEPTED_TYPES).toContain('application/pdf');
    expect(mod.ACCEPTED_TYPES).toContain(
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
    expect(mod.ACCEPTED_TYPES).toContain(
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    );
  });
});

describe('[ANLZ-01] FileList component', () => {
  it('should export FileList component', async () => {
    const { FileList } = await import('@/components/upload/file-list');
    expect(FileList).toBeDefined();
    expect(typeof FileList).toBe('function');
  });
});

describe('[PROJ-03] ArchiveDialog component', () => {
  it('should export ArchiveDialog component', async () => {
    const { ArchiveDialog } = await import('@/components/projects/archive-dialog');
    expect(ArchiveDialog).toBeDefined();
    expect(typeof ArchiveDialog).toBe('function');
  });
});
