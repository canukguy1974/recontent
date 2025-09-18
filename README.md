# recontent

Python-first SaaS for real-estate image composition and virtual staging on Google Cloud.

- API: FastAPI on Cloud Run
- Worker: FastAPI push subscriber for Pub/Sub jobs
- Storage: GCS (raw, processed, published)
- AI: Vertex AI (Gemini image + text; Imagen inpaint) with MOCK mode for local dev
- DB: Cloud SQL (Postgres) via Cloud SQL Python Connector
- Deploy: Cloud Build + Terraform
- Social: stubs for Instagram, X, TikTok

## Quick start (local)

cp .env.example .env
make setup
make run-api   # http://localhost:8080/docs
make run-worker # http://localhost:8081/health

Note: Local DB uses Cloud SQL connector only on Cloud Run; for local DB dev you can point DB_* to a local Postgres and update services/api/deps.py accordingly.

## Provision infra (staging/prod)

cd infra/terraform
terraform init
terraform apply -var="project_id=recontent-472506" -var="region=us-central1"

It creates:
- Buckets (recontent-raw/processed/published)
- Pub/Sub topic 'jobs'
- Cloud SQL Postgres 15 instance 'recontent-sql' and DB 'recontent'
- Service accounts with least-privilege roles

## Deploy to Cloud Run (staging)

gcloud builds submit --config infra/cloudbuild/build-api.yaml --substitutions _TAG=v1
gcloud builds submit --config infra/cloudbuild/build-worker.yaml --substitutions _TAG=v1

## Create Pub/Sub push subscription

See infra/terraform/README.md after deploy (needs worker URL).

## Test

Open API /docs, request an upload URL, upload a JPEG via signed URL, queue a composite job, watch worker logs.

## Next

- Wire Imagen inpainting in services/worker/processors/stager.py
- Add Stripe checkout and handle webhooks in services/api/routers/stripe_webhooks.py
- Implement real social publishers in services/worker/processors/publisher.py
