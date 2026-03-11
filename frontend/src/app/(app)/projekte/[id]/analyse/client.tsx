'use client';

import { useReducer } from 'react';
import { ArrowLeft, ArrowRight, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { WizardStepper } from '@/components/analysis/wizard-stepper';
import { StepFiles } from '@/components/analysis/step-files';
import { StepCatalog } from '@/components/analysis/step-catalog';
import { StepConfig } from '@/components/analysis/step-config';
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
      if (!state.completedSteps.has(action.step)) return state;
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

export function AnalyseWizardClient({ project }: AnalyseWizardClientProps) {
  const [state, dispatch] = useReducer(wizardReducer, undefined, createInitialState);

  const canGoBack = state.currentStep > 1 && !state.isAnalyzing;
  const canGoForward =
    state.currentStep < 5 &&
    state.currentStep !== 4 &&
    stepIsValid(state, state.currentStep);
  const showBackButton = state.currentStep > 1;
  const showForwardButton = state.currentStep < 4;
  const isStep4 = state.currentStep === 4;

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
            <div className="flex flex-col items-center py-12 text-center">
              <BarChart3 className="mb-4 size-12 text-muted-foreground" />
              <p className="text-muted-foreground">
                Wird in Plan 02 implementiert
              </p>
            </div>
          )}

          {state.currentStep === 5 && (
            <div className="flex flex-col items-center py-12 text-center">
              <BarChart3 className="mb-4 size-12 text-muted-foreground" />
              <p className="text-muted-foreground">
                Wird in Plan 02 implementiert
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation bar */}
      <div className="flex items-center justify-between">
        <div>
          {showBackButton && !isStep4 && (
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
          {isStep4 && (
            <Button
              variant="outline"
              disabled={!state.isAnalyzing}
              className="gap-2"
            >
              Analyse abbrechen
            </Button>
          )}
        </div>

        <div>
          {showForwardButton && (
            <Button
              disabled={!canGoForward}
              onClick={() => dispatch({ type: 'NEXT_STEP' })}
              className="gap-2"
            >
              Weiter
              <ArrowRight className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
