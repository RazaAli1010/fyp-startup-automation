interface FormProgressProps {
  currentStep: number;
  totalSteps: number;
  stepLabels: string[];
}

export function FormProgress({ currentStep, totalSteps, stepLabels }: FormProgressProps) {
  return (
    <div className="mb-10">
      {/* Progress bar */}
      <div className="mb-4 h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 transition-all duration-500 ease-out"
          style={{ width: `${((currentStep + 1) / totalSteps) * 100}%` }}
        />
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-between">
        {stepLabels.map((label, i) => {
          const isCompleted = i < currentStep;
          const isCurrent = i === currentStep;

          return (
            <div key={label} className="flex items-center gap-2">
              {/* Step circle */}
              <div
                className={`
                  flex h-7 w-7 shrink-0 items-center justify-center rounded-full
                  text-xs font-bold transition-all duration-300
                  ${
                    isCompleted
                      ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/25"
                      : isCurrent
                        ? "border-2 border-indigo-500 bg-indigo-500/10 text-indigo-300 shadow-md shadow-indigo-500/15"
                        : "border border-slate-700 bg-slate-800/50 text-slate-600"
                  }
                `}
              >
                {isCompleted ? (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>

              {/* Label (hidden on small screens for middle steps) */}
              <span
                className={`
                  hidden text-xs font-medium sm:inline
                  ${
                    isCompleted
                      ? "text-indigo-400"
                      : isCurrent
                        ? "text-slate-200"
                        : "text-slate-600"
                  }
                `}
              >
                {label}
              </span>

              {/* Connector line (except last) */}
              {i < totalSteps - 1 && (
                <div
                  className={`
                    mx-1 hidden h-px flex-1 sm:block
                    ${i < currentStep ? "bg-indigo-500/40" : "bg-slate-800"}
                  `}
                  style={{ minWidth: "1.5rem" }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
