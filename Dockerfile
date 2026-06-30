FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy only requirements file (faster build, no wheel building needed)
COPY requirements.txt ./

# Install dependencies only (NOT the package itself)
RUN uv pip install --system --no-cache -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Render assigns the actual port via $PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/api/v1/health')" || exit 1

# Run with gunicorn + uvicorn workers for production
# Uses $PORT env var (Render sets this automatically)
CMD gunicorn src.app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000}
