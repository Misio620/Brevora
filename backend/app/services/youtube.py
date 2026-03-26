"""YouTube API service — fetches subscriptions and channel videos.

Refactored from the original backend/services/youtube.py to accept
credentials as a parameter (user-scoped) instead of using a global auth module.
"""
import asyncio
import logging
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import get_settings
from app.services.encryption import decrypt_token

logger = logging.getLogger(__name__)
settings = get_settings()

YOUTUBE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_credentials(user) -> Credentials:
    """Build Google OAuth Credentials from a User model."""
    access_token = decrypt_token(user.access_token) if user.access_token else None
    refresh_token = decrypt_token(user.refresh_token) if user.refresh_token else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=YOUTUBE_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def _get_youtube_service(user):
    creds = _build_credentials(user)
    return build("youtube", "v3", credentials=creds)


def _fetch_subscriptions(user) -> list[dict]:
    """Fetches ALL subscriptions for a user (with pagination). Blocking."""
    youtube = _get_youtube_service(user)
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


def _fetch_channel_videos(user, channel_id: str, max_results: int = 20) -> list[dict]:
    """Fetches recent videos from a specific channel. Blocking."""
    youtube = _get_youtube_service(user)
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


# Async wrappers
async def get_subscriptions(user) -> list[dict]:
    return await asyncio.to_thread(_fetch_subscriptions, user)


async def get_channel_videos(user, channel_id: str, max_results: int = 20) -> list[dict]:
    return await asyncio.to_thread(_fetch_channel_videos, user, channel_id, max_results)
