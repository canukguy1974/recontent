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
- Local GCP creds: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
- Allowed CORS origins for API: `ALLOWED_ORIGINS` (comma-separated, default `http://localhost:3000`)
- Buckets and project are configured in `packages/common/config.py`

### Health Checks
- API: `curl http://localhost:8080/health`
- Worker: `curl http://localhost:8081/health`

### Tips
- Always match the `Content-Type` used to sign the URL on the subsequent PUT.
- If you see 501 from API routes that touch GCP, check ADC creds.
- Restart Next dev server after adding Tailwind configs or env vars so the client bundle picks them up.
