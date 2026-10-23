import type { Animal } from "@/lib/types";

/**
 * Base URL for the FastAPI backend.
 * Set NEXT_PUBLIC_API_URL in apps/web/.env.local (see .env.example at repo root).
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}

/**
 * API fetching: call the backend over HTTP and turn the JSON body into
 * typed TypeScript objects. The browser (or server) waits for the response
 * with `await`, then we check `response.ok` before trusting the data.
 */
export async function getAnimals(): Promise<Animal[]> {
  const response = await fetch(`${API_BASE_URL}/animals`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to load animals (HTTP ${response.status})`);
  }

  return response.json() as Promise<Animal[]>;
}
