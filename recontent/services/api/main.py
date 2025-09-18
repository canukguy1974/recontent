from fastapi import FastAPI
from services.api.routers import health, uploads, jobs, stripe_webhooks
from packages.common.logging import get_logger

app = FastAPI(title="recontent API")
log = get_logger("api")

app.include_router(health.router, tags=["system"])
app.include_router(uploads.router, prefix="/assets", tags=["assets"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(stripe_webhooks.router, tags=["billing"])
