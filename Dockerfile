# Stage 1: Base -- runtime dependencies
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install runtime deps from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY . .

# -----------------------------------------------------------
# Stage 2: Dev -- adds testing and linting tools
FROM base AS dev

RUN pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

# -----------------------------------------------------------
# Stage 3: Prod -- minimal, secure, production-ready
FROM base AS prod

# Create non-root user
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

# Ensure app files are accessible
RUN chown -R appuser:appuser /app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8080/health || exit 1

USER appuser

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
