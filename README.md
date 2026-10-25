# ZooLog AI

Full-stack app for an AI agent that observes animal footage, recognizes visible behaviors, and writes daily observation journals.

Built **incrementally**. Current steps:

1. Next.js frontend + FastAPI backend health check
2. Persistent SQLite database, Alembic migrations, animal CRUD
3. Nature-inspired dashboard UI (sidebar, animal profiles, mock stats/observations/journals)
4. Private local video uploads (`POST /videos/upload`) + dashboard list
5. OpenCV frame extraction (every 15s, max 12) + frame gallery
6. Gemini vision analysis of one frame → Observation
7. Full **Analyze Video** workflow (background job: extract → analyze → save)
8. AI hourly journals from saved observations (facts vs interpretations + traceability)
9. Behavioral analytics (sample counts, coverage, day compare, weekly summary)
10. Authorized camera monitoring (scheduler + local sample folder / snapshot URL)

## Project structure

```
zoologai/
├── apps/
│   ├── web/                 # Next.js (TypeScript, Tailwind, App Router)
│   └── api/                 # FastAPI + SQLAlchemy + Alembic
│       ├── app/
│       │   ├── models/      # ORM table classes
│       │   ├── schemas/     # Request/response validation
│       │   ├── routers/     # HTTP endpoints
│       │   ├── config.py    # Environment settings
│       │   └── database.py  # Engine + sessions
│       ├── alembic/         # Migration scripts
│       ├── scripts/seed.py  # Example animal seeder
│       ├── scripts/seed_zoo_inat.py  # LPZ iNaturalist → animals/obs/journals
│       ├── uploads/videos/  # Private uploaded files (gitignored)
│       ├── uploads/frames/  # Extracted JPEGs per video (gitignored)
│       └── zoologai.db      # Local SQLite file (gitignored)
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Windows PowerShell

## Setup

### 1. Backend (FastAPI + database)

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\..\.env.example .env
# Keep DATABASE_URL=sqlite:///./zoologai.db for local SQLite

# Create tables from migrations
alembic upgrade head

# Insert one example animal
python -m scripts.seed

# Optional: import public Lincoln Park Zoo-area iNaturalist sightings
# into animals + observations + hourly journals (attribution: iNaturalist)
python -m scripts.seed_zoo_inat
```

If PowerShell blocks script activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Frontend (Next.js)

```powershell
cd apps\web
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
```

## Run both servers

**Terminal 1 — API (port 8000):**

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port 8000 is stuck on Windows, use `8001` instead and set `NEXT_PUBLIC_API_URL=http://localhost:8001` in `apps/web/.env.local`.

**Terminal 2 — Web (port 3000):**

```powershell
cd apps\web
npm run dev
```

Useful URLs:

- Frontend: http://localhost:3000
- API health: http://127.0.0.1:8000/health (or `:8001`)
- Interactive API docs: http://127.0.0.1:8000/docs (or `:8001`)


## Animal CRUD (try in `/docs`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/animals` | Create |
| `GET` | `/animals` | List |
| `GET` | `/animals/{id}` | Get one |
| `PATCH` | `/animals/{id}` | Update |
| `DELETE` | `/animals/{id}` | Delete |

## Verify data survives a server restart

1. Open http://127.0.0.1:8000/docs
2. Use `POST /animals` (or run `python -m scripts.seed`) to create an animal
3. Call `GET /animals` and note the returned `id` / `name`
4. Stop the API server (`Ctrl+C`)
5. Start it again with the same `uvicorn` command
6. Call `GET /animals` again — the same rows should still be there

That works because SQLite stores data in `apps/api/zoologai.db` on disk, not only in memory.

## Beginner concepts

### ORM models

An **ORM model** is a Python class that represents a database table.  
Example: the `Animal` class maps to the `animals` table. Each instance is one row.

### Database sessions

A **session** is a short-lived conversation with the database for one request:

1. Open a session
2. Read or change objects
3. `commit()` to save, or close without committing to discard
4. Close the session

`get_db()` in FastAPI gives each request its own session.

### Foreign keys

A **foreign key** links one table to another.  
Example: `videos.animal_id` must match an existing `animals.id`, so every video belongs to one animal.

### Migrations (Alembic)

**Migrations** are versioned scripts that change the database schema (create tables, add columns, etc.).

- Edit models in Python
- `alembic revision --autogenerate -m "message"` creates a migration
- `alembic upgrade head` applies migrations

This keeps everyone’s database structure in sync without hand-editing SQL.

## Major API files

| File | Role |
|------|------|
| `app/config.py` | Loads `DATABASE_URL` from `.env` |
| `app/database.py` | SQLAlchemy engine, `SessionLocal`, `get_db` |
| `app/models/*.py` | Animal, Video, Observation, DailyJournal tables |
| `app/schemas/animal.py` | Pydantic validation for animal create/update/read |
| `app/routers/animals.py` | Animal CRUD endpoints |
| `alembic/` | Migration environment + version scripts |
| `scripts/seed.py` | Inserts one example animal if missing |

## Dashboard UI (step 3)

The Next.js app includes a sidebar (Dashboard, Animals, Videos, Observations, Journal).

- **Animals** and the homepage animal cards load real data from `GET /animals`.
- Stats, recent observations, and journal preview use **clearly labeled mock data** until those API endpoints exist.

## Video uploads (step 4)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/videos/upload` | Multipart upload (animal_id + file) |
| `GET` | `/videos` | List video metadata |

Rules:

- Allowed types: **MP4, MOV, WebM**
- Max size: **100 MB**
- Stored under `apps/api/uploads/videos/` with a **UUID filename** (never trust the client path)
- Metadata saved in SQLite; files are **not** served publicly and are **gitignored**

### Test with a short video you have permission to use

1. Start API + web servers (commands above).
2. Ensure an animal exists (`python -m scripts.seed` or create one in `/docs`).
3. Open http://localhost:3000/videos
4. Pick the animal, choose an MP4/MOV/WebM file you own or have rights to use, click **Upload video**.
5. Confirm success message, then check:
   - The list on `/videos` and the dashboard “Recent uploads”
   - A new file under `apps/api/uploads/videos/`
   - A row via `GET /videos` in http://127.0.0.1:8000/docs

Or upload from `/docs`: open `POST /videos/upload`, enter `animal_id`, choose a file, Execute.

### multipart/form-data (quick idea)

The browser does not send the file as plain JSON. It sends **multipart/form-data**: one part for `animal_id`, one part for the binary `file`. FastAPI’s `UploadFile` reads that file part safely in chunks.

## Frame extraction (step 5)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/videos/{id}/extract-frames` | Sample frames with OpenCV (idempotent) |
| `GET` | `/videos/{id}/frames` | List frame metadata + image URLs |
| `GET` | `/videos/{id}/frames/{frame_id}/image` | Serve one JPEG |

Rules:

- One frame every **15 seconds**
- Max **12** frames per video
- Frames resized (longest edge 1280px) under `uploads/frames/video_{id}/`
- Each row stores `timestamp_seconds` (position in the source video)
- Calling extract again **reuses** existing DB rows (no duplicates)

### FPS and why we sample

**FPS (frames per second)** is how many still images make up one second of video. A 30 FPS clip has 30 pictures per second.

Analyzing every frame of a long video is expensive. Sampling sparsely (e.g. every 15 seconds, capped at 12) keeps a useful timeline for later AI behavior detection without processing thousands of nearly identical images.

### Try it in the UI

1. Upload a real short MP4/MOV/WebM on http://localhost:3000/videos
2. Click **Extract frames**
3. Confirm thumbnails + timestamps appear
4. Click extract again — response should say frames already existed (`reused: true`)

## Gemini vision (step 6)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/frames/{id}/analyze` | Send one frame to Gemini; save Observation |
| `GET` | `/frames/{id}/observation` | Fetch saved observation for a frame |

Setup:

1. Put your key in `apps/api/.env` only (never `NEXT_PUBLIC_`):
   ```
   GEMINI_API_KEY=your-google-ai-studio-key
   GEMINI_MODEL=gemini-3.5-flash-lite
   MAX_AI_CALLS_PER_VIDEO_JOB=12
   ```
2. Restart the API
3. On `/videos`, click **Analyze** on a frame (or use **Analyze Video** below)

Rules baked into the prompt + schema:

- Labels: eating, resting, walking, swimming, climbing, playing, not_visible, unknown
- Never invent unseen behavior; prefer `not_visible` / `unknown` when unclear
- Confidence is a model estimate, not a calibrated probability
- One frame cannot prove duration
- Missing key → **503**; rate limits / API failures → **502**; we do **not** fake success

### How Gemini integration works

1. **Image input** — JPEG bytes are sent with `types.Part.from_bytes(..., mime_type="image/jpeg")`.
2. **Structured outputs** — `response_mime_type="application/json"` + `response_json_schema` from our Pydantic model.
3. **Validation** — `json.loads` + Pydantic (`BehaviorAnalysisResult` / `JournalDraft`) before DB writes.
4. **API key** — loaded as `GEMINI_API_KEY` on the backend only.

## Analyze Video workflow (step 7)

One button runs the full pipeline in a **local background thread** (no Redis/Celery yet):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/videos/{id}/analyze` | Queue job → **202 Accepted** immediately |
| `GET` | `/videos/{id}/analysis` | Poll progress / status / errors |

States: `pending` → `processing` → `completed` or `failed`.

Behavior:

1. Load the uploaded video
2. Extract frames if none exist yet
3. Analyze each frame with Gemini (skip frames that already have observations)
4. Save validated observations
5. Update progress fields on the `videos` row
6. Frontend polls every ~1.5s and shows a progress bar

Guards:

- **Duplicate protection** — while `pending`/`processing`, a second start returns **409**
- **Retry** — call again after `failed`, or pass `?force=true` after `completed`
- **AI call cap** — `MAX_AI_CALLS_PER_VIDEO_JOB` (default 12) limits Gemini calls per job

### Why longer jobs must not block HTTP

Frame extraction plus many vision API calls can take minutes. Holding the HTTP connection open that long:

- Ties up a server worker for the whole job
- Risks browser / proxy timeouts
- Prevents the UI from showing live progress

Instead the API accepts the job quickly (**202**), runs work in a background thread, and the client polls status.

### Try it

1. Upload a short MP4/MOV/WebM on http://localhost:3000/videos
2. Click **Analyze Video**
3. Watch status move through pending → processing → completed
4. Confirm frame thumbnails + observations appear
5. Click again while running → should get a conflict / stay disabled
6. After failure, use **Retry analysis**

## AI journals — hourly by default (step 8)

Journals are written from **persistent database memory**, not chat history.
The default bucket is **one UTC hour** (`daily_journals.hour` 0–23). Legacy
full-day summaries use `hour=-1`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/journals` | List journals (`animal_id`, `journal_date`, `hour` filters) |
| `GET` | `/journals/eligibility` | Count observations for animal/date/hour (empty-state UI) |
| `POST` | `/journals/generate` | Generate or regenerate (`force=true`); pass `hour` 0–23 |

### How persistent memory works

1. Frame / camera analysis saves **Observation** rows (behavior, evidence, confidence, timestamps).
2. Journal generation **reloads** those rows for the selected animal + UTC date + hour.
3. Gemini (text) receives only that payload and must produce overview, behaviors,
   notable events, **observed facts**, and **possible interpretations** separately.
4. Supporting **observation IDs** are validated against the DB list and stored on
   `daily_journals.source_observation_ids` for traceability.
5. If the hour has **zero** observations, the API returns **404** and the UI shows
   an empty state — no invented journal. Camera monitoring skips empty hours the same way.

Tone: engaging, scientifically cautious (no duration claims from one frame;
interpretations labeled as tentative).

### Try it

1. Ensure observations exist for a UTC hour (Analyze Video / camera capture).
2. Open http://localhost:3000/journal
3. Pick animal + date + hour → **Generate journal**
4. Confirm sections + supporting observation IDs
5. Pick an hour with no observations → empty state (generate disabled)
6. **Regenerate** overwrites the saved hourly entry from current observations

## Behavioral analytics (step 9)

Charts and summaries use **real Observation rows** only.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/analytics/behaviors` | Counts by behavior / day / hour, timeline, coverage |
| `GET` | `/analytics/compare-days` | Compare two UTC days for one animal |
| `POST` | `/analytics/weekly-summary` | AI weekly summary from recorded samples only |

### How aggregation works

- Each observation is one analyzed frame sample (`observed_at` in UTC).
- **By behavior / day / hour** = tallies of those samples — **not** continuous time.
- Never treat sample counts as a **percentage of an animal's entire day**.
- A day or hour with **zero samples means missing data**, not proven inactivity.
- **Coverage** reports frames in range, observations, missing frame analyses, and
  calendar slots without samples.

UI: http://localhost:3000/analytics (Recharts, animal + date filters).

## Authorized camera monitoring (step 10)

Poll **only** sources you are allowed to access automatically:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/cameras` | Create snapshot URL or local-folder source |
| `GET` | `/cameras` | List sources |
| `POST` | `/cameras/{id}/start` | Start monitoring |
| `POST` | `/cameras/{id}/stop` | Stop monitoring |
| `GET` | `/cameras/{id}/status` | Status + recent logs |

Supported sources:

- **live_stream** — direct HLS (`.m3u8`), MJPEG, RTSP, or similar media URL OpenCV can open
- **snapshot_url** — direct refreshing image URL (`.jpg` / `.png`) that permits automated polling
- **local_folder** — folder of sample JPEGs/PNGs for local testing (`uploads/camera_samples`)

`POST /cameras/probe` grabs one still to verify a URL before you start monitoring.

`POST /cameras/extract-frames` pulls N JPEGs from an authorized live URL (direct
HLS/RTSP/snapshot, or YouTube / Explore.org live pages resolved via yt-dlp when
`access_authorized=true`). Stills land in `uploads/extracted_frames/` and are
served at `/cameras/extracted/{job_dir}/{filename}`. CLI: `python -m scripts.extract_live_frames --authorized --url …`.

Not supported: scraping zoo websites, bypassing stream protections, or unauthorized streams.
Paste a **direct media endpoint**, not a zoo homepage.

### Scheduling, state, rate limits, backend stop

- **Scheduling** — a daemon thread wakes ~every 30s and runs due `CameraSource` rows (`next_run_at`).
- **Persistent state** — status, hashes, counters, and `monitoring_logs` live in SQLite; the thread does not.
- **Rate limits** — default interval **15 minutes** (configurable; floor via `MIN_MONITOR_INTERVAL_MINUTES`), HTTP timeout, max image bytes, duplicate SHA-256 skips.
- **When the API stops** — the scheduler dies. Sources left `running` resume on next startup; missed ticks are not backfilled.

Each tick: fetch image → skip if duplicate → vision analyze → if `animals_seen` is non-empty, create/match Animal rows and save Observations with the **real capture timestamp** → after each completed UTC hour, write an **hourly journal per animal that was actually sighted** (dark / not_visible hours are skipped; nothing invented). Cameras do **not** require picking an animal up front.

UI: http://localhost:3000/monitoring

## What's next (not in this step)

- Observation list API for the Observations page
- Replacing remaining mock dashboard stats
- External job queue for production
