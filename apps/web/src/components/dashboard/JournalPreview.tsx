import type { MockJournalEntry } from "@/lib/types";

type JournalPreviewProps = {
  entries: MockJournalEntry[];
};

function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${isoDate}T12:00:00`));
}

export function JournalPreview({ entries }: JournalPreviewProps) {
  const latest = entries[0];

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl text-sage-900">
          Daily journal preview
        </h2>
        <span className="rounded-md bg-cream-deep px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
          Mock data
        </span>
      </div>
      <p className="mt-1 text-sm text-muted">
        Placeholder journal text until journal endpoints exist.
      </p>

      {!latest ? (
        <p className="mt-6 text-sm text-muted">No mock journal entries yet.</p>
      ) : (
        <article className="mt-5 rounded-xl bg-sage-50/70 p-4 md:p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-sage-700">
            {latest.animalName} · {formatDate(latest.date)}
          </p>
          <p className="mt-3 text-sm leading-7 text-ink/90">{latest.content}</p>
          {entries.length > 1 ? (
            <p className="mt-4 text-xs text-muted">
              +{entries.length - 1} more mock{" "}
              {entries.length - 1 === 1 ? "entry" : "entries"} available
            </p>
          ) : null}
        </article>
      )}
    </section>
  );
}
