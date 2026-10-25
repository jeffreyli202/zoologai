"use client";

import { ObservationResult } from "@/components/videos/ObservationResult";
import { frameImageSrc } from "@/lib/api";
import type { Frame, Observation } from "@/lib/types";

type FrameGalleryProps = {
  frames: Frame[];
  observationsByFrameId?: Record<number, Observation>;
  analyzingFrameId?: number | null;
  analyzeErrorByFrameId?: Record<number, string>;
  reusedByFrameId?: Record<number, boolean>;
  onAnalyzeFrame?: (frameId: number) => void;
  emptyMessage?: string;
};

function formatTimestamp(seconds: number): string {
  const whole = Math.floor(seconds);
  const mins = Math.floor(whole / 60);
  const secs = whole % 60;
  const ms = Math.round((seconds - whole) * 1000);
  if (mins > 0) {
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  }
  if (ms > 0) {
    return `${secs}.${ms.toString().padStart(3, "0")}s`;
  }
  return `${secs}s`;
}

export function FrameGallery({
  frames,
  observationsByFrameId = {},
  analyzingFrameId = null,
  analyzeErrorByFrameId = {},
  reusedByFrameId = {},
  onAnalyzeFrame,
  emptyMessage = "No frames extracted yet.",
}: FrameGalleryProps) {
  if (frames.length === 0) {
    return <p className="text-sm text-muted">{emptyMessage}</p>;
  }

  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
      {frames.map((frame) => {
        const observation = observationsByFrameId[frame.id];
        const busy = analyzingFrameId === frame.id;
        const error = analyzeErrorByFrameId[frame.id];

        return (
          <li
            key={frame.id}
            className="overflow-hidden rounded-xl border border-border bg-cream"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={frameImageSrc(frame)}
              alt={`Frame at ${formatTimestamp(frame.timestamp_seconds)}`}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
            <div className="space-y-2 px-2.5 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-medium text-sage-900">
                    {formatTimestamp(frame.timestamp_seconds)}
                  </p>
                  <p className="text-[11px] text-muted">
                    index {frame.frame_index} ·{" "}
                    {frame.timestamp_seconds.toFixed(3)}s
                  </p>
                </div>
                {onAnalyzeFrame ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onAnalyzeFrame(frame.id)}
                    className="rounded-lg bg-sage-700 px-2.5 py-1.5 text-[11px] font-medium text-cream transition hover:bg-sage-900 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busy
                      ? "Analyzing…"
                      : observation
                        ? "Re-check"
                        : "Analyze"}
                  </button>
                ) : null}
              </div>

              {error ? (
                <p className="rounded-md bg-danger-soft px-2 py-1.5 text-[11px] text-danger">
                  {error}
                </p>
              ) : null}

              {observation ? (
                <ObservationResult
                  observation={observation}
                  reused={Boolean(reusedByFrameId[frame.id])}
                />
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
