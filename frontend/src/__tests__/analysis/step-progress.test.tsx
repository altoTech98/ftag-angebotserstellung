import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StepProgress } from '@/components/analysis/step-progress';

// Mock SSE client
const mockClose = vi.fn();
let capturedOnEvent: ((data: Record<string, unknown>) => void) | null = null;
let capturedOnError: ((error: Error) => void) | null = null;

vi.mock('@/lib/sse-client', () => ({
  connectToAnalysis: vi.fn(
    async (
      _jobId: string,
      onEvent: (data: Record<string, unknown>) => void,
      onError?: (error: Error) => void
    ) => {
      capturedOnEvent = onEvent;
      capturedOnError = onError ?? null;
      return { close: mockClose };
    }
  ),
}));

describe('[ANLZ-04] Progress display step', () => {
  const defaultProps = {
    jobId: 'test-job-123',
    onComplete: vi.fn(),
    onFailed: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnEvent = null;
    capturedOnError = null;
  });

  it('renders 4 stage items: Dokument lesen, Anforderungen extrahieren, Produkte zuordnen, Ergebnis generieren', () => {
    render(<StepProgress {...defaultProps} />);

    expect(screen.getByTestId('stage-parse')).toBeDefined();
    expect(screen.getByTestId('stage-extract')).toBeDefined();
    expect(screen.getByTestId('stage-match')).toBeDefined();
    expect(screen.getByTestId('stage-generate')).toBeDefined();

    expect(screen.getByText('Dokument lesen')).toBeDefined();
    expect(screen.getByText('Anforderungen extrahieren')).toBeDefined();
    expect(screen.getByText('Produkte zuordnen')).toBeDefined();
    expect(screen.getByText('Ergebnis generieren')).toBeDefined();
  });

  it('shows cancel button with confirmation dialog', async () => {
    const user = userEvent.setup();
    render(<StepProgress {...defaultProps} />);

    const cancelBtn = screen.getByTestId('cancel-analysis-btn');
    expect(cancelBtn).toBeDefined();

    await user.click(cancelBtn);

    // Dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Analyse abbrechen?')).toBeDefined();
      expect(screen.getByText(/Analyse wirklich abbrechen/)).toBeDefined();
    });
  });

  it('calls onComplete when analysis succeeds', async () => {
    render(<StepProgress {...defaultProps} />);

    // Wait for SSE connection to be established
    await waitFor(() => {
      expect(capturedOnEvent).not.toBeNull();
    });

    // Simulate completed event
    const mockResult = {
      status: 'completed',
      result: {
        matched: [],
        partial: [],
        unmatched: [],
        summary: {
          total_positions: 0,
          matched_count: 0,
          partial_count: 0,
          unmatched_count: 0,
          match_rate: 0,
        },
      },
    };

    capturedOnEvent!(mockResult);

    expect(defaultProps.onComplete).toHaveBeenCalledTimes(1);
  });

  it('calls onFailed when analysis fails', async () => {
    render(<StepProgress {...defaultProps} />);

    await waitFor(() => {
      expect(capturedOnEvent).not.toBeNull();
    });

    capturedOnEvent!({ status: 'failed', error: 'Something went wrong' });

    expect(defaultProps.onFailed).toHaveBeenCalledWith('Something went wrong');
  });

  it('calls onCancel after confirming cancel dialog', async () => {
    const user = userEvent.setup();

    // Mock fetch for cancel endpoint
    global.fetch = vi.fn().mockResolvedValue({ ok: true });

    render(<StepProgress {...defaultProps} />);

    // Click cancel button
    await user.click(screen.getByTestId('cancel-analysis-btn'));

    // Wait for dialog
    await waitFor(() => {
      expect(screen.getByTestId('confirm-cancel-btn')).toBeDefined();
    });

    // Confirm cancel
    await user.click(screen.getByTestId('confirm-cancel-btn'));

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });
});
