import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock next/headers
vi.mock('next/headers', () => ({
  headers: vi.fn().mockResolvedValue(new Headers()),
}));

// Mock @/lib/auth
const mockGetSession = vi.fn();
vi.mock('@/lib/auth', () => ({
  auth: {
    api: {
      getSession: mockGetSession,
    },
  },
}));

// Store original fetch
const originalFetch = globalThis.fetch;
const mockFetch = vi.fn();

beforeEach(() => {
  globalThis.fetch = mockFetch;
  mockFetch.mockReset();
  mockGetSession.mockReset();

  // Default env
  vi.stubEnv('PYTHON_BACKEND_URL', 'http://localhost:8000');
  vi.stubEnv('PYTHON_SERVICE_KEY', 'test-service-key');
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.unstubAllEnvs();
});

describe('[INFRA-03] BFF Proxy', () => {
  it('returns 401 without session', async () => {
    mockGetSession.mockResolvedValue(null);
    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/analyze');
    const response = await GET(request, { params: Promise.resolve({ path: ['analyze'] }) });
    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error).toBeDefined();
  });

  it('forwards with X-Service-Key header', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'analyst' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products');
    await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    expect(mockFetch).toHaveBeenCalled();
    const [url, options] = mockFetch.mock.calls[0];
    expect(options.headers['X-Service-Key']).toBe('test-service-key');
  });

  it('forwards user context headers', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'manager' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products');
    await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers['X-User-Id']).toBe('user-1');
    expect(options.headers['X-User-Role']).toBe('manager');
    expect(options.headers['X-User-Email']).toBe('test@test.com');
  });

  it('strips /api/backend prefix and maps to /api/', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'viewer' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200 }));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/analyze');
    await GET(request, { params: Promise.resolve({ path: ['analyze'] }) });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/analyze');
  });

  it('forwards query params', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'viewer' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200 }));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products?q=door&limit=10');
    await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('?q=door&limit=10');
  });

  it('forwards POST body', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'analyst' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200 }));

    const { POST } = await import('@/app/api/backend/[...path]/route');
    const body = JSON.stringify({ file_id: 'abc' });
    const request = new Request('http://localhost:3000/api/backend/analyze', {
      method: 'POST',
      body,
      headers: { 'Content-Type': 'application/json' },
    });
    await POST(request, { params: Promise.resolve({ path: ['analyze'] }) });

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(options.body).toBeDefined();
  });

  it('passes through Python error responses', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'viewer' },
      session: {},
    });
    const errorBody = JSON.stringify({ detail: 'Validation error' });
    mockFetch.mockResolvedValue(new Response(errorBody, {
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: { 'Content-Type': 'application/json' },
    }));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products');
    const response = await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    expect(response.status).toBe(422);
    const body = await response.json();
    expect(body.detail).toBe('Validation error');
  });

  it('returns 504 on timeout', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'viewer' },
      session: {},
    });
    const abortError = new DOMException('The operation was aborted', 'AbortError');
    mockFetch.mockRejectedValue(abortError);

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products');
    const response = await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    expect(response.status).toBe(504);
  });

  it('returns 502 on connection error', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'viewer' },
      session: {},
    });
    mockFetch.mockRejectedValue(new Error('ECONNREFUSED'));

    const { GET } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/products');
    const response = await GET(request, { params: Promise.resolve({ path: ['products'] }) });

    expect(response.status).toBe(502);
  });

  it('uses long timeout for analyze paths', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'analyst' },
      session: {},
    });
    mockFetch.mockResolvedValue(new Response('{}', { status: 200 }));

    const { POST } = await import('@/app/api/backend/[...path]/route');
    const request = new Request('http://localhost:3000/api/backend/analyze', {
      method: 'POST',
      body: '{}',
      headers: { 'Content-Type': 'application/json' },
    });
    await POST(request, { params: Promise.resolve({ path: ['analyze'] }) });

    const [, options] = mockFetch.mock.calls[0];
    // The signal should be from an AbortController -- we check it's present
    expect(options.signal).toBeDefined();
  });
});
