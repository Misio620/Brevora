"""YouTube API service — fetches subscriptions and channel videos.

Refactored from the original backend/services/youtube.py to accept
credentials as a parameter (user-scoped) instead of using a global auth module.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import get_settings
from app.services.encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)
settings = get_settings()

YOUTUBE_TOKEN_URI = "https://oauth2.googleapis.com/token"

# A chapter line in a video description: "00:00 Intro", "(1:02:03) Title", "0:00 - Title"
_CHAPTER_LINE = re.compile(r"^\s*[(\[]?((?:\d{1,2}:)?\d{1,2}:\d{2})[)\]]?\s*[-–—:|]?\s*(\S.*)$")


def parse_chapters(description: str | None) -> list[tuple[int, str]]:
    """Extracts creator chapters as (start_seconds, title) from a video description.

    Follows YouTube's own rules for chapters: the first starts at 0:00, there are
    at least three, and they are in ascending order. Returns [] otherwise.
    """
    chapters = []
    for line in (description or "").splitlines():
        match = _CHAPTER_LINE.match(line)
        if match:
            seconds = 0
            for part in match.group(1).split(":"):
                seconds = seconds * 60 + int(part)
            chapters.append((seconds, match.group(2).strip()))

    starts = [start for start, _ in chapters]
    if len(chapters) < 3 or starts[0] != 0 or starts != sorted(set(starts)):
        return []
    return chapters


def _build_credentials(user) -> Credentials:
    """Build Google OAuth Credentials from a User model. Makes no network call."""
    access_token = decrypt_token(user.access_token) if user.access_token else None
    refresh_token = decrypt_token(user.refresh_token) if user.refresh_token else None
    # google-auth compares expiry as naive UTC; without it, an expired token is never refreshed up front
    expiry = user.token_expiry.astimezone(timezone.utc).replace(tzinfo=None) if user.token_expiry else None

    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=YOUTUBE_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        expiry=expiry,
    )


def _refresh_if_expired(creds: Credentials) -> bool:
    """Refreshes an expired access token. Blocking. Returns True if it refreshed."""
    if creds.refresh_token and (not creds.token or creds.expired):
        creds.refresh(Request())
        return True
    return False


def _save_credentials(user, creds: Credentials) -> None:
    """Writes refreshed tokens back to the user; the caller's session commits them."""
    user.access_token = encrypt_token(creds.token)
    if creds.refresh_token:
        user.refresh_token = encrypt_token(creds.refresh_token)
    user.token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None


async def ensure_fresh_credentials(user) -> Credentials:
    """Returns usable credentials, refreshing and saving the access token if it expired.

    Saving matters: an unsaved token is refreshed again on every request after it
    expires, which adds a round trip to Google each time.
    """
    creds = _build_credentials(user)
    if await asyncio.to_thread(_refresh_if_expired, creds):
        _save_credentials(user, creds)
        logger.info(f"Refreshed Google access token for user {user.id}")
    return creds


async def _call(user, fetch, *args):
    """Runs a blocking YouTube call with fresh credentials and saves any token it refreshed."""
    creds = await ensure_fresh_credentials(user)
    token_before = creds.token
    result = await asyncio.to_thread(fetch, creds, *args)
    # The client library also refreshes on its own when Google rejects a token early
    if creds.token != token_before:
        _save_credentials(user, creds)
    return result


def _get_youtube_service(creds: Credentials):
    # The discovery file cache needs oauth2client < 4.0 and only logs a warning on every build
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _fetch_subscriptions(creds: Credentials) -> list[dict]:
    """Fetches ALL subscriptions for a user (with pagination). Blocking."""
    youtube = _get_youtube_service(creds)
    subscriptions = []
    next_page_token = None

    while True:
        request = youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50,
            order="alphabetical",
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            subscriptions.append({
                "id": item["snippet"]["resourceId"]["channelId"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return subscriptions


def _fetch_channel_videos(creds: Credentials, channel_id: str, max_results: int = 20) -> list[dict]:
    """Fetches recent videos from a specific channel. Blocking."""
    youtube = _get_youtube_service(creds)
    videos = []

    # Get the Uploads playlist ID
    channel_response = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()

    if not channel_response.get("items"):
        return []

    uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch videos from uploads playlist
    playlist_response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=max_results,
    ).execute()

    for item in playlist_response.get("items", []):
        snippet = item["snippet"]
        published_str = snippet.get("publishedAt")
        published_at = None
        if published_str:
            published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        videos.append({
            "youtube_id": snippet["resourceId"]["videoId"],
            "channel_id": channel_id,
            "title": snippet["title"],
            "thumbnail": snippet["thumbnails"].get("medium", {}).get("url"),
            "published_at": published_at,
            "channel_title": snippet.get("channelTitle"),
        })

    return videos


def _fetch_video_description(creds: Credentials, youtube_id: str) -> str | None:
    """Fetches a video's description. Blocking."""
    youtube = _get_youtube_service(creds)
    response = youtube.videos().list(part="snippet", id=youtube_id).execute()
    items = response.get("items", [])
    return items[0]["snippet"].get("description") if items else None


# Async wrappers
async def get_subscriptions(user) -> list[dict]:
    return await _call(user, _fetch_subscriptions)


async def get_channel_videos(user, channel_id: str, max_results: int = 20) -> list[dict]:
    return await _call(user, _fetch_channel_videos, channel_id, max_results)


async def get_video_chapters(user, youtube_id: str) -> list[tuple[int, str]]:
    description = await _call(user, _fetch_video_description, youtube_id)
    return parse_chapters(description)
