import { RecentObservations } from "@/components/dashboard/RecentObservations";
import { MOCK_OBSERVATIONS } from "@/lib/mock-data";

export default function ObservationsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Observations
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
          Behavior timeline for each animal. Showing mock rows for now — real
          API wiring comes in a later step.
        </p>
      </header>
      <RecentObservations observations={MOCK_OBSERVATIONS} />
    </div>
  );
}
