#!/usr/bin/env bash
# EquityIQ -- Firestore Database Setup
# Creates and configures a Firestore database in Native mode for production.
# Idempotent: safe to run multiple times.

set -euo pipefail

# Collection name (must match memory/firestore_vault.py _COLLECTION)
COLLECTION="verdicts"

# Default region (matches deploy/cloudrun.yaml)
DEFAULT_REGION="us-central1"

# Defaults
REGION="$DEFAULT_REGION"
SERVICE_ACCOUNT=""
VERIFY_ONLY=false

# ---------- Usage ----------

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Create and configure a Firestore database for EquityIQ production deployment.

Sets up:
  - Firestore database in Native mode
  - Collection: ${COLLECTION}
  - Composite index: ticker (ASC) + created_at (DESC)
  - IAM binding for Cloud Run service account

Options:
  --project ID            GCP project ID (or set GCP_PROJECT_ID env var)
  --region REGION         Firestore region (default: ${DEFAULT_REGION})
  --service-account EMAIL Custom Cloud Run service account email
  --verify                Only verify Firestore setup (no create)
  --help                  Show this help message

Examples:
  # Create Firestore database with defaults
  $(basename "$0") --project my-gcp-project

  # Create in a specific region
  $(basename "$0") --project my-gcp-project --region us-east1

  # Verify existing setup
  $(basename "$0") --project my-gcp-project --verify
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
        --region)
            REGION="$2"
            shift 2
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

echo "=== EquityIQ Firestore Setup ==="
echo "Project: $GCP_PROJECT_ID"
echo "Region:  $REGION"
echo "Mode:    $(if $VERIFY_ONLY; then echo 'verify'; else echo 'create'; fi)"
echo ""

# ---------- Enable Firestore API ----------

echo "--- Enabling Firestore API ---"
gcloud services enable firestore.googleapis.com --project="$GCP_PROJECT_ID" 2>/dev/null || true
echo "  DONE: firestore.googleapis.com enabled"
echo ""

# ---------- Verify mode ----------

if $VERIFY_ONLY; then
    echo "--- Firestore Verification ---"
    all_ok=true

    # Check database exists
    if gcloud firestore databases describe --project="$GCP_PROJECT_ID" &>/dev/null; then
        db_type=$(gcloud firestore databases describe --project="$GCP_PROJECT_ID" \
            --format="value(type)" 2>/dev/null || echo "UNKNOWN")
        echo "  OK: Database exists (type: $db_type)"
        if [[ "$db_type" != "FIRESTORE_NATIVE" ]]; then
            echo "  WARNING: Database is not in Native mode (type: $db_type)"
            all_ok=false
        fi
    else
        echo "  MISSING: Firestore database not found"
        all_ok=false
    fi

    # Check composite indexes
    index_count=$(gcloud firestore indexes composite list --project="$GCP_PROJECT_ID" \
        --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$index_count" -gt 0 ]]; then
        echo "  OK: $index_count composite index(es) found"
    else
        echo "  WARNING: No composite indexes found"
        all_ok=false
    fi

    echo ""
    if $all_ok; then
        echo "Firestore setup verified."
    else
        echo "Some items need attention (see above)."
        exit 1
    fi
    exit 0
fi

# ---------- Create Firestore database ----------

echo "--- Creating Firestore Database ---"

# Check if database already exists (idempotency)
if gcloud firestore databases describe --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo "  SKIP: Firestore database already exists"
else
    echo "  Creating Firestore database in Native mode..."
    gcloud firestore databases create \
        --project="$GCP_PROJECT_ID" \
        --location="$REGION" \
        --type=FIRESTORE_NATIVE \
        --quiet
    echo "  CREATED: Firestore database (Native mode, region: $REGION)"
fi
echo ""

# ---------- Create composite index ----------

echo "--- Creating Composite Indexes ---"
echo "  Collection: $COLLECTION"
echo "  Index: ticker (ASC) + created_at (DESC)"

# Check if index already exists by listing and looking for our fields
existing_indexes=$(gcloud firestore indexes composite list \
    --project="$GCP_PROJECT_ID" \
    --format="table(name,state)" 2>/dev/null || echo "")

if echo "$existing_indexes" | grep -q "READY\|CREATING"; then
    echo "  SKIP: Composite index already exists or is being created"
else
    gcloud firestore indexes composite create \
        --project="$GCP_PROJECT_ID" \
        --collection-group="$COLLECTION" \
        --field-config field-path=ticker,order=ascending \
        --field-config field-path=created_at,order=descending \
        --quiet 2>/dev/null || echo "  NOTE: Index may already exist or is being created"
    echo "  CREATED: Composite index on ${COLLECTION} (ticker ASC, created_at DESC)"
fi
echo ""

# ---------- IAM binding ----------

echo "--- IAM Binding ---"

# Determine service account
if [[ -n "$SERVICE_ACCOUNT" ]]; then
    sa_email="$SERVICE_ACCOUNT"
else
    # Default Cloud Run service account: PROJECT_NUMBER-compute@developer.gserviceaccount.com
    project_number=$(gcloud projects describe "$GCP_PROJECT_ID" \
        --format="value(projectNumber)" 2>/dev/null || echo "")
    if [[ -z "$project_number" ]]; then
        echo "  WARNING: Could not determine project number. Skipping IAM binding."
        echo "  Run manually: gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \\"
        echo "    --member=serviceAccount:SA_EMAIL --role=roles/datastore.user"
        echo ""
        echo "=== Setup complete (IAM binding skipped) ==="
        exit 0
    fi
    sa_email="${project_number}-compute@developer.gserviceaccount.com"
fi

echo "  Service account: $sa_email"
echo "  Granting roles/datastore.user..."

gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:${sa_email}" \
    --role="roles/datastore.user" \
    --quiet &>/dev/null

echo "  DONE: IAM binding applied"
echo ""
echo "=== Firestore setup complete ==="
echo "Database is ready for FirestoreVault (ENVIRONMENT=production)."
echo "Collection '${COLLECTION}' will be auto-created on first write."
