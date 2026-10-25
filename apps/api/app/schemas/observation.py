from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    animal_name: Optional[str] = None
    video_id: Optional[int] = None
    frame_id: Optional[int] = None
    camera_source_id: Optional[int] = None
    camera_capture_id: Optional[int] = None
    observed_at: datetime
    video_timestamp_seconds: float
    behavior: str
    description: Optional[str] = None
    visible_evidence: Optional[str] = None
    confidence: Optional[float] = None


class AnalyzeFrameResponse(BaseModel):
    reused: bool = Field(
        description="True when this frame was already analyzed and the model was not called again."
    )
    detail: str
    observation: ObservationRead
