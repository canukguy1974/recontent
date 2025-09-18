Next.js UI placeholder.

Start later with: npx create-next-app@latest .

Use API endpoints:

GET /assets/upload-url?org_id=1
POST /jobs/composite with JSON: {
  "org_id": 1,
  "user_id": 1,
  "agent_gcs": "gs://...",
  "room_gcs": "gs://...",
  "brief": "..."
}
