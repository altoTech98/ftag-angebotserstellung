import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock prisma
vi.mock('@/lib/prisma', () => ({
  default: {
    file: {
      create: vi.fn(),
      findUnique: vi.fn(),
      delete: vi.fn(),
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

// Mock next/cache
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

// Mock @vercel/blob
vi.mock('@vercel/blob', () => ({
  del: vi.fn(),
}));

// Mock @vercel/blob/client
vi.mock('@vercel/blob/client', () => ({
  handleUpload: vi.fn(),
}));

import { auth } from '@/lib/auth';
import prisma from '@/lib/prisma';

describe('[INFRA-04] Upload API route', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should reject unauthenticated requests with 401', async () => {
    vi.mocked(auth.api.getSession).mockResolvedValue(null as any);

    const { POST } = await import('@/app/api/upload/route');

    const request = new Request('http://localhost:3000/api/upload', {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' },
    });

    const response = await POST(request);
    expect(response.status).toBe(401);

    const body = await response.json();
    expect(body.error).toBeDefined();
  });

  it('should call handleUpload for authenticated requests', async () => {
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);

    const { handleUpload } = await import('@vercel/blob/client');
    vi.mocked(handleUpload).mockResolvedValue(
      new Response(JSON.stringify({ url: 'https://blob.vercel-storage.com/test' }), {
        headers: { 'Content-Type': 'application/json' },
      }) as any
    );

    const { POST } = await import('@/app/api/upload/route');

    const request = new Request('http://localhost:3000/api/upload', {
      method: 'POST',
      body: JSON.stringify({ type: 'blob.generate-client-token' }),
      headers: { 'Content-Type': 'application/json' },
    });

    await POST(request);
    expect(handleUpload).toHaveBeenCalled();
  });
});

describe('[ANLZ-01] saveFileMetadata', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
  });

  it('should create a File record linked to project', async () => {
    vi.mocked(prisma.file.create).mockResolvedValue({
      id: 'file-1',
      name: 'tender.pdf',
      blobUrl: 'https://blob.vercel-storage.com/tender.pdf',
      downloadUrl: 'https://blob.vercel-storage.com/tender.pdf?download=1',
      size: 1024,
      contentType: 'application/pdf',
      projectId: 'proj-1',
      uploadedBy: 'user-1',
    } as any);

    const { saveFileMetadata } = await import('@/lib/actions/file-actions');
    const result = await saveFileMetadata({
      name: 'tender.pdf',
      blobUrl: 'https://blob.vercel-storage.com/tender.pdf',
      downloadUrl: 'https://blob.vercel-storage.com/tender.pdf?download=1',
      size: 1024,
      contentType: 'application/pdf',
      projectId: 'proj-1',
    });

    expect(prisma.file.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        name: 'tender.pdf',
        blobUrl: 'https://blob.vercel-storage.com/tender.pdf',
        projectId: 'proj-1',
        uploadedBy: 'user-1',
      }),
    });
    expect(result).toBeDefined();
  });
});

describe('[ANLZ-01] deleteFile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth.api.getSession).mockResolvedValue({
      user: { id: 'user-1', name: 'Test', email: 'test@ftag.ch', role: 'manager' },
      session: { id: 'sess-1', token: 'tok', expiresAt: new Date() },
    } as any);
  });

  it('should remove File record and call blob del()', async () => {
    const { del } = await import('@vercel/blob');

    vi.mocked(prisma.file.findUnique).mockResolvedValue({
      id: 'file-1',
      blobUrl: 'https://blob.vercel-storage.com/tender.pdf',
      projectId: 'proj-1',
    } as any);
    vi.mocked(prisma.file.delete).mockResolvedValue({ id: 'file-1' } as any);

    const { deleteFile } = await import('@/lib/actions/file-actions');
    await deleteFile('file-1');

    expect(del).toHaveBeenCalledWith('https://blob.vercel-storage.com/tender.pdf');
    expect(prisma.file.delete).toHaveBeenCalledWith({
      where: { id: 'file-1' },
    });
  });
});
