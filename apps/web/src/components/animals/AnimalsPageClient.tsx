"use client";

import { useEffect, useState } from "react";

import { AnimalProfileCard } from "@/components/dashboard/AnimalProfileCard";
import { StatePanel } from "@/components/ui/StatePanel";
import { getAnimals } from "@/lib/api";
import type { Animal } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; animals: Animal[] };

export function AnimalsPageClient() {
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

  useEffect(() => {
    void loadAnimals();
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Animals
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
          Live profiles loaded from the FastAPI{" "}
          <code className="text-sage-700">/animals</code> endpoint.
        </p>
      </header>

      {state.status === "loading" ? (
        <StatePanel
          title="Loading animals…"
          message="Fetching records from the backend."
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
          message="Create an animal via the API /docs page or run the seed script."
        />
      ) : null}

      {state.status === "success" && state.animals.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {state.animals.map((animal) => (
            <AnimalProfileCard key={animal.id} animal={animal} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
