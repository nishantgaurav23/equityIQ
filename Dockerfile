# Stage 1: Build frontend static assets
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# -----------------------------------------------------------
# Stage 2: Base -- Python runtime dependencies
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install runtime deps from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY . .

# Copy built frontend static files
COPY --from=frontend-builder /frontend/out /app/frontend_static

# -----------------------------------------------------------
# Stage 3: Dev -- adds testing and linting tools
FROM base AS dev

RUN pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

# -----------------------------------------------------------
# Stage 4: Prod -- minimal, secure, production-ready
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
