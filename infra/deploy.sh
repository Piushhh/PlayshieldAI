#!/bin/bash
# IP Guardian — GCP Deployment Script
set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
REPO="ipguardian"
BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend"
WORKER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/worker"

echo "🛡️ Deploying IP Guardian to GCP..."
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"

# 1. Create Artifact Registry repo (if not exists)
gcloud artifacts repositories create ${REPO} \
  --repository-format=docker \
  --location=${REGION} \
  --project=${PROJECT_ID} 2>/dev/null || true

# 2. Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# 3. Build and push images
echo "📦 Building backend..."
docker build -t ${BACKEND_IMAGE}:latest ./backend
docker push ${BACKEND_IMAGE}:latest

echo "📦 Building worker..."
docker build -t ${WORKER_IMAGE}:latest -f ./backend/Dockerfile.worker ./backend
docker push ${WORKER_IMAGE}:latest

echo "📦 Building frontend..."
docker build -t ${FRONTEND_IMAGE}:latest ./frontend
docker push ${FRONTEND_IMAGE}:latest

# 4. Deploy Backend to Cloud Run
echo "🚀 Deploying backend..."
gcloud run deploy ipguardian-backend \
  --image=${BACKEND_IMAGE}:latest \
  --platform=managed \
  --region=${REGION} \
  --port=8000 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=5 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --allow-unauthenticated \
  --project=${PROJECT_ID}

# 5. Get backend URL
BACKEND_URL=$(gcloud run services describe ipguardian-backend \
  --platform=managed --region=${REGION} --project=${PROJECT_ID} \
  --format='value(status.url)')
echo "   Backend URL: ${BACKEND_URL}"

# 6. Deploy Frontend to Cloud Run
echo "🚀 Deploying frontend..."
gcloud run deploy ipguardian-frontend \
  --image=${FRONTEND_IMAGE}:latest \
  --platform=managed \
  --region=${REGION} \
  --port=3000 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --allow-unauthenticated \
  --project=${PROJECT_ID}

FRONTEND_URL=$(gcloud run services describe ipguardian-frontend \
  --platform=managed --region=${REGION} --project=${PROJECT_ID} \
  --format='value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "   Frontend: ${FRONTEND_URL}"
echo "   Backend:  ${BACKEND_URL}"
echo "   API Docs: ${BACKEND_URL}/docs"
