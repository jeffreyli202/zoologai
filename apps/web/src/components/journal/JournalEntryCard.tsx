"use client";

import type { DailyJournal } from "@/lib/types";

type JournalEntryCardProps = {
  journal: DailyJournal;
};

function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function periodLabel(journal: DailyJournal): string {
  if (journal.hour >= 0 && journal.hour <= 23) {
    const h = String(journal.hour).padStart(2, "0");
    return `${h}:00–${h}:59 UTC`;
  }
  return "Full day (UTC)";
}

/** Light rendering for ## section journals without a full markdown stack. */
function renderContent(content: string) {
  const blocks = content.split(/\n(?=## )/);
  return blocks.map((block, index) => {
    const lines = block.trim().split("\n");
    const first = lines[0] ?? "";
    if (first.startsWith("## ")) {
      const title = first.replace(/^##\s+/, "");
      const body = lines.slice(1).join("\n").trim();
      return (
        <section key={`${title}-${index}`} className="mt-4 first:mt-0">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-sage-700">
            {title}
          </h4>
          <p className="mt-1.5 whitespace-pre-wrap text-sm leading-7 text-ink/90">
            {body}
          </p>
        </section>
      );
    }
    return (
      <p
        key={`plain-${index}`}
        className="whitespace-pre-wrap text-sm leading-7 text-ink/90"
      >
        {block.trim()}
      </p>
    );
  });
}

export function JournalEntryCard({ journal }: JournalEntryCardProps) {
  const ids = journal.source_observation_ids ?? [];

  return (
    <article className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-ink">
            {journal.animal_name ?? `Animal #${journal.animal_id}`}
          </p>
          <p className="mt-0.5 text-xs text-sage-700">{periodLabel(journal)}</p>
        </div>
        <p className="text-xs text-muted">
          Saved {formatWhen(journal.updated_at ?? journal.created_at)}
        </p>
      </div>

      <div className="mt-4 border-t border-border/70 pt-3">
        {renderContent(journal.content)}
      </div>

      {ids.length > 0 ? (
        <p className="mt-4 text-xs text-muted">
          Traceability: observation{" "}
          {ids.length === 1 ? "ID" : "IDs"} {ids.join(", ")}
        </p>
      ) : null}
    </article>
  );
}
