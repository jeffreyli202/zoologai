import Link from "next/link";

import type { DailyJournal } from "@/lib/types";

type JournalPreviewProps = {
  entries: DailyJournal[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
};

function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${isoDate}T12:00:00`));
}

function hourLabel(hour: number): string {
  if (hour < 0) return "Full day";
  return `${String(hour).padStart(2, "0")}:00 UTC`;
}

export function JournalPreview({
  entries,
  loading = false,
  error = null,
  onRetry,
}: JournalPreviewProps) {
  const latest = entries[0];

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl text-sage-900">
          Latest journal
        </h2>
        <Link
          href="/journal"
          className="text-sm font-medium text-sage-700 hover:text-sage-900"
        >
          Open journal →
        </Link>
      </div>
      <p className="mt-1 text-sm text-muted">
        Hourly summaries written from saved sightings.
      </p>

      {loading ? (
        <p className="mt-6 text-sm text-muted">Loading journals…</p>
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

      {!loading && !error && !latest ? (
        <p className="mt-6 text-sm text-muted">
          No journals yet. Monitoring writes them when an hour ends with
          sightings.
        </p>
      ) : null}

      {!loading && !error && latest ? (
        <article className="mt-5 rounded-xl bg-sage-50/70 p-4 md:p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-sage-700">
            {latest.animal_name ?? `Animal #${latest.animal_id}`} ·{" "}
            {formatDate(latest.date)} · {hourLabel(latest.hour)}
          </p>
          <p className="mt-3 text-sm leading-7 text-ink/90 line-clamp-6">
            {latest.content}
          </p>
          {entries.length > 1 ? (
            <p className="mt-4 text-xs text-muted">
              +{entries.length - 1} more{" "}
              {entries.length - 1 === 1 ? "entry" : "entries"}
            </p>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
