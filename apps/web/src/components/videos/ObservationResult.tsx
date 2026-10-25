"use client";

import type { Observation } from "@/lib/types";

type ObservationResultProps = {
  observation: Observation;
  reused?: boolean;
};

export function ObservationResult({
  observation,
  reused = false,
}: ObservationResultProps) {
  const confidencePct =
    observation.confidence == null
      ? null
      : `${Math.round(observation.confidence * 100)}%`;

  return (
    <div className="mt-2 rounded-lg border border-sage-100 bg-sage-50/80 px-2.5 py-2 text-left">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-sage-800">
          {observation.behavior.replaceAll("_", " ")}
        </p>
        {confidencePct ? (
          <p className="text-[11px] text-muted">confidence {confidencePct}</p>
        ) : null}
        {reused ? (
          <span className="rounded bg-cream-deep px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted">
            saved
          </span>
        ) : null}
      </div>
      {observation.description ? (
        <p className="mt-1 text-[11px] leading-4 text-ink/90">
          {observation.description}
        </p>
      ) : null}
      {observation.visible_evidence ? (
        <p className="mt-1 text-[11px] leading-4 text-muted">
          <span className="font-medium text-sage-700">Evidence: </span>
          {observation.visible_evidence}
        </p>
      ) : null}
      <p className="mt-1 text-[10px] text-muted">
        Model estimate only · single-frame snapshot at{" "}
        {observation.video_timestamp_seconds.toFixed(1)}s · not a duration
      </p>
    </div>
  );
}
