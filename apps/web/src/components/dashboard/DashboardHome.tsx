"use client";

/**
 * useState + useEffect live in client components.
 *
 * - useState: remember values that can change (animals list, loading, error).
 *   When state updates, React re-renders this component with the new values.
 * - useEffect: run side effects after render — here, fetch animals from the API
 *   when the page first mounts (empty dependency array []).
 */

import { useEffect, useState } from "react";

import { AnimalProfileCard } from "@/components/dashboard/AnimalProfileCard";
import { JournalPreview } from "@/components/dashboard/JournalPreview";
import { RecentObservations } from "@/components/dashboard/RecentObservations";
import { StatCard } from "@/components/dashboard/StatCard";
import { StatePanel } from "@/components/ui/StatePanel";
import { getAnimals } from "@/lib/api";
import {
  MOCK_JOURNAL_ENTRIES,
  MOCK_OBSERVATIONS,
  MOCK_STATS,
} from "@/lib/mock-data";
import type { Animal } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; animals: Animal[] };

export function DashboardHome() {
  // useState: start in "loading" until the first fetch finishes.
  const [state, setState] = useState<LoadState>({ status: "loading" });

  async function loadAnimals() {
    setState({ status: "loading" });
    try {
      const animals = await getAnimals();
      setState({ status: "success", animals });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not reach the API.";
      setState({ status: "error", message });
    }
  }

  // useEffect: fetch once when this component appears on screen.
  useEffect(() => {
    void loadAnimals();
  }, []);

  const featuredAnimal =
    state.status === "success" && state.animals.length > 0
      ? state.animals[0]
      : null;

  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <p className="text-sm font-medium uppercase tracking-wide text-sage-500">
          Welcome
        </p>
        <h1 className="mt-2 font-display text-4xl leading-tight text-sage-900 md:text-5xl">
          ZooLog AI
        </h1>
        <p className="mt-4 text-base leading-7 text-muted">
          A calm workspace for watching animal footage, noticing behaviors, and
          writing daily observation journals. This dashboard shows live animal
          records from your API, plus clearly labeled mock observation and
          journal data until those endpoints are ready.
        </p>
      </header>

      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">
          Statistics
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Total observations"
            value={MOCK_STATS.totalObservations}
            hint="From mock observation list"
            isMock
          />
          <StatCard
            label="Behaviors detected"
            value={MOCK_STATS.behaviorsDetected}
            hint="Unique behaviors in mock data"
            isMock
          />
          <StatCard
            label="Journal entries"
            value={MOCK_STATS.journalEntries}
            hint="From mock journal list"
            isMock
          />
        </div>
      </section>

      <section aria-labelledby="animals-heading" className="space-y-4">
        <div>
          <h2
            id="animals-heading"
            className="font-display text-xl text-sage-900"
          >
            Animals from API
          </h2>
          <p className="mt-1 text-sm text-muted">
            Live data from <code className="text-sage-700">GET /animals</code>
          </p>
        </div>

        {state.status === "loading" ? (
          <StatePanel
            title="Loading animals…"
            message="Fetching records from the FastAPI backend."
          />
        ) : null}

        {state.status === "error" ? (
          <StatePanel
            tone="danger"
            title="Could not load animals"
            message={state.message}
            actionLabel="Try again"
            onAction={() => void loadAnimals()}
          />
        ) : null}

        {state.status === "success" && state.animals.length === 0 ? (
          <StatePanel
            title="No animals yet"
            message="The database has no animal records. Seed the API or create one via /docs."
          />
        ) : null}

        {state.status === "success" && featuredAnimal ? (
          <div className="grid gap-4 md:grid-cols-2">
            <AnimalProfileCard animal={featuredAnimal} featured />
            {state.animals.length > 1 ? (
              <div className="grid gap-4">
                {state.animals.slice(1, 3).map((animal) => (
                  <AnimalProfileCard key={animal.id} animal={animal} />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border bg-sage-50/40 p-5 text-sm leading-6 text-muted">
                Add more animals in FastAPI <code>/docs</code> to see additional
                profile cards here.
              </div>
            )}
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentObservations observations={MOCK_OBSERVATIONS} />
        <JournalPreview entries={MOCK_JOURNAL_ENTRIES} />
      </div>
    </div>
  );
}
