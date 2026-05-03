# ============================================================
# PackageGo API – Multi-stage Dockerfile
# ============================================================
# Techniques for small & fast image:
#   1. Multi-stage build   – build deps in 'builder', copy only wheels to 'runtime'
#   2. python:3.12-slim    – ~45 MB vs ~900 MB for full python image
#   3. --no-cache-dir      – no pip wheel cache stored in image
#   4. --no-compile         – skip .pyc generation during pip install
#   5. Single RUN chains   – fewer layers → smaller image
#   6. Non-root user       – security best practice
#   7. .dockerignore        – smaller build context, faster COPY
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system deps needed to compile Python packages (psycopg2, Pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first → layer caching (code changes don't re-install deps)
COPY requirements.txt .

# Install Python dependencies into a virtualenv for clean copy
# Use /opt/venv so shebang paths match the runtime stage
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir --no-compile -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install only runtime C libraries (no compilers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

# Copy virtualenv from builder (contains all installed packages)
# Place in /opt/venv so bind mount (.:/app) cannot overwrite it
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY . .

# Fix ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Ensure the virtualenv is on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Default command: run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
