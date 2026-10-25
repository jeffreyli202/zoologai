"use client";

type AnalysisProgressProps = {
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
  framesDone: number;
  framesTotal: number;
  aiCalls: number;
  maxAiCalls?: number;
};

const ACTIVE = new Set(["pending", "processing"]);

export function AnalysisProgress({
  status,
  progress,
  message,
  error,
  framesDone,
  framesTotal,
  aiCalls,
  maxAiCalls,
}: AnalysisProgressProps) {
  const clamped = Math.max(0, Math.min(100, progress));
  const isActive = ACTIVE.has(status);
  const showBar =
    isActive || status === "completed" || status === "failed" || progress > 0;

  if (!showBar && !message && !error) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2">
      {showBar ? (
        <div
          className="h-2 overflow-hidden rounded-full bg-sage-100"
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Video analysis progress"
        >
          <div
            className={`h-full rounded-full transition-[width] duration-300 ease-out ${
              status === "failed"
                ? "bg-danger"
                : status === "completed"
                  ? "bg-sage-700"
                  : "bg-sage-500"
            }`}
            style={{ width: `${clamped}%` }}
          />
        </div>
      ) : null}

      <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted">
        <span>
          {clamped}%
          {framesTotal > 0
            ? ` · frames ${framesDone}/${framesTotal}`
            : null}
          {aiCalls > 0 || maxAiCalls != null
            ? ` · AI calls ${aiCalls}${maxAiCalls != null ? `/${maxAiCalls}` : ""}`
            : null}
        </span>
        <span className="font-medium uppercase tracking-wide text-sage-500">
          {status}
        </span>
      </div>

      {message ? (
        <p
          className={`rounded-lg px-3 py-2 text-sm ${
            status === "completed"
              ? "bg-sage-50 text-sage-900"
              : "bg-sage-50/80 text-sage-900"
          }`}
        >
          {message}
        </p>
      ) : null}

      {error ? (
        <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      {isActive ? (
        <p className="text-xs text-muted">
          Job runs in the background so the page stays responsive. Progress
          refreshes automatically.
        </p>
      ) : null}
    </div>
  );
}
