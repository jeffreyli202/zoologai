"use client";

import { useCallback, useEffect, useState } from "react";

import { BehaviorBarChart } from "@/components/analytics/BehaviorBarChart";
import { DayCompareChart } from "@/components/analytics/DayCompareChart";
import {
  DaySamplesChart,
  HourSamplesChart,
} from "@/components/analytics/DayHourCharts";
import { TimelineChart } from "@/components/analytics/TimelineChart";
import { StatePanel } from "@/components/ui/StatePanel";
import {
  compareAnalyticsDays,
  generateWeeklySummary,
  getAnimals,
  getBehaviorAnalytics,
} from "@/lib/api";
import type {
  Animal,
  BehaviorAnalytics,
  DayCompare,
  WeeklySummary,
} from "@/lib/types";

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

function utcDaysAgo(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

export function AnalyticsPageClient() {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [animalId, setAnimalId] = useState<string>("");
  // Defer Date reads until after mount — cacheComponents forbids new Date() during prerender.
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [dayA, setDayA] = useState("");
  const [dayB, setDayB] = useState("");
  const [weekStart, setWeekStart] = useState("");
  const [clockReady, setClockReady] = useState(false);

  const [analytics, setAnalytics] = useState<BehaviorAnalytics | null>(null);
  const [compare, setCompare] = useState<DayCompare | null>(null);
  const [weekly, setWeekly] = useState<WeeklySummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [weeklyError, setWeeklyError] = useState<string | null>(null);

  useEffect(() => {
    setStartDate(utcDaysAgo(6));
    setEndDate(utcToday());
    setDayA(utcDaysAgo(1));
    setDayB(utcToday());
    setWeekStart(utcDaysAgo(6));
    setClockReady(true);
  }, []);

  const loadAnimals = useCallback(async () => {
    const list = await getAnimals();
    setAnimals(list);
    if (!animalId && list[0]) {
      setAnimalId(String(list[0].id));
    }
    return list;
  }, [animalId]);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBehaviorAnalytics({
        animalId: animalId ? Number(animalId) : undefined,
        startDate,
        endDate,
      });
      setAnalytics(data);
    } catch (err) {
      setAnalytics(null);
      setError(
        err instanceof Error ? err.message : "Could not load analytics.",
      );
    } finally {
      setLoading(false);
    }
  }, [animalId, startDate, endDate]);

  useEffect(() => {
    void (async () => {
      try {
        await loadAnimals();
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load animals.",
        );
        setLoading(false);
      }
    })();
  }, [loadAnimals]);

  useEffect(() => {
    if (!clockReady || !startDate || !endDate) return;
    if (!animalId && animals.length === 0) return;
    void loadAnalytics();
  }, [
    animalId,
    animals.length,
    clockReady,
    endDate,
    loadAnalytics,
    startDate,
  ]);

  async function handleCompare() {
    if (!animalId) {
      setCompareError("Select an animal to compare days.");
      return;
    }
    setComparing(true);
    setCompareError(null);
    try {
      const result = await compareAnalyticsDays(
        Number(animalId),
        dayA,
        dayB,
      );
      setCompare(result);
    } catch (err) {
      setCompare(null);
      setCompareError(
        err instanceof Error ? err.message : "Day comparison failed.",
      );
    } finally {
      setComparing(false);
    }
  }

  async function handleWeeklySummary() {
    if (!animalId) {
      setWeeklyError("Select an animal for the weekly summary.");
      return;
    }
    setSummarizing(true);
    setWeeklyError(null);
    try {
      const result = await generateWeeklySummary(Number(animalId), weekStart);
      setWeekly(result);
    } catch (err) {
      setWeekly(null);
      setWeeklyError(
        err instanceof Error ? err.message : "Weekly summary failed.",
      );
    } finally {
      setSummarizing(false);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Behavioral analytics
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Charts use real Observation rows from the database. Counts are{" "}
          <span className="text-sage-700">sample tallies</span> from analyzed
          frames — never a percentage of an animal&apos;s entire day. Empty
          days or hours mean missing samples, not proven inactivity.
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">Filters</h2>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="font-medium text-ink">Animal</span>
            <select
              className="mt-1.5 block min-w-[200px] rounded-xl border border-border bg-cream px-3 py-2.5 text-ink outline-none focus:border-sage-500"
              value={animalId}
              onChange={(e) => setAnimalId(e.target.value)}
            >
              {animals.length === 0 ? (
                <option value="">No animals</option>
              ) : (
                animals.map((animal) => (
                  <option key={animal.id} value={animal.id}>
                    {animal.name}
                  </option>
                ))
              )}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-ink">Start (UTC)</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-ink">End (UTC)</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={() => void loadAnalytics()}
            className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream hover:bg-sage-900"
          >
            Refresh
          </button>
        </div>
      </section>

      {loading ? (
        <StatePanel
          title="Loading analytics…"
          message="Aggregating observation samples from the API."
        />
      ) : error ? (
        <StatePanel tone="danger" title="Analytics unavailable" message={error} />
      ) : analytics ? (
        <>
          <section className="rounded-2xl border border-border bg-sage-50/60 p-5 md:p-6">
            <h2 className="font-display text-lg text-sage-900">
              How this data is aggregated
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              {analytics.meta.explanation}
            </p>
            <p className="mt-2 text-sm text-sage-800">
              {analytics.meta.total_observations} observation sample
              {analytics.meta.total_observations === 1 ? "" : "s"}
              {analytics.meta.animal_name
                ? ` for ${analytics.meta.animal_name}`
                : ""}{" "}
              from {analytics.meta.start_date} to {analytics.meta.end_date}{" "}
              (UTC).
            </p>
          </section>

          <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
            <h2 className="font-display text-xl text-sage-900">
              Observation coverage & missing data
            </h2>
            <p className="mt-1 text-sm text-muted">{analytics.coverage.note}</p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <CoverageStat
                label="Frames in range"
                value={analytics.coverage.frames_in_range}
              />
              <CoverageStat
                label="Observations"
                value={analytics.coverage.observations_in_range}
              />
              <CoverageStat
                label="Missing frame analyses"
                value={analytics.coverage.missing_frame_analyses}
              />
              <CoverageStat
                label="Days with no samples"
                value={analytics.coverage.days_with_no_samples}
              />
              <CoverageStat
                label="Days with samples"
                value={analytics.coverage.days_with_samples}
              />
              <CoverageStat
                label="UTC hours with samples"
                value={analytics.coverage.hours_with_samples}
              />
              <CoverageStat
                label="UTC hours without samples"
                value={
                  analytics.coverage.hours_with_no_samples_among_sampled_days
                }
              />
              <CoverageStat
                label="Days in range"
                value={analytics.coverage.days_in_range}
              />
            </dl>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
              <h2 className="font-display text-xl text-sage-900">
                Counts by behavior
              </h2>
              <p className="mt-1 text-sm text-muted">
                Sample counts only — Y-axis is number of observations, not day
                share.
              </p>
              <div className="mt-4">
                <BehaviorBarChart data={analytics.by_behavior} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
              <h2 className="font-display text-xl text-sage-900">
                Samples by day
              </h2>
              <p className="mt-1 text-sm text-muted">
                Zero on a day means no recorded samples that UTC date.
              </p>
              <div className="mt-4">
                <DaySamplesChart data={analytics.by_day} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
              <h2 className="font-display text-xl text-sage-900">
                Samples by UTC hour
              </h2>
              <p className="mt-1 text-sm text-muted">
                Across the selected range, grouped by hour of{" "}
                <code className="text-sage-700">observed_at</code>.
              </p>
              <div className="mt-4">
                <HourSamplesChart data={analytics.by_hour} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface p-5 md:p-6 lg:col-span-2">
              <h2 className="font-display text-xl text-sage-900">
                Behavioral timeline
              </h2>
              <p className="mt-1 text-sm text-muted">
                Each point is one saved observation (sparse samples in time).
              </p>
              <div className="mt-4">
                <TimelineChart points={analytics.timeline} />
              </div>
            </section>
          </div>
        </>
      ) : null}

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">
          Compare two days
        </h2>
        <p className="mt-1 text-sm text-muted">
          Side-by-side sample counts by behavior. Unequal totals usually mean
          different numbers of analyzed frames.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="font-medium text-ink">Day A</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
              value={dayA}
              onChange={(e) => setDayA(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-ink">Day B</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
              value={dayB}
              onChange={(e) => setDayB(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={comparing || !animalId}
            onClick={() => void handleCompare()}
            className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream hover:bg-sage-900 disabled:opacity-60"
          >
            {comparing ? "Comparing…" : "Compare"}
          </button>
        </div>
        {compareError ? (
          <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {compareError}
          </p>
        ) : null}
        {compare ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-muted">{compare.explanation}</p>
            <p className="text-xs text-muted">
              {compare.day_a.note} · {compare.day_b.note}
            </p>
            <DayCompareChart compare={compare} />
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">
          AI weekly summary
        </h2>
        <p className="mt-1 text-sm text-muted">
          Gemini summarizes only recorded observations for a 7-day UTC window
          starting on the date you pick. Missing days stay missing.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="font-medium text-ink">Week start (UTC)</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={summarizing || !animalId}
            onClick={() => void handleWeeklySummary()}
            className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream hover:bg-sage-900 disabled:opacity-60"
          >
            {summarizing ? "Generating…" : "Generate weekly summary"}
          </button>
        </div>
        {weeklyError ? (
          <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {weeklyError}
          </p>
        ) : null}
        {weekly ? (
          <article className="mt-4 rounded-xl bg-sage-50/80 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-sage-700">
              {weekly.animal_name} · {weekly.week_start} → {weekly.week_end} ·{" "}
              {weekly.observation_count} samples
            </p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-ink/90">
              {weekly.summary}
            </p>
            {weekly.source_observation_ids.length > 0 ? (
              <p className="mt-3 text-xs text-muted">
                Source observation IDs:{" "}
                {weekly.source_observation_ids.join(", ")}
              </p>
            ) : null}
          </article>
        ) : null}
      </section>
    </div>
  );
}

function CoverageStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-cream px-3 py-3">
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 font-display text-2xl text-sage-900">{value}</dd>
    </div>
  );
}
