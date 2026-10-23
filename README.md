# ZooLog AI

Full-stack app for an AI agent that observes animal footage, recognizes visible behaviors, and writes daily observation journals.

Built **incrementally**. Current steps:

1. Next.js frontend + FastAPI backend health check
2. Persistent SQLite database, Alembic migrations, animal CRUD
3. Nature-inspired dashboard UI (sidebar, animal profiles, mock stats/observations/journals)

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

**Terminal 2 — Web (port 3000):**

```powershell
cd apps\web
npm run dev
```

Useful URLs:

- Frontend: http://localhost:3000
- API health: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

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

The Next.js app includes a sidebar (Dashboard, Animals, Observations, Journal).

- **Animals** and the homepage animal cards load real data from `GET /animals`.
- Stats, recent observations, and journal preview use **clearly labeled mock data** until those API endpoints exist.

## What's next (not in this step)

- Video upload / processing
- AI behavior recognition
- Observation / journal API endpoints
- Replacing mock dashboard data with live API responses
