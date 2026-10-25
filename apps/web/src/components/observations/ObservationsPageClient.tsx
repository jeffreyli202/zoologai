"use client";

import { useCallback, useEffect, useState } from "react";

import { RecentObservations } from "@/components/dashboard/RecentObservations";
import { StatePanel } from "@/components/ui/StatePanel";
import { getAnimals, getObservations } from "@/lib/api";
import type { Animal, Observation } from "@/lib/types";

const ALL = "all";

export function ObservationsPageClient() {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [animalId, setAnimalId] = useState<string>(ALL);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [animalList, obsList] = await Promise.all([
        getAnimals(),
        getObservations({
          animalId: animalId !== ALL ? Number(animalId) : undefined,
          limit: 100,
        }),
      ]);
      setAnimals(animalList);
      setObservations(obsList);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load observations.",
      );
    } finally {
      setLoading(false);
    }
  }, [animalId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Observations
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
          Behavior labels saved from video frames and live camera captures.
          Empty or not-visible frames are not listed as sightings for journals.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="block text-sm">
          <span className="text-muted">Animal</span>
          <select
            value={animalId}
            onChange={(e) => setAnimalId(e.target.value)}
            className="mt-1 block min-w-[12rem] rounded-lg border border-border bg-surface px-3 py-2 text-ink"
          >
            <option value={ALL}>All animals</option>
            {animals.map((a) => (
              <option key={a.id} value={String(a.id)}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && !loading ? (
        <StatePanel
          tone="danger"
          title="Could not load observations"
          message={error}
          actionLabel="Try again"
          onAction={() => void load()}
        />
      ) : (
        <RecentObservations
          observations={observations}
          loading={loading}
          error={null}
          onRetry={() => void load()}
        />
      )}
    </div>
  );
}
