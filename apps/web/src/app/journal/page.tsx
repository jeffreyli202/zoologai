import { JournalPreview } from "@/components/dashboard/JournalPreview";
import { MOCK_JOURNAL_ENTRIES } from "@/lib/mock-data";

export default function JournalPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Journal
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
          Daily written summaries. Preview uses mock entries until journal
          endpoints exist.
        </p>
      </header>
      <JournalPreview entries={MOCK_JOURNAL_ENTRIES} />
    </div>
  );
}
