import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, async_session
from app.middleware.auth import get_current_user
from app.models.channel import PinnedChannel
from app.models.user import User
from app.models.video import Video, UserVideo
from app.schemas.video import (
    MetadataUpdate,
    ProcessResponse,
    SyncResponse,
    VideoFeedResponse,
    VideoWithUserState,
)
from app.services import ai, youtube

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])
settings = get_settings()

SYNC_CONCURRENCY = 5


def _video_to_response(video: Video, uv: UserVideo | None) -> VideoWithUserState:
    return VideoWithUserState(
        youtube_id=video.youtube_id,
        channel_id=video.channel_id,
        title=video.title,
        thumbnail=video.thumbnail,
        published_at=video.published_at,
        channel_title=video.channel_title,
        is_read=uv.is_read if uv else False,
        is_favorite=uv.is_favorite if uv else False,
        note=uv.note if uv else "",
        processing_status=uv.processing_status if uv else "pending",
        summary=uv.summary if uv else None,
        translated_title=uv.translated_title if uv else None,
        error_message=uv.error_message if uv else None,
    )


@router.get("/feed", response_model=VideoFeedResponse)
async def get_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    channel_id: str | None = None,
    status: str | None = None,
    favorites: bool = False,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns paginated video feed from user's pinned channels."""
    # Get pinned channel IDs
    pinned_result = await db.execute(
        select(PinnedChannel.channel_id).where(PinnedChannel.user_id == current_user.id)
    )
    pinned_channel_ids = [row[0] for row in pinned_result.all()]

    if not pinned_channel_ids:
        return VideoFeedResponse(videos=[], total=0, page=page, per_page=per_page, has_more=False)

    # Build query
    query = (
        select(Video, UserVideo)
        .outerjoin(
            UserVideo,
            and_(UserVideo.video_id == Video.id, UserVideo.user_id == current_user.id),
        )
        .where(Video.channel_id.in_(pinned_channel_ids if not channel_id else [channel_id]))
    )

    # Apply filters
    if channel_id and channel_id not in pinned_channel_ids:
        return VideoFeedResponse(videos=[], total=0, page=page, per_page=per_page, has_more=False)

    if status == "done":
        query = query.where(UserVideo.processing_status == "done")
    elif status == "pending":
        query = query.where(or_(UserVideo.processing_status.is_(None), UserVideo.processing_status != "done"))

    if favorites:
        query = query.where(UserVideo.is_favorite.is_(True))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Video.title.ilike(search_term),
                Video.channel_title.ilike(search_term),
                UserVideo.translated_title.ilike(search_term),
                UserVideo.summary.ilike(search_term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate and sort
    query = query.order_by(Video.published_at.desc().nulls_last())
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    videos = [_video_to_response(video, uv) for video, uv in rows]

    return VideoFeedResponse(
        videos=videos,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(offset + per_page) < total,
    )


@router.get("/{youtube_id}", response_model=VideoWithUserState)
async def get_video(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single video with user state."""
    result = await db.execute(
        select(Video, UserVideo)
        .outerjoin(
            UserVideo,
            and_(UserVideo.video_id == Video.id, UserVideo.user_id == current_user.id),
        )
        .where(Video.youtube_id == youtube_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")

    video, uv = row
    return _video_to_response(video, uv)


@router.patch("/{youtube_id}/metadata", response_model=VideoWithUserState)
async def update_metadata(
    youtube_id: str,
    updates: MetadataUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user-specific video metadata (read, favorite, note)."""
    # Find the video
    video_result = await db.execute(select(Video).where(Video.youtube_id == youtube_id))
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Find or create UserVideo
    uv_result = await db.execute(
        select(UserVideo).where(
            UserVideo.user_id == current_user.id,
            UserVideo.video_id == video.id,
        )
    )
    uv = uv_result.scalar_one_or_none()

    if not uv:
        uv = UserVideo(user_id=current_user.id, video_id=video.id)
        db.add(uv)

    if updates.is_read is not None:
        uv.is_read = updates.is_read
    if updates.is_favorite is not None:
        uv.is_favorite = updates.is_favorite
    if updates.note is not None:
        uv.note = updates.note

    uv.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return _video_to_response(video, uv)


@router.post("/{youtube_id}/process", response_model=ProcessResponse, status_code=202)
async def process_video(
    youtube_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async AI summary generation."""
    # Find the video
    video_result = await db.execute(select(Video).where(Video.youtube_id == youtube_id))
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Find or create UserVideo, mark as processing
    uv_result = await db.execute(
        select(UserVideo).where(
            UserVideo.user_id == current_user.id,
            UserVideo.video_id == video.id,
        )
    )
    uv = uv_result.scalar_one_or_none()

    if not uv:
        uv = UserVideo(user_id=current_user.id, video_id=video.id, processing_status="processing")
        db.add(uv)
    else:
        uv.processing_status = "processing"
        uv.error_message = None

    await db.commit()

    # Enqueue background task
    background_tasks.add_task(
        _run_ai_processing,
        user_id=str(current_user.id),
        video_id=str(video.id),
        youtube_id=youtube_id,
        title=video.title,
    )

    return ProcessResponse(status="processing", youtube_id=youtube_id)


async def _run_ai_processing(user_id: str, video_id: str, youtube_id: str, title: str):
    """Background task to generate AI summary."""
    async with async_session() as db:
        try:
            # Generate summary
            summary = await ai.generate_summary(youtube_id)

            # Translate title
            translated_title = await ai.translate_title(title)

            # Update DB
            result = await db.execute(
                select(UserVideo).where(
                    UserVideo.user_id == user_id,
                    UserVideo.video_id == video_id,
                )
            )
            uv = result.scalar_one_or_none()
            if uv:
                uv.processing_status = "done"
                uv.summary = summary
                uv.translated_title = translated_title
                uv.processed_at = datetime.now(timezone.utc)
                uv.updated_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"AI processing complete for {youtube_id}")

        except Exception as e:
            logger.error(f"AI processing failed for {youtube_id}: {e}")
            result = await db.execute(
                select(UserVideo).where(
                    UserVideo.user_id == user_id,
                    UserVideo.video_id == video_id,
                )
            )
            uv = result.scalar_one_or_none()
            if uv:
                uv.processing_status = "error"
                uv.error_message = str(e)
                uv.updated_at = datetime.now(timezone.utc)

            await db.commit()


@router.post("/sync", response_model=SyncResponse)
async def sync_videos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch latest videos from all pinned channels and add new ones to the user's feed."""
    result = await db.execute(
        select(PinnedChannel.channel_id).where(PinnedChannel.user_id == current_user.id)
    )
    channel_ids = [row[0] for row in result.all()]

    if not channel_ids:
        return SyncResponse(status="done", new_videos=0)

    semaphore = asyncio.Semaphore(SYNC_CONCURRENCY)

    async def fetch(channel_id: str) -> list[dict] | None:
        async with semaphore:
            try:
                return await youtube.get_channel_videos(current_user, channel_id)
            except Exception as e:
                logger.warning(f"Failed to fetch videos for channel {channel_id}: {e}")
                return None

    results = await asyncio.gather(*(fetch(ch) for ch in channel_ids))
    fetched = [videos for videos in results if videos is not None]

    if not fetched:
        raise HTTPException(status_code=502, detail="Failed to fetch videos from YouTube")

    new_count = await _add_videos_to_feed(db, current_user.id, [v for videos in fetched for v in videos])
    logger.info(f"Sync complete for user {current_user.id}: {new_count} new videos")

    return SyncResponse(
        status="done",
        new_videos=new_count,
        failed_channels=len(channel_ids) - len(fetched),
    )


async def _add_videos_to_feed(db: AsyncSession, user_id, videos: list[dict]) -> int:
    """Upsert videos into the shared cache and link any the user doesn't have yet. Returns the number linked."""
    incoming = {v["youtube_id"]: v for v in videos}
    if not incoming:
        return 0

    result = await db.execute(select(Video).where(Video.youtube_id.in_(incoming.keys())))
    by_youtube_id = {video.youtube_id: video for video in result.scalars().all()}

    for youtube_id, v in incoming.items():
        if youtube_id not in by_youtube_id:
            video = Video(
                youtube_id=youtube_id,
                channel_id=v["channel_id"],
                title=v["title"],
                thumbnail=v.get("thumbnail"),
                published_at=v.get("published_at"),
                channel_title=v.get("channel_title"),
            )
            db.add(video)
            by_youtube_id[youtube_id] = video
    await db.flush()

    video_ids = [video.id for video in by_youtube_id.values()]
    result = await db.execute(
        select(UserVideo.video_id).where(
            UserVideo.user_id == user_id,
            UserVideo.video_id.in_(video_ids),
        )
    )
    linked = {row[0] for row in result.all()}

    new_links = [UserVideo(user_id=user_id, video_id=vid) for vid in video_ids if vid not in linked]
    db.add_all(new_links)
    await db.flush()
    return len(new_links)


@router.get("/{youtube_id}/transcript")
async def get_transcript(
    youtube_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the transcript for a video."""
    transcript = await ai.get_transcript(youtube_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not available")
    return {"transcript": transcript}
