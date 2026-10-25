"use client";

import { useCallback, useEffect, useState } from "react";

import { StatePanel } from "@/components/ui/StatePanel";
import {
  createCamera,
  deleteCamera,
  extractLiveFrames,
  extractedFrameImageUrl,
  getCameraMonitorStatus,
  getCameras,
  probeCameraUrl,
  startCameraMonitor,
  stopCameraMonitor,
  type FrameExtractResult,
} from "@/lib/api";
import type { CameraMonitorStatus, CameraSource } from "@/lib/types";

type SourceType = "live_stream" | "snapshot_url" | "local_folder";

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(iso));
}

export function MonitoringPageClient() {
  const [cameras, setCameras] = useState<CameraSource[]>([]);
  const [statusById, setStatusById] = useState<
    Record<number, CameraMonitorStatus>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [name, setName] = useState("ONC camera");
  const [sourceType, setSourceType] = useState<SourceType>("live_stream");
  const [localFolder, setLocalFolder] = useState("./uploads/camera_samples");
  const [mediaUrl, setMediaUrl] = useState(
    "https://media.oceannetworks.ca:4935/rtplive/SUBCRAYFIN21017/playlist.m3u8",
  );
  const [intervalMinutes, setIntervalMinutes] = useState(5);
  const [authorized, setAuthorized] = useState(false);
  const [creating, setCreating] = useState(false);
  const [probing, setProbing] = useState(false);

  const [extractUrl, setExtractUrl] = useState(
    "https://www.youtube.com/watch?v=7i8ARjIeM2k",
  );
  const [extractLabel, setExtractLabel] = useState("coral_city");
  const [extractCount, setExtractCount] = useState(4);
  const [extractInterval, setExtractInterval] = useState(5);
  const [extractAuthorized, setExtractAuthorized] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractResult, setExtractResult] = useState<FrameExtractResult | null>(
    null,
  );

  const refreshStatus = useCallback(async (list: CameraSource[]) => {
    const entries = await Promise.all(
      list.map(async (camera) => {
        try {
          const status = await getCameraMonitorStatus(camera.id);
          return [camera.id, status] as const;
        } catch {
          return null;
        }
      }),
    );
    const map: Record<number, CameraMonitorStatus> = {};
    for (const entry of entries) {
      if (entry) map[entry[0]] = entry[1];
    }
    setStatusById(map);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cameraList = await getCameras();
      setCameras(cameraList);
      await refreshStatus(cameraList);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load monitoring data.",
      );
    } finally {
      setLoading(false);
    }
  }, [refreshStatus]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (cameras.length === 0) return;
    const timer = setInterval(() => {
      void refreshStatus(cameras);
      void getCameras()
        .then(setCameras)
        .catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
  }, [cameras, refreshStatus]);

  function isYouTubeUrl(url: string): boolean {
    const lower = url.toLowerCase();
    return (
      lower.includes("youtube.com") ||
      lower.includes("youtu.be") ||
      lower.includes("youtube-nocookie.com")
    );
  }

  function handleSourceTypeChange(next: SourceType) {
    setSourceType(next);
    if (next === "live_stream") {
      setName((current) =>
        current === "Local sample folder" || current === "Camera snapshot"
          ? "ONC camera"
          : current,
      );
      setIntervalMinutes((m) => (m > 15 ? 5 : m));
    } else if (next === "snapshot_url") {
      setName((current) =>
        current === "ONC camera" || current === "Local sample folder"
          ? "Camera snapshot"
          : current,
      );
    } else {
      setName((current) =>
        current === "ONC camera" || current === "Camera snapshot"
          ? "Local sample folder"
          : current,
      );
      setIntervalMinutes(15);
    }
  }

  async function handleProbe() {
    if (!mediaUrl || !authorized) {
      setError("Check authorization and paste a direct media URL first.");
      return;
    }
    setProbing(true);
    setError(null);
    setMessage(null);
    try {
      const result = await probeCameraUrl({
        url: mediaUrl,
        prefer_stream: sourceType === "live_stream",
        access_authorized: true,
      });
      setMessage(
        `${result.detail} (${result.width}×${result.height}, ${result.byte_size} bytes).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Probe failed.");
    } finally {
      setProbing(false);
    }
  }

  async function handleExtract(event: React.FormEvent) {
    event.preventDefault();
    setExtracting(true);
    setError(null);
    setMessage(null);
    setExtractResult(null);
    try {
      const result = await extractLiveFrames({
        url: extractUrl,
        count: extractCount,
        interval_seconds: extractInterval,
        label: extractLabel || undefined,
        access_authorized: extractAuthorized,
      });
      setExtractResult(result);
      setMessage(result.detail);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Frame extraction failed.",
      );
    } finally {
      setExtracting(false);
    }
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setMessage(null);
    try {
      const camera = await createCamera({
        name,
        source_type: sourceType,
        snapshot_url:
          sourceType === "local_folder" ? undefined : mediaUrl,
        local_folder_path:
          sourceType === "local_folder" ? localFolder : undefined,
        access_authorized: authorized,
        interval_minutes: intervalMinutes,
      });
      setCameras((prev) => [camera, ...prev]);
      setMessage(
        `Created “${camera.name}”. Vision will identify animals and journal sightings.`,
      );
      setAuthorized(false);
      await refreshStatus([camera, ...cameras]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create source.");
    } finally {
      setCreating(false);
    }
  }

  async function handleStart(id: number) {
    setBusyId(id);
    setError(null);
    try {
      const result = await startCameraMonitor(id);
      setMessage(result.detail);
      setCameras((prev) =>
        prev.map((c) => (c.id === id ? result.camera : c)),
      );
      const status = await getCameraMonitorStatus(id);
      setStatusById((prev) => ({ ...prev, [id]: status }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Start failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleStop(id: number) {
    setBusyId(id);
    setError(null);
    try {
      const result = await stopCameraMonitor(id);
      setMessage(result.detail);
      setCameras((prev) =>
        prev.map((c) => (c.id === id ? result.camera : c)),
      );
      const status = await getCameraMonitorStatus(id);
      setStatusById((prev) => ({ ...prev, [id]: status }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stop failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRemove(camera: CameraSource) {
    const ok = window.confirm(
      `Remove “${camera.name}”? Monitoring will stop. Saved observations stay.`,
    );
    if (!ok) return;

    setBusyId(camera.id);
    setError(null);
    try {
      const result = await deleteCamera(camera.id);
      setMessage(result.detail);
      setCameras((prev) => prev.filter((c) => c.id !== camera.id));
      setStatusById((prev) => {
        const next = { ...prev };
        delete next[camera.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Remove failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-3xl text-sage-900 md:text-4xl">
          Camera monitoring
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Poll an{" "}
          <span className="text-sage-700">authorized direct media URL</span>{" "}
          (HLS, MJPEG, RTSP, or snapshot)—including public Ocean Networks
          Canada camera streams. Each tick grabs one still; the AI lists
          animals it can see, creates animal profiles as needed, and journals
          them after the hour ends. You do not pick an animal up front. We do
          not scrape websites or bypass stream protections.
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-sage-50/70 p-5 md:p-6">
        <h2 className="font-display text-lg text-sage-900">
          What URLs work?
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted">
          <li>
            Direct <strong className="font-medium text-sage-800">.m3u8</strong>{" "}
            HLS (e.g. ONC{" "}
            <code className="text-sage-700">media.oceannetworks.ca</code>),
            MJPEG, RTSP, or a refreshing{" "}
            <strong className="font-medium text-sage-800">.jpg</strong> snapshot.
          </li>
          <li>
            Not a website homepage or player page — those return HTML and are
            rejected.
          </li>
          <li>
            ONC underwater cams are often only lit a few minutes each hour;
            dark frames mean the camera is off-schedule, not a bug.
          </li>
          <li>
            Confirm permission, then use{" "}
            <span className="text-sage-700">Test URL</span> before starting.
          </li>
        </ul>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">
          Extract frames (authorized)
        </h2>
        <p className="mt-1 text-sm text-muted">
          Pull JPEG stills from a live source you have permission to use —
          direct HLS/RTSP/snapshot, or YouTube live pages (resolved via
          yt-dlp). Explore.org player pages are not direct media — use the
          matching YouTube watch URL (e.g. Coral City{" "}
          <code className="text-sage-700">7i8ARjIeM2k</code>, Utopia Edge-of-Wall{" "}
          <code className="text-sage-700">Sq-X4Ga1oyc</code>).
        </p>
        <form
          onSubmit={(e) => void handleExtract(e)}
          className="mt-4 space-y-4"
        >
          <label className="block text-sm">
            <span className="font-medium text-ink">Live URL</span>
            <input
              className="mt-1.5 block w-full max-w-xl rounded-xl border border-border bg-cream px-3 py-2.5"
              value={extractUrl}
              onChange={(e) => setExtractUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=… or Explore.org livecam"
              required
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <label className="block text-sm">
              <span className="font-medium text-ink">Label</span>
              <input
                className="mt-1.5 block min-w-[160px] rounded-xl border border-border bg-cream px-3 py-2.5"
                value={extractLabel}
                onChange={(e) => setExtractLabel(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium text-ink">Frames</span>
              <input
                type="number"
                min={1}
                max={24}
                className="mt-1.5 block w-24 rounded-xl border border-border bg-cream px-3 py-2.5"
                value={extractCount}
                onChange={(e) => setExtractCount(Number(e.target.value))}
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium text-ink">Interval (sec)</span>
              <input
                type="number"
                min={0}
                max={300}
                step={1}
                className="mt-1.5 block w-28 rounded-xl border border-border bg-cream px-3 py-2.5"
                value={extractInterval}
                onChange={(e) => setExtractInterval(Number(e.target.value))}
              />
            </label>
          </div>
          <label className="flex items-start gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="mt-1"
              checked={extractAuthorized}
              onChange={(e) => setExtractAuthorized(e.target.checked)}
            />
            <span>
              I confirm I have permission to extract frames from this source
              (required).
            </span>
          </label>
          <button
            type="submit"
            disabled={extracting || !extractAuthorized || !extractUrl}
            className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream hover:bg-sage-900 disabled:opacity-60"
          >
            {extracting ? "Extracting…" : "Extract frames"}
          </button>
        </form>
        {extractResult ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-muted">
              Job <span className="text-sage-800">{extractResult.job_dir}</span>{" "}
              · {extractResult.frame_count} frame(s)
              {extractResult.resolved_media
                ? " · platform URL resolved"
                : ""}
            </p>
            <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {extractResult.frames.map((frame) => (
                <li key={frame.filename}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={extractedFrameImageUrl(frame.image_url)}
                    alt={frame.filename}
                    className="aspect-video w-full rounded-lg border border-border object-cover"
                  />
                  <p className="mt-1 truncate text-xs text-muted">
                    {frame.filename}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5 md:p-6">
        <h2 className="font-display text-xl text-sage-900">Add live source</h2>
        <form onSubmit={(e) => void handleCreate(e)} className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-3">
            <label className="block text-sm">
              <span className="font-medium text-ink">Name</span>
              <input
                className="mt-1.5 block min-w-[200px] rounded-xl border border-border bg-cream px-3 py-2.5"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium text-ink">Source</span>
              <select
                className="mt-1.5 block rounded-xl border border-border bg-cream px-3 py-2.5"
                value={sourceType}
                onChange={(e) =>
                  handleSourceTypeChange(e.target.value as SourceType)
                }
              >
                <option value="live_stream">Live stream (HLS / MJPEG / RTSP)</option>
                <option value="snapshot_url">Refreshing snapshot image URL</option>
                <option value="local_folder">Local sample folder (test)</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-medium text-ink">Interval (minutes)</span>
              <input
                type="number"
                min={1}
                max={1440}
                className="mt-1.5 block w-28 rounded-xl border border-border bg-cream px-3 py-2.5"
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(Number(e.target.value))}
              />
            </label>
          </div>

          {sourceType === "local_folder" ? (
            <label className="block text-sm">
              <span className="font-medium text-ink">Local folder path</span>
              <input
                className="mt-1.5 block w-full max-w-xl rounded-xl border border-border bg-cream px-3 py-2.5"
                value={localFolder}
                onChange={(e) => setLocalFolder(e.target.value)}
                placeholder="./uploads/camera_samples"
              />
            </label>
          ) : (
            <label className="block text-sm">
              <span className="font-medium text-ink">
                {sourceType === "live_stream"
                  ? "Direct live media URL"
                  : "Direct snapshot image URL"}
              </span>
              <input
                className="mt-1.5 block w-full max-w-xl rounded-xl border border-border bg-cream px-3 py-2.5"
                value={mediaUrl}
                onChange={(e) => {
                  const next = e.target.value;
                  setMediaUrl(next);
                  if (isYouTubeUrl(next)) {
                    setIntervalMinutes(5);
                  }
                }}
                placeholder={
                  sourceType === "live_stream"
                    ? "https://…/stream.m3u8  or  YouTube live watch URL"
                    : "https://…/camera/latest.jpg"
                }
                required
              />
              <span className="mt-1 block text-xs text-muted">
                Direct media (HLS/RTSP/snapshot) or an authorized YouTube live
                watch URL. YouTube cams capture every 5 minutes.
              </span>
            </label>
          )}

          <label className="flex items-start gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="mt-1"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
            />
            <span>
              I confirm this camera/source explicitly permits automated access
              (required).
            </span>
          </label>

          <div className="flex flex-wrap gap-2">
            {sourceType !== "local_folder" ? (
              <button
                type="button"
                disabled={probing || !authorized || !mediaUrl}
                onClick={() => void handleProbe()}
                className="rounded-xl border border-sage-300 bg-cream px-4 py-2.5 text-sm font-medium text-sage-900 hover:bg-sage-50 disabled:opacity-60"
              >
                {probing ? "Testing…" : "Test URL"}
              </button>
            ) : null}
            <button
              type="submit"
              disabled={creating || !authorized}
              className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream hover:bg-sage-900 disabled:opacity-60"
            >
              {creating ? "Creating…" : "Create source"}
            </button>
          </div>
        </form>
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

      {loading ? (
        <StatePanel title="Loading…" message="Fetching camera sources." />
      ) : cameras.length === 0 ? (
        <StatePanel
          title="No live sources yet"
          message="Add an authorized live stream/snapshot URL, or use the local sample folder to test."
        />
      ) : (
        <ul className="space-y-5">
          {cameras.map((camera) => {
            const status = statusById[camera.id];
            const running = camera.status === "running";
            return (
              <li
                key={camera.id}
                className="rounded-2xl border border-border bg-surface p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-ink">{camera.name}</p>
                    <p className="mt-1 text-sm text-muted">
                      AI discovers animals · {camera.source_type} · every{" "}
                      {camera.interval_minutes} min · status{" "}
                      <span className="text-sage-700">{camera.status}</span>
                    </p>
                    {camera.snapshot_url ? (
                      <p className="mt-1 max-w-xl truncate text-xs text-muted">
                        {camera.snapshot_url}
                      </p>
                    ) : null}
                    <p className="mt-1 text-xs text-muted">
                      Last run {formatWhen(camera.last_run_at)} · next{" "}
                      {formatWhen(camera.next_run_at)} · captures{" "}
                      {camera.capture_count} · skips {camera.skip_count} ·
                      errors {camera.error_count}
                    </p>
                    {camera.last_error ? (
                      <p className="mt-2 text-sm text-danger">
                        {camera.last_error}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busyId === camera.id || running}
                      onClick={() => void handleStart(camera.id)}
                      className="rounded-xl bg-sage-700 px-3.5 py-2 text-sm font-medium text-cream hover:bg-sage-900 disabled:opacity-60"
                    >
                      Start watching
                    </button>
                    <button
                      type="button"
                      disabled={busyId === camera.id || !running}
                      onClick={() => void handleStop(camera.id)}
                      className="rounded-xl border border-sage-300 bg-cream px-3.5 py-2 text-sm font-medium text-sage-900 hover:bg-sage-50 disabled:opacity-60"
                    >
                      Stop
                    </button>
                    <button
                      type="button"
                      disabled={busyId === camera.id}
                      onClick={() => void handleRemove(camera)}
                      className="rounded-xl border border-danger/40 bg-cream px-3.5 py-2 text-sm font-medium text-danger hover:bg-danger-soft disabled:opacity-60"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {status ? (
                  <div className="mt-4 rounded-xl bg-cream px-3 py-3 text-xs text-muted">
                    Scheduler:{" "}
                    {status.scheduler_running ? "running" : "stopped"} ·{" "}
                    {status.detail}
                  </div>
                ) : null}

                {status?.recent_logs?.length ? (
                  <div className="mt-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-sage-500">
                      Recent logs
                    </p>
                    <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto text-sm">
                      {status.recent_logs.map((log) => (
                        <li
                          key={log.id}
                          className={`rounded-lg px-3 py-2 ${
                            log.level === "error"
                              ? "bg-danger-soft text-danger"
                              : log.level === "skip"
                                ? "bg-sage-50 text-sage-800"
                                : "bg-sage-50/70 text-ink/90"
                          }`}
                        >
                          <span className="font-medium">{log.event}</span> ·{" "}
                          {log.message}
                          <span className="mt-0.5 block text-xs opacity-80">
                            {formatWhen(log.created_at)}
                            {log.detail ? ` · ${log.detail}` : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
