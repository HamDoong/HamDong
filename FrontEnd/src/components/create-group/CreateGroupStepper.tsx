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
  const progress =
    steps.length > 1 ? ((currentStep - 1) / (steps.length - 1)) * 100 : 0;

  return (
    <div className="relative mx-auto max-w-[720px] px-2 sm:px-6">
      <div
        className="pointer-events-none absolute left-[16.666%] right-[16.666%] top-5"
        aria-hidden="true"
      >
        <div className="border-t-2 border-dashed border-slate-200" />
        <div
          className="absolute right-0 top-0 border-t-2 border-dashed border-emerald-500 transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {steps.map((step) => {
          const isCompleted = step.id < currentStep;
          const isActive = step.id === currentStep;
          const isDone = isCompleted || isActive;

          return (
            <div
              key={step.id}
              className="relative flex flex-col items-center text-center"
            >
              <div
                className={cn(
                  'relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300',
                  isDone
                    ? 'border-emerald-500 bg-emerald-500 text-white shadow-[0_8px_20px_rgba(0,168,107,0.18)]'
                    : 'border-slate-200 bg-white text-slate-500',
                )}
              >
                {step.id}
              </div>

              <span
                className={cn(
                  'mt-3 text-sm font-semibold leading-6 transition-colors duration-300 sm:text-base',
                  isDone ? 'text-emerald-600' : 'text-slate-500',
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}