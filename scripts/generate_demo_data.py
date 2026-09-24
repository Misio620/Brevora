"""Generates the frontend demo dataset from real YouTube videos and real Gemini notes.

Usage (from the repo root, after `node scripts/backend.mjs install`):
    backend/venv/bin/python scripts/generate_demo_data.py [--force] [VIDEO_ID ...]

Needs GOOGLE_API_KEY (Gemini) and YOUTUBE_API_KEY (YouTube Data API v3).
Metadata comes from the Data API, never from youtube.com pages: YouTube answers
cloud IPs with a "confirm you're not a bot" page. Notes and Chinese titles come
from app.services.ai, the same code the product uses.

Videos already in the output file are skipped unless --force is given, so a run
that hits the Gemini free-tier limit (~8 hours of YouTube video per day) can be
resumed the next day without paying for finished videos again.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.services import ai  # noqa: E402

OUTPUT = REPO_ROOT / "frontend" / "src" / "demo" / "demo-data.json"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

# Three channels, two videos each
DEMO_VIDEOS = [
    "LMT-bknLmNo", "QBmgF1kJSK4",  # How I AI
    "MGxcosNuC8k", "32u5T6lO8qk",  # The Diary Of A CEO
    "8xgnm6SynH4", "8BtHk-oNlN0",  # Starter Story
]


def parse_duration(iso: str) -> int:
    """Converts an ISO 8601 duration such as PT1H2M3S to seconds."""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


def best_thumbnail(thumbnails: dict) -> str | None:
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbnails:
            return thumbnails[size]["url"]
    return None


def fetch_metadata(api_key: str, video_ids: list[str]) -> tuple[list[dict], list[dict]]:
    """Returns (videos, channels) metadata from the YouTube Data API."""
    with httpx.Client(timeout=30) as client:
        res = client.get(
            f"{YOUTUBE_API}/videos",
            params={"part": "snippet,contentDetails", "id": ",".join(video_ids), "key": api_key},
        )
        res.raise_for_status()
        items = {item["id"]: item for item in res.json()["items"]}

        missing = [vid for vid in video_ids if vid not in items]
        if missing:
            sys.exit(f"Videos not found or not public: {', '.join(missing)}")

        videos = []
        for vid in video_ids:
            snippet = items[vid]["snippet"]
            videos.append({
                "youtube_id": vid,
                "channel_id": snippet["channelId"],
                "channel_title": snippet["channelTitle"],
                "title": snippet["title"],
                "thumbnail": best_thumbnail(snippet["thumbnails"]),
                "published_at": snippet["publishedAt"],
                "duration_seconds": parse_duration(items[vid]["contentDetails"]["duration"]),
            })

        channel_ids = list(dict.fromkeys(v["channel_id"] for v in videos))
        res = client.get(
            f"{YOUTUBE_API}/channels",
            params={"part": "snippet", "id": ",".join(channel_ids), "key": api_key},
        )
        res.raise_for_status()
        by_id = {item["id"]: item["snippet"] for item in res.json()["items"]}
        channels = [
            {"id": cid, "title": by_id[cid]["title"], "thumbnail": best_thumbnail(by_id[cid]["thumbnails"])}
            for cid in channel_ids
        ]

    return videos, channels


def load_existing() -> dict[str, dict]:
    if not OUTPUT.exists():
        return {}
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    return {v["youtube_id"]: v for v in data.get("videos", [])}


def write_output(videos: list[dict], channels: list[dict]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channels": channels,
        "videos": videos,
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video_ids", nargs="*", default=DEMO_VIDEOS)
    parser.add_argument("--force", action="store_true", help="regenerate notes that already exist")
    args = parser.parse_args()

    youtube_key = os.environ.get("YOUTUBE_API_KEY")
    if not youtube_key:
        sys.exit("YOUTUBE_API_KEY is not set")
    if not get_settings().GOOGLE_API_KEY:
        sys.exit("GOOGLE_API_KEY is not set")

    videos, channels = fetch_metadata(youtube_key, args.video_ids)
    existing = load_existing()
    total_minutes = sum(v["duration_seconds"] for v in videos) / 60
    print(f"{len(videos)} videos, {total_minutes:.0f} min in total")

    failures = 0
    for i, video in enumerate(videos):
        label = f"[{i + 1}/{len(videos)}] {video['youtube_id']} ({video['duration_seconds'] // 60} min)"
        previous = existing.get(video["youtube_id"])
        if previous and previous.get("summary") and not args.force:
            print(f"{label} skipped, already generated")
            video.update({k: previous[k] for k in ("summary", "translated_title", "model", "generated_at")})
            continue

        print(f"{label} generating...", flush=True)
        started = time.monotonic()
        try:
            video["summary"] = await ai.generate_summary(video["youtube_id"])
            # Records the model that actually answered, which may be the fallback
            video["model"] = ai.last_model_used
            video["translated_title"] = await ai.translate_title(video["title"])
        except Exception as e:
            failures += 1
            print(f"{label} failed: {e}")
            if previous:
                video.update({k: previous.get(k) for k in ("summary", "translated_title", "model", "generated_at")})
            continue
        video["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"{label} done in {time.monotonic() - started:.0f}s with {video['model']}")
        # Save after every video so an interrupted run keeps its progress
        write_output(videos, channels)

    write_output(videos, channels)
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    if failures:
        sys.exit(f"{failures} video(s) failed; rerun the script to retry only those")


if __name__ == "__main__":
    asyncio.run(main())
