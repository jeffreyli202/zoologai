from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    animal_name: Optional[str] = None
    filename: str
    original_filename: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    uploaded_at: datetime
    analysis_progress: int = 0
    analysis_message: Optional[str] = None
    analysis_error: Optional[str] = None
    analysis_frames_total: int = 0
    analysis_frames_done: int = 0
    analysis_ai_calls: int = 0
    analysis_started_at: Optional[datetime] = None
    analysis_finished_at: Optional[datetime] = None


class VideoUploadResponse(VideoRead):
    """Returned after a successful multipart upload."""

    detail: str = Field(default="Video uploaded successfully.")


class VideoAnalysisStatus(BaseModel):
    """Progress payload for POST /videos/{id}/analyze and GET .../analysis."""

    video_id: int
    status: str
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    frames_total: int = 0
    frames_done: int = 0
    ai_calls: int = 0
    max_ai_calls: int = 12
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    detail: str = ""
