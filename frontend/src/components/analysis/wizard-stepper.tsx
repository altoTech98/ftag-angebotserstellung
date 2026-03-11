'use client';

import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WIZARD_STEPS } from './types';

interface WizardStepperProps {
  currentStep: number;
  completedSteps: Set<number>;
  onStepClick: (step: number) => void;
}

export function WizardStepper({
  currentStep,
  completedSteps,
  onStepClick,
}: WizardStepperProps) {
  return (
    <nav aria-label="Analyse-Schritte">
      {/* Desktop stepper */}
      <ol className="hidden sm:flex items-center justify-between gap-2">
        {WIZARD_STEPS.map((step, idx) => {
          const isCompleted = completedSteps.has(step.number);
          const isCurrent = step.number === currentStep;
          const isClickable = isCompleted;

          return (
            <li key={step.number} className="flex flex-1 items-center">
              <div className="flex flex-col items-center gap-1.5 w-full">
                <div className="flex items-center w-full">
                  {/* Connector line before */}
                  {idx > 0 && (
                    <div
                      className={cn(
                        'h-0.5 flex-1',
                        completedSteps.has(WIZARD_STEPS[idx - 1].number)
                          ? 'bg-primary'
                          : 'bg-border'
                      )}
                    />
                  )}

                  {/* Step circle */}
                  <button
                    type="button"
                    disabled={!isClickable}
                    onClick={() => isClickable && onStepClick(step.number)}
                    className={cn(
                      'flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-medium transition-colors',
                      isCurrent &&
                        'bg-primary text-primary-foreground ring-2 ring-primary/30',
                      isCompleted &&
                        !isCurrent &&
                        'bg-green-600 text-white cursor-pointer hover:bg-green-700',
                      !isCurrent &&
                        !isCompleted &&
                        'border-2 border-border text-muted-foreground cursor-default'
                    )}
                    aria-current={isCurrent ? 'step' : undefined}
                    aria-label={`Schritt ${step.number}: ${step.label}`}
                  >
                    {isCompleted && !isCurrent ? (
                      <Check className="size-4" />
                    ) : (
                      step.number
                    )}
                  </button>

                  {/* Connector line after */}
                  {idx < WIZARD_STEPS.length - 1 && (
                    <div
                      className={cn(
                        'h-0.5 flex-1',
                        isCompleted ? 'bg-primary' : 'bg-border'
                      )}
                    />
                  )}
                </div>

                {/* Label */}
                <span
                  className={cn(
                    'text-xs whitespace-nowrap',
                    isCurrent
                      ? 'font-medium text-foreground'
                      : 'text-muted-foreground'
                  )}
                >
                  {step.label}
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      {/* Mobile compact stepper */}
      <div className="flex sm:hidden items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
            {currentStep}
          </span>
          <span className="text-sm font-medium">
            {WIZARD_STEPS[currentStep - 1]?.label}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {WIZARD_STEPS.map((step) => (
            <div
              key={step.number}
              className={cn(
                'size-2 rounded-full',
                step.number === currentStep
                  ? 'bg-primary'
                  : completedSteps.has(step.number)
                    ? 'bg-green-600'
                    : 'bg-border'
              )}
            />
          ))}
        </div>
      </div>
    </nav>
  );
}
