from datetime import datetime
from pydantic import BaseModel


class VideoInfo(BaseModel):
    youtube_id: str
    channel_id: str
    title: str
    thumbnail: str | None = None
    published_at: datetime | None = None
    channel_title: str | None = None


class VideoWithUserState(BaseModel):
    youtube_id: str
    channel_id: str
    title: str
    thumbnail: str | None
    published_at: datetime | None
    channel_title: str | None
    # User-specific state
    is_read: bool = False
    is_favorite: bool = False
    note: str = ""
    processing_status: str = "pending"
    summary: str | None = None
    translated_title: str | None = None
    error_message: str | None = None


class VideoFeedResponse(BaseModel):
    videos: list[VideoWithUserState]
    total: int
    page: int
    per_page: int
    has_more: bool


class MetadataUpdate(BaseModel):
    is_read: bool | None = None
    is_favorite: bool | None = None
    note: str | None = None


class ProcessResponse(BaseModel):
    status: str
    youtube_id: str


class SyncResponse(BaseModel):
    status: str
    new_videos: int = 0
    failed_channels: int = 0
