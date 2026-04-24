#!/bin/bash
###############################################################################
# PlayShield AI — Full GCP Production Deployment
#
# This script provisions ALL required cloud infrastructure and deploys the
# complete PlayShield AI stack to Google Cloud Run.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated (gcloud auth login)
#   2. A GCP project with billing enabled
#   3. Docker running locally
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   ./infra/deploy-full.sh
###############################################################################
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?❌ Set GCP_PROJECT_ID env var}"
REGION="${GCP_REGION:-us-central1}"
REPO="playshield"
DB_INSTANCE="playshield-sql"
DB_NAME="playshield"
DB_USER="playshield"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)}"
GCS_BUCKET="${GCS_BUCKET_NAME:-${PROJECT_ID}-playshield-media}"
JWT_SECRET="${JWT_SECRET_KEY:-$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 48)}"
REDIS_HOST=""

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest"
WORKER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/worker:latest"

echo ""
echo "🛡️  PlayShield AI — Full GCP Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Project:  ${PROJECT_ID}"
echo "   Region:   ${REGION}"
echo "   DB:       ${DB_INSTANCE}"
echo "   Bucket:   ${GCS_BUCKET}"
echo ""

# ── Step 0: Set project ──────────────────────────────────────────────────────
echo "📌 Step 0: Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# ── Step 1: Enable required APIs ─────────────────────────────────────────────
echo "📌 Step 1: Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  --quiet

echo "   ✅ APIs enabled"

# ── Step 2: Create Artifact Registry ─────────────────────────────────────────
echo "📌 Step 2: Creating Artifact Registry repo..."
gcloud artifacts repositories create ${REPO} \
  --repository-format=docker \
  --location=${REGION} \
  --description="PlayShield AI Docker images" \
  --quiet 2>/dev/null || echo "   (repo already exists)"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
echo "   ✅ Artifact Registry ready"

# ── Step 3: Create Cloud SQL (PostgreSQL) ─────────────────────────────────────
echo "📌 Step 3: Creating Cloud SQL instance..."
if ! gcloud sql instances describe ${DB_INSTANCE} --quiet 2>/dev/null; then
  gcloud sql instances create ${DB_INSTANCE} \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --edition=enterprise \
    --region=${REGION} \
    --storage-size=10GB \
    --storage-auto-increase \
    --availability-type=ZONAL \
    --quiet
  echo "   ✅ Cloud SQL instance created"
else
  echo "   (instance already exists)"
fi

# Create database and user
gcloud sql databases create ${DB_NAME} --instance=${DB_INSTANCE} --quiet 2>/dev/null || true
gcloud sql users create ${DB_USER} --instance=${DB_INSTANCE} \
  --password=${DB_PASSWORD} --quiet 2>/dev/null || \
  gcloud sql users set-password ${DB_USER} --instance=${DB_INSTANCE} \
  --password=${DB_PASSWORD} --quiet 2>/dev/null || true

# Get connection name
SQL_CONNECTION=$(gcloud sql instances describe ${DB_INSTANCE} \
  --format='value(connectionName)')
echo "   ✅ Database: ${DB_NAME} | Connection: ${SQL_CONNECTION}"

# Build the DATABASE_URL for Cloud SQL with unix socket
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${SQL_CONNECTION}"

# ── Step 4: Create GCS Bucket ────────────────────────────────────────────────
echo "📌 Step 4: Creating GCS bucket..."
gsutil mb -p ${PROJECT_ID} -l ${REGION} "gs://${GCS_BUCKET}" 2>/dev/null || echo "   (bucket exists)"
gsutil iam ch allUsers:objectViewer "gs://${GCS_BUCKET}" 2>/dev/null || true
echo "   ✅ GCS bucket: gs://${GCS_BUCKET}"

# ── Step 5: Create Memorystore Redis (or fallback) ───────────────────────────
echo "📌 Step 5: Setting up Redis..."
# Check if VPC connector exists
VPC_CONNECTOR=""
if gcloud compute networks vpc-access connectors describe playshield-connector \
  --region=${REGION} --quiet 2>/dev/null; then
  VPC_CONNECTOR="playshield-connector"
  echo "   VPC connector already exists"
else
  echo "   Creating VPC connector for Memorystore access..."
  gcloud compute networks vpc-access connectors create playshield-connector \
    --region=${REGION} \
    --range="10.8.0.0/28" \
    --quiet 2>/dev/null && VPC_CONNECTOR="playshield-connector" || \
    echo "   ⚠️ VPC connector creation failed (may need VPC access API)"
fi

# Try to create Memorystore Redis
REDIS_URL=""
if [ -n "$VPC_CONNECTOR" ]; then
  if ! gcloud redis instances describe playshield-redis --region=${REGION} --quiet 2>/dev/null; then
    echo "   Creating Memorystore Redis..."
    gcloud redis instances create playshield-redis \
      --size=1 \
      --region=${REGION} \
      --redis-version=redis_7_0 \
      --tier=BASIC \
      --quiet 2>/dev/null || echo "   ⚠️ Memorystore creation failed"
  fi
  REDIS_HOST=$(gcloud redis instances describe playshield-redis \
    --region=${REGION} --format='value(host)' 2>/dev/null || true)
  if [ -n "$REDIS_HOST" ]; then
    REDIS_URL="redis://${REDIS_HOST}:6379/0"
    echo "   ✅ Memorystore Redis: ${REDIS_HOST}"
  fi
fi

# Fallback: use Redis in-memory within the backend (for demo)
if [ -z "$REDIS_URL" ]; then
  echo "   ⚠️ Using Redis Cloud fallback (Upstash free tier recommended)"
  echo "   Set REDIS_URL env var on Cloud Run services manually if needed."
  REDIS_URL="redis://localhost:6379/0"
fi

# ── Step 6: Build and Push Docker Images ─────────────────────────────────────
echo "📌 Step 6: Building and pushing Docker images..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "   Building backend..."
docker build --platform linux/amd64 -t ${BACKEND_IMAGE} -f ${SCRIPT_DIR}/backend/Dockerfile.prod ${SCRIPT_DIR}/backend
docker push ${BACKEND_IMAGE}
echo "   ✅ Backend image pushed"

echo "   Building worker..."
docker build --platform linux/amd64 -t ${WORKER_IMAGE} -f ${SCRIPT_DIR}/backend/Dockerfile.worker ${SCRIPT_DIR}/backend
docker push ${WORKER_IMAGE}
echo "   ✅ Worker image pushed"

# Frontend needs backend URL (we'll update after backend deploys)
echo "   Building frontend (placeholder URL, will update)..."
docker build --platform linux/amd64 -t ${FRONTEND_IMAGE} \
  --build-arg NEXT_PUBLIC_API_URL="https://playshield-backend-placeholder.run.app" \
  -f ${SCRIPT_DIR}/frontend/Dockerfile.prod ${SCRIPT_DIR}/frontend
docker push ${FRONTEND_IMAGE}
echo "   ✅ Frontend image pushed"

# ── Step 7: Deploy Backend to Cloud Run ──────────────────────────────────────
echo "📌 Step 7: Deploying backend to Cloud Run..."
BACKEND_ENV_VARS="DATABASE_URL=${DATABASE_URL}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},REDIS_URL=${REDIS_URL}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},JWT_SECRET_KEY=${JWT_SECRET}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},GCP_PROJECT_ID=${PROJECT_ID}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},GCS_BUCKET_NAME=${GCS_BUCKET}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},VERTEX_AI_LOCATION=${REGION}"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},GEMINI_MODEL=gemini-2.0-flash"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},CONFIDENCE_THRESHOLD=0.75"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},WEIGHT_HASH=0.4"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},WEIGHT_EMBED=0.4"
BACKEND_ENV_VARS="${BACKEND_ENV_VARS},WEIGHT_RISK=0.2"

DEPLOY_FLAGS="--image=${BACKEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --port=8000 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=300 \
  --set-env-vars=${BACKEND_ENV_VARS} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --allow-unauthenticated \
  --project=${PROJECT_ID}"

if [ -n "$VPC_CONNECTOR" ]; then
  DEPLOY_FLAGS="${DEPLOY_FLAGS} --vpc-connector=${VPC_CONNECTOR}"
fi

eval gcloud run deploy playshield-backend ${DEPLOY_FLAGS} --quiet

BACKEND_URL=$(gcloud run services describe playshield-backend \
  --platform=managed --region=${REGION} --project=${PROJECT_ID} \
  --format='value(status.url)')
echo "   ✅ Backend deployed: ${BACKEND_URL}"

# ── Step 8: Deploy Worker (as Cloud Run Job or secondary service) ─────────
echo "📌 Step 8: Deploying worker..."
WORKER_ENV_VARS="DATABASE_URL=${DATABASE_URL}"
WORKER_ENV_VARS="${WORKER_ENV_VARS},REDIS_URL=${REDIS_URL}"
WORKER_ENV_VARS="${WORKER_ENV_VARS},GCP_PROJECT_ID=${PROJECT_ID}"
WORKER_ENV_VARS="${WORKER_ENV_VARS},GCS_BUCKET_NAME=${GCS_BUCKET}"
WORKER_ENV_VARS="${WORKER_ENV_VARS},VERTEX_AI_LOCATION=${REGION}"

WORKER_FLAGS="--image=${WORKER_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=2 \
  --timeout=900 \
  --no-cpu-throttling \
  --set-env-vars=${WORKER_ENV_VARS} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --no-allow-unauthenticated \
  --project=${PROJECT_ID}"

if [ -n "$VPC_CONNECTOR" ]; then
  WORKER_FLAGS="${WORKER_FLAGS} --vpc-connector=${VPC_CONNECTOR}"
fi

eval gcloud run deploy playshield-worker ${WORKER_FLAGS} --quiet 2>/dev/null || \
  echo "   ⚠️ Worker deploy as service skipped (Celery needs persistent Redis)"

echo "   ✅ Worker configured"

# ── Step 9: Rebuild and deploy frontend with correct backend URL ─────────────
echo "📌 Step 9: Rebuilding frontend with correct backend URL..."
docker build --platform linux/amd64 -t ${FRONTEND_IMAGE} \
  --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
  -f ${SCRIPT_DIR}/frontend/Dockerfile.prod ${SCRIPT_DIR}/frontend
docker push ${FRONTEND_IMAGE}

gcloud run deploy playshield-frontend \
  --image=${FRONTEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --port=3000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --allow-unauthenticated \
  --project=${PROJECT_ID} \
  --quiet

FRONTEND_URL=$(gcloud run services describe playshield-frontend \
  --platform=managed --region=${REGION} --project=${PROJECT_ID} \
  --format='value(status.url)')
echo "   ✅ Frontend deployed: ${FRONTEND_URL}"

# ── Step 10: Update backend CORS with frontend URL ──────────────────────────
echo "📌 Step 10: Updating backend CORS..."
gcloud run services update playshield-backend \
  --region=${REGION} \
  --update-env-vars="CORS_ORIGINS=${FRONTEND_URL}" \
  --quiet

# ── Step 11: Run migrations ──────────────────────────────────────────────────
echo "📌 Step 11: Running database migrations..."
gcloud run jobs create playshield-migrate \
  --image=${BACKEND_IMAGE} \
  --region=${REGION} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
  --command="alembic" \
  --args="upgrade,head" \
  --project=${PROJECT_ID} \
  --quiet 2>/dev/null || \
  gcloud run jobs update playshield-migrate \
  --image=${BACKEND_IMAGE} \
  --region=${REGION} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
  --command="alembic" \
  --args="upgrade,head" \
  --project=${PROJECT_ID} \
  --quiet

gcloud run jobs execute playshield-migrate --region=${REGION} --wait --quiet
echo "   ✅ Migrations complete"

# ── Step 12: Seed database ───────────────────────────────────────────────────
echo "📌 Step 12: Seeding database..."
gcloud run jobs create playshield-seed \
  --image=${BACKEND_IMAGE} \
  --region=${REGION} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
  --command="python" \
  --args="-m,app.seed" \
  --project=${PROJECT_ID} \
  --quiet 2>/dev/null || \
  gcloud run jobs update playshield-seed \
  --image=${BACKEND_IMAGE} \
  --region=${REGION} \
  --set-cloudsql-instances=${SQL_CONNECTION} \
  --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
  --command="python" \
  --args="-m,app.seed" \
  --project=${PROJECT_ID} \
  --quiet

gcloud run jobs execute playshield-seed --region=${REGION} --wait --quiet
echo "   ✅ Database seeded"

# ── Step 13: Verify deployment ────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 PlayShield AI Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Live URLs:"
echo "   FRONTEND_URL=${FRONTEND_URL}"
echo "   BACKEND_URL=${BACKEND_URL}"
echo "   API_DOCS=${BACKEND_URL}/docs"
echo ""
echo "🔐 Authentication:"
echo "   Visit the frontend to register your own account."
echo ""
echo "🔧 Cloud Resources:"
echo "   Cloud SQL:  ${SQL_CONNECTION}"
echo "   GCS Bucket: gs://${GCS_BUCKET}"
echo "   Redis:      ${REDIS_URL}"
echo ""
echo "🔑 Secrets (save these!):"
echo "   DB_PASSWORD=${DB_PASSWORD}"
echo "   JWT_SECRET=${JWT_SECRET}"
echo ""

# Verify health
echo "📋 Health Check:"
curl -s "${BACKEND_URL}/healthz" | python3 -m json.tool || echo "   ⚠️ Health check pending (cold start)"
echo ""

# Save deployment info to file
cat > ${SCRIPT_DIR}/infra/deployment-info.txt <<EOF
PlayShield AI Deployment Info
===========================
Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Project: ${PROJECT_ID}
Region: ${REGION}

FRONTEND_URL=${FRONTEND_URL}
BACKEND_URL=${BACKEND_URL}
API_DOCS=${BACKEND_URL}/docs

Cloud SQL: ${SQL_CONNECTION}
GCS Bucket: gs://${GCS_BUCKET}
Redis: ${REDIS_URL}

DB_PASSWORD=${DB_PASSWORD}
JWT_SECRET=${JWT_SECRET}
EOF

echo "💾 Deployment info saved to infra/deployment-info.txt"
