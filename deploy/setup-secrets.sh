#!/usr/bin/env bash
# EquityIQ -- GCP Secret Manager Setup
# Creates and manages Secret Manager secrets for Cloud Run deployment.
# Idempotent: safe to run multiple times.

set -euo pipefail

# Required secrets (must match deploy/cloudrun.yaml secretKeyRef entries)
SECRETS=(
    "GOOGLE_API_KEY"
    "POLYGON_API_KEY"
    "FRED_API_KEY"
    "NEWS_API_KEY"
    "SERPER_API_KEY"
    "TAVILY_API_KEY"
)

# Defaults
FROM_ENV=false
SERVICE_ACCOUNT=""
VERIFY_ONLY=false

# ---------- Usage ----------

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Create GCP Secret Manager secrets for EquityIQ Cloud Run deployment.

Options:
  --project ID            GCP project ID (or set GCP_PROJECT_ID env var)
  --from-env              Populate secret values from current environment variables
  --service-account EMAIL Custom Cloud Run service account email
  --verify                Only verify secrets exist (no create)
  --help                  Show this help message

Secrets created:
$(printf '  - %s\n' "${SECRETS[@]}")

Examples:
  # Create empty secrets (add values via Console or gcloud)
  $(basename "$0") --project my-gcp-project

  # Create and populate from current env vars
  $(basename "$0") --project my-gcp-project --from-env

  # Use a custom service account
  $(basename "$0") --project my-gcp-project --service-account mysa@my-gcp-project.iam.gserviceaccount.com
EOF
    exit 0
}

# ---------- Argument parsing ----------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            GCP_PROJECT_ID="$2"
            shift 2
            ;;
        --from-env)
            FROM_ENV=true
            shift
            ;;
        --service-account)
            SERVICE_ACCOUNT="$2"
            shift 2
            ;;
        --verify)
            VERIFY_ONLY=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Run $(basename "$0") --help for usage."
            exit 1
            ;;
    esac
done

# ---------- Preflight checks ----------

# Check gcloud CLI is available
if ! command -v gcloud &>/dev/null; then
    echo "ERROR: gcloud CLI not found. Install it from https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check GCP_PROJECT_ID
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
if [[ -z "$GCP_PROJECT_ID" ]]; then
    echo "ERROR: GCP_PROJECT_ID is required."
    echo "Set it via --project flag or GCP_PROJECT_ID environment variable."
    exit 1
fi

echo "=== EquityIQ Secret Manager Setup ==="
echo "Project: $GCP_PROJECT_ID"
echo "Mode: $(if $VERIFY_ONLY; then echo 'verify'; elif $FROM_ENV; then echo 'create + populate from env'; else echo 'create (empty)'; fi)"
echo ""

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="$GCP_PROJECT_ID" 2>/dev/null || true

# ---------- Verify mode ----------

if $VERIFY_ONLY; then
    echo "--- Secret Verification ---"
    all_ok=true
    for secret in "${SECRETS[@]}"; do
        if gcloud secrets describe "$secret" --project="$GCP_PROJECT_ID" &>/dev/null; then
            version_count=$(gcloud secrets versions list "$secret" --project="$GCP_PROJECT_ID" --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
            if [[ "$version_count" -eq 0 ]]; then
                echo "  WARNING: $secret exists but has no versions"
                all_ok=false
            else
                echo "  OK: $secret ($version_count version(s))"
            fi
        else
            echo "  MISSING: $secret"
            all_ok=false
        fi
    done
    echo ""
    if $all_ok; then
        echo "All secrets verified."
    else
        echo "Some secrets need attention (see above)."
        exit 1
    fi
    exit 0
fi

# ---------- Create secrets ----------

echo "--- Creating Secrets ---"
for secret in "${SECRETS[@]}"; do
    # Check if secret already exists (idempotency)
    if gcloud secrets describe "$secret" --project="$GCP_PROJECT_ID" &>/dev/null; then
        echo "  SKIP: $secret already exists"
    else
        gcloud secrets create "$secret" \
            --project="$GCP_PROJECT_ID" \
            --replication-policy="automatic" \
            --quiet
        echo "  CREATED: $secret"
    fi

    # Populate from env if requested
    if $FROM_ENV; then
        env_value="${!secret:-}"
        if [[ -z "$env_value" ]]; then
            echo "    WARNING: $secret env var is empty or not set, skipping value population"
        else
            echo -n "$env_value" | gcloud secrets versions add "$secret" \
                --project="$GCP_PROJECT_ID" \
                --data-file=- \
                --quiet
            echo "    POPULATED: $secret from environment"
        fi
    fi
done
echo ""

# ---------- IAM binding ----------

echo "--- IAM Binding ---"

# Determine service account
if [[ -n "$SERVICE_ACCOUNT" ]]; then
    sa_email="$SERVICE_ACCOUNT"
else
    # Default Cloud Run service account: PROJECT_NUMBER-compute@developer.gserviceaccount.com
    project_number=$(gcloud projects describe "$GCP_PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || echo "")
    if [[ -z "$project_number" ]]; then
        echo "  WARNING: Could not determine project number. Skipping IAM binding."
        echo "  Run manually: gcloud projects add-iam-policy-binding PROJECT_ID --member=serviceAccount:SA_EMAIL --role=roles/secretmanager.secretAccessor"
        echo ""
        echo "=== Setup complete (IAM binding skipped) ==="
        exit 0
    fi
    sa_email="${project_number}-compute@developer.gserviceaccount.com"
fi

echo "  Service account: $sa_email"
echo "  Granting roles/secretmanager.secretAccessor..."

gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${sa_email}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet &>/dev/null

echo "  DONE: IAM binding applied"
echo ""
echo "=== Setup complete ==="
echo "Secrets are ready for Cloud Run. Deploy with:"
echo "  gcloud run services replace deploy/cloudrun.yaml --project=$GCP_PROJECT_ID --region=us-central1"
