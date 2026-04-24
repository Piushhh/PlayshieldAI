# IP Guardian — Demo Script

## Prerequisites
- Docker Compose running (`make dev`)
- Database migrated and seeded (`make migrate && make seed`)
- Browser open to http://localhost:3000

---

## Demo Flow (5 minutes)

### 1. Login (30s)
1. Navigate to http://localhost:3000
2. Login as **admin@ipguardian.dev** / **admin123**
3. Point out: JWT auth, role-based access

### 2. Dashboard Overview (45s)
1. Show stat cards: Protected Assets, Total Scans, Open Cases, High Risk
2. Point out the Detection Trend chart (Recharts area chart)
3. Show Confidence Distribution bar chart
4. Explain the scoring formula: `confidence = 0.4×hash + 0.4×embed + 0.2×risk`

### 3. Protected Assets (45s)
1. Navigate to **Protected Assets**
2. Show the 3 seeded assets
3. Click **Upload Asset** — demonstrate the upload modal
4. Explain: On upload, system extracts pHash + CLIP embeddings, rebuilds FAISS index

### 4. Cases — The Core Flow (90s)
1. Navigate to **Cases**
2. Show the filterable case list with score badges and status pills
3. Click into a high-confidence case
4. Walk through the **Score Breakdown**:
   - Hash Similarity (perceptual hash comparison)
   - Embedding Similarity (CLIP/FAISS cosine distance)
   - Risk Score (unauthorized source detection)
5. Show the **Evidence** panel with raw JSON

### 5. AI-Powered Takedown Draft (60s)
1. On the case detail page, click **"Generate Draft (Gemini)"**
2. Wait for Vertex AI Gemini to generate the draft
3. Show the generated takedown notice in the modal
4. Point out the **legal disclaimer**: "AI-generated draft; requires human legal review"
5. Click **Export** to download as .txt or .md
6. If Gemini is not configured, show the deterministic fallback template

### 6. Case Decision (30s)
1. Click **"Approve & Action"** on a case
2. Show status change from New → Actioned
3. Explain: Every action creates an immutable audit log entry

### 7. Settings — Admin Panel (30s)
1. Navigate to **Settings**
2. Show **Run Crawl** button (triggers Playwright crawler via Celery)
3. Show **Test Alerts** (Slack webhook + email)
4. Show system info

---

## Key Technical Highlights

1. **CV/ML Pipeline**: CLIP embeddings + FAISS for semantic similarity, imagehash for perceptual matching
2. **Vertex AI Gemini**: Real AI-generated takedown drafts with structured case context
3. **Async Architecture**: Celery + Redis for background crawling and scanning
4. **Immutable Audit Trail**: Every case action logged with before/after state
5. **Cloud-Ready**: Docker Compose locally, Cloud Run + Cloud SQL in production
6. **CI/CD**: GitHub Actions pipeline for automated testing and deployment

---

## Talking Points for Judges
- End-to-end automated pipeline: ingest → fingerprint → crawl → detect → case → draft
- Real Google AI integration (Vertex AI Gemini)
- Production-ready architecture (not a toy)
- Human-in-the-loop design (AI assists, humans decide)
- Full audit trail for legal compliance
