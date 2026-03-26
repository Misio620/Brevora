import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import LoginResponse, UserResponse
from app.services.encryption import encrypt_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
YOUTUBE_SCOPES = "openid email profile https://www.googleapis.com/auth/youtube.readonly"


@router.get("/google/login", response_model=LoginResponse)
async def google_login():
    """Returns the Google OAuth URL for the frontend to redirect to."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.BACKEND_URL}/auth/google/callback",
        "response_type": "code",
        "scope": YOUTUBE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return LoginResponse(auth_url=auth_url)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handles the OAuth callback, exchanges code for tokens, creates/updates user."""
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
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

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
        raise HTTPException(status_code=400, detail="Failed to get user info")

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

    # Redirect to frontend with token
    redirect_url = f"{settings.FRONTEND_URL}/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the current authenticated user."""
    return UserResponse.from_user(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Client-side logout — just discard the JWT."""
    return
