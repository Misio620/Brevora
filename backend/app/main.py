import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, channels, videos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="Brevora API",
    description="AI-powered video digest — grasp key insights from your subscriptions in minutes",
    version="1.0.0",
)

# CORS — allow frontend dev ports
cors_origins = [settings.FRONTEND_URL]
if "localhost" in settings.FRONTEND_URL:
    # Also allow nearby ports for Vite fallback
    from urllib.parse import urlparse
    parsed = urlparse(settings.FRONTEND_URL)
    base_port = parsed.port or 5173
    for p in range(base_port, base_port + 5):
        origin = f"{parsed.scheme}://{parsed.hostname}:{p}"
        if origin not in cors_origins:
            cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(videos.router)


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Brevora API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
