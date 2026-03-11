import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch for token and polling
const mockFetch = vi.fn();
const originalFetch = globalThis.fetch;

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
  readyState = 0; // CONNECTING
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }, 0);
  }

  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }

  // Helper to simulate receiving a message
  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  // Helper to simulate an error
  simulateError() {
    this.onerror?.();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  globalThis.fetch = mockFetch;
  mockFetch.mockReset();
  MockEventSource.instances = [];
  vi.stubGlobal('EventSource', MockEventSource);

  // Default env
  vi.stubGlobal('process', {
    ...process,
    env: { ...process.env, NEXT_PUBLIC_PYTHON_SSE_URL: 'http://localhost:8000' },
  });
});

afterEach(() => {
  vi.useRealTimers();
  globalThis.fetch = originalFetch;
  vi.unstubAllGlobals();
});

describe('[INFRA-03] SSE Client', () => {
  it('connects to SSE with token', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    await connectToAnalysis('job-1', onEvent);

    // Should have fetched the token
    expect(mockFetch).toHaveBeenCalledWith('/api/backend/sse-token');

    // Should have created EventSource with correct URL
    expect(MockEventSource.instances.length).toBe(1);
    expect(MockEventSource.instances[0].url).toBe(
      'http://localhost:8000/api/analyze/stream/job-1?token=test-token'
    );
  });

  it('dispatches events to callback', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    await connectToAnalysis('job-1', onEvent);

    const es = MockEventSource.instances[0];
    es.simulateMessage({ status: 'processing', progress: '50%' });

    expect(onEvent).toHaveBeenCalledWith({ status: 'processing', progress: '50%' });
  });

  it('closes on completed status', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    await connectToAnalysis('job-1', onEvent);

    const es = MockEventSource.instances[0];
    es.simulateMessage({ status: 'completed', result: {} });

    expect(es.closed).toBe(true);
  });

  it('closes on failed status', async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    await connectToAnalysis('job-1', onEvent);

    const es = MockEventSource.instances[0];
    es.simulateMessage({ status: 'failed', error: 'Something went wrong' });

    expect(es.closed).toBe(true);
  });

  it('retries on error up to 3 times', async () => {
    // Token fetch for initial + retries
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    const onError = vi.fn();
    await connectToAnalysis('job-1', onEvent, onError);

    // Simulate error on first connection
    const es1 = MockEventSource.instances[0];
    es1.simulateError();

    // Advance timer for retry delay (1s * 1)
    await vi.advanceTimersByTimeAsync(1000);
    expect(MockEventSource.instances.length).toBe(2);

    // Error on retry 1
    MockEventSource.instances[1].simulateError();
    await vi.advanceTimersByTimeAsync(2000);
    expect(MockEventSource.instances.length).toBe(3);

    // Error on retry 2
    MockEventSource.instances[2].simulateError();
    await vi.advanceTimersByTimeAsync(3000);
    // After 3 failures, should have fallen back to polling (no more EventSource)
    // The 4th instance would be from polling, not SSE
  });

  it('falls back to polling after 3 retries', async () => {
    // Token fetch for initial + retries
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    const onError = vi.fn();
    await connectToAnalysis('job-1', onEvent, onError);

    // Fail 3 times
    MockEventSource.instances[0].simulateError();
    await vi.advanceTimersByTimeAsync(1000);
    MockEventSource.instances[1].simulateError();
    await vi.advanceTimersByTimeAsync(2000);
    MockEventSource.instances[2].simulateError();
    await vi.advanceTimersByTimeAsync(3000);

    // Reset fetch call count to track polling calls
    const fetchCallsBeforePolling = mockFetch.mock.calls.length;

    // Advance 3 seconds for first poll
    await vi.advanceTimersByTimeAsync(3000);

    // Should have made a polling fetch to the status endpoint
    const pollingCalls = mockFetch.mock.calls.slice(fetchCallsBeforePolling);
    const hasPollingCall = pollingCalls.some(
      (call) => typeof call[0] === 'string' && call[0].includes('/api/backend/analyze/status/job-1')
    );
    expect(hasPollingCall).toBe(true);
  });

  it('polling dispatches events', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    await connectToAnalysis('job-1', onEvent);

    // Fail SSE 3 times to trigger polling
    MockEventSource.instances[0].simulateError();
    await vi.advanceTimersByTimeAsync(1000);
    MockEventSource.instances[1].simulateError();
    await vi.advanceTimersByTimeAsync(2000);
    MockEventSource.instances[2].simulateError();
    await vi.advanceTimersByTimeAsync(3000);

    // Set up polling response
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'processing', progress: '75%' }))
    );

    // Advance for poll
    await vi.advanceTimersByTimeAsync(3000);

    // onEvent should have been called with polling data
    const calls = onEvent.mock.calls;
    const hasPollingEvent = calls.some(
      (call) => call[0]?.status === 'processing' && call[0]?.progress === '75%'
    );
    expect(hasPollingEvent).toBe(true);
  });

  it('close stops SSE and polling', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ token: 'test-token', expires_in: 600 }))
    );

    const { connectToAnalysis } = await import('@/lib/sse-client');
    const onEvent = vi.fn();
    const { close } = await connectToAnalysis('job-1', onEvent);

    const es = MockEventSource.instances[0];
    close();
    expect(es.closed).toBe(true);
  });

  it('throws without SSE URL configured', async () => {
    vi.stubGlobal('process', {
      ...process,
      env: { ...process.env, NEXT_PUBLIC_PYTHON_SSE_URL: '' },
    });

    // Need to re-import to get fresh module with new env
    vi.resetModules();
    const { connectToAnalysis } = await import('@/lib/sse-client');

    await expect(connectToAnalysis('job-1', vi.fn())).rejects.toThrow();
  });
});
