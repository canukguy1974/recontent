from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.routers import health, uploads, jobs, stripe_webhooks, nlp
from packages.common.logging import get_logger
import os

app = FastAPI(title="recontent API")
log = get_logger("api")

allowed_origins = os.getenv(
	"ALLOWED_ORIGINS",
	"http://localhost:3000,http://127.0.0.1:3000",
).split(",")
allowed_origin_regex = os.getenv(
	"ALLOWED_ORIGIN_REGEX",
	r"https?://(localhost|127\.0\.0\.1)(:\\d+)?",
)
log.info(
	"CORS configured",
	extra={
		"allow_origins": [o.strip() for o in allowed_origins if o.strip()],
		"allow_origin_regex": allowed_origin_regex,
	},
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=[o.strip() for o in allowed_origins if o.strip()],
	allow_origin_regex=allowed_origin_regex,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


app.include_router(health.router, tags=["system"])
app.include_router(uploads.router, prefix="/assets", tags=["assets"])
app.include_router(jobs.router, tags=["jobs"])
app.include_router(stripe_webhooks.router, tags=["billing"])
app.include_router(nlp.router, prefix="/nlp", tags=["nlp"])
