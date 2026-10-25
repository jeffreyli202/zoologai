from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SourceType = Literal["snapshot_url", "live_stream", "local_folder"]


class CameraSourceCreate(BaseModel):
    # Optional legacy field — monitoring discovers animals from vision instead.
    animal_id: Optional[int] = Field(default=None, ge=1)
    name: str = Field(..., min_length=1, max_length=120)
    source_type: SourceType
    snapshot_url: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Direct image or live media URL (snapshot / HLS / MJPEG / RTSP).",
    )
    local_folder_path: Optional[str] = Field(default=None, max_length=500)
    # Must be true — confirms the operator has permission to poll this source.
    access_authorized: bool = False
    interval_minutes: int = Field(default=15, ge=1, le=24 * 60)
    observation_window_hours: int = Field(default=24, ge=1, le=48)

    @field_validator("name", "snapshot_url", "local_folder_path")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_source_fields(self) -> "CameraSourceCreate":
        if not self.access_authorized:
            raise ValueError(
                "access_authorized must be true. Only configure sources you are "
                "explicitly permitted to poll (no scraping or bypassing protections)."
            )
        if self.source_type in {"snapshot_url", "live_stream"}:
            if not self.snapshot_url:
                raise ValueError(
                    "snapshot_url is required for snapshot_url / live_stream sources."
                )
            url = self.snapshot_url
            if self.source_type == "live_stream":
                if not (
                    url.startswith("http://")
                    or url.startswith("https://")
                    or url.startswith("rtsp://")
                    or url.startswith("rtsps://")
                ):
                    raise ValueError(
                        "live_stream URL must be http(s) or rtsp(s). Use a direct "
                        "media endpoint, or an authorized YouTube / Explore.org "
                        "live page (resolved when access_authorized is true)."
                    )
            else:
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise ValueError("snapshot_url must be an http(s) URL.")
        if self.source_type == "local_folder" and not self.local_folder_path:
            raise ValueError(
                "local_folder_path is required for source_type=local_folder."
            )
        return self


class CameraSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    snapshot_url: Optional[str] = Field(default=None, max_length=1000)
    local_folder_path: Optional[str] = Field(default=None, max_length=500)
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=24 * 60)
    observation_window_hours: Optional[int] = Field(default=None, ge=1, le=48)
    access_authorized: Optional[bool] = None


class CameraSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: Optional[int] = None
    animal_name: Optional[str] = None
    name: str
    source_type: str
    snapshot_url: Optional[str] = None
    local_folder_path: Optional[str] = None
    access_authorized: bool
    interval_minutes: int
    observation_window_hours: int
    status: str
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_image_hash: Optional[str] = None
    local_folder_index: int
    last_journal_date: Optional[date] = None
    last_journal_hour_at: Optional[datetime] = None
    capture_count: int
    skip_count: int
    error_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class MonitoringLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_source_id: int
    level: str
    event: str
    message: str
    detail: Optional[str] = None
    created_at: datetime


class CameraMonitorStatus(BaseModel):
    camera_source_id: int
    status: str
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    capture_count: int
    skip_count: int
    error_count: int
    scheduler_running: bool
    detail: str
    recent_logs: list[MonitoringLogRead] = Field(default_factory=list)


class CameraMonitorActionResponse(BaseModel):
    camera: CameraSourceRead
    detail: str


class CameraProbeRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000)
    prefer_stream: bool = Field(
        default=True,
        description="Try OpenCV live frame grab (HLS/MJPEG/RTSP) before plain image GET.",
    )
    access_authorized: bool = False

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_authorization(self) -> "CameraProbeRequest":
        if not self.access_authorized:
            raise ValueError(
                "access_authorized must be true before probing a live URL."
            )
        return self


class CameraProbeResponse(BaseModel):
    ok: bool
    byte_size: int = 0
    extension: str = ""
    width: int = 0
    height: int = 0
    detail: str


class FrameExtractRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000)
    count: int = Field(default=4, ge=1, le=24)
    interval_seconds: float = Field(default=5.0, ge=0, le=300)
    label: Optional[str] = Field(default=None, max_length=80)
    access_authorized: bool = False

    @field_validator("url", "label")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_authorization(self) -> "FrameExtractRequest":
        if not self.access_authorized:
            raise ValueError(
                "access_authorized must be true before extracting frames."
            )
        if not self.url:
            raise ValueError("url is required.")
        return self


class ExtractedFrameRead(BaseModel):
    index: int
    filename: str
    byte_size: int
    image_url: str


class FrameExtractResponse(BaseModel):
    job_id: str
    job_dir: str
    source_url: str
    resolved_media: bool
    frame_count: int
    interval_seconds: float
    frames: list[ExtractedFrameRead]
    detail: str
