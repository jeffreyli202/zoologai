import type {
  AnalyzeFrameResponse,
  Animal,
  BehaviorAnalytics,
  CameraMonitorActionResponse,
  CameraMonitorStatus,
  CameraSource,
  DailyJournal,
  DayCompare,
  ExtractFramesResponse,
  Frame,
  JournalEligibility,
  JournalGenerateResponse,
  Observation,
  ObservationStats,
  Video,
  VideoAnalysisStatus,
  WeeklySummary,
} from "@/lib/types";

/**
 * Base URL for the FastAPI backend.
 * Set NEXT_PUBLIC_API_URL in apps/web/.env.local (see .env.example at repo root).
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
};

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) =>
          typeof item === "object" && item && "msg" in item
            ? String((item as { msg: string }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
  } catch {
    // ignore JSON parse errors
  }
  return `Request failed (HTTP ${response.status})`;
}

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

export async function getVideos(): Promise<Video[]> {
  const response = await fetch(`${API_BASE_URL}/videos`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to load videos (HTTP ${response.status})`);
  }

  return response.json() as Promise<Video[]>;
}

/**
 * Upload uses multipart/form-data via the browser FormData API.
 * Do NOT set Content-Type manually — the browser adds the boundary string.
 */
export async function uploadVideo(
  animalId: number,
  file: File,
): Promise<Video> {
  const body = new FormData();
  body.append("animal_id", String(animalId));
  body.append("file", file);

  const response = await fetch(`${API_BASE_URL}/videos/upload`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<Video>;
}

export async function extractFrames(
  videoId: number,
): Promise<ExtractFramesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/videos/${videoId}/extract-frames`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<ExtractFramesResponse>;
}

/**
 * Start the full analyze job (extract frames if needed + Gemini per frame).
 * Returns 202 quickly; poll getVideoAnalysis for progress.
 */
export async function startVideoAnalysis(
  videoId: number,
  options?: { force?: boolean },
): Promise<VideoAnalysisStatus> {
  const force = options?.force ? "?force=true" : "";
  const response = await fetch(
    `${API_BASE_URL}/videos/${videoId}/analyze${force}`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<VideoAnalysisStatus>;
}

export async function getVideoAnalysis(
  videoId: number,
): Promise<VideoAnalysisStatus> {
  const response = await fetch(
    `${API_BASE_URL}/videos/${videoId}/analysis`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<VideoAnalysisStatus>;
}

export async function getVideoFrames(videoId: number): Promise<Frame[]> {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/frames`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<Frame[]>;
}

/** Full URL for a frame JPEG served by the API. */
export function frameImageSrc(frame: Frame): string {
  if (frame.image_url.startsWith("http")) {
    return frame.image_url;
  }
  return `${API_BASE_URL}${frame.image_url}`;
}

export async function analyzeFrame(
  frameId: number,
): Promise<AnalyzeFrameResponse> {
  const response = await fetch(`${API_BASE_URL}/frames/${frameId}/analyze`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<AnalyzeFrameResponse>;
}

export async function getObservations(options?: {
  animalId?: number;
  limit?: number;
}): Promise<Observation[]> {
  const params = new URLSearchParams();
  if (options?.animalId != null) {
    params.set("animal_id", String(options.animalId));
  }
  if (options?.limit != null) {
    params.set("limit", String(options.limit));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/observations${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<Observation[]>;
}

export async function getObservationStats(options?: {
  animalId?: number;
}): Promise<ObservationStats> {
  const params = new URLSearchParams();
  if (options?.animalId != null) {
    params.set("animal_id", String(options.animalId));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/observations/stats${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<ObservationStats>;
}

export async function getFrameObservation(
  frameId: number,
): Promise<Observation | null> {
  const response = await fetch(
    `${API_BASE_URL}/frames/${frameId}/observation`,
    { cache: "no-store" },
  );

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<Observation>;
}

export async function getJournals(options?: {
  animalId?: number;
  journalDate?: string;
  hour?: number;
}): Promise<DailyJournal[]> {
  const params = new URLSearchParams();
  if (options?.animalId != null) {
    params.set("animal_id", String(options.animalId));
  }
  if (options?.journalDate) {
    params.set("journal_date", options.journalDate);
  }
  if (options?.hour != null) {
    params.set("hour", String(options.hour));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/journals${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<DailyJournal[]>;
}

export async function getJournalEligibility(
  animalId: number,
  journalDate?: string,
  hour?: number,
): Promise<JournalEligibility> {
  const params = new URLSearchParams({ animal_id: String(animalId) });
  if (journalDate) {
    params.set("journal_date", journalDate);
  }
  if (hour != null) {
    params.set("hour", String(hour));
  }
  const response = await fetch(
    `${API_BASE_URL}/journals/eligibility?${params.toString()}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<JournalEligibility>;
}

export async function generateJournal(
  animalId: number,
  options?: { journalDate?: string; hour?: number; force?: boolean },
): Promise<JournalGenerateResponse> {
  const body: {
    animal_id: number;
    journal_date?: string;
    hour?: number;
    force?: boolean;
  } = {
    animal_id: animalId,
  };
  if (options?.journalDate) {
    body.journal_date = options.journalDate;
  }
  if (options?.hour != null) {
    body.hour = options.hour;
  }
  if (options?.force) {
    body.force = true;
  }

  const response = await fetch(`${API_BASE_URL}/journals/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<JournalGenerateResponse>;
}

export async function getBehaviorAnalytics(options?: {
  animalId?: number;
  startDate?: string;
  endDate?: string;
}): Promise<BehaviorAnalytics> {
  const params = new URLSearchParams();
  if (options?.animalId != null) {
    params.set("animal_id", String(options.animalId));
  }
  if (options?.startDate) {
    params.set("start_date", options.startDate);
  }
  if (options?.endDate) {
    params.set("end_date", options.endDate);
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/analytics/behaviors${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<BehaviorAnalytics>;
}

export async function compareAnalyticsDays(
  animalId: number,
  dayA: string,
  dayB: string,
): Promise<DayCompare> {
  const params = new URLSearchParams({
    animal_id: String(animalId),
    day_a: dayA,
    day_b: dayB,
  });
  const response = await fetch(
    `${API_BASE_URL}/analytics/compare-days?${params.toString()}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<DayCompare>;
}

export async function generateWeeklySummary(
  animalId: number,
  weekStart: string,
): Promise<WeeklySummary> {
  const response = await fetch(`${API_BASE_URL}/analytics/weekly-summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ animal_id: animalId, week_start: weekStart }),
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json() as Promise<WeeklySummary>;
}

export async function getCameras(): Promise<CameraSource[]> {
  const response = await fetch(`${API_BASE_URL}/cameras`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraSource[]>;
}

export async function createCamera(body: {
  name: string;
  source_type: "snapshot_url" | "live_stream" | "local_folder";
  snapshot_url?: string;
  local_folder_path?: string;
  access_authorized: boolean;
  interval_minutes?: number;
  observation_window_hours?: number;
  animal_id?: number;
}): Promise<CameraSource> {
  const response = await fetch(`${API_BASE_URL}/cameras`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraSource>;
}

export type CameraProbeResult = {
  ok: boolean;
  byte_size: number;
  extension: string;
  width: number;
  height: number;
  detail: string;
};

export async function probeCameraUrl(body: {
  url: string;
  prefer_stream?: boolean;
  access_authorized: boolean;
}): Promise<CameraProbeResult> {
  const response = await fetch(`${API_BASE_URL}/cameras/probe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraProbeResult>;
}

export type ExtractedFrame = {
  index: number;
  filename: string;
  byte_size: number;
  image_url: string;
};

export type FrameExtractResult = {
  job_id: string;
  job_dir: string;
  source_url: string;
  resolved_media: boolean;
  frame_count: number;
  interval_seconds: number;
  frames: ExtractedFrame[];
  detail: string;
};

export async function extractLiveFrames(body: {
  url: string;
  count?: number;
  interval_seconds?: number;
  label?: string;
  access_authorized: boolean;
}): Promise<FrameExtractResult> {
  const response = await fetch(`${API_BASE_URL}/cameras/extract-frames`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<FrameExtractResult>;
}

export function extractedFrameImageUrl(imagePath: string): string {
  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    return imagePath;
  }
  return `${API_BASE_URL}${imagePath.startsWith("/") ? "" : "/"}${imagePath}`;
}

export async function deleteCamera(
  cameraId: number,
): Promise<{ detail: string; id: number }> {
  const response = await fetch(`${API_BASE_URL}/cameras/${cameraId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<{ detail: string; id: number }>;
}

export async function startCameraMonitor(
  cameraId: number,
): Promise<CameraMonitorActionResponse> {
  const response = await fetch(`${API_BASE_URL}/cameras/${cameraId}/start`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraMonitorActionResponse>;
}

export async function stopCameraMonitor(
  cameraId: number,
): Promise<CameraMonitorActionResponse> {
  const response = await fetch(`${API_BASE_URL}/cameras/${cameraId}/stop`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraMonitorActionResponse>;
}

export async function getCameraMonitorStatus(
  cameraId: number,
): Promise<CameraMonitorStatus> {
  const response = await fetch(
    `${API_BASE_URL}/cameras/${cameraId}/status`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<CameraMonitorStatus>;
}
