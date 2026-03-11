import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock next/headers
vi.mock('next/headers', () => ({
  headers: vi.fn().mockResolvedValue(new Headers()),
}));

// Mock next/cache
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

// Mock auth
vi.mock('@/lib/auth', () => ({
  auth: {
    api: {
      getSession: vi.fn().mockResolvedValue({
        user: { id: 'user-1', email: 'test@example.com' },
      }),
    },
  },
}));

// Mock prisma
const mockFindMany = vi.fn();
vi.mock('@/lib/prisma', () => ({
  default: {
    file: {
      findMany: (...args: unknown[]) => mockFindMany(...args),
    },
  },
}));

// Mock email
vi.mock('@/lib/email', () => ({
  resend: { emails: { send: vi.fn() } },
  EMAIL_FROM: 'test@test.com',
}));

// Mock emails template
vi.mock('@/emails/analysis-complete', () => ({
  AnalysisCompleteEmail: vi.fn(),
}));

describe('[ANLZ-04] prepareFilesForPython file bridge', () => {
  let originalFetch: typeof globalThis.fetch;
  let fetchCalls: Array<{ url: string; init?: RequestInit }>;

  beforeEach(() => {
    vi.clearAllMocks();
    fetchCalls = [];
    originalFetch = globalThis.fetch;

    // Mock fetch: first call = blob download, second call = Python upload
    globalThis.fetch = vi.fn().mockImplementation(async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      fetchCalls.push({ url: urlStr, init });

      // Blob download (downloadUrl)
      if (urlStr === 'https://blob.example.com/test-file.pdf') {
        return {
          ok: true,
          arrayBuffer: async () => new ArrayBuffer(10),
        };
      }

      // Python upload endpoint
      if (urlStr.includes('/api/upload/')) {
        return {
          ok: true,
          text: async () => '{"project_id":"py-abc123"}',
          json: async () => ({ project_id: 'py-abc123' }),
        };
      }

      return { ok: false, text: async () => 'Not found' };
    });

    mockFindMany.mockResolvedValue([
      {
        id: 'file-1',
        name: 'test-file.pdf',
        downloadUrl: 'https://blob.example.com/test-file.pdf',
        contentType: 'application/pdf',
      },
    ]);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('calls /api/upload/folder (not /api/upload/project)', async () => {
    const { prepareFilesForPython } = await import('@/lib/actions/analysis-actions');
    await prepareFilesForPython('proj-1', ['file-1']);

    const uploadCall = fetchCalls.find((c) => c.url.includes('/api/upload/'));
    expect(uploadCall).toBeDefined();
    expect(uploadCall!.url).toContain('/api/upload/folder');
    expect(uploadCall!.url).not.toContain('/api/upload/project');
  });

  it('sends X-Service-Key header (not X-API-Key)', async () => {
    const { prepareFilesForPython } = await import('@/lib/actions/analysis-actions');
    await prepareFilesForPython('proj-1', ['file-1']);

    const uploadCall = fetchCalls.find((c) => c.url.includes('/api/upload/'));
    expect(uploadCall).toBeDefined();
    const headers = uploadCall!.init?.headers as Record<string, string>;
    expect(headers).toHaveProperty('X-Service-Key');
    expect(headers).not.toHaveProperty('X-API-Key');
  });

  it('returns { success: true, pythonProjectId } on success', async () => {
    const { prepareFilesForPython } = await import('@/lib/actions/analysis-actions');
    const result = await prepareFilesForPython('proj-1', ['file-1']);

    expect(result).toEqual({
      success: true,
      pythonProjectId: 'py-abc123',
    });
  });

  it('does NOT include project_id in FormData', async () => {
    const { prepareFilesForPython } = await import('@/lib/actions/analysis-actions');
    await prepareFilesForPython('proj-1', ['file-1']);

    const uploadCall = fetchCalls.find((c) => c.url.includes('/api/upload/'));
    expect(uploadCall).toBeDefined();
    const body = uploadCall!.init?.body;
    expect(body).toBeInstanceOf(FormData);
    const formData = body as FormData;
    expect(formData.has('project_id')).toBe(false);
  });
});
