# Deployment Guide

## Local Development with Docker

### Prerequisites
- Docker and Docker Compose installed
- `.env` file with API keys (see [Environment Variables](#environment-variables))

### Start Dev Container

```bash
# Build and start with hot-reload
make dev
# or
docker compose up --build
```

This runs the `dev` target of the multi-stage Dockerfile, mounting your local source for hot-reload. The app is available at `http://localhost:8000`.

### Run Tests in Container

```bash
make test
# or
docker compose run --rm app python -m pytest tests/ -v --tb=short
```

### Stop

```bash
docker compose down
```

---

## Production: GCP Cloud Run

EquityIQ is designed to run as a single Cloud Run container, keeping costs under $50/month.

### Architecture

- **Cloud Run**: Single container, 0-4 instances, all agents as internal async functions
- **Firestore**: Analysis history persistence (free tier: 1GB, 50K reads/day)
- **Secret Manager**: API keys and credentials (free tier: 6 active versions)
- **Artifact Registry**: Docker image storage

### Build Production Image

```bash
docker build --target prod -t equityiq:prod .
```

The production image:
- Uses multi-stage build (slim base)
- Runs as non-root user (`appuser`)
- Exposes port 8080
- Includes HEALTHCHECK on `/health`
- Runs uvicorn with 1 worker

### Deploy to Cloud Run

```bash
# Tag and push to Artifact Registry
docker tag equityiq:prod gcr.io/YOUR_PROJECT/equityiq:latest
docker push gcr.io/YOUR_PROJECT/equityiq:latest

# Deploy
gcloud run deploy equityiq \
  --image gcr.io/YOUR_PROJECT/equityiq:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 4 \
  --port 8080 \
  --set-env-vars ENVIRONMENT=production
```

### Health Check

Cloud Run automatically uses the `/health` endpoint:

```bash
curl https://your-service-url/health
```

Returns:

```json
{
  "status": "ok",
  "environment": "production",
  "version": "0.1.0"
}
```

### Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Cloud Run (0-4 instances, pay-per-use) | ~$15-30 |
| Firestore (free tier) | $0 |
| Secret Manager (free tier) | $0 |
| Artifact Registry | ~$1-2 |
| **Total** | **< $50** |

---

## Environment Variables

All configuration flows through `config/settings.py` via pydantic-settings. Create a `.env` file from the template:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI / Gemini API key for all agents | Yes |
| `POLYGON_API_KEY` | Polygon.io key for fundamentals and price data | Yes |
| `FRED_API_KEY` | FRED API key for macro economic data | Yes |
| `NEWS_API_KEY` | NewsAPI key for news sentiment | Yes |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `local` | `local` (SQLite) or `production` (Firestore) |
| `SQLITE_DB_PATH` | `data/equityiq.db` | Path to SQLite database file |
| `GCP_PROJECT_ID` | `""` | GCP project ID (production only) |
| `GCP_REGION` | `us-central1` | GCP region for Cloud Run |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `VALUATION_AGENT_URL` | `http://localhost:8001` | ValuationScout agent URL |
| `MOMENTUM_AGENT_URL` | `http://localhost:8002` | MomentumTracker agent URL |
| `PULSE_AGENT_URL` | `http://localhost:8003` | PulseMonitor agent URL |
| `ECONOMY_AGENT_URL` | `http://localhost:8004` | EconomyWatcher agent URL |
| `COMPLIANCE_AGENT_URL` | `http://localhost:8005` | ComplianceChecker agent URL |
| `SYNTHESIZER_AGENT_URL` | `http://localhost:8006` | SignalSynthesizer agent URL |
| `RISK_AGENT_URL` | `http://localhost:8007` | RiskGuardian agent URL |

### Production Secrets

On GCP, use Secret Manager instead of `.env`:

```bash
# Create secrets
echo -n "your-key" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "your-key" | gcloud secrets create POLYGON_API_KEY --data-file=-
echo -n "your-key" | gcloud secrets create FRED_API_KEY --data-file=-
echo -n "your-key" | gcloud secrets create NEWS_API_KEY --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --member="serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Dockerfile Details

The Dockerfile uses a 3-stage build:

1. **base**: Python 3.12-slim, installs runtime dependencies from pyproject.toml
2. **dev**: Adds test/lint tools (pytest, ruff), used by docker-compose for local dev
3. **prod**: Adds non-root user, HEALTHCHECK, exposes port 8080

```
# Local development
docker compose up --build        # Uses 'dev' target

# Production build
docker build --target prod .     # Uses 'prod' target
```
