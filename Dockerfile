FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy only requirements file (faster build, no wheel building needed)
COPY requirements.txt ./

# Install runtime dependencies only. Dev deps (ruff, mypy, pytest, etc.) live
# in requirements-dev.txt and must never end up in the production image.
RUN uv pip install --system --no-cache -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code. The .dockerignore in the repo root excludes .env,
# .git, __pycache__, tests, scripts, and other files that must not ship.
# Note: alembic.ini lives at src/alembic.ini in the repo, so it is copied
# as part of src/ — no separate COPY line is needed.
COPY src ./src

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Render assigns the actual port via $PORT env var)
EXPOSE 8000

# Health check. Falls back to the PORT env var if set, otherwise 8000.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health').read()" || exit 1

# Run with gunicorn + uvicorn workers for production.
# Uses $PORT env var (Render sets this automatically).
# Shell form via /bin/sh -c so ${PORT:-8000} expansion works while still
# satisfying the JSONArgsRecommended lint.
CMD ["/bin/sh", "-c", "exec gunicorn src.app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}"]
