# Backend API image (Flask + Celery worker/beat share this image)
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary needs no build deps; curl is for container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py alembic.ini ./
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Uploaded avatars live here in v1 (local file storage, git-ignored)
RUN mkdir -p uploads/avatars

EXPOSE 5000

CMD ["python", "app.py"]
