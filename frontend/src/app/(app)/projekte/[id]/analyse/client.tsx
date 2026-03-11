'use client';

import { useReducer, useState, useCallback, useEffect, useTransition } from 'react';
import { ArrowLeft, ArrowRight, BarChart3, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { WizardStepper } from '@/components/analysis/wizard-stepper';
import { StepFiles } from '@/components/analysis/step-files';
import { StepCatalog } from '@/components/analysis/step-catalog';
import type { CatalogInfo } from '@/components/analysis/step-catalog';
import { StepConfig } from '@/components/analysis/step-config';
import { StepProgress } from '@/components/analysis/step-progress';
import { StepResults } from '@/components/analysis/step-results';
import {
  prepareFilesForPython,
  createAnalysis,
  saveAnalysisResult,
} from '@/lib/actions/analysis-actions';
import { getCatalogs } from '@/lib/actions/catalog-actions';
import type {
  WizardState,
  WizardAction,
  AnalysisResult,
  ProjectFile,
} from '@/components/analysis/types';

interface AnalyseWizardClientProps {
  project: {
    id: string;
    name: string;
    files: ProjectFile[];
  };
  initialResult?: AnalysisResult | null;
}

function createInitialState(): WizardState {
  return {
    currentStep: 1,
    completedSteps: new Set<number>(),
    selectedFileIds: [],
    catalogId: null,
    config: {
      highThreshold: 90,
      lowThreshold: 70,
      validationPasses: 1,
    },
    jobId: null,
    analysisId: null,
    analysisResult: null,
    isAnalyzing: false,
    error: null,
  };
}

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'NEXT_STEP': {
      const completed = new Set(state.completedSteps);
      completed.add(state.currentStep);
      return {
        ...state,
        currentStep: Math.min(state.currentStep + 1, 5),
        completedSteps: completed,
      };
    }
    case 'PREV_STEP': {
      if (state.isAnalyzing) return state;
      return {
        ...state,
        currentStep: Math.max(state.currentStep - 1, 1),
      };
    }
    case 'GO_TO_STEP': {
      // Allow going to completed steps, or back to step 3 (from failure/cancel)
      if (!state.completedSteps.has(action.step) && action.step > state.currentStep) return state;
      return {
        ...state,
        currentStep: action.step,
      };
    }
    case 'SET_FILES':
      return { ...state, selectedFileIds: action.fileIds };
    case 'SET_CATALOG':
      return { ...state, catalogId: action.catalogId };
    case 'SET_CONFIG':
      return {
        ...state,
        config: { ...state.config, ...action.config },
      };
    case 'START_ANALYSIS':
      return {
        ...state,
        jobId: action.jobId,
        analysisId: action.analysisId,
        isAnalyzing: true,
        error: null,
      };
    case 'SET_RESULT': {
      const completed = new Set(state.completedSteps);
      completed.add(4);
      return {
        ...state,
        analysisResult: action.result,
        isAnalyzing: false,
        currentStep: 5,
        completedSteps: completed,
      };
    }
    case 'ANALYSIS_FAILED':
      return {
        ...state,
        isAnalyzing: false,
        error: action.error,
      };
    case 'RESET_ERROR':
      return { ...state, error: null };
    default:
      return state;
  }
}

function stepIsValid(state: WizardState, step: number): boolean {
  switch (step) {
    case 1:
      return state.selectedFileIds.length >= 1;
    case 2:
      return state.catalogId !== null;
    case 3:
    case 4:
    case 5:
      return true;
    default:
      return false;
  }
}

export function AnalyseWizardClient({ project, initialResult }: AnalyseWizardClientProps) {
  const [state, dispatch] = useReducer(
    wizardReducer,
    undefined,
    () => {
      if (initialResult) {
        return {
          ...createInitialState(),
          currentStep: 5,
          completedSteps: new Set([1, 2, 3, 4, 5]),
          analysisResult: initialResult,
        };
      }
      return createInitialState();
    }
  );

  const isViewingPastResult = !!initialResult;
  const [isStarting, setIsStarting] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [catalogs, setCatalogs] = useState<CatalogInfo[]>([]);
  const [, startCatalogTransition] = useTransition();

  // Fetch catalogs on mount for step-catalog
  useEffect(() => {
    startCatalogTransition(async () => {
      try {
        const result = await getCatalogs();
        const mapped: CatalogInfo[] = result.map((c) => ({
          id: c.id,
          name: c.name,
          productCount: c.versions[0]?.totalProducts ?? 0,
          updatedAt: c.updatedAt,
          isActive: !!c.versions[0]?.isActive,
          blobUrl: c.versions[0]?.blobUrl ?? null,
        }));
        setCatalogs(mapped);
      } catch {
        // Catalogs will remain empty -- step-catalog shows empty state
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const canGoBack = state.currentStep > 1 && !state.isAnalyzing && !isViewingPastResult;
  const canGoForward =
    state.currentStep < 5 &&
    state.currentStep !== 4 &&
    stepIsValid(state, state.currentStep) &&
    !isViewingPastResult;
  const showBackButton = state.currentStep > 1 && !isViewingPastResult;
  const showForwardButton = state.currentStep < 4 && !isViewingPastResult;
  const isStep3 = state.currentStep === 3;
  const isStep4 = state.currentStep === 4;

  // Start analysis: prepare files -> create record -> trigger Python -> advance to step 4
  const handleStartAnalysis = useCallback(async () => {
    setIsStarting(true);
    try {
      // 1. Transfer Blob files to Python cache
      const prepareResult = await prepareFilesForPython(project.id, state.selectedFileIds);
      if ('error' in prepareResult) {
        toast.error(prepareResult.error);
        setIsStarting(false);
        return;
      }

      // 2. Create Analysis record in Prisma
      const analysisResult = await createAnalysis(project.id);
      if ('error' in analysisResult) {
        toast.error(analysisResult.error);
        setIsStarting(false);
        return;
      }

      // 3. Start analysis on Python backend (use Python-generated project_id, not Prisma ID)
      const selectedCatalog = catalogs.find(c => c.id === state.catalogId);
      const response = await fetch('/api/backend/analyze/project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: prepareResult.pythonProjectId,
          catalog_blob_url: selectedCatalog?.blobUrl ?? null,
        }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: 'Analyse konnte nicht gestartet werden' }));
        toast.error(errData.error || 'Analyse konnte nicht gestartet werden');
        setIsStarting(false);
        return;
      }
      const { job_id } = await response.json();

      // 4. Dispatch and advance to step 4
      dispatch({ type: 'START_ANALYSIS', jobId: job_id, analysisId: analysisResult.analysisId });
      dispatch({ type: 'NEXT_STEP' }); // move to step 4
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setIsStarting(false);
    }
  }, [project.id, state.selectedFileIds, state.catalogId, catalogs]);

  // Handle analysis completion from StepProgress
  const handleAnalysisComplete = useCallback(
    async (result: AnalysisResult) => {
      if (state.analysisId) {
        await saveAnalysisResult(state.analysisId, result);
      }
      dispatch({ type: 'SET_RESULT', result });
      toast.success('Analyse abgeschlossen');
    },
    [state.analysisId]
  );

  // Handle analysis failure from StepProgress
  const handleAnalysisFailed = useCallback((error: string) => {
    dispatch({ type: 'ANALYSIS_FAILED', error });
    toast.error(error);
    dispatch({ type: 'GO_TO_STEP', step: 3 });
  }, []);

  // Handle cancel from StepProgress
  const handleAnalysisCancel = useCallback(() => {
    dispatch({ type: 'ANALYSIS_FAILED', error: 'Analyse abgebrochen' });
    dispatch({ type: 'GO_TO_STEP', step: 3 });
  }, []);

  // Step 3 "Weiter" triggers analysis start instead of simple next
  const handleNextClick = useCallback(() => {
    if (isStep3) {
      handleStartAnalysis();
    } else {
      dispatch({ type: 'NEXT_STEP' });
    }
  }, [isStep3, handleStartAnalysis]);

  return (
    <div className="space-y-6">
      {/* Stepper */}
      <WizardStepper
        currentStep={state.currentStep}
        completedSteps={state.completedSteps}
        onStepClick={(step) => dispatch({ type: 'GO_TO_STEP', step })}
      />

      {/* Error display */}
      {state.error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {state.error}
          <button
            type="button"
            onClick={() => dispatch({ type: 'RESET_ERROR' })}
            className="ml-2 underline"
          >
            Schliessen
          </button>
        </div>
      )}

      {/* Step content */}
      <Card>
        <CardContent className="pt-6">
          {state.currentStep === 1 && (
            <StepFiles
              files={project.files}
              selectedIds={state.selectedFileIds}
              onSelectionChange={(ids) =>
                dispatch({ type: 'SET_FILES', fileIds: ids })
              }
            />
          )}

          {state.currentStep === 2 && (
            <StepCatalog
              catalogId={state.catalogId}
              onCatalogChange={(id) =>
                dispatch({ type: 'SET_CATALOG', catalogId: id })
              }
              catalogs={catalogs}
            />
          )}

          {state.currentStep === 3 && (
            <StepConfig
              config={state.config}
              onConfigChange={(cfg) =>
                dispatch({ type: 'SET_CONFIG', config: cfg })
              }
            />
          )}

          {state.currentStep === 4 && (
            <StepProgress
              jobId={state.jobId}
              onComplete={handleAnalysisComplete}
              onFailed={handleAnalysisFailed}
              onCancel={handleAnalysisCancel}
            />
          )}

          {state.currentStep === 5 && state.analysisResult && (
            <StepResults
              result={state.analysisResult}
              config={state.config}
              onExpandRow={(index) => setExpandedRow(expandedRow === index ? null : index)}
              expandedRow={expandedRow}
            />
          )}

          {state.currentStep === 5 && !state.analysisResult && (
            <div className="flex flex-col items-center py-12 text-center">
              <BarChart3 className="mb-4 size-12 text-muted-foreground" />
              <p className="text-muted-foreground">
                Keine Analyseergebnisse vorhanden
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation bar */}
      <div className="flex items-center justify-between">
        <div>
          {showBackButton && !isStep4 && state.currentStep !== 5 && (
            <Button
              variant="outline"
              disabled={!canGoBack}
              onClick={() => dispatch({ type: 'PREV_STEP' })}
              className="gap-2"
            >
              <ArrowLeft className="size-4" />
              Zurueck
            </Button>
          )}
        </div>

        <div>
          {showForwardButton && (
            <Button
              disabled={!canGoForward || isStarting}
              onClick={handleNextClick}
              className="gap-2"
            >
              {isStarting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Analyse wird gestartet...
                </>
              ) : isStep3 ? (
                <>
                  Analyse starten
                  <ArrowRight className="size-4" />
                </>
              ) : (
                <>
                  Weiter
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
