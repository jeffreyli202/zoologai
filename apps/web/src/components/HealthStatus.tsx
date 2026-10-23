"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, getHealth } from "@/lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "ok"; status: string }
  | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await getHealth();
        if (!cancelled) {
          setState({ kind: "ok", status: data.status });
        }
      } catch (error) {
        if (!cancelled) {
          const message =
            error instanceof Error ? error.message : "Unknown error";
          setState({ kind: "error", message });
        }
      }
    }

    void check();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mt-8 w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-zinc-900">API health</h2>
      <p className="mt-1 text-sm text-zinc-500">
        Calling <code className="text-zinc-700">{API_BASE_URL}/health</code>
      </p>

      <div className="mt-4 text-sm">
        {state.kind === "loading" && (
          <p className="text-zinc-600">Checking backend…</p>
        )}
        {state.kind === "ok" && (
          <p className="font-medium text-emerald-700">
            Connected — status: {state.status}
          </p>
        )}
        {state.kind === "error" && (
          <p className="font-medium text-red-700">
            Could not reach API: {state.message}
          </p>
        )}
      </div>
    </section>
  );
}
