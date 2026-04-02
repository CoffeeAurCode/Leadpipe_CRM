/**
 * Custom Joyride tooltip styled with Tailwind to match the CRM theme.
 */
export function OnboardingTooltip({
  step,
  index,
  size,
  isLastStep,
  backProps,
  primaryProps,
  skipProps,
  tooltipProps,
}) {
  return (
    <div
      {...tooltipProps}
      className="w-full max-w-md rounded-xl border border-border bg-card shadow-xl p-5 space-y-4"
      style={{ zIndex: 10001 }}
    >
      <div>
        {step.title && (
          <h3 className="font-semibold text-foreground text-base">{step.title}</h3>
        )}
        {step.content && (
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">{step.content}</p>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">
          {index + 1} of {size}
        </span>
        <div className="flex gap-2">
          <button
            {...skipProps}
            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary"
          >
            Skip Tour
          </button>
          {index > 0 && (
            <button
              {...backProps}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary"
            >
              Back
            </button>
          )}
          <button
            {...primaryProps}
            className="px-4 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors shadow-sm"
          >
            {isLastStep ? 'Finish' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
