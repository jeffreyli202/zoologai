"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { JournalEntryCard } from "@/components/journal/JournalEntryCard";
import { StatePanel } from "@/components/ui/StatePanel";
import {
  generateJournal,
  getAnimals,
  getJournalEligibility,
  getJournals,
} from "@/lib/api";
import type { Animal, DailyJournal, JournalEligibility } from "@/lib/types";

const ALL_ANIMALS = "all";

function todayUtcDate(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Previous completed UTC hour (0–23). */
function defaultUtcHour(): number {
  const now = new Date();
  return (now.getUTCHours() + 23) % 24;
}

function formatDateHeading(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${isoDate}T12:00:00`));
}

function sortEntries(a: DailyJournal, b: DailyJournal): number {
  // Hourly first (desc), then full-day (-1) last within a date.
  return (b.hour ?? -1) - (a.hour ?? -1);
}

function groupByDate(journals: DailyJournal[]): [string, DailyJournal[]][] {
  const map = new Map<string, DailyJournal[]>();
  for (const journal of journals) {
    const list = map.get(journal.date) ?? [];
    list.push(journal);
    map.set(journal.date, list);
  }
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, entries]) => [date, [...entries].sort(sortEntries)]);
}

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, h) => h);

export function JournalPageClient() {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [animalId, setAnimalId] = useState<string>(ALL_ANIMALS);
  // Defer Date reads until after mount — cacheComponents forbids new Date() during prerender.
  const [journalDate, setJournalDate] = useState<string>("");
  const [hour, setHour] = useState<number>(0);
  const [clockReady, setClockReady] = useState(false);
  const [journals, setJournals] = useState<DailyJournal[]>([]);
  const [eligibility, setEligibility] = useState<JournalEligibility | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [checkingDay, setCheckingDay] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const isAll = animalId === ALL_ANIMALS;

  useEffect(() => {
    setJournalDate(todayUtcDate());
    setHour(defaultUtcHour());
    setClockReady(true);
  }, []);

  const loadJournals = useCallback(async (selectedAnimalId: string) => {
    const list = await getJournals(
      selectedAnimalId !== ALL_ANIMALS
        ? { animalId: Number(selectedAnimalId) }
        : undefined,
    );
    setJournals(list);
  }, []);

  const refreshEligibility = useCallback(
    async (selectedAnimalId: string, date: string, selectedHour: number) => {
      if (!selectedAnimalId || selectedAnimalId === ALL_ANIMALS) {
        setEligibility(null);
        return;
      }
      setCheckingDay(true);
      try {
        const result = await getJournalEligibility(
          Number(selectedAnimalId),
          date,
          selectedHour,
        );
        setEligibility(result);
      } catch (err) {
        setEligibility(null);
        setError(
          err instanceof Error
            ? err.message
            : "Could not check observations for this hour.",
        );
      } finally {
        setCheckingDay(false);
      }
    },
    [],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const animalList = await getAnimals();
      setAnimals(animalList);
      await loadJournals(animalId);
      if (!isAll) {
        await refreshEligibility(animalId, journalDate, hour);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load journals.");
    } finally {
      setLoading(false);
    }
  }, [
    animalId,
    hour,
    isAll,
    journalDate,
    loadJournals,
    refreshEligibility,
  ]);

  useEffect(() => {
    if (!clockReady) return;
    void load();
    // Initial load once the UTC clock is ready — later changes use targeted refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clockReady]);

  useEffect(() => {
    if (!clockReady || !journalDate) return;
    void loadJournals(animalId);
    if (isAll) {
      setEligibility(null);
      return;
    }
    void refreshEligibility(animalId, journalDate, hour);
  }, [
    animalId,
    clockReady,
    journalDate,
    hour,
    isAll,
    loadJournals,
    refreshEligibility,
  ]);

  const grouped = useMemo(() => groupByDate(journals), [journals]);

  const noObservationsForHour =
    !isAll &&
    !!eligibility &&
    eligibility.observation_count === 0 &&
    !checkingDay;

  const hourLabel = `${String(hour).padStart(2, "0")}:00–${String(hour).padStart(2, "0")}:59 UTC`;

  async function handleGenerate(force: boolean) {
    if (isAll || !animalId) {
      setError("Pick a specific animal to generate a journal (All is view-only).");
      return;
    }
    if (noObservationsForHour) {
      setError(null);
      setMessage(null);
      return;
    }

    setGenerating(true);
    setError(null);
    setMessage(null);
    try {
      const result = await generateJournal(Number(animalId), {
        journalDate,
        hour,
        force,
      });
      setMessage(result.detail);
      setJournals((prev) => {
        const withoutSame = prev.filter(
          (j) =>
            !(
              j.animal_id === result.journal.animal_id &&
              j.date === result.journal.date &&
              j.hour === result.journal.hour
            ),
        );
        return [result.journal, ...withoutSame];
      });
      await refreshEligibility(animalId, journalDate, hour);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Journal generation failed.",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Journal
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Journals are written per UTC hour from saved observation rows.
          Camera monitoring discovers animals in each still, then journals
          them when the hour ends — empty / not-visible frames do not create
          entries. Use <span className="text-sage-700">All</span> to browse
          every journal.
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">
          Generate hourly journal
        </h2>
        <p className="mt-1 text-sm text-muted">
          Filter by animal (or All), then pick a UTC date and hour. Generating
          requires a specific animal with sightings in that hour.
        </p>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="font-medium text-ink">Animal</span>
            <select
              className="mt-1.5 block min-w-[220px] rounded-xl border border-border bg-cream px-3 py-2.5 text-ink outline-none focus:border-sage-500"
              value={animalId}
              onChange={(e) => setAnimalId(e.target.value)}
              disabled={generating}
            >
              <option value={ALL_ANIMALS}>All</option>
              {animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name} ({animal.species})
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="font-medium text-ink">Date (UTC)</span>
            <input
              type="date"
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5 text-ink outline-none focus:border-sage-500"
              value={journalDate}
              onChange={(e) => setJournalDate(e.target.value)}
              disabled={generating}
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-ink">Hour (UTC)</span>
            <select
              className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5 text-ink outline-none focus:border-sage-500"
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              disabled={generating}
            >
              {HOUR_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, "0")}:00–{String(h).padStart(2, "0")}
                  :59
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            disabled={generating || isAll || noObservationsForHour}
            onClick={() => void handleGenerate(false)}
            className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream transition hover:bg-sage-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {generating
              ? "Generating…"
              : eligibility?.has_journal
                ? "Open saved journal"
                : "Generate journal"}
          </button>

          {eligibility?.has_journal && !isAll ? (
            <button
              type="button"
              disabled={generating || noObservationsForHour}
              onClick={() => void handleGenerate(true)}
              className="rounded-xl border border-sage-300 bg-cream px-4 py-2.5 text-sm font-medium text-sage-900 transition hover:bg-sage-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Regenerate
            </button>
          ) : null}
        </div>

        {isAll ? (
          <p className="mt-3 text-sm text-muted">
            Showing journals for all animals. Select one animal to check
            eligibility or generate.
          </p>
        ) : checkingDay ? (
          <p className="mt-3 text-sm text-muted">Checking observations…</p>
        ) : eligibility ? (
          <p className="mt-3 text-sm text-muted">{eligibility.detail}</p>
        ) : null}

        {message ? (
          <p className="mt-3 rounded-lg bg-sage-50 px-3 py-2 text-sm text-sage-900">
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
            {error}
          </p>
        ) : null}
      </section>

      {noObservationsForHour ? (
        <StatePanel
          title="No observations for this hour"
          message={`Nothing was invented for ${journalDate} ${hourLabel}. Capture or analyze frames that produce observations in this UTC hour, then generate a journal.`}
        />
      ) : null}

      {loading ? (
        <StatePanel
          title="Loading journals…"
          message="Fetching saved hourly journals from the API."
        />
      ) : grouped.length === 0 ? (
        <StatePanel
          title="No journals yet"
          message="When the camera AI identifies animals and an hour ends with sightings, journals appear here. Use All to see every animal."
        />
      ) : (
        <div className="space-y-8">
          <h2 className="font-display text-xl text-sage-900">
            Past journals{isAll ? " (all animals)" : ""}
          </h2>
          {grouped.map(([date, entries]) => (
            <section key={date}>
              <h3 className="border-b border-border pb-2 font-display text-lg text-sage-900">
                {formatDateHeading(date)}
              </h3>
              <ul className="mt-4 space-y-4">
                {entries.map((journal) => (
                  <li key={journal.id}>
                    <JournalEntryCard journal={journal} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
