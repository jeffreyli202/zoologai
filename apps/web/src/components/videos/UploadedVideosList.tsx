"use client";

import { AnalysisProgress } from "@/components/videos/AnalysisProgress";
import { FrameGallery } from "@/components/videos/FrameGallery";
import { StatePanel } from "@/components/ui/StatePanel";
import type { Frame, Observation, Video } from "@/lib/types";

type UploadedVideosListProps = {
  videos: Video[];
  framesByVideoId: Record<number, Frame[]>;
  observationsByFrameId?: Record<number, Observation>;
  extractingId?: number | null;
  analyzingVideoId?: number | null;
  analyzingFrameId?: number | null;
  extractMessageById?: Record<number, string>;
  extractErrorById?: Record<number, string>;
  analyzeVideoErrorById?: Record<number, string>;
  analyzeErrorByFrameId?: Record<number, string>;
  reusedByFrameId?: Record<number, boolean>;
  maxAiCallsByVideoId?: Record<number, number>;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onExtractFrames?: (videoId: number) => void;
  onAnalyzeVideo?: (videoId: number) => void;
  onAnalyzeFrame?: (frameId: number) => void;
};

function formatBytes(size: number | null): string {
  if (size == null) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function analyzeButtonLabel(
  status: string,
  busy: boolean,
): string {
  if (busy || status === "pending" || status === "processing") {
    return "Analyzing…";
  }
  if (status === "failed") return "Retry analysis";
  if (status === "completed") return "Re-analyze";
  return "Analyze Video";
}

export function UploadedVideosList({
  videos,
  framesByVideoId,
  observationsByFrameId = {},
  extractingId = null,
  analyzingVideoId = null,
  analyzingFrameId = null,
  extractMessageById = {},
  extractErrorById = {},
  analyzeVideoErrorById = {},
  analyzeErrorByFrameId = {},
  reusedByFrameId = {},
  maxAiCallsByVideoId = {},
  loading = false,
  error = null,
  onRetry,
  onExtractFrames,
  onAnalyzeVideo,
  onAnalyzeFrame,
}: UploadedVideosListProps) {
  if (loading) {
    return (
      <StatePanel
        title="Loading videos…"
        message="Fetching upload metadata from the API."
      />
    );
  }

  if (error) {
    return (
      <StatePanel
        tone="danger"
        title="Could not load videos"
        message={error}
        actionLabel={onRetry ? "Try again" : undefined}
        onAction={onRetry}
      />
    );
  }

  if (videos.length === 0) {
    return (
      <StatePanel
        title="No videos yet"
        message="Upload an MP4, MOV, or WebM file to see it listed here. Files are stored privately on the API server."
      />
    );
  }

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
      <h2 className="font-display text-xl text-sage-900">Uploaded videos</h2>
      <p className="mt-1 text-sm text-muted">
        Use <span className="text-sage-700">Analyze Video</span> for the full
        pipeline (extract + Gemini), or extract and analyze frames one at a
        time.
      </p>

      <ul className="mt-5 divide-y divide-border/80">
        {videos.map((video) => {
          const frames = framesByVideoId[video.id] ?? [];
          const extractBusy = extractingId === video.id;
          const analyzeBusy =
            analyzingVideoId === video.id ||
            video.status === "pending" ||
            video.status === "processing";

          return (
            <li key={video.id} className="py-5 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-ink">
                    {video.original_filename ?? video.filename}
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    {video.animal_name ?? `Animal #${video.animal_id}`} ·{" "}
                    {formatBytes(video.size_bytes)} · status{" "}
                    <span className="text-sage-700">{video.status}</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {formatWhen(video.uploaded_at)}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {onAnalyzeVideo ? (
                    <button
                      type="button"
                      disabled={analyzeBusy}
                      onClick={() => onAnalyzeVideo(video.id)}
                      className="rounded-xl bg-sage-700 px-3.5 py-2 text-sm font-medium text-cream transition hover:bg-sage-900 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {analyzeButtonLabel(video.status, analyzeBusy)}
                    </button>
                  ) : null}
                  {onExtractFrames ? (
                    <button
                      type="button"
                      disabled={extractBusy || analyzeBusy}
                      onClick={() => onExtractFrames(video.id)}
                      className="rounded-xl border border-sage-300 bg-cream px-3.5 py-2 text-sm font-medium text-sage-900 transition hover:bg-sage-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {extractBusy
                        ? "Extracting…"
                        : frames.length > 0
                          ? "Re-check frames"
                          : "Extract frames"}
                    </button>
                  ) : null}
                </div>
              </div>

              <AnalysisProgress
                status={video.status}
                progress={video.analysis_progress ?? 0}
                message={video.analysis_message}
                error={
                  analyzeVideoErrorById[video.id] ?? video.analysis_error
                }
                framesDone={video.analysis_frames_done ?? 0}
                framesTotal={video.analysis_frames_total ?? 0}
                aiCalls={video.analysis_ai_calls ?? 0}
                maxAiCalls={maxAiCallsByVideoId[video.id]}
              />

              {extractMessageById[video.id] ? (
                <p className="mt-3 rounded-lg bg-sage-50 px-3 py-2 text-sm text-sage-900">
                  {extractMessageById[video.id]}
                </p>
              ) : null}
              {extractErrorById[video.id] ? (
                <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">
                  {extractErrorById[video.id]}
                </p>
              ) : null}

              {frames.length > 0 ? (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-sage-500">
                    Extracted frames ({frames.length})
                  </p>
                  <FrameGallery
                    frames={frames}
                    observationsByFrameId={observationsByFrameId}
                    analyzingFrameId={analyzingFrameId}
                    analyzeErrorByFrameId={analyzeErrorByFrameId}
                    reusedByFrameId={reusedByFrameId}
                    onAnalyzeFrame={onAnalyzeFrame}
                  />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
