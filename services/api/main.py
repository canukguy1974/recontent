from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.routers import health, uploads, jobs, stripe_webhooks
from packages.common.logging import get_logger
import os

app = FastAPI(title="recontent API")
log = get_logger("api")

allowed_origins = os.getenv(
	"ALLOWED_ORIGINS",
	"http://localhost:3000,http://127.0.0.1:3000",
).split(",")
app.add_middleware(
	CORSMiddleware,
	allow_origins=[o.strip() for o in allowed_origins if o.strip()],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health.router, tags=["system"])
app.include_router(uploads.router, prefix="/assets", tags=["assets"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(stripe_webhooks.router, tags=["billing"])
