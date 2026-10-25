from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    analytics,
    animals,
    cameras,
    frames,
    health,
    journals,
    observations,
    videos,
)
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # In-process monitor loop for local development (not an external queue).
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title="ZooLog AI API",
    description="Backend for ZooLog AI animal observation journals.",
    version="0.9.0",
    lifespan=lifespan,
)

_settings = get_settings()
# Local Next.js, Vercel production/custom domains (CORS_ORIGINS), and optional
# preview regex (CORS_ORIGIN_REGEX, default *.vercel.app).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list(),
    allow_origin_regex=_settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(animals.router)
app.include_router(videos.router)
app.include_router(frames.router)
app.include_router(observations.router)
app.include_router(journals.router)
app.include_router(analytics.router)
app.include_router(cameras.router)
