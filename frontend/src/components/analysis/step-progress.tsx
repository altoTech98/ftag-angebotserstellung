'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { CheckCircle2, Circle, Loader2, X } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ANALYSIS_STAGES } from '@/components/analysis/types';
import type { AnalysisResult } from '@/components/analysis/types';
import { connectToAnalysis } from '@/lib/sse-client';
import type { AnalysisEvent } from '@/lib/sse-client';

interface StepProgressProps {
  jobId: string | null;
  onComplete: (result: AnalysisResult) => void;
  onFailed: (error: string) => void;
  onCancel: () => void;
}

// Map active stage index to progress percentage
const STAGE_PROGRESS: Record<number, number> = {
  0: 10,
  1: 35,
  2: 60,
  3: 85,
};

function matchStage(progressText: string): number {
  for (let i = ANALYSIS_STAGES.length - 1; i >= 0; i--) {
    if (ANALYSIS_STAGES[i].pattern.test(progressText)) {
      return i;
    }
  }
  return 0;
}

function extractCounter(progressText: string): string | null {
  const match = progressText.match(/(\d+)\/(\d+)/);
  return match ? `${match[1]}/${match[2]}` : null;
}

export function StepProgress({ jobId, onComplete, onFailed, onCancel }: StepProgressProps) {
  const [activeStage, setActiveStage] = useState(-1);
  const [progressPercent, setProgressPercent] = useState(0);
  const [counter, setCounter] = useState<string | null>(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const connectionRef = useRef<{ close: () => void } | null>(null);
  const completedStagesRef = useRef<Set<number>>(new Set());

  const handleEvent = useCallback(
    (data: AnalysisEvent) => {
      if (data.status === 'completed') {
        setProgressPercent(100);
        // Mark all stages as completed
        completedStagesRef.current = new Set([0, 1, 2, 3]);
        setActiveStage(4); // past last stage
        const result = (data.result ?? data) as unknown as AnalysisResult;
        onComplete(result);
        return;
      }

      if (data.status === 'failed') {
        const errorMsg =
          typeof data.error === 'string'
            ? data.error
            : 'Analyse fehlgeschlagen';
        onFailed(errorMsg);
        return;
      }

      if (data.progress && typeof data.progress === 'string') {
        const stageIdx = matchStage(data.progress);
        // Mark all stages up to the current one as completed
        for (let i = 0; i < stageIdx; i++) {
          completedStagesRef.current.add(i);
        }
        setActiveStage(stageIdx);
        setProgressPercent(STAGE_PROGRESS[stageIdx] ?? 10);

        const cnt = extractCounter(data.progress);
        setCounter(cnt);
      }
    },
    [onComplete, onFailed]
  );

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    async function connect() {
      try {
        const conn = await connectToAnalysis(jobId!, handleEvent, (err) => {
          if (!cancelled) {
            onFailed(err.message);
          }
        });
        if (!cancelled) {
          connectionRef.current = conn;
        } else {
          conn.close();
        }
      } catch (err) {
        if (!cancelled) {
          onFailed(err instanceof Error ? err.message : 'SSE-Verbindung fehlgeschlagen');
        }
      }
    }

    connect();

    return () => {
      cancelled = true;
      connectionRef.current?.close();
      connectionRef.current = null;
    };
  }, [jobId, handleEvent, onFailed]);

  async function handleCancelConfirm() {
    setCancelDialogOpen(false);
    connectionRef.current?.close();
    connectionRef.current = null;

    if (jobId) {
      try {
        await fetch(`/api/backend/analyze/cancel/${jobId}`, {
          method: 'POST',
        });
      } catch {
        // Best effort cancel
      }
    }

    onCancel();
  }

  function getStageIcon(stageIdx: number) {
    if (completedStagesRef.current.has(stageIdx) || stageIdx < activeStage) {
      return <CheckCircle2 className="size-5 text-primary" data-testid={`stage-done-${stageIdx}`} />;
    }
    if (stageIdx === activeStage) {
      return (
        <span className="relative flex size-5 items-center justify-center" data-testid={`stage-active-${stageIdx}`}>
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/40" />
          <span className="relative inline-flex size-3 rounded-full bg-primary" />
        </span>
      );
    }
    return <Circle className="size-5 text-muted-foreground" data-testid={`stage-pending-${stageIdx}`} />;
  }

  return (
    <div className="flex flex-col items-center gap-8 py-8" data-testid="step-progress">
      {/* Spinner and title */}
      <div className="flex items-center gap-3">
        <Loader2 className="size-5 animate-spin text-primary" />
        <span className="text-lg font-medium">Analyse laeuft...</span>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-md">
        <Progress value={progressPercent} className="h-3" />
      </div>

      {/* Stage checklist */}
      <div className="flex w-full max-w-md flex-col gap-3">
        {ANALYSIS_STAGES.map((stage, idx) => (
          <div
            key={stage.key}
            className="flex items-center gap-3"
            data-testid={`stage-${stage.key}`}
          >
            {getStageIcon(idx)}
            <span
              className={
                idx === activeStage
                  ? 'font-medium text-foreground'
                  : idx < activeStage || completedStagesRef.current.has(idx)
                    ? 'text-muted-foreground line-through'
                    : 'text-muted-foreground'
              }
            >
              {stage.label}
              {idx === activeStage && counter && (
                <span className="ml-2 text-sm text-muted-foreground">
                  {counter}
                </span>
              )}
            </span>
          </div>
        ))}
      </div>

      {/* Cancel button with confirmation dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogTrigger
          render={<Button variant="outline" className="gap-2" data-testid="cancel-analysis-btn" />}
        >
          <X className="size-4" />
          Analyse abbrechen
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Analyse abbrechen?</DialogTitle>
            <DialogDescription>
              Analyse wirklich abbrechen? Der aktuelle Fortschritt geht verloren.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCancelDialogOpen(false)}
            >
              Zurueck
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancelConfirm}
              data-testid="confirm-cancel-btn"
            >
              Ja, abbrechen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
