import type { MockObservation } from "@/lib/types";

type RecentObservationsProps = {
  observations: MockObservation[];
};

function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function RecentObservations({ observations }: RecentObservationsProps) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl text-sage-900">
          Recent observations
        </h2>
        <span className="rounded-md bg-cream-deep px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
          Mock data
        </span>
      </div>
      <p className="mt-1 text-sm text-muted">
        Placeholder rows until observation endpoints exist.
      </p>

      {observations.length === 0 ? (
        <p className="mt-6 text-sm text-muted">No mock observations yet.</p>
      ) : (
        <ul className="mt-5 divide-y divide-border/80">
          {observations.map((obs) => (
            <li key={obs.id} className="py-4 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-medium text-ink">
                  {obs.behavior}
                  <span className="font-normal text-muted">
                    {" "}
                    · {obs.animalName}
                  </span>
                </p>
                <p className="text-xs text-muted">{formatWhen(obs.observedAt)}</p>
              </div>
              <p className="mt-1 text-sm leading-6 text-muted">
                {obs.description}
              </p>
              <p className="mt-2 text-xs text-sage-700">
                @{obs.videoTimestampSeconds}s · confidence{" "}
                {Math.round(obs.confidence * 100)}%
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
