FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 (PDF export uses pure-Python reportlab — no system libs).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

COPY . .

EXPOSE 8000

# entrypoint runs migrations + seeds reference data, then starts the server
CMD ["sh", "-c", "alembic upgrade head && python -m seeds.seed_plans && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
