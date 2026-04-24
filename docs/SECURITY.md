# PlayshieldAI — Security & Compliance Architecture

## Identity & Access Management (IAM)

### Authentication
- **JWT Implementation**: Stateless authentication using secure JSON Web Tokens.
  - **Access Tokens**: Short-lived (30 minutes) for active request authorization.
  - **Refresh Tokens**: Long-lived (7 days) for session persistence.
- **Credential Safety**: All passwords are encrypted using **bcrypt** (passlib implementation) with unique salts. No plaintext credentials are ever stored or logged.
- **Workflows**: Production-grade flows for user registration, email verification, and secure password recovery are fully implemented.

### Role-Based Access Control (RBAC)
PlayshieldAI enforces granular permissions based on organizational roles:
- **Admin**: Full administrative control over registry scans, global settings, and user management.
- **Analyst/Reviewer**: Capability to triage cases, review Gemini rationales, and approve/reject takedown drafts.
- **Tenant Isolation**: All data objects (Assets, Cases, Detections, Notifications) are strictly scoped to the tenant ID of the authenticated user.

---

## Data Protection & Privacy

### Infrastructure Security
- **Cloud SQL Connectivity**: Internal backend services communicate with the PostgreSQL database via **Unix Sockets** or secure IAM-proxy connections, ensuring no database ports are exposed to the public internet.
- **Secret Management**: Production secrets (JWT keys, API credentials) are managed via **Google Cloud Secret Manager** or encrypted environment variables in Cloud Run.
- **Media Archival**: User-uploaded assets are stored in private **Google Cloud Storage** buckets with signed URL access for internal processing only.

### Immutable Audit Trail
To ensure legal defensibility for IP takedowns, the platform maintains an append-only audit log:
- **Event Capture**: Every AI generation attempt, draft revision, mark-as-reviewed, and final decision is recorded.
- **Metadata**: Logs include the actor, timestamp, entity delta (before/after states), and Gemini model/provider metadata.

---

## API & Network Security

### Transport Security
- **TLS 1.3**: All traffic to `*.playshieldai.dev` is encrypted in transit via TLS 1.3.
- **CORS Policy**: Configured with a strict allow-list limited to the production frontend domain.

### Rate Limiting & Safety
- **Detection Crawler**: Our discovery engine respects `robots.txt` and implements intelligent back-off strategies.
- **AI Safety**: Gemini rationale generation includes safety filters to ensure compliance with Google Vertex AI responsible AI guidelines.

---

## Compliance & Auditing

PlayshieldAI is designed to provide a verifiable chain of custody for intellectual property enforcement. By preserving original AI rationales alongside human-in-the-loop edits, we provide the transparency required for legal compliance in IP management.
