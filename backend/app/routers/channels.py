import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.channel import PinnedChannel
from app.models.user import User
from app.schemas.channel import ChannelInfo, PinnedChannelResponse, PinRequest
from app.services import youtube

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/subscriptions", response_model=list[ChannelInfo])
async def get_subscriptions(current_user: User = Depends(get_current_user)):
    """Fetches the user's YouTube subscriptions (from YouTube API)."""
    try:
        subs = await youtube.get_subscriptions(current_user)
        return [ChannelInfo(**s) for s in subs]
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions for user {current_user.id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch subscriptions from YouTube")


@router.get("/pinned", response_model=list[PinnedChannelResponse])
async def get_pinned(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the user's pinned channels."""
    result = await db.execute(
        select(PinnedChannel)
        .where(PinnedChannel.user_id == current_user.id)
        .order_by(PinnedChannel.pinned_at)
    )
    channels = result.scalars().all()
    return [
        PinnedChannelResponse(
            id=str(ch.id),
            channel_id=ch.channel_id,
            title=ch.title,
            thumbnail=ch.thumbnail,
        )
        for ch in channels
    ]


@router.post("/pin/{channel_id}", response_model=PinnedChannelResponse)
async def pin_channel(
    channel_id: str,
    body: PinRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pin a channel for the current user."""
    # Check if already pinned
    result = await db.execute(
        select(PinnedChannel).where(
            PinnedChannel.user_id == current_user.id,
            PinnedChannel.channel_id == channel_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return PinnedChannelResponse(
            id=str(existing.id),
            channel_id=existing.channel_id,
            title=existing.title,
            thumbnail=existing.thumbnail,
        )

    channel = PinnedChannel(
        user_id=current_user.id,
        channel_id=channel_id,
        title=body.title if body else None,
        thumbnail=body.thumbnail if body else None,
    )
    db.add(channel)
    await db.flush()

    return PinnedChannelResponse(
        id=str(channel.id),
        channel_id=channel.channel_id,
        title=channel.title,
        thumbnail=channel.thumbnail,
    )


@router.delete("/unpin/{channel_id}", status_code=204)
async def unpin_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unpin a channel for the current user."""
    await db.execute(
        delete(PinnedChannel).where(
            PinnedChannel.user_id == current_user.id,
            PinnedChannel.channel_id == channel_id,
        )
    )
