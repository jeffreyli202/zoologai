/** Real animal shape returned by GET /animals */
export type Animal = {
  id: number;
  name: string;
  species: string;
  description: string | null;
};

/** Real video metadata from GET /videos (files stay private on the server). */
export type Video = {
  id: number;
  animal_id: number;
  animal_name: string | null;
  filename: string;
  original_filename: string | null;
  size_bytes: number | null;
  /** uploaded | pending | processing | completed | failed (+ legacy values) */
  status: string;
  uploaded_at: string;
  analysis_progress: number;
  analysis_message: string | null;
  analysis_error: string | null;
  analysis_frames_total: number;
  analysis_frames_done: number;
  analysis_ai_calls: number;
  analysis_started_at: string | null;
  analysis_finished_at: string | null;
};

/** Progress payload from POST /videos/{id}/analyze and GET .../analysis. */
export type VideoAnalysisStatus = {
  video_id: number;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
  frames_total: number;
  frames_done: number;
  ai_calls: number;
  max_ai_calls: number;
  started_at: string | null;
  finished_at: string | null;
  detail: string;
};

/** Extracted still frame metadata (image served via image_url on the API). */
export type Frame = {
  id: number;
  video_id: number;
  filename: string;
  timestamp_seconds: number;
  frame_index: number;
  created_at: string;
  image_url: string;
};

export type ExtractFramesResponse = {
  video_id: number;
  reused: boolean;
  detail: string;
  frames: Frame[];
};

/** Vision-model observation saved for one frame. */
export type Observation = {
  id: number;
  animal_id: number;
  animal_name: string | null;
  video_id: number | null;
  frame_id: number | null;
  camera_source_id?: number | null;
  camera_capture_id?: number | null;
  observed_at: string;
  video_timestamp_seconds: number;
  behavior: string;
  description: string | null;
  visible_evidence: string | null;
  confidence: number | null;
};

export type ObservationStats = {
  total: number;
  distinct_behaviors: number;
};

export type AnalyzeFrameResponse = {
  reused: boolean;
  detail: string;
  observation: Observation;
};

export type DailyJournal = {
  id: number;
  animal_id: number;
  animal_name: string | null;
  date: string;
  /** UTC hour 0–23, or -1 for a full-day / legacy journal. */
  hour: number;
  content: string;
  source_observation_ids: number[];
  created_at: string;
  updated_at: string | null;
};

export type JournalGenerateResponse = {
  reused: boolean;
  regenerated: boolean;
  detail: string;
  journal: DailyJournal;
  observation_count: number;
};

export type JournalEligibility = {
  animal_id: number;
  journal_date: string;
  hour: number | null;
  observation_count: number;
  observation_ids: number[];
  has_journal: boolean;
  journal_id: number | null;
  detail: string;
};

export type BehaviorCount = {
  behavior: string;
  count: number;
};

export type DayCount = {
  date: string;
  count: number;
  by_behavior: BehaviorCount[];
};

export type HourCount = {
  hour: number;
  count: number;
  by_behavior: BehaviorCount[];
};

export type TimelinePoint = {
  observation_id: number;
  observed_at: string;
  behavior: string;
  confidence: number | null;
  video_timestamp_seconds: number;
  description: string | null;
  visible_evidence: string | null;
  /** Null for camera-capture observations (not from an uploaded video). */
  video_id: number | null;
  frame_id: number | null;
  camera_source_id?: number | null;
  camera_capture_id?: number | null;
};

export type CoverageStats = {
  frames_in_range: number;
  observations_in_range: number;
  missing_frame_analyses: number;
  days_in_range: number;
  days_with_samples: number;
  days_with_no_samples: number;
  hours_with_samples: number;
  hours_with_no_samples_among_sampled_days: number;
  note: string;
};

export type BehaviorAnalytics = {
  meta: {
    animal_id: number | null;
    animal_name: string | null;
    start_date: string;
    end_date: string;
    total_observations: number;
    explanation: string;
  };
  by_behavior: BehaviorCount[];
  by_day: DayCount[];
  by_hour: HourCount[];
  timeline: TimelinePoint[];
  coverage: CoverageStats;
};

export type DayBehaviorSnapshot = {
  date: string;
  total_observations: number;
  by_behavior: BehaviorCount[];
  note: string;
};

export type DayCompare = {
  animal_id: number;
  animal_name: string | null;
  day_a: DayBehaviorSnapshot;
  day_b: DayBehaviorSnapshot;
  explanation: string;
};

export type WeeklySummary = {
  animal_id: number;
  animal_name: string | null;
  week_start: string;
  week_end: string;
  observation_count: number;
  source_observation_ids: number[];
  summary: string;
  detail: string;
};

export type CameraSource = {
  id: number;
  animal_id: number | null;
  animal_name: string | null;
  name: string;
  source_type: "snapshot_url" | "live_stream" | "local_folder" | string;
  snapshot_url: string | null;
  local_folder_path: string | null;
  access_authorized: boolean;
  interval_minutes: number;
  observation_window_hours: number;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  last_image_hash: string | null;
  local_folder_index: number;
  last_journal_date: string | null;
  last_journal_hour_at: string | null;
  capture_count: number;
  skip_count: number;
  error_count: number;
  created_at: string;
  updated_at: string | null;
};

export type MonitoringLog = {
  id: number;
  camera_source_id: number;
  level: string;
  event: string;
  message: string;
  detail: string | null;
  created_at: string;
};

export type CameraMonitorStatus = {
  camera_source_id: number;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  capture_count: number;
  skip_count: number;
  error_count: number;
  scheduler_running: boolean;
  detail: string;
  recent_logs: MonitoringLog[];
};

export type CameraMonitorActionResponse = {
  camera: CameraSource;
  detail: string;
};
