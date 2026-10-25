"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { UploadedVideosList } from "@/components/videos/UploadedVideosList";
import { getVideoFrames, getVideos } from "@/lib/api";
import type { Frame, Video } from "@/lib/types";

export function DashboardVideos() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [framesByVideoId, setFramesByVideoId] = useState<
    Record<number, Frame[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const list = await getVideos();
      const recent = list.slice(0, 5);
      setVideos(recent);
      const entries = await Promise.all(
        recent.map(async (video) => {
          try {
            return [video.id, await getVideoFrames(video.id)] as const;
          } catch {
            return [video.id, [] as Frame[]] as const;
          }
        }),
      );
      setFramesByVideoId(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load videos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="font-display text-xl text-sage-900">
            Recent uploads
          </h2>
          <p className="mt-1 text-sm text-muted">
            Live metadata + extracted frames from the API
          </p>
        </div>
        <Link
          href="/videos"
          className="text-sm font-medium text-sage-700 hover:text-sage-900"
        >
          Manage videos →
        </Link>
      </div>
      <UploadedVideosList
        videos={videos}
        framesByVideoId={framesByVideoId}
        loading={loading}
        error={error}
        onRetry={() => void load()}
      />
    </section>
  );
}
