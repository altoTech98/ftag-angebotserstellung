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

beforeEach(() => {
  mockGetSession.mockReset();
  vi.stubEnv('SSE_TOKEN_SECRET', 'test-sse-secret');
  vi.stubEnv('PYTHON_SERVICE_KEY', 'test-service-key');
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('[INFRA-03] SSE Token', () => {
  it('returns 401 without session', async () => {
    mockGetSession.mockResolvedValue(null);
    const { GET } = await import('@/app/api/backend/sse-token/route');
    const request = new Request('http://localhost:3000/api/backend/sse-token');
    const response = await GET(request);
    expect(response.status).toBe(401);
  });

  it('returns signed token with expires_in', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'analyst' },
      session: {},
    });
    const { GET } = await import('@/app/api/backend/sse-token/route');
    const request = new Request('http://localhost:3000/api/backend/sse-token');
    const response = await GET(request);

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.token).toBeDefined();
    expect(typeof body.token).toBe('string');
    expect(body.expires_in).toBeDefined();
    expect(typeof body.expires_in).toBe('number');
  });

  it('returns token in base64url.hex format', async () => {
    mockGetSession.mockResolvedValue({
      user: { id: 'user-1', email: 'test@test.com', role: 'analyst' },
      session: {},
    });
    const { GET } = await import('@/app/api/backend/sse-token/route');
    const request = new Request('http://localhost:3000/api/backend/sse-token');
    const response = await GET(request);

    const body = await response.json();
    const parts = body.token.split('.');
    expect(parts.length).toBe(2);
    // Payload part should be non-empty
    expect(parts[0].length).toBeGreaterThan(0);
    // Signature part should be exactly 64 hex characters (SHA-256 hex digest)
    expect(parts[1]).toMatch(/^[0-9a-f]{64}$/);
  });
});
