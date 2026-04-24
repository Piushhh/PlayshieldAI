# PlayShield AI Production Architecture & Rules

*This document serves as the absolute source of truth for the PlayShield AI production deployment. Future development and AI agents must adhere strictly to these rules.*

## 1. Frontend Configuration
*   **Production URL**: `https://playshieldai.dev`
*   **Backend API URL**: The frontend communicates with the backend via `NEXT_PUBLIC_API_URL=https://playshield-backend-nfzz4olvxq-uc.a.run.app`.
*   **Deployment**: Handled via `gcloud run deploy playshield-frontend --source ./frontend --region us-central1`. Next.js bakes the env variables at build time, so `.env.production` **must** be present locally before deploying.

## 2. Backend CORS Handling
*   **Hardcoded Origins**: CORS is explicitly hardcoded in `backend/app/main.py`. The `allow_origins` array contains `https://playshieldai.dev`, `https://www.playshieldai.dev`, and the frontend Cloud Run URL. 
*   **Settings**: It is set to allow all credentials, methods, and headers.
*   **Rule**: **Do not attempt to revert this to environment variables** unless explicitly instructed.

## 3. Database Connection (Cloud SQL)
*   **Method**: Secure connection to Postgres via a Google Cloud Unix Socket (NOT a Public IP).
*   **Socket Path**: `/cloudsql/playshield-ai:us-central1:playshield-sql`
*   **Connection String Format**: `DATABASE_URL=postgresql+asyncpg://playshield:[PASSWORD]@/playshield?host=/cloudsql/playshield-ai:us-central1:playshield-sql`
*   **IAM**: The Cloud Run service account must have `roles/cloudsql.client` and `roles/cloudsql.admin`. The SQL Admin API must be enabled.

## 4. Strict Deployment Rules for Backend
*   **Cloud SQL Flag**: Any `gcloud` command to update backend code or environment variables **MUST** include the `--add-cloudsql-instances` flag, or the database tunnel will break and cause a `socket.gaierror`.
*   **Correct Format Example**:
    ```bash
    gcloud run services update playshield-backend \
      --region us-central1 \
      --add-cloudsql-instances playshield-ai:us-central1:playshield-sql \
      --update-env-vars "NEW_VAR=value"
    ```

## 5. Security
*   All `.env`, `.env.local`, and `.env.production` files are strictly in `.gitignore`. 
*   **Never** instruct the user to run `git add` or `git commit` if these files are exposed.
