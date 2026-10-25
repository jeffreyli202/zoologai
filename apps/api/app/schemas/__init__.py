"""Pydantic schemas for request/response validation."""

from app.schemas.animal import AnimalCreate, AnimalRead, AnimalUpdate
from app.schemas.frame import ExtractFramesResponse, FrameRead
from app.schemas.journal import (
    DailyJournalRead,
    JournalEligibilityResponse,
    JournalGenerateRequest,
    JournalGenerateResponse,
)
from app.schemas.analytics import (
    BehaviorAnalyticsResponse,
    DayCompareResponse,
    WeeklySummaryRequest,
    WeeklySummaryResponse,
)
from app.schemas.observation import AnalyzeFrameResponse, ObservationRead
from app.schemas.video import VideoAnalysisStatus, VideoRead, VideoUploadResponse

__all__ = [
    "AnimalCreate",
    "AnimalRead",
    "AnimalUpdate",
    "VideoRead",
    "VideoUploadResponse",
    "VideoAnalysisStatus",
    "FrameRead",
    "ExtractFramesResponse",
    "ObservationRead",
    "AnalyzeFrameResponse",
    "DailyJournalRead",
    "JournalEligibilityResponse",
    "JournalGenerateRequest",
    "JournalGenerateResponse",
    "BehaviorAnalyticsResponse",
    "DayCompareResponse",
    "WeeklySummaryRequest",
    "WeeklySummaryResponse",
]
