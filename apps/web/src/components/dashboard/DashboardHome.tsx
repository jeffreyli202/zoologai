"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { AnimalProfileCard } from "@/components/dashboard/AnimalProfileCard";
import { DashboardVideos } from "@/components/dashboard/DashboardVideos";
import { JournalPreview } from "@/components/dashboard/JournalPreview";
import { RecentObservations } from "@/components/dashboard/RecentObservations";
import { StatCard } from "@/components/dashboard/StatCard";
import { StatePanel } from "@/components/ui/StatePanel";
import {
  getAnimals,
  getCameras,
  getJournals,
  getObservationStats,
  getObservations,
} from "@/lib/api";
import type {
  Animal,
  CameraSource,
  DailyJournal,
  Observation,
  ObservationStats,
} from "@/lib/types";

type DashboardData = {
  animals: Animal[];
  observations: Observation[];
  observationStats: ObservationStats;
  journals: DailyJournal[];
  cameras: CameraSource[];
};

export function DashboardHome() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [animals, observations, observationStats, journals, cameras] =
        await Promise.all([
          getAnimals(),
          getObservations({ limit: 8 }),
          getObservationStats(),
          getJournals(),
          getCameras(),
        ]);
      setData({
        animals,
        observations,
        observationStats,
        journals,
        cameras,
      });
    } catch (err) {
      setData(null);
      setError(
        err instanceof Error ? err.message : "Could not load dashboard data.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const animals = data?.animals ?? [];
  const observations = data?.observations ?? [];
  const observationStats = data?.observationStats ?? {
    total: 0,
    distinct_behaviors: 0,
  };
  const journals = data?.journals ?? [];
  const cameras = data?.cameras ?? [];

  const activeCameras = cameras.filter((c) => c.status === "running").length;
  const featuredAnimal = animals[0] ?? null;
  const recentJournals = journals.slice(0, 5);

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
          Live animals, camera captures, and hourly journals from your API —
          observations only appear when vision actually saved a row.
        </p>
      </header>

      {error ? (
        <StatePanel
          tone="danger"
          title="Could not load dashboard"
          message={error}
          actionLabel="Try again"
          onAction={() => void load()}
        />
      ) : null}

      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">
          Statistics
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Animals"
            value={loading ? "…" : animals.length}
            hint="Profiles in the database"
          />
          <StatCard
            label="Observations"
            value={loading ? "…" : observationStats.total}
            hint={
              loading
                ? "Loading…"
                : `${observationStats.distinct_behaviors} distinct behavior label${observationStats.distinct_behaviors === 1 ? "" : "s"}`
            }
          />
          <StatCard
            label="Journal entries"
            value={loading ? "…" : journals.length}
            hint="Hourly summaries saved so far"
          />
          <StatCard
            label="Cameras"
            value={loading ? "…" : cameras.length}
            hint={
              loading ? "Loading…" : `${activeCameras} monitoring now`
            }
          />
        </div>
      </section>

      <section aria-labelledby="animals-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2
              id="animals-heading"
              className="font-display text-xl text-sage-900"
            >
              Animals
            </h2>
            <p className="mt-1 text-sm text-muted">
              Discovered from monitoring or added manually
            </p>
          </div>
          <Link
            href="/animals"
            className="text-sm font-medium text-sage-700 hover:text-sage-900"
          >
            Manage animals →
          </Link>
        </div>

        {loading ? (
          <StatePanel
            title="Loading animals…"
            message="Fetching records from the FastAPI backend."
          />
        ) : null}

        {!loading && !error && animals.length === 0 ? (
          <StatePanel
            title="No animals yet"
            message="Start camera monitoring — vision creates animal profiles when it sees something — or add one on the Animals page."
          />
        ) : null}

        {!loading && featuredAnimal ? (
          <div className="grid gap-4 md:grid-cols-2">
            <AnimalProfileCard animal={featuredAnimal} featured />
            {animals.length > 1 ? (
              <div className="grid gap-4">
                {animals.slice(1, 3).map((animal) => (
                  <AnimalProfileCard key={animal.id} animal={animal} />
                ))}
                {animals.length > 3 ? (
                  <p className="text-sm text-muted">
                    +{animals.length - 3} more on{" "}
                    <Link
                      href="/animals"
                      className="font-medium text-sage-700 hover:text-sage-900"
                    >
                      Animals
                    </Link>
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border bg-sage-50/40 p-5 text-sm leading-6 text-muted">
                Only one animal so far. Monitoring can discover more as it
                analyzes stills.
              </div>
            )}
          </div>
        ) : null}
      </section>

      <DashboardVideos />

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentObservations
          observations={observations}
          loading={loading}
          error={error}
          onRetry={() => void load()}
          showViewAll
        />
        <JournalPreview
          entries={recentJournals}
          loading={loading}
          error={error}
          onRetry={() => void load()}
        />
      </div>
    </div>
  );
}
