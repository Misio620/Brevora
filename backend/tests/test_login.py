"""Google login: OAuth state, one-time login code exchange (docs/decisions.md §8)."""
import asyncio
import types
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from jose import jwt
from sqlalchemy import select, update

from app.config import get_settings
from app.database import async_session
from app.main import app
from app.models.login_code import LoginCode
from app.models.user import User
from app.routers import auth as auth_router

settings = get_settings()


@pytest.fixture
def fake_google_oauth(monkeypatch):
    """Fakes Google's token and userinfo endpoints. Set .token_status to fail the exchange."""

    class Response:
        def __init__(self, status, data):
            self.status_code, self._data, self.text = status, data, str(data)

        def json(self):
            return self._data

    class AsyncClient:
        token_status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, data):
            return Response(AsyncClient.token_status, {"access_token": "g-access", "refresh_token": "g-refresh", "expires_in": 3600})

        async def get(self, url, headers):
            return Response(200, {"id": "google-123", "email": "me@example.com", "name": "Me", "picture": "p"})

    monkeypatch.setattr(auth_router, "httpx", types.SimpleNamespace(AsyncClient=AsyncClient))
    return AsyncClient


async def start_login(client) -> str:
    r = await client.get("/auth/google/login")
    return parse_qs(urlparse(r.headers["location"]).query)["state"][0]


async def finish_login(client) -> str:
    """Runs a full login and returns the one-time code from the callback URL."""
    state = await start_login(client)
    r = await client.get("/auth/google/callback", params={"code": "google-code", "state": state})
    return r.headers["location"].split("#code=", 1)[1]


async def user_count() -> int:
    async with async_session() as db:
        return len((await db.execute(select(User))).all())


# --- OAuth state ---------------------------------------------------------------

async def test_login_redirects_to_google_with_state_in_an_httponly_cookie(client):
    r = await client.get("/auth/google/login")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    cookie = r.headers["set-cookie"].lower()

    assert r.status_code == 307 and r.headers["location"].startswith("https://accounts.google.com/")
    assert len(state) >= 40 and f"oauth_state={state.lower()}" in cookie
    assert all(flag in cookie for flag in ["httponly", "samesite=lax", "path=/auth/google", "max-age=600"])
    assert "secure" not in cookie  # the backend runs on http://localhost in tests


async def test_each_login_gets_a_new_state(client):
    assert await start_login(client) != await start_login(client)


@pytest.mark.parametrize("cookie, params", [
    (False, {"code": "c", "state": "S"}),  # another browser: no cookie
    (True, {"code": "c", "state": "attacker"}),  # different state
    (True, {"code": "c"}),  # no state
])
async def test_callback_with_bad_state_is_rejected_without_creating_a_user(client, fake_google_oauth, cookie, params):
    state = await start_login(client)
    if not cookie:
        client.cookies.clear()
    params = {k: (state if v == "S" else v) for k, v in params.items()}

    r = await client.get("/auth/google/callback", params=params)

    assert r.headers["location"] == f"{settings.FRONTEND_URL}/login?error=state"
    assert await user_count() == 0


async def test_cancel_and_exchange_failure_return_to_login(client, fake_google_oauth):
    state = await start_login(client)
    cancelled = await client.get("/auth/google/callback", params={"error": "access_denied", "state": state})
    assert cancelled.headers["location"].endswith("/login?error=cancelled")

    state = await start_login(client)
    fake_google_oauth.token_status = 400
    failed = await client.get("/auth/google/callback", params={"code": "bad", "state": state})
    assert failed.headers["location"].endswith("/login?error=google")


# --- One-time login code -------------------------------------------------------

async def test_callback_hands_over_a_one_time_code_and_clears_the_cookie(client, fake_google_oauth):
    state = await start_login(client)
    r = await client.get("/auth/google/callback", params={"code": "google-code", "state": state})

    location = r.headers["location"]
    assert location.startswith(f"{settings.FRONTEND_URL}/callback#code=")
    assert "token" not in location
    assert "max-age=0" in r.headers["set-cookie"].lower()


async def test_code_exchanges_once_for_the_users_jwt(client, fake_google_oauth):
    code = await finish_login(client)

    first = await client.post("/auth/exchange", json={"code": code})
    second = await client.post("/auth/exchange", json={"code": code})

    token = first.json()["access_token"]
    async with async_session() as db:
        user = (await db.execute(select(User))).scalar_one()
    assert first.status_code == 200
    assert jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])["sub"] == str(user.id)
    assert second.status_code == 400
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "me@example.com"


async def test_expired_and_unknown_codes_are_rejected(client, fake_google_oauth):
    code = await finish_login(client)
    async with async_session() as db:
        await db.execute(update(LoginCode).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        await db.commit()

    assert (await client.post("/auth/exchange", json={"code": code})).status_code == 400
    assert (await client.post("/auth/exchange", json={"code": "never-issued"})).status_code == 400


@pytest.mark.parametrize("code", ["", "x" * 101])
async def test_malformed_codes_are_rejected(client, code):
    assert (await client.post("/auth/exchange", json={"code": code})).status_code == 422


async def test_concurrent_exchanges_of_one_code_succeed_once(client, fake_google_oauth):
    code = await finish_login(client)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as other:
        results = await asyncio.gather(*(
            (client if i % 2 else other).post("/auth/exchange", json={"code": code}) for i in range(5)
        ))
    assert sorted(r.status_code for r in results) == [200, 400, 400, 400, 400]


async def test_only_the_code_hash_is_stored(client, fake_google_oauth):
    code = await finish_login(client)
    async with async_session() as db:
        stored = (await db.execute(select(LoginCode.code_hash))).scalars().all()
    assert len(stored) == 1 and len(stored[0]) == 64 and stored[0] != code
