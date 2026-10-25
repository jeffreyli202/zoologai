"use client";

import { useEffect, useState } from "react";

import { getAnimals, uploadVideo } from "@/lib/api";
import type { Animal, Video } from "@/lib/types";

type VideoUploadFormProps = {
  onUploaded?: (video: Video) => void;
};

const ACCEPT = ".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm";
const MAX_BYTES = 100 * 1024 * 1024;

export function VideoUploadForm({ onUploaded }: VideoUploadFormProps) {
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [animalsError, setAnimalsError] = useState<string | null>(null);
  const [animalId, setAnimalId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const list = await getAnimals();
        if (cancelled) return;
        setAnimals(list);
        if (list.length > 0) {
          setAnimalId(String(list[0].id));
        }
      } catch (err) {
        if (!cancelled) {
          setAnimalsError(
            err instanceof Error ? err.message : "Could not load animals.",
          );
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(null);
    setError(null);

    if (!animalId) {
      setError("Select an animal before uploading.");
      return;
    }
    if (!file) {
      setError("Choose an MP4, MOV, or WebM file.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("File is larger than the 100 MB limit.");
      return;
    }

    setLoading(true);
    try {
      const video = await uploadVideo(Number(animalId), file);
      setSuccess(
        `Uploaded “${video.original_filename ?? video.filename}” for ${
          video.animal_name ?? `animal #${video.animal_id}`
        }.`,
      );
      setFile(null);
      onUploaded?.(video);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="rounded-2xl border border-border bg-surface p-5 md:p-6"
    >
      <h2 className="font-display text-xl text-sage-900">Upload video</h2>
      <p className="mt-1 text-sm leading-6 text-muted">
        Sends <code className="text-sage-700">multipart/form-data</code> to{" "}
        <code className="text-sage-700">POST /videos/upload</code>. Files stay
        private on the server (not committed to Git).
      </p>

      {animalsError ? (
        <p className="mt-4 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">
          {animalsError}
        </p>
      ) : null}

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium text-ink">Animal</span>
          <select
            className="mt-1.5 w-full rounded-xl border border-border bg-cream px-3 py-2.5 text-ink outline-none focus:border-sage-500"
            value={animalId}
            onChange={(e) => setAnimalId(e.target.value)}
            disabled={loading || animals.length === 0}
            required
          >
            {animals.length === 0 ? (
              <option value="">No animals available</option>
            ) : (
              animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name} ({animal.species})
                </option>
              ))
            )}
          </select>
        </label>

        <label className="block text-sm">
          <span className="font-medium text-ink">Video file</span>
          <input
            type="file"
            accept={ACCEPT}
            className="mt-1.5 block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-sage-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sage-900"
            disabled={loading}
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setSuccess(null);
              setError(null);
            }}
          />
          <span className="mt-1 block text-xs text-muted">
            MP4, MOV, or WebM · max 100 MB
            {file ? ` · selected ${(file.size / (1024 * 1024)).toFixed(1)} MB` : ""}
          </span>
        </label>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={loading || animals.length === 0}
          className="rounded-xl bg-sage-700 px-4 py-2.5 text-sm font-medium text-cream transition hover:bg-sage-900 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Uploading…" : "Upload video"}
        </button>
        {loading ? (
          <span className="text-sm text-muted" role="status">
            Saving file and metadata…
          </span>
        ) : null}
      </div>

      {success ? (
        <p
          className="mt-4 rounded-xl bg-sage-50 px-3 py-2 text-sm text-sage-900"
          role="status"
        >
          {success}
        </p>
      ) : null}
      {error ? (
        <p
          className="mt-4 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </form>
  );
}
