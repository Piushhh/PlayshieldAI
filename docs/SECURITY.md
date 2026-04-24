# IP Guardian — Security Documentation

## Authentication

### JWT Tokens
- **Access Token**: Short-lived (30 min default), used for API requests
- **Refresh Token**: Long-lived (7 days default), used to obtain new access tokens
- Tokens are signed with HS256 using a configurable secret key
- Token payload includes: user ID, role, type, expiration

### Password Security
- Passwords hashed using bcrypt via passlib
- No plaintext passwords stored
- Minimum password requirements should be enforced in production

## Authorization (RBAC)

### Roles
| Role | Permissions |
|------|------------|
| Admin | All operations, including crawl, scan, settings |
| Reviewer | View/action cases, generate drafts, view assets |

### Protected Endpoints
- Crawl/scan operations: Admin only
- Case viewing/actioning: Both roles
- Settings page: Admin only (frontend-enforced)

## Data Protection

### Sensitive Data
- JWT secret key: Must be ≥32 chars, stored in env vars
- Database credentials: Never logged, stored in env
- GCP service account: JSON key file, not committed to VCS
- Slack webhooks, SMTP passwords: Environment variables only

### Audit Logging
- Every case action creates an immutable audit log entry
- Logs include: actor, entity, action, before/after state, timestamp
- Audit logs are append-only — no delete/update operations

## API Security

### CORS
- Configured to allow specific origins (frontend URL)
- Credentials enabled for cookie/auth support

### Rate Limiting
- Crawler respects robots.txt
- Configurable rate limits and concurrency
- Recommended: Add API rate limiting in production (e.g., slowapi)

## Deployment Security

### Environment Variables
- Never commit `.env` files (gitignored)
- Use GCP Secret Manager in production
- Rotate JWT secret keys periodically

### Container Security
- Non-root user recommended in production Dockerfiles
- Minimal base images (python:3.11-slim, node:20-alpine)
- Regular dependency updates

## Known Limitations (MVP)
- No email verification
- No password reset flow
- No MFA/2FA
- No API rate limiting (add slowapi for production)
- CORS is permissive for development
