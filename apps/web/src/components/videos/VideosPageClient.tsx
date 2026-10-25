"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { UploadedVideosList } from "@/components/videos/UploadedVideosList";
import { VideoUploadForm } from "@/components/videos/VideoUploadForm";
import {
  analyzeFrame,
  extractFrames,
  getFrameObservation,
  getVideoAnalysis,
  getVideoFrames,
  getVideos,
  startVideoAnalysis,
} from "@/lib/api";
import type { Frame, Observation, Video, VideoAnalysisStatus } from "@/lib/types";

const TERMINAL = new Set(["completed", "failed"]);
const ACTIVE = new Set(["pending", "processing"]);

function applyAnalysisToVideo(
  video: Video,
  status: VideoAnalysisStatus,
): Video {
  return {
    ...video,
    status: status.status,
    analysis_progress: status.progress,
    analysis_message: status.message,
    analysis_error: status.error,
    analysis_frames_total: status.frames_total,
    analysis_frames_done: status.frames_done,
    analysis_ai_calls: status.ai_calls,
    analysis_started_at: status.started_at,
    analysis_finished_at: status.finished_at,
  };
}

export function VideosPageClient() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [framesByVideoId, setFramesByVideoId] = useState<
    Record<number, Frame[]>
  >({});
  const [observationsByFrameId, setObservationsByFrameId] = useState<
    Record<number, Observation>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [extractingId, setExtractingId] = useState<number | null>(null);
  const [analyzingVideoId, setAnalyzingVideoId] = useState<number | null>(null);
  const [analyzingFrameId, setAnalyzingFrameId] = useState<number | null>(null);
  const [extractMessageById, setExtractMessageById] = useState<
    Record<number, string>
  >({});
  const [extractErrorById, setExtractErrorById] = useState<
    Record<number, string>
  >({});
  const [analyzeVideoErrorById, setAnalyzeVideoErrorById] = useState<
    Record<number, string>
  >({});
  const [analyzeErrorByFrameId, setAnalyzeErrorByFrameId] = useState<
    Record<number, string>
  >({});
  const [reusedByFrameId, setReusedByFrameId] = useState<
    Record<number, boolean>
  >({});
  const [maxAiCallsByVideoId, setMaxAiCallsByVideoId] = useState<
    Record<number, number>
  >({});

  const pollTimers = useRef<Record<number, ReturnType<typeof setInterval>>>(
    {},
  );

  const loadObservationsForFrames = useCallback(async (frames: Frame[]) => {
    const entries = await Promise.all(
      frames.map(async (frame) => {
        try {
          const obs = await getFrameObservation(frame.id);
          return obs ? ([frame.id, obs] as const) : null;
        } catch {
          return null;
        }
      }),
    );
    const map: Record<number, Observation> = {};
    for (const entry of entries) {
      if (entry) {
        map[entry[0]] = entry[1];
      }
    }
    setObservationsByFrameId((prev) => ({ ...prev, ...map }));
  }, []);

  const loadFramesForVideos = useCallback(
    async (list: Video[]) => {
      const entries = await Promise.all(
        list.map(async (video) => {
          try {
            const frames = await getVideoFrames(video.id);
            return [video.id, frames] as const;
          } catch {
            return [video.id, [] as Frame[]] as const;
          }
        }),
      );
      setFramesByVideoId(Object.fromEntries(entries));
      const allFrames = entries.flatMap(([, frames]) => frames);
      await loadObservationsForFrames(allFrames);
    },
    [loadObservationsForFrames],
  );

  const stopPolling = useCallback((videoId: number) => {
    const timer = pollTimers.current[videoId];
    if (timer) {
      clearInterval(timer);
      delete pollTimers.current[videoId];
    }
  }, []);

  const refreshAfterJob = useCallback(
    async (videoId: number) => {
      try {
        const frames = await getVideoFrames(videoId);
        setFramesByVideoId((prev) => ({ ...prev, [videoId]: frames }));
        await loadObservationsForFrames(frames);
      } catch {
        // Progress already updated; frame refresh is best-effort.
      }
    },
    [loadObservationsForFrames],
  );

  const startPolling = useCallback(
    (videoId: number) => {
      stopPolling(videoId);

      const tick = async () => {
        try {
          const status = await getVideoAnalysis(videoId);
          setMaxAiCallsByVideoId((prev) => ({
            ...prev,
            [videoId]: status.max_ai_calls,
          }));
          setVideos((prev) =>
            prev.map((video) =>
              video.id === videoId
                ? applyAnalysisToVideo(video, status)
                : video,
            ),
          );

          if (TERMINAL.has(status.status)) {
            stopPolling(videoId);
            setAnalyzingVideoId((current) =>
              current === videoId ? null : current,
            );
            await refreshAfterJob(videoId);
          }
        } catch (err) {
          stopPolling(videoId);
          setAnalyzingVideoId((current) =>
            current === videoId ? null : current,
          );
          setAnalyzeVideoErrorById((prev) => ({
            ...prev,
            [videoId]:
              err instanceof Error
                ? err.message
                : "Could not poll analysis status.",
          }));
        }
      };

      void tick();
      pollTimers.current[videoId] = setInterval(() => {
        void tick();
      }, 1500);
    },
    [refreshAfterJob, stopPolling],
  );

  const loadVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await getVideos();
      setVideos(list);
      await loadFramesForVideos(list);
      for (const video of list) {
        if (ACTIVE.has(video.status)) {
          startPolling(video.id);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load videos.");
    } finally {
      setLoading(false);
    }
  }, [loadFramesForVideos, startPolling]);

  useEffect(() => {
    void loadVideos();
    const timers = pollTimers.current;
    return () => {
      for (const id of Object.keys(timers)) {
        const handle = timers[Number(id)];
        if (handle) {
          window.clearInterval(handle);
          delete timers[Number(id)];
        }
      }
    };
  }, [loadVideos]);

  async function handleExtract(videoId: number) {
    setExtractingId(videoId);
    setExtractErrorById((prev) => {
      const next = { ...prev };
      delete next[videoId];
      return next;
    });

    try {
      const result = await extractFrames(videoId);
      setFramesByVideoId((prev) => ({ ...prev, [videoId]: result.frames }));
      setExtractMessageById((prev) => ({
        ...prev,
        [videoId]: result.detail,
      }));
      setVideos((prev) =>
        prev.map((video) =>
          video.id === videoId
            ? {
                ...video,
                status: result.reused ? video.status : "frames_extracted",
              }
            : video,
        ),
      );
      await loadObservationsForFrames(result.frames);
    } catch (err) {
      setExtractErrorById((prev) => ({
        ...prev,
        [videoId]:
          err instanceof Error ? err.message : "Frame extraction failed.",
      }));
      setVideos((prev) =>
        prev.map((video) =>
          video.id === videoId
            ? { ...video, status: "extraction_failed" }
            : video,
        ),
      );
    } finally {
      setExtractingId(null);
    }
  }

  async function handleAnalyzeVideo(videoId: number) {
    setAnalyzingVideoId(videoId);
    setAnalyzeVideoErrorById((prev) => {
      const next = { ...prev };
      delete next[videoId];
      return next;
    });

    const current = videos.find((v) => v.id === videoId);
    const force = current?.status === "completed";

    try {
      const status = await startVideoAnalysis(videoId, { force });
      setMaxAiCallsByVideoId((prev) => ({
        ...prev,
        [videoId]: status.max_ai_calls,
      }));
      setVideos((prev) =>
        prev.map((video) =>
          video.id === videoId ? applyAnalysisToVideo(video, status) : video,
        ),
      );

      if (ACTIVE.has(status.status) || status.status === "pending") {
        startPolling(videoId);
      } else {
        setAnalyzingVideoId(null);
        if (status.status === "completed") {
          await refreshAfterJob(videoId);
        }
      }
    } catch (err) {
      setAnalyzingVideoId(null);
      setAnalyzeVideoErrorById((prev) => ({
        ...prev,
        [videoId]:
          err instanceof Error ? err.message : "Could not start analysis.",
      }));
    }
  }

  async function handleAnalyze(frameId: number) {
    setAnalyzingFrameId(frameId);
    setAnalyzeErrorByFrameId((prev) => {
      const next = { ...prev };
      delete next[frameId];
      return next;
    });

    try {
      const result = await analyzeFrame(frameId);
      setObservationsByFrameId((prev) => ({
        ...prev,
        [frameId]: result.observation,
      }));
      setReusedByFrameId((prev) => ({
        ...prev,
        [frameId]: result.reused,
      }));
    } catch (err) {
      setAnalyzeErrorByFrameId((prev) => ({
        ...prev,
        [frameId]:
          err instanceof Error ? err.message : "Vision analysis failed.",
      }));
    } finally {
      setAnalyzingFrameId(null);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Videos
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Upload a clip, then click{" "}
          <span className="text-sage-700">Analyze Video</span> to extract
          frames and run Gemini on each still in the background. The HTTP
          request returns immediately; progress updates while the job runs.
          Requires <code className="text-sage-700">GEMINI_API_KEY</code> in the
          API <code className="text-sage-700">.env</code> (never in the
          frontend).
        </p>
      </header>

      <VideoUploadForm
        onUploaded={(video) => {
          setVideos((current) => [video, ...current]);
          setFramesByVideoId((current) => ({ ...current, [video.id]: [] }));
        }}
      />

      <UploadedVideosList
        videos={videos}
        framesByVideoId={framesByVideoId}
        observationsByFrameId={observationsByFrameId}
        extractingId={extractingId}
        analyzingVideoId={analyzingVideoId}
        analyzingFrameId={analyzingFrameId}
        extractMessageById={extractMessageById}
        extractErrorById={extractErrorById}
        analyzeVideoErrorById={analyzeVideoErrorById}
        analyzeErrorByFrameId={analyzeErrorByFrameId}
        reusedByFrameId={reusedByFrameId}
        maxAiCallsByVideoId={maxAiCallsByVideoId}
        loading={loading}
        error={error}
        onRetry={() => void loadVideos()}
        onExtractFrames={(id) => void handleExtract(id)}
        onAnalyzeVideo={(id) => void handleAnalyzeVideo(id)}
        onAnalyzeFrame={(id) => void handleAnalyze(id)}
      />
    </div>
  );
}
