"""Shared test setup.

Tests run against a real PostgreSQL database (TEST_DATABASE_URL, default
postgresql+asyncpg://postgres:postgres@localhost:5432/brevora_test) and never call
Google or Gemini: every external call is replaced by a fake below, so no API keys
or quota are needed.
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import Fernet

# Settings are read once at import time, so configure them before importing the app
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/brevora_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["GOOGLE_API_KEY"] = "test-gemini-key"

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import async_session, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.auth import create_access_token  # noqa: E402
from app.models.channel import PinnedChannel  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.video import UserVideo, Video  # noqa: E402
from app.services import ai  # noqa: E402
from app.services.encryption import encrypt_token  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_alembic(*args: str, database_url: str = TEST_DATABASE_URL) -> None:
    """Runs alembic in a subprocess so it reads the given database URL fresh."""
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": database_url},
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Builds the schema from the migrations, exactly as a real deployment would."""
    run_alembic("upgrade", "head")


@pytest.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, videos, user_videos, pinned_channels, login_codes CASCADE"))
    # Each test runs in its own event loop; pooled connections cannot cross loops
    await engine.dispose()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        yield c


async def make_user(email: str = "a@example.com", token_expiry: datetime | None = None, **fields) -> User:
    async with async_session() as db:
        user = User(
            google_id=f"google-{email}",
            email=email,
            access_token=encrypt_token("stored-access-token"),
            refresh_token=encrypt_token("stored-refresh-token"),
            token_expiry=token_expiry or datetime.now(timezone.utc) + timedelta(hours=1),
            **fields,
        )
        db.add(user)
        await db.commit()
        return user


def auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


async def make_videos(count: int, channel_id: str = "ch1", users: list[User] = ()) -> list[Video]:
    """Creates videos on one channel, pinned by and in the feed of each given user."""
    async with async_session() as db:
        videos = [
            Video(
                youtube_id=f"vid{i}",
                channel_id=channel_id,
                title=f"Title {i}",
                channel_title="Channel",
                published_at=datetime(2026, 9, i + 1, tzinfo=timezone.utc),
            )
            for i in range(count)
        ]
        db.add_all(videos)
        await db.flush()
        for user in users:
            db.add(PinnedChannel(user_id=user.id, channel_id=channel_id, title="Channel"))
            db.add_all([UserVideo(user_id=user.id, video_id=v.id) for v in videos])
        await db.commit()
        return videos


@pytest.fixture
def fake_ai(monkeypatch):
    """Replaces Gemini. Records every summary request; set .fail to an exception to fail."""

    class FakeAI:
        calls: list[str] = []
        fail: Exception | None = None
        delay: float = 0.0

        async def generate_summary(self, video_id, chapters=None):
            import asyncio

            self.calls.append(video_id)
            await asyncio.sleep(self.delay)
            if self.fail:
                raise self.fail
            return ai.Summary(text=f"## 一句話主題\nnote for {video_id}", model="fake-model", chapters_used=len(chapters or []))

        async def translate_title(self, title):
            return f"譯：{title}"

    fake = FakeAI()
    fake.calls = []
    monkeypatch.setattr(ai, "generate_summary", fake.generate_summary)
    monkeypatch.setattr(ai, "translate_title", fake.translate_title)
    return fake


@pytest.fixture
def fake_chapters(monkeypatch):
    from app.services import youtube

    async def chapters(user, youtube_id):
        return [(0, "Intro"), (60, "A"), (120, "B")]

    monkeypatch.setattr(youtube, "get_video_chapters", chapters)
