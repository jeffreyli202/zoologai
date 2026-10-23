import type { MockJournalEntry, MockObservation } from "@/lib/types";

/**
 * MOCK DATA ONLY
 * Replace these helpers when FastAPI exposes Observation and DailyJournal endpoints.
 */

export const MOCK_OBSERVATIONS: MockObservation[] = [
  {
    id: "mock-obs-1",
    animalName: "Mara",
    behavior: "Resting",
    description: "Lying in shade near the rock outcrop, ears flicking occasionally.",
    observedAt: "2026-10-22T09:14:00Z",
    videoTimestampSeconds: 42,
    confidence: 0.91,
  },
  {
    id: "mock-obs-2",
    animalName: "Mara",
    behavior: "Grooming",
    description: "Self-grooming along the right flank for roughly two minutes.",
    observedAt: "2026-10-22T11:02:00Z",
    videoTimestampSeconds: 318,
    confidence: 0.86,
  },
  {
    id: "mock-obs-3",
    animalName: "Mara",
    behavior: "Walking",
    description: "Slow perimeter walk along the enclosure fence line.",
    observedAt: "2026-10-21T16:40:00Z",
    videoTimestampSeconds: 105,
    confidence: 0.78,
  },
];

export const MOCK_JOURNAL_ENTRIES: MockJournalEntry[] = [
  {
    id: "mock-journal-1",
    animalName: "Mara",
    date: "2026-10-22",
    content:
      "Mara spent the morning resting in shade, then groomed briefly before a calm perimeter walk. Overall demeanor appeared relaxed with no signs of agitation.",
  },
  {
    id: "mock-journal-2",
    animalName: "Mara",
    date: "2026-10-21",
    content:
      "Afternoon activity centered on exploratory walking. Fewer social interactions noted than the previous day; appetite and alertness remained normal.",
  },
];

/** Derived mock stats for the dashboard cards. */
export const MOCK_STATS = {
  totalObservations: MOCK_OBSERVATIONS.length,
  behaviorsDetected: new Set(MOCK_OBSERVATIONS.map((o) => o.behavior)).size,
  journalEntries: MOCK_JOURNAL_ENTRIES.length,
};
