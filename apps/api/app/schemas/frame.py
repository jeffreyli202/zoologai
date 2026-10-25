from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FrameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    filename: str
    timestamp_seconds: float
    frame_index: int
    created_at: datetime
    # Absolute URL path on this API (frontend prefixes with API_BASE_URL).
    image_url: str


class ExtractFramesResponse(BaseModel):
    video_id: int
    reused: bool = Field(
        description="True when frames already existed and nothing new was written."
    )
    detail: str
    frames: list[FrameRead]
