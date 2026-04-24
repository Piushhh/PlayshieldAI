# PlayshieldAI — V2 Production Demo Script

## Prerequisites
- High-speed internet access.
- Authenticated account on [https://playshieldai.dev](https://playshieldai.dev).
- (Optional) Local instance running via `make dev` for architecture walkthroughs.

---

## 🎬 The Demo Flow (6 Minutes)

### 1. The Entry Point (30s)
1. Navigate to [https://playshieldai.dev](https://playshieldai.dev).
2. Login with your tenant credentials.
3. **Talking Point**: "PlayshieldAI is an enterprise IP risk platform. We are now looking at a live production instance hosted on Google Cloud Run."

### 2. The Control Room: Dashboard (60s)
1. Point out the **Brutalist Editorial UI**: Bordered panels, high-density charts, and accent tiles.
2. Highlight **Global AI Insights**: Show the Gemini-generated summary cards that triage risk across the entire registry.
3. **Talking Point**: "Our dashboard doesn't just show numbers; it uses Vertex AI Gemini to summarize why specific sources are surfacing as high-risk."

### 3. Protection Registry: Asset Management (60s)
1. Navigate to **Registry**.
2. Click into an asset card.
3. Show the **Gemini rationale** explaining *why* that specific asset is being monitored (e.g., high-value kinetic media).
4. **Talking Point**: "Every asset in our registry is fingerprinted using CLIP and imagehash, then analyzed by Gemini to establish its protection rationale."

### 4. The Core Flow: Case Triage (120s)
1. Navigate to **Cases**.
2. Select a high-confidence case.
3. **Why This Match?**: Point to the `GeminiCallout` component. Explain that Gemini 2.0 analyzed the pixel-level similarity alongside source risk.
4. **Evidence Panel**: Briefly show the raw signal data (Hash, Embed, Risk scores).
5. **Talking Point**: "This is the human-in-the-loop review. The AI provide the rationale, but the analyst makes the final decision."

### 5. Auditable Takedown Drafting (60s)
1. Show the **Editable Draft** panel.
2. Make a small edit to the draft letter.
3. Click **Save Edits** — point out that this creates a new auditable revision.
4. Click **Mark as Reviewed** — show the stamp badge appearing.
5. **Talking Point**: "We preserve the original AI output while allowing analysts to refine the letter. Every revision is logged for legal compliance."

### 6. The Decision & Audit Trail (30s)
1. Click **Approve**.
2. Scroll to the **Audit Trail** at the bottom of the page.
3. Show the event logs: "Draft Edited", "Draft Reviewed", "Case Approved".
4. **Talking Point**: "Our audit trail is immutable. In a legal dispute, we can prove exactly how the AI reasoned and how the human analyst refined the action."

---

## 🏗️ Technical Highlights for Judges

1. **Production Infrastructure**: Google Cloud Run + Cloud SQL + Secret Manager.
2. **Stateful AI Integration**: Vertex AI Gemini 2.0 Flash with deterministic fallback safety.
3. **Hybrid CV Pipeline**: FAISS-powered CLIP embeddings for semantic search + perceptual hashing for exact match.
4. **Editorial UI**: Responsive Tailwind system designed for complex, multi-panel data analysis.
5. **Enterprise Compliance**: Full tenant isolation and immutable action logging.
