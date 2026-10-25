import Link from "next/link";

import type { Observation } from "@/lib/types";

type RecentObservationsProps = {
  observations: Observation[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  /** When true, show a link to the full observations page. */
  showViewAll?: boolean;
};

function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(iso));
}

function formatBehavior(behavior: string): string {
  return behavior.replaceAll("_", " ");
}

export function RecentObservations({
  observations,
  loading = false,
  error = null,
  onRetry,
  showViewAll = false,
}: RecentObservationsProps) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl text-sage-900">
          Recent observations
        </h2>
        {showViewAll ? (
          <Link
            href="/observations"
            className="text-sm font-medium text-sage-700 hover:text-sage-900"
          >
            View all →
          </Link>
        ) : null}
      </div>
      <p className="mt-1 text-sm text-muted">
        Saved behavior labels from video frames and camera captures.
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-muted">Loading observations…</p>
      ) : null}

      {!loading && error ? (
        <div className="mt-6 space-y-2">
          <p className="text-sm text-danger">{error}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="text-sm font-medium text-sage-700 hover:text-sage-900"
            >
              Try again
            </button>
          ) : null}
        </div>
      ) : null}

      {!loading && !error && observations.length === 0 ? (
        <p className="mt-6 text-sm text-muted">
          No observations yet. Analyze video frames or start camera monitoring.
        </p>
      ) : null}

      {!loading && !error && observations.length > 0 ? (
        <ul className="mt-5 divide-y divide-border/80">
          {observations.map((obs) => {
            const confidencePct =
              obs.confidence == null
                ? null
                : `${Math.round(obs.confidence * 100)}%`;
            const fromCamera = obs.camera_capture_id != null;
            return (
              <li key={obs.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium capitalize text-ink">
                    {formatBehavior(obs.behavior)}
                    <span className="font-normal text-muted">
                      {" "}
                      · {obs.animal_name ?? `Animal #${obs.animal_id}`}
                    </span>
                  </p>
                  <p className="text-xs text-muted">
                    {formatWhen(obs.observed_at)}
                  </p>
                </div>
                {obs.description ? (
                  <p className="mt-1 text-sm leading-6 text-muted">
                    {obs.description}
                  </p>
                ) : null}
                <p className="mt-2 text-xs text-sage-700">
                  {fromCamera
                    ? "Camera capture"
                    : `@${obs.video_timestamp_seconds.toFixed(1)}s`}
                  {confidencePct ? ` · confidence ${confidencePct}` : null}
                </p>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
