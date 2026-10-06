import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.encryption import encrypt_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
YOUTUBE_SCOPES = "openid email profile https://www.googleapis.com/auth/youtube.readonly"

# Ties the Google callback to the browser that started the login (prevents login CSRF)
STATE_COOKIE = "oauth_state"
STATE_COOKIE_PATH = "/auth/google"
STATE_MAX_AGE = 600  # seconds to finish signing in with Google


def _login_failed(reason: str) -> RedirectResponse:
    """Sends the user back to the login page with a short reason code."""
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={reason}")
    response.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)
    return response


@router.get("/google/login")
async def google_login():
    """Redirects the browser to Google, remembering a random state in an HttpOnly cookie."""
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.BACKEND_URL}/auth/google/callback",
        "response_type": "code",
        "scope": YOUTUBE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    response = RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=STATE_MAX_AGE,
        path=STATE_COOKIE_PATH,
        httponly=True,
        secure=settings.BACKEND_URL.startswith("https://"),
        # Lax still sends the cookie on Google's top-level redirect back to the callback
        samesite="lax",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handles the OAuth callback, exchanges code for tokens, creates/updates user."""
    if error or not code:
        # The user cancelled on Google's consent screen, or Google returned no code
        return _login_failed("cancelled")

    expected_state = request.cookies.get(STATE_COOKIE)
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        logger.warning("OAuth callback rejected: state missing or does not match the login cookie")
        return _login_failed("state")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.BACKEND_URL}/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        logger.error(f"Token exchange failed: {token_response.text}")
        return _login_failed("google")

    token_data = token_response.json()
    google_access_token = token_data["access_token"]
    google_refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    # Get user info
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_response.status_code != 200:
        logger.error(f"Userinfo request failed: {userinfo_response.status_code}")
        return _login_failed("google")

    userinfo = userinfo_response.json()
    google_id = userinfo["id"]
    email = userinfo["email"]
    display_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if user:
        user.email = email
        user.display_name = display_name
        user.avatar_url = avatar_url
        user.access_token = encrypt_token(google_access_token)
        if google_refresh_token:
            user.refresh_token = encrypt_token(google_refresh_token)
        user.token_expiry = token_expiry
        user.updated_at = datetime.now(timezone.utc)
    else:
        user = User(
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            access_token=encrypt_token(google_access_token),
            refresh_token=encrypt_token(google_refresh_token) if google_refresh_token else None,
            token_expiry=token_expiry,
        )
        db.add(user)

    await db.flush()

    # Create JWT
    jwt_token = create_access_token(str(user.id))

    # Redirect to frontend with the token in the fragment: browsers never send the part
    # after # to a server, so it stays out of access logs and Referer headers
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/callback#token={jwt_token}")
    response.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the current authenticated user."""
    return UserResponse.from_user(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Client-side logout — just discard the JWT."""
    return
