## Dev Cheatsheet

- API: FastAPI on Uvicorn
- Worker: FastAPI app for Pub/Sub push jobs
- Web: Next.js (apps/web)

### Start Services (Local)
- API server:
  - `cd /home/canuk/projects/recontent`
  - `uvicorn services.api.main:app --reload --port 8080`
  - Docs: `http://localhost:8080/docs`

- Worker server (local push endpoint):
  - `cd /home/canuk/projects/recontent`
  - `uvicorn services.worker.main:app --reload --port 8081`
  - Health: `http://localhost:8081/health`
  - Purpose: Receives Pub/Sub push messages at `POST /pubsub` and executes jobs (e.g., composite). In production, Pub/Sub will push to the Cloud Run URL.

- Web (Next.js dev):
  - `cd /home/canuk/projects/recontent/apps/web`
  - Ensure `.env.local` contains `NEXT_PUBLIC_API_BASE_URL=http://localhost:8080`
  - `npm run dev`
  - Open `http://localhost:3000`

Shortcut targets (Makefile)
- From repo root (preferred):
  - `make run-api`     → Start API (8080)
  - `make run-worker`  → Start Worker (8081)
  - `make run-web`     → Start Web (3000)
  - `make stop-api`    → Kill API
  - `make stop-worker` → Kill Worker
  - `make stop-web`    → Kill Web
  - `make restart-api` → Stop then start API
  - `make restart-worker` → Stop then start Worker

- From apps/web (forwarders added):
  - Same targets are available; they call into the root Makefile.

### Stop/Restart Quickly (Linux)
- Stop API (uvicorn on 8080):
  ```bash
  # by process name
  pkill -f "uvicorn services.api.main:app" || true
  # or by port
  lsof -ti:8080 | xargs -r kill -9
  # or
  fuser -k 8080/tcp || true
  ```

- Stop Worker (uvicorn on 8081):
  ```bash
  pkill -f "uvicorn services.worker.main:app" || true
  lsof -ti:8081 | xargs -r kill -9
  fuser -k 8081/tcp || true
  ```

- Stop Web (Next.js dev on 3000):
  ```bash
  lsof -ti:3000 | xargs -r kill -9
  fuser -k 3000/tcp || true
  ```

- Inspect who is using a port:
  ```bash
  ss -ltnp | grep -E ':3000|:8080|:8081'
  ps aux | grep -E 'uvicorn|node|next' | grep -v grep
  ```

- Restart API/Worker after stopping:
  ```bash
  # API
  uvicorn services.api.main:app --reload --port 8080
  # Worker
  uvicorn services.worker.main:app --reload --port 8081
  ```

### GCS Signed URL Flow
- Get signed PUT URL:
  - `curl "http://localhost:8080/assets/upload-url?org_id=1&content_type=image%2Fjpeg"`
- Use it to upload (must match Content-Type):
  - `curl -i -X PUT -H "Content-Type: image/jpeg" --data-binary @sample.jpg "$URL"`
- Get signed GET URL for viewing:
  - `curl "http://localhost:8080/assets/view-url?gcs_uri=gs://recontent-raw/org_1/FILE.jpg"`

### Queue a Composite Job
- API publishes to Pub/Sub `jobs` topic:
  - `POST /jobs/composite` with body:
```
{
  "org_id": 1,
  "user_id": 123,
  "agent_gcs": "gs://recontent-raw/org_1/agent.jpg",
  "room_gcs": "gs://recontent-raw/org_1/room.jpg",
  "brief": "stage as modern living room"
}
```
- Worker handles `type: composite` messages at `/pubsub` and calls processors to generate outputs.

### Environment
- Local GCP creds (ADC):
  - Put your service account JSON somewhere safe, e.g., `~/keys/recontent-sa.json`.
  - Either export it in your shell:
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS=~/keys/recontent-sa.json
    ```
    or set it in `.env` at repo root (Make targets auto-load `.env`):
    ```bash
    GOOGLE_APPLICATION_CREDENTIALS=~/keys/recontent-sa.json
    ```
  - Verify: `python -c "from google.cloud import storage; storage.Client(); print('OK')"`
- Allowed CORS origins for API: `ALLOWED_ORIGINS` (comma-separated, default `http://localhost:3000`)
- Buckets and project are configured in `packages/common/config.py`

### Health Checks
- API: `curl http://localhost:8080/health`
- Worker: `curl http://localhost:8081/health`

### Tips
- Always match the `Content-Type` used to sign the URL on the subsequent PUT.
- If you see 501 from API routes that touch GCP, check ADC creds.
- Restart Next dev server after adding Tailwind configs or env vars so the client bundle picks them up.
