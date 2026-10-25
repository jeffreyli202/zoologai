"""ORM models — Python classes that map to database tables."""

from app.models.animal import Animal
from app.models.camera_capture import CameraCapture
from app.models.camera_source import CameraSource
from app.models.daily_journal import DailyJournal
from app.models.frame import Frame
from app.models.monitoring_log import MonitoringLog
from app.models.observation import Observation
from app.models.video import Video

__all__ = [
    "Animal",
    "Video",
    "Observation",
    "DailyJournal",
    "Frame",
    "CameraSource",
    "CameraCapture",
    "MonitoringLog",
]
