/** Real animal shape returned by GET /animals */
export type Animal = {
  id: number;
  name: string;
  species: string;
  description: string | null;
};

/**
 * MOCK observation — used until Observation API endpoints exist.
 * Clearly not persisted; labels in the UI say "Mock data".
 */
export type MockObservation = {
  id: string;
  animalName: string;
  behavior: string;
  description: string;
  observedAt: string;
  videoTimestampSeconds: number;
  confidence: number;
};

/**
 * MOCK journal — used until DailyJournal API endpoints exist.
 */
export type MockJournalEntry = {
  id: string;
  animalName: string;
  date: string;
  content: string;
};
