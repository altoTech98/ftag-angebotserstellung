export type AnalysisEvent = {
  status?: string;
  progress?: string;
  type?: string;
  [key: string]: unknown;
};

const MAX_SSE_RETRIES = 3;
const POLL_INTERVAL_MS = 3_000;

function getSseUrl(): string {
  const url =
    (typeof window !== 'undefined' && (window as Record<string, unknown>).__NEXT_PUBLIC_PYTHON_SSE_URL as string) ||
    process.env.NEXT_PUBLIC_PYTHON_SSE_URL ||
    '';
  if (!url) {
    throw new Error('NEXT_PUBLIC_PYTHON_SSE_URL ist nicht konfiguriert');
  }
  return url;
}

export async function connectToAnalysis(
  jobId: string,
  onEvent: (data: AnalysisEvent) => void,
  onError?: (error: Error) => void
): Promise<{ close: () => void }> {
  const pythonSseUrl = getSseUrl();

  // Fetch SSE token from BFF
  const tokenResponse = await fetch('/api/backend/sse-token');
  const { token } = await tokenResponse.json();

  let eventSource: EventSource | null = null;
  let pollingInterval: ReturnType<typeof setInterval> | null = null;
  let retryCount = 0;
  let closed = false;

  function cleanup() {
    closed = true;
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  function startPolling() {
    pollingInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/backend/analyze/status/${jobId}`);
        const data: AnalysisEvent = await response.json();
        onEvent(data);

        if (data.status === 'completed' || data.status === 'failed') {
          cleanup();
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      }
    }, POLL_INTERVAL_MS);
  }

  function connectSSE() {
    if (closed) return;

    const sseUrl = `${pythonSseUrl}/api/analyze/stream/${jobId}?token=${token}`;
    eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const data: AnalysisEvent = JSON.parse(event.data);
        onEvent(data);

        if (data.status === 'completed' || data.status === 'failed') {
          cleanup();
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      }
    };

    eventSource.onerror = () => {
      if (closed) return;

      eventSource?.close();
      eventSource = null;
      retryCount++;

      if (retryCount >= MAX_SSE_RETRIES) {
        // Fall back to polling
        onError?.(new Error(`SSE fehlgeschlagen nach ${MAX_SSE_RETRIES} Versuchen, wechsle zu Polling`));
        startPolling();
      } else {
        // Retry with backoff
        const delay = 1000 * retryCount;
        setTimeout(() => connectSSE(), delay);
      }
    };
  }

  connectSSE();

  return { close: cleanup };
}
