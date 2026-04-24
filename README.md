# 🛡️ PlayshieldAI — Enterprise IP Risk Management

> An automated AI-powered platform designed to detect, triage, and manage Intellectual Property (IP) risks across digital landscapes. PlayshieldAI leverages Vertex AI Gemini 2.0 to provide stateful reasoning and auditable takedown workflows for unauthorized media reuse.

## 🚀 Live Production Environment

The PlayshieldAI V2 platform is live and fully operational on Google Cloud.

- **Frontend / Application:** [https://playshieldai.dev](https://playshieldai.dev)
- **Account Registration:** [https://playshieldai.dev/register](https://playshieldai.dev/register)
- **Status:** Stable Release / Production-Ready.

---

## 🏗️ Technical Architecture

PlayshieldAI is built on a resilient, serverless architecture designed for high availability and secure data isolation.

- **Frontend:** Next.js application containerized and hosted on **Google Cloud Run**.
- **Backend:** FastAPI (Python) services containerized and hosted on **Google Cloud Run**.
- **Database:** **Google Cloud SQL (PostgreSQL)**, utilizing secure Unix Sockets for internal service communication.
- **AI Engine:** **Google Vertex AI (Gemini 2.0 Flash)** for stateful case rationale generation, automated risk scoring, and metadata-rich takedown drafting.
- **Task Orchestration:** Celery with Redis for asynchronous detection pipelines and scheduled registry scans.
- **Storage:** Google Cloud Storage for media asset fingerprinting and secure artifact archival.

---

## 💻 Local Development

For engineers contributing to the core platform or running private instances.

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Environment Setup
```bash
cp .env.example .env
# Configure local secrets (PostgreSQL, Redis, Gemini API Keys)
```

### 2. Launch Services
```bash
make dev      # Starts all containers
make migrate  # Applies latest schema changes
make seed     # Optional: Seeds development data
```

### 3. Local Access
- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
- **Interactive Docs:** `http://localhost:8000/docs`

---

## 🚢 Deployment & CI/CD

Updates to the V2 platform are managed via Google Cloud SDK.

### Database Migrations
To sync the production schema after backend updates:
```bash
gcloud run jobs execute playshield-migrate --region us-central1
```

### Manual Service Deployment
```bash
# Deploy Backend
gcloud run deploy playshield-backend \
  --source ./backend \
  --region us-central1 \
  --add-cloudsql-instances <YOUR_INSTANCE_CONNECTION_NAME>

# Deploy Frontend
gcloud run deploy playshield-frontend \
  --source ./frontend \
  --region us-central1
```

### Automated CI/CD
Pushing to the `main` branch triggers an automated GitHub Action workflow that builds and deploys all service containers to their respective Google Cloud Run environments.

---

## 🛡️ Security & Compliance

PlayshieldAI implements strict **Tenant Isolation** and **Role-Based Access Control (RBAC)**.

- **Audit Logs:** Every action (AI generation, draft edit, approval) is recorded in an immutable audit trail.
- **Data Privacy:** All assets and detections are strictly scoped to the authenticated tenant.
- **Compliance:** Built with defensibility in mind, preserving original AI rationales alongside user-edited takedown letters.

For detailed security policies, refer to [docs/SECURITY.md](./docs/SECURITY.md).

---

## 📄 License

Proprietary — All rights reserved. Intellectual property of PlayshieldAI.
