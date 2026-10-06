"""Secrets check, safe error messages and Google token refresh (docs/decisions.md §8)."""
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from google.genai import errors as genai_errors
from google.oauth2.credentials import Credentials
from sqlalchemy import text

from app import main
from app.config import Settings, secret_problems
from app.database import async_session
from app.models.user import User
from app.services import ai, youtube
from app.services.encryption import decrypt_token
from tests.conftest import auth_header, make_user, make_videos

GOOD_JWT = "x" * 64
GOOD_KEY = Fernet.generate_key().decode()


# --- Secrets -----------------------------------------------------------------

@pytest.mark.parametrize(
    "jwt_secret, encryption_key, expected",
    [
        ("", "", 2),
        ("change-me-in-production", GOOD_KEY, 1),
        ("short", GOOD_KEY, 1),
        (GOOD_JWT, "not-a-fernet-key", 1),
        (GOOD_JWT, GOOD_KEY, 0),
    ],
)
def test_secret_problems(jwt_secret, encryption_key, expected):
    settings = Settings(JWT_SECRET=jwt_secret, ENCRYPTION_KEY=encryption_key, _env_file=None)
    assert len(secret_problems(settings)) == expected


async def test_server_refuses_to_start_with_the_public_default(monkeypatch):
    monkeypatch.setattr(main.settings, "JWT_SECRET", "change-me-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        async with main.lifespan(main.app):
            pass


# --- Error messages ----------------------------------------------------------

def _api_error(cls, code):
    return cls(code, {"error": {"code": code, "message": "quota for project 987654321"}})


@pytest.mark.parametrize(
    "error, message",
    [
        (_api_error(genai_errors.ClientError, 429), "AI 服務的使用額度暫時用完，請稍後再試"),
        (_api_error(genai_errors.ServerError, 503), "AI 服務暫時忙碌，請稍後再試"),
        (_api_error(genai_errors.ClientError, 400), "筆記生成失敗，請稍後再試"),
        (RuntimeError("Empty response"), "筆記生成失敗，請稍後再試"),
    ],
)
def test_user_facing_error(error, message):
    assert ai.user_facing_error(error) == message


async def test_failed_note_hides_api_details_but_logs_them(client, fake_ai, fake_chapters, caplog):
    user = await make_user()
    await make_videos(1, users=[user])
    fake_ai.fail = _api_error(genai_errors.ClientError, 429)

    await client.post("/videos/vid0/process", headers=auth_header(user))

    note = (await client.get("/videos/vid0", headers=auth_header(user))).json()
    assert note["error_message"] == "AI 服務的使用額度暫時用完，請稍後再試"
    assert "987654321" not in note["error_message"]
    assert "987654321" in caplog.text


# --- Google token refresh ----------------------------------------------------

@pytest.fixture
def fake_google(monkeypatch):
    """Fakes Google's token endpoint and the YouTube API, recording what was used."""

    class Google:
        refreshes = 0
        tokens_seen: list[str] = []
        rotate_mid_call = False  # simulate the client library refreshing on its own

    state = Google()
    state.tokens_seen = []

    def refresh(self, request):
        state.refreshes += 1
        self.token = f"fresh-token-{state.refreshes}"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    class Request:
        def __init__(self, creds, payload):
            self.creds, self.payload = creds, payload

        def execute(self):
            state.tokens_seen.append(self.creds.token)
            if state.rotate_mid_call:
                self.creds.token = "library-token"
                self.creds.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
            return self.payload

    class Service:
        def __init__(self, creds):
            self.creds = creds

        def __getattr__(self, _):  # subscriptions(), channels(), playlistItems(), videos()
            return lambda: self

        def list(self, **kw):
            if "mine" in kw:
                payload = {"items": [{"snippet": {"resourceId": {"channelId": "chA"}, "title": "A", "thumbnails": {"default": {"url": "u"}}}}]}
            elif "playlistId" in kw:
                payload = {"items": [{"snippet": {
                    "resourceId": {"videoId": f"v-{kw['playlistId']}"}, "title": "t", "thumbnails": {},
                    "publishedAt": "2026-10-01T00:00:00Z", "channelTitle": "c"}}]}
            elif kw.get("part") == "contentDetails":
                payload = {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": f"UU-{kw['id']}"}}}]}
            else:
                payload = {"items": [{"snippet": {"description": "0:00 Intro\n1:00 A\n2:00 B"}}]}
            return Request(self.creds, payload)

    monkeypatch.setattr(Credentials, "refresh", refresh)
    monkeypatch.setattr(youtube, "build", lambda *a, credentials=None, **k: Service(credentials))
    return state


async def stored_user(user_id) -> User:
    async with async_session() as db:
        return await db.get(User, user_id)


EXPIRED = datetime.now(timezone.utc) - timedelta(minutes=5)


async def test_expired_token_is_refreshed_once_and_saved_encrypted(client, fake_google):
    user = await make_user(token_expiry=EXPIRED)

    r = await client.get("/channels/subscriptions", headers=auth_header(user))

    saved = await stored_user(user.id)
    assert r.status_code == 200
    assert fake_google.refreshes == 1 and fake_google.tokens_seen == ["fresh-token-1"]
    assert decrypt_token(saved.access_token) == "fresh-token-1"
    assert decrypt_token(saved.refresh_token) == "stored-refresh-token"
    assert saved.token_expiry > datetime.now(timezone.utc) + timedelta(minutes=55)
    async with async_session() as db:
        raw = (await db.execute(text("SELECT access_token FROM users WHERE id = :id"), {"id": user.id})).scalar_one()
    assert "fresh-token" not in raw


async def test_valid_token_is_reused(client, fake_google):
    user = await make_user()
    await client.get("/channels/subscriptions", headers=auth_header(user))
    assert fake_google.refreshes == 0 and fake_google.tokens_seen == ["stored-access-token"]


async def test_sync_refreshes_once_for_all_channels(client, fake_google):
    user = await make_user(token_expiry=EXPIRED)
    async with async_session() as db:
        from app.models.channel import PinnedChannel
        db.add_all([PinnedChannel(user_id=user.id, channel_id=f"ch{i}", title=f"C{i}") for i in range(5)])
        await db.commit()

    r = await client.post("/videos/sync", headers=auth_header(user))

    assert r.status_code == 200 and r.json()["new_videos"] == 5
    assert fake_google.refreshes == 1
    assert len(fake_google.tokens_seen) == 10 and set(fake_google.tokens_seen) == {"fresh-token-1"}
    assert decrypt_token((await stored_user(user.id)).access_token) == "fresh-token-1"


async def test_token_refreshed_by_the_client_library_is_saved(client, fake_google):
    user = await make_user()
    fake_google.rotate_mid_call = True
    await client.get("/channels/subscriptions", headers=auth_header(user))
    assert decrypt_token((await stored_user(user.id)).access_token) == "library-token"


async def test_token_refreshed_for_chapters_survives_a_failed_note(client, fake_google, fake_ai):
    user = await make_user(token_expiry=EXPIRED)
    await make_videos(1, users=[user])
    fake_ai.fail = RuntimeError("Gemini down")

    await client.post("/videos/vid0/process", headers=auth_header(user))

    assert decrypt_token((await stored_user(user.id)).access_token) == "fresh-token-1"


async def test_row_without_expiry_is_not_force_refreshed(client, fake_google):
    user = await make_user()
    async with async_session() as db:
        await db.execute(text("UPDATE users SET token_expiry = NULL WHERE id = :id"), {"id": user.id})
        await db.commit()
    await client.get("/channels/subscriptions", headers=auth_header(user))
    assert fake_google.refreshes == 0
