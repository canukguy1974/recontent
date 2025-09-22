# AGENTS.md

## Project Overview

recontent is a SaaS platform for real estate agents to generate AI-powered listing images and marketing content. It enables agents to upload property and agent photos, use natural language prompts to compose scenes (e.g., virtual staging, agent-in-room), and generate social-ready posts with captions, facts, and CTAs. The platform is built as a monorepo with Python (FastAPI, SQLAlchemy, Alembic), Next.js (React, TypeScript, Tailwind CSS), and Google Cloud (GCS, Pub/Sub, Vertex AI, Cloud SQL).

### Architecture
- **Backend**: FastAPI (Python 3.12), Uvicorn, SQLAlchemy, Alembic, Cloud SQL Connector
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Worker**: Python, Pub/Sub, Vertex AI
- **Infra**: Terraform, Makefile automation
- **Storage**: Google Cloud Storage (GCS)
- **Other**: Stripe integration, Makefile for automation

## Setup Commands

- Install dependencies:
  - Backend: `cd services/api && pip install -r requirements.txt`
  - Frontend: `cd apps/web && npm install`
- Environment setup:
  - Copy `.env.example` to `.env` and fill in GCP/DB/Stripe variables
  - Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set to your service account JSON
- Database setup:
  - `cd services/api && alembic upgrade head`
- GCP setup:
  - Enable GCS, Pub/Sub, Vertex AI, Cloud SQL
  - Set GCS CORS: `gsutil cors set /tmp/gcs-cors.json gs://<your-bucket>`

## Development Workflow

- Start backend API: `make run-api`
- Start worker: `make run-worker`
- Start frontend: `make run-web` (or `cd apps/web && npm run dev`)
- Stop/restart: `make stop-api`, `make stop-worker`, `make stop-web`, `make restart-api`, etc.
- Hot reload: Enabled by default for API and web
- Use Makefile for all common tasks

## Testing Instructions

- Backend tests: `cd services/api && pytest`
- Frontend tests: `cd apps/web && npm test`
- E2E tests: (if present) `cd apps/web && npm run e2e`
- Coverage: `pytest --cov` (backend), `npm run coverage` (frontend)
- Test files: `*_test.py` (backend), `*.test.tsx` (frontend)

## Code Style Guidelines

- Python: Black, isort, flake8 (`make lint-api`)
- JS/TS: ESLint, Prettier (`npm run lint`)
- Naming: snake_case for Python, camelCase for JS/TS, PascalCase for React components
- File organization: Feature-based folders, colocate tests with code
- Imports: Absolute imports preferred, use barrel files for React components

## Build and Deployment

- Build frontend: `cd apps/web && npm run build`
- Build backend: (Python, no build step)
- Deploy infra: `cd infra/terraform && terraform apply`
- Deploy API/worker: Use GCP Cloud Build or custom scripts
- Environment configs: Use `.env` and GCP Secret Manager for secrets
- CI/CD: See `.github/workflows/` for GitHub Actions pipelines

## Security Considerations

- Never commit secrets; use `.env` and GCP Secret Manager
- CORS must be set for GCS buckets to allow browser uploads
- Use HTTPS in production
- API authentication/authorization: (implement as needed)

## Monorepo Instructions

- Each subproject (api, web, worker) has its own dependencies and scripts
- Use Makefile at root for cross-project automation
- Infra managed in `infra/terraform`

## Pull Request Guidelines

- Title format: `[component] Brief description`
- Required checks: `make lint-api`, `npm run lint`, `pytest`, `npm test`
- Review: At least one approval required
- Commit messages: Conventional commits preferred

## Debugging and Troubleshooting

- Common issues: CORS errors (check GCS config), ADC errors (check service account and env)
- Logs: API/worker logs in terminal, frontend logs in browser console
- Makefile: Use `make` targets for quick troubleshooting
- Performance: Use GCP monitoring and profiling tools

## Additional Notes

- For local dev, ensure all services are running and .env is configured
- See `DEV-CHEATSHEET.md` for quickstart and Makefile usage
- Update this file as workflows or architecture evolve
