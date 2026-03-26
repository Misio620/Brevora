FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg for audio processing fallback
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic/ ./alembic/
COPY alembic.ini .
COPY app/ ./app/

# Run migrations then start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
