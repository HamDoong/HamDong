interface StepItem {
  id: number;
  label: string;
}

interface CreateGroupStepperProps {
  currentStep: number;
  steps: StepItem[];
}

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function CreateGroupStepper({
  currentStep,
  steps,
}: CreateGroupStepperProps) {
  return (
    <div className="create-group-stepper mx-auto w-full max-w-[560px]" dir="rtl">
      <div className="flex items-start justify-center">
        {steps.map((step, index) => {
          const isCompleted = step.id < currentStep;
          const isActive = step.id === currentStep;
          const isDone = isCompleted || isActive;
          const isConnectorDone = currentStep > step.id;

          return (
            <div key={step.id} className="flex items-start">
              <div className="flex min-w-[108px] flex-col items-center text-center sm:min-w-[140px]">
                <div
                  className={cn(
                    'relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300',
                    isDone
                      ? 'border-emerald-500 bg-emerald-500 text-white shadow-[0_8px_20px_rgba(0,168,107,0.18)] dark:border-emerald-500 dark:bg-emerald-500 dark:text-white'
                      : 'border-slate-200 bg-white text-slate-500 dark:border-border dark:bg-slate-900/80 dark:text-slate-300',
                  )}
                >
                  {step.id}
                </div>

                <span
                  className={cn(
                    'mt-3 text-sm font-semibold leading-6 transition-colors duration-300 sm:text-base',
                    isDone ? 'text-emerald-600 dark:text-emerald-300' : 'text-slate-500 dark:text-slate-400',
                  )}
                >
                  {step.label}
                </span>
              </div>

              {index < steps.length - 1 ? (
                <div className="mx-1 mt-5 w-16 sm:mx-2 sm:w-28" aria-hidden="true">
                  <div
                    className={cn(
                      'border-t-2 border-dashed transition-colors duration-300',
                      isConnectorDone ? 'border-emerald-500 dark:border-emerald-500' : 'border-slate-200 dark:border-border',
                    )}
                  />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
