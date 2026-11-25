# API image — no secrets baked in. Pass API_KEY / ES settings at runtime.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Skip Windows-only marker packages; torch wheel is large — required for generation path.
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src ./src
COPY pyproject.toml README.md SECURITY.md ./

EXPOSE 8000

# Bind 0.0.0.0 inside the container network; keep API_KEY set in orchestrator secrets.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
