#!/usr/bin/env python3
import io
import textwrap
import zipfile


PROJECT_ID = "recontent-472506"
REGION = "us-central1"
INSTANCE_NAME = "recontent-sql"
INSTANCE_CONN = f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}"


files: dict[str, str] = {}


def add(path: str, content: str):
    files[path] = textwrap.dedent(content).lstrip("\n")


# ---------- top-level ----------
add(
    ".gitignore",
    """
    __pycache__/
    *.pyc
    .env
    .venv/
    node_modules/
    .tfstate
    .terraform/
    .DS_Store
    """,
)

add(
    ".env.example",
    f"""
    # Google Cloud
    GOOGLE_CLOUD_PROJECT={PROJECT_ID}
    GOOGLE_CLOUD_LOCATION={REGION}
    GOOGLE_APPLICATION_CREDENTIALS=

    # Storage buckets
    GCS_BUCKET_RAW=recontent-raw
    GCS_BUCKET_PROCESSED=recontent-processed
    GCS_BUCKET_PUBLISHED=recontent-published

    # Pub/Sub
    PUBSUB_TOPIC_JOBS=jobs
    PUBSUB_SUBSCRIPTION_JOBS=jobs-sub

    # Database (Cloud SQL via connector)
    DB_INSTANCE_CONN_NAME={INSTANCE_CONN}
    DB_NAME=recontent
    DB_USER=recontent
    DB_PASSWORD=
    # will be output by Terraform; copy into Cloud Run env for staging/prod

    # Stripe
    STRIPE_SECRET=
    STRIPE_WEBHOOK_SECRET=

    # Social (fill when integrating)
    IG_APP_ID=
    IG_APP_SECRET=
    IG_ACCESS_TOKEN=
    TWITTER_BEARER=
    TWITTER_API_KEY=
    TWITTER_API_SECRET=
    TIKTOK_CLIENT_KEY=
    TIKTOK_CLIENT_SECRET=

    # AI models
    AI_PROVIDER=vertex
    GEMINI_IMAGE_MODEL_ID=gemini-2.5-flash-image-preview
    GEMINI_TEXT_MODEL_ID=gemini-2.5-flash
    IMAGEN_MODEL_ID=imagen-3.0

    # Local dev
    MOCK_AI=1
    LOG_LEVEL=INFO
    """,
)

add(
    "requirements.txt",
    """
    fastapi==0.115.0
    uvicorn[standard]==0.30.6
    pydantic==2.9.2
    SQLAlchemy==2.0.35
    alembic==1.13.2
    psycopg[binary]==3.2.1
    pg8000==1.31.2
    cloud-sql-python-connector==1.9.1
    python-dotenv==1.0.1
    stripe==9.11.0
    google-cloud-storage==2.18.2
    google-cloud-pubsub==2.22.0
    google-cloud-secret-manager==2.20.2
    google-cloud-logging==3.11.2
    google-cloud-aiplatform==1.65.0
    Pillow==10.4.0
    tenacity==8.5.0
    """,
)

add(
    "Makefile",
    """
    .PHONY: setup run-api run-worker db-upgrade fmt

    setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

    run-api:
	. .venv/bin/activate && uvicorn services.api.main:app --reload --port 8080

    run-worker:
	. .venv/bin/activate && uvicorn services.worker.main:app --reload --port 8081

    db-upgrade:
	alembic upgrade head
    """,
)

add(
    "README.md",
    f"""
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
    terraform apply -var="project_id={PROJECT_ID}" -var="region={REGION}"

    It creates:
    - Buckets (recontent-raw/processed/published)
    - Pub/Sub topic 'jobs'
    - Cloud SQL Postgres 15 instance '{INSTANCE_NAME}' and DB 'recontent'
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
    """,
)

# ---------- db ----------
add(
    "db/alembic.ini",
    """
    [alembic]
    script_location = db/migrations
    sqlalchemy.url = postgresql+pg8000://placeholder/placeholder@localhost/recontent
    """,
)

add(
    "db/models.py",
    """
    from datetime import datetime
    from sqlalchemy import (
        Column,
        Integer,
        String,
        DateTime,
        Enum,
        Boolean,
        ForeignKey,
        JSON,
        BigInteger,
    )
    from sqlalchemy.orm import declarative_base, relationship
    import enum

    Base = declarative_base()

    class Plan(enum.Enum):
        BASIC = "basic"
        PRO = "pro"
        PREMIUM = "premium"

    class AssetKind(enum.Enum):
        HEADSHOT = "headshot"
        LISTING = "listing"
        MASK = "mask"
        OUTPUT = "output"

    class JobType(enum.Enum):
        COMPOSITE = "composite"
        STAGING = "staging"
        CAPTION = "caption"
        PUBLISH = "publish"

    class JobStatus(enum.Enum):
        CREATED = "created"
        QUEUED = "queued"
        RENDERING = "rendering"
        FAILED = "failed"
        COMPLETE = "complete"

    class Org(Base):
        __tablename__ = "orgs"
        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        plan = Column(Enum(Plan), nullable=False)
        weekly_limit = Column(Integer, nullable=False, default=2)
        status = Column(String, default="active")
        created_at = Column(DateTime, default=datetime.utcnow)

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
        email = Column(String, unique=True, nullable=False)
        role = Column(String, default="creator")
        status = Column(String, default="active")
        created_at = Column(DateTime, default=datetime.utcnow)
        org = relationship("Org")

    class Asset(Base):
        __tablename__ = "assets"
        id = Column(Integer, primary_key=True)
        org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
        owner_user_id = Column(Integer, ForeignKey("users.id"))
        kind = Column(Enum(AssetKind), nullable=False)
        gcs_uri = Column(String, nullable=False)
        width = Column(Integer)
        height = Column(Integer)
        checksum = Column(String)
        staged = Column(Boolean, default=False)
        contains_people = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)

    class Job(Base):
        __tablename__ = "jobs"
        id = Column(BigInteger, primary_key=True)
        org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
        user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
        type = Column(Enum(JobType), nullable=False)
        input_asset_ids = Column(JSON, default=list)
        status = Column(Enum(JobStatus), default=JobStatus.CREATED)
        model = Column(String)
        params = Column(JSON, default=dict)
        output_asset_ids = Column(JSON, default=list)
        error = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)

    class Post(Base):
        __tablename__ = "posts"
        id = Column(Integer, primary_key=True)
        org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
        platform = Column(String, nullable=False)
        caption = Column(String)
        image_asset_ids = Column(JSON, default=list)
        scheduled_for = Column(DateTime)
        published_at = Column(DateTime)
        external_id = Column(String)
        status = Column(String, default="draft")

    class Quota(Base):
        __tablename__ = "quotas"
        id = Column(Integer, primary_key=True)
        org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
        window_start = Column(DateTime, nullable=False)
        window_end = Column(DateTime, nullable=False)
        weekly_limit = Column(Integer, nullable=False, default=2)
        used_count = Column(Integer, default=0)
    """,
)

add(
    "db/migrations/versions/0001_initial.py",
    '''
    from alembic import op
    import sqlalchemy as sa

    revision = "0001_initial"
    down_revision = None
    branch_labels = None
    depends_on = None

    def upgrade():
        op.execute("""
        CREATE TYPE plan AS ENUM ('basic','pro','premium');
        CREATE TYPE assetkind AS ENUM ('headshot','listing','mask','output');
        CREATE TYPE jobtype AS ENUM ('composite','staging','caption','publish');
        CREATE TYPE jobstatus AS ENUM ('created','queued','rendering','failed','complete');
        """)

        op.create_table(
            "orgs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String, nullable=False),
            sa.Column("plan", sa.Enum(name="plan"), nullable=False),
            sa.Column("weekly_limit", sa.Integer, nullable=False, server_default="2"),
            sa.Column("status", sa.String, server_default="active"),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        )

        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
            sa.Column("email", sa.String, unique=True, nullable=False),
            sa.Column("role", sa.String, server_default="creator"),
            sa.Column("status", sa.String, server_default="active"),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        )

        op.create_table(
            "assets",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
            sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("users.id")),
            sa.Column("kind", sa.Enum(name="assetkind"), nullable=False),
            sa.Column("gcs_uri", sa.String, nullable=False),
            sa.Column("width", sa.Integer),
            sa.Column("height", sa.Integer),
            sa.Column("checksum", sa.String),
            sa.Column("staged", sa.Boolean, server_default="false"),
            sa.Column("contains_people", sa.Boolean, server_default="false"),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        )

        op.create_table(
            "jobs",
            sa.Column("id", sa.BigInteger, primary_key=True),
            sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("type", sa.Enum(name="jobtype"), nullable=False),
            sa.Column("input_asset_ids", sa.JSON, server_default="[]"),
            sa.Column("status", sa.Enum(name="jobstatus"), server_default="created"),
            sa.Column("model", sa.String),
            sa.Column("params", sa.JSON, server_default="{}"),
            sa.Column("output_asset_ids", sa.JSON, server_default="[]"),
            sa.Column("error", sa.String),
            sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()")),
        )

        op.create_table(
            "posts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
            sa.Column("platform", sa.String, nullable=False),
            sa.Column("caption", sa.String),
            sa.Column("image_asset_ids", sa.JSON, server_default="[]"),
            sa.Column("scheduled_for", sa.DateTime),
            sa.Column("published_at", sa.DateTime),
            sa.Column("external_id", sa.String),
            sa.Column("status", sa.String, server_default="draft"),
        )

        op.create_table(
            "quotas",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("org_id", sa.Integer, sa.ForeignKey("orgs.id"), nullable=False),
            sa.Column("window_start", sa.DateTime, nullable=False),
            sa.Column("window_end", sa.DateTime, nullable=False),
            sa.Column("weekly_limit", sa.Integer, nullable=False, server_default="2"),
            sa.Column("used_count", sa.Integer, server_default="0"),
        )

    def downgrade():
        op.drop_table("quotas")
        op.drop_table("posts")
        op.drop_table("jobs")
        op.drop_table("assets")
        op.drop_table("users")
        op.drop_table("orgs")
        op.execute("DROP TYPE jobstatus; DROP TYPE jobtype; DROP TYPE assetkind; DROP TYPE plan;")
    ''',
)

# ---------- common package ----------
add("packages/common/__init__.py", "")

add(
    "packages/common/config.py",
    f"""
    import os

    def env(name: str, default: str | None = None, cast=str):
        val = os.getenv(name, default)
        if val is None:
            raise RuntimeError(f"Missing env var: {{name}}")
        return cast(val) if cast is not None and val is not None else val

    GOOGLE_CLOUD_PROJECT = env("GOOGLE_CLOUD_PROJECT", "{PROJECT_ID}")
    GOOGLE_CLOUD_LOCATION = env("GOOGLE_CLOUD_LOCATION", "{REGION}")
    BUCKET_RAW = env("GCS_BUCKET_RAW", "recontent-raw")
    BUCKET_PROCESSED = env("GCS_BUCKET_PROCESSED", "recontent-processed")
    BUCKET_PUBLISHED = env("GCS_BUCKET_PUBLISHED", "recontent-published")
    PUBSUB_TOPIC_JOBS = env("PUBSUB_TOPIC_JOBS", "jobs")
    MOCK_AI = env("MOCK_AI", "1") == "1"
    GEMINI_IMAGE_MODEL_ID = env("GEMINI_IMAGE_MODEL_ID", "gemini-2.5-flash-image-preview")
    GEMINI_TEXT_MODEL_ID = env("GEMINI_TEXT_MODEL_ID", "gemini-2.5-flash")
    IMAGEN_MODEL_ID = env("IMAGEN_MODEL_ID", "imagen-3.0")

    DB_INSTANCE_CONN_NAME = env("DB_INSTANCE_CONN_NAME", "{INSTANCE_CONN}")
    DB_NAME = env("DB_NAME", "recontent")
    DB_USER = env("DB_USER", "recontent")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")  # allow empty in local MOCK
    """,
)

add(
    "packages/common/logging.py",
    """
    import logging
    import os

    def get_logger(name: str):
        lvl = os.getenv("LOG_LEVEL", "INFO").upper()
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            handler.setFormatter(fmt)
            logger.addHandler(handler)
        logger.setLevel(lvl)
        return logger
    """,
)

add(
    "packages/common/gcs.py",
    """
    from google.cloud import storage

    _client = None

    def client():
        global _client
        if not _client:
            _client = storage.Client()
        return _client

    def download_bytes(gcs_uri: str) -> bytes:
        assert gcs_uri.startswith("gs://")
        _, bucket, *path = gcs_uri.replace("gs://", "").split("/")
        blob = client().bucket(bucket).blob("/".join(path))
        return blob.download_as_bytes()

    def upload_bytes(gcs_uri: str, data: bytes, content_type="image/jpeg"):
        _, bucket, *path = gcs_uri.replace("gs://", "").split("/")
        blob = client().bucket(bucket).blob("/".join(path))
        blob.upload_from_string(data, content_type=content_type)
        return gcs_uri
    """,
)

add(
    "packages/common/crops.py",
    """
    from PIL import Image, ImageOps
    from io import BytesIO

    SIZES = [(1080, 1080), (1080, 1350), (1080, 1920)]

    def social_crops(img_bytes: bytes) -> list[bytes]:
        im = Image.open(BytesIO(img_bytes)).convert("RGB")
        outs = []
        for w, h in SIZES:
            c = ImageOps.fit(im, (w, h), method=Image.Resampling.LANCZOS)
            b = BytesIO()
            c.save(b, format="JPEG", quality=92)
            outs.append(b.getvalue())
        return outs
    """,
)

add(
    "packages/common/schemas.py",
    """
    from pydantic import BaseModel, Field

    class CompositeJob(BaseModel):
        org_id: int
        user_id: int
        agent_gcs: str
        room_gcs: str
        brief: str = Field(default="")
    """,
)

add(
    "packages/common/pubsub.py",
    """
    import base64
    import json
    from fastapi import Request, HTTPException

    async def parse_push(request: Request) -> dict:
        payload = await request.json()
        try:
            data = payload["message"]["data"]
            return json.loads(base64.b64decode(data).decode("utf-8"))
        except Exception as e:
            raise HTTPException(400, f"Bad Pub/Sub payload: {e}")
    """,
)

# ---------- API ----------
add(
    "services/api/Dockerfile",
    """
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . /app
    EXPOSE 8080
    CMD ["uvicorn","services.api.main:app","--host","0.0.0.0","--port","8080"]
    """,
)

add("services/api/__init__.py", "")

add(
    "services/api/deps.py",
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from google.cloud.sql.connector import Connector, IPTypes
    from packages.common.config import DB_INSTANCE_CONN_NAME, DB_USER, DB_PASSWORD, DB_NAME

    connector = Connector()

    def getconn():
        conn = connector.connect(
            DB_INSTANCE_CONN_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            ip_type=IPTypes.PUBLIC,
        )
        return conn

    engine = create_engine("postgresql+pg8000://", creator=getconn, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    """,
)

add(
    "services/api/routers/health.py",
    """
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/health")
    def health():
        return {"ok": True}
    """,
)

add(
    "services/api/routers/uploads.py",
    """
    from fastapi import APIRouter, Query
    from google.cloud import storage
    import uuid
    from packages.common.config import BUCKET_RAW

    router = APIRouter()
    client = storage.Client()

    @router.get("/upload-url")
    def upload_url(org_id: int, content_type: str = Query("image/jpeg")):
        blob_name = f"org_{org_id}/{uuid.uuid4()}.jpg"
        blob = client.bucket(BUCKET_RAW).blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=600,
            method="PUT",
            content_type=content_type,
        )
        return {"url": url, "gcs_uri": f"gs://{BUCKET_RAW}/{blob_name}"}
    """,
)

add(
    "services/api/routers/jobs.py",
    """
    from fastapi import APIRouter
    from google.cloud import pubsub_v1
    import json
    from packages.common.config import PUBSUB_TOPIC_JOBS, GOOGLE_CLOUD_PROJECT
    from packages.common.schemas import CompositeJob

    router = APIRouter()
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(GOOGLE_CLOUD_PROJECT, PUBSUB_TOPIC_JOBS)

    @router.post("/jobs/composite")
    def jobs_composite(job: CompositeJob):
        publisher.publish(topic_path, data=json.dumps(job.model_dump()).encode("utf-8"))
        return {"status": "queued"}
    """,
)

add(
    "services/api/routers/stripe_webhooks.py",
    """
    from fastapi import APIRouter, Request, HTTPException
    import os, stripe

    router = APIRouter()
    stripe.api_key = os.getenv("STRIPE_SECRET", "")

    @router.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("Stripe-Signature", ".")
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        try:
            stripe.Webhook.construct_event(payload, sig, endpoint_secret)
        except Exception as e:
            raise HTTPException(400, f"Invalid webhook: {e}")
        # TODO: handle checkout.session.completed, subscription.updated, invoice.payment_failed
        return {"received": True}
    """,
)

add(
    "services/api/main.py",
    """
    from fastapi import FastAPI
    from services.api.routers import health, uploads, jobs, stripe_webhooks
    from packages.common.logging import get_logger

    app = FastAPI(title="recontent API")
    log = get_logger("api")

    app.include_router(health.router, tags=["system"])
    app.include_router(uploads.router, prefix="/assets", tags=["assets"])
    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(stripe_webhooks.router, tags=["billing"])
    """,
)

# ---------- Worker ----------
add(
    "services/worker/Dockerfile",
    """
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . /app
    EXPOSE 8081
    CMD ["uvicorn","services.worker.main:app","--host","0.0.0.0","--port","8081"]
    """,
)

add("services/worker/__init__.py", "")

add(
    "services/worker/main.py",
    """
    from fastapi import FastAPI, Request
    from packages.common.pubsub import parse_push
    from packages.common.logging import get_logger
    from services.worker.processors import compositor, captioner

    app = FastAPI(title="recontent Worker")
    log = get_logger("worker")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/pubsub")
    async def pubsub_push(request: Request):
        msg = await parse_push(request)
        typ = msg.get("type")
        log.info(f"Received job type={typ}")
        if typ == "composite":
            uris = compositor.run(msg)
            return {"status": "ok", "outputs": uris}
        return {"status": "ignored", "type": typ}
    """,
)

add("services/worker/ai/__init__.py", "")

add(
    "services/worker/ai/mock_client.py",
    """
    from PIL import Image, ImageDraw
    from io import BytesIO

    class MockAIClient:
        def composite(self, agent_bytes: bytes, room_bytes: bytes, brief: str) -> list[bytes]:
            img = Image.open(BytesIO(room_bytes)).convert("RGB")
            out = []
            for i in range(3):
                im = img.copy()
                draw = ImageDraw.Draw(im)
                draw.rectangle([(10, 10), (360, 80)], fill=(0, 0, 0, 160))
                draw.text((20, 25), f"MOCK COMPOSITE #{i+1}", fill=(255, 255, 255))
                b = BytesIO()
                im.save(b, format="JPEG", quality=92)
                out.append(b.getvalue())
            return out

        def caption(self, brief: str, staged: bool) -> str:
            disclosure = " One or more photos are virtually staged." if staged else ""
            return (brief[:120] + " — #ForSale #RealEstate #Home" + disclosure).strip()
    """,
)

add(
    "services/worker/ai/vertex_client.py",
    """
    from packages.common.config import (
        GEMINI_IMAGE_MODEL_ID,
        GEMINI_TEXT_MODEL_ID,
        GOOGLE_CLOUD_PROJECT,
        GOOGLE_CLOUD_LOCATION,
    )
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel, Part

    class VertexAIClient:
        def __init__(self):
            vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
            self.image_model = GenerativeModel(GEMINI_IMAGE_MODEL_ID)
            self.text_model = GenerativeModel(GEMINI_TEXT_MODEL_ID)

        def composite(self, agent_bytes: bytes, room_bytes: bytes, brief: str) -> list[bytes]:
            system = (
                "You are a professional real-estate retoucher for Ontario listings. "
                "Make realistic, non-deceptive edits only."
            )
            instruction = (
                "Composite the person from the first image into the second (interior/exterior). "
                "Preserve identity/clothing; match perspective and lighting; add soft plausible shadow. "
                "Do not alter permanent fixtures, windows, or views. No text/logos. Return 3 options."
            )
            resp = self.image_model.generate_content(
                [
                    system,
                    f"Context: {brief}",
                    Part.from_data(agent_bytes, mime_type="image/jpeg"),
                    Part.from_data(room_bytes, mime_type="image/jpeg"),
                    instruction,
                ],
                generation_config={"candidate_count": 3, "response_modalities": ["TEXT", "IMAGE"]},
            )
            images = []
            for cand in getattr(resp, "candidates", []):
                for part in getattr(cand.content, "parts", []):
                    if getattr(part, "inline_data", None):
                        images.append(part.inline_data.data)
            return images

        def caption(self, brief: str, staged: bool) -> str:
            disclosure = " One or more photos are virtually staged." if staged else ""
            resp = self.text_model.generate_content(
                f"Write a neutral real-estate caption (180–220 chars) with 3–5 neutral hashtags for: {brief}.{disclosure}"
            )
            return resp.text.strip()
    """,
)

add("services/worker/processors/__init__.py", "")

add(
    "services/worker/processors/compositor.py",
    """
    from packages.common.gcs import download_bytes, upload_bytes
    from packages.common.crops import social_crops
    from services.worker.ai.mock_client import MockAIClient
    from services.worker.ai.vertex_client import VertexAIClient
    from packages.common.config import MOCK_AI, BUCKET_PROCESSED
    from uuid import uuid4

    _ai = MockAIClient() if MOCK_AI else VertexAIClient()

    def run(job: dict) -> list[str]:
        agent = download_bytes(job["agent_gcs"])
        room = download_bytes(job["room_gcs"])
        variants = _ai.composite(agent, room, job.get("brief", ""))
        uris = []
        for img_bytes in variants:
            for crop_bytes in social_crops(img_bytes):
                out_uri = f"gs://{BUCKET_PROCESSED}/org{job['org_id']}/{uuid4()}.jpg"
                upload_bytes(out_uri, crop_bytes, content_type="image/jpeg")
                uris.append(out_uri)
        return uris
    """,
)

add(
    "services/worker/processors/captioner.py",
    """
    from services.worker.ai.mock_client import MockAIClient
    from services.worker.ai.vertex_client import VertexAIClient
    from packages.common.config import MOCK_AI

    _ai = MockAIClient() if MOCK_AI else VertexAIClient()

    def run(brief: str, staged: bool) -> str:
        return _ai.caption(brief, staged)
    """,
)

add(
    "services/worker/processors/stager.py",
    """
    # Placeholder for Imagen inpainting path (mask insertion) — implement when masks are uploaded
    def run(job: dict) -> list[str]:
        return []
    """,
)

add(
    "services/worker/processors/publisher.py",
    """
    # Stubs; fill with real API calls for IG/FB/LinkedIn/X/TikTok
    def run(post: dict) -> dict:
        return {"status": "published", "external_id": "stub-123"}
    """,
)

# ---------- AI prompts ----------
add(
    "ai/prompts/image-composer/instructions.md",
    """
    You are a professional real-estate retoucher. Ontario/MLS rules apply: realistic, non-deceptive edits only.
    Inputs: [Agent.jpg], [Target.jpg], optional placement hint/mask.
    Do: preserve identity/clothing; match perspective/lighting; add soft plausible shadows.
    Don’t: alter permanent fixtures, windows, or views; add text/logos.
    Output: 3 candidates; we will crop to 1:1 (1080), 4:5 (1080×1350), 9:16 (1080×1920).
    """,
)

add(
    "ai/prompts/virtual-staging/instructions.md",
    """
    Use the provided mask as the placement zone. Do not modify architecture. Style: Scandinavian 84" sofa, walnut coffee table, low-pile rug; neutral color; contact shadows. Return 3 variants.
    """,
)

add(
    "ai/prompts/captioner/instructions.md",
    """
    Write a neutral, professional caption (180–220 chars) with 3–5 neutral hashtags.
    If staged=true, append: “One or more photos are virtually staged.”
    """,
)

add(
    "ai/prompts/compliance/instructions.md",
    """
    Validate per org policy: disclosure present if staged; consent present if people appear; MLS profile rules (people allowed? non-staged companion?);
    IG JPEG + aspect ratios. Return pass/fail and fixes.
    """,
)

add(
    "ai/prompts/publisher/instructions.md",
    """
    Check org weekly quota and platform limits (e.g., Instagram content_publishing_limit). Publish, store external IDs, handle retries with backoff, reschedule on rate-limit.
    """,
)

# ---------- Terraform ----------
add(
    "infra/terraform/variables.tf",
    """
    variable "project_id" { type = string }
    variable "region" { type = string default = "us-central1" }
    variable "raw_bucket" { type = string default = "recontent-raw" }
    variable "processed_bucket" { type = string default = "recontent-processed" }
    variable "published_bucket" { type = string default = "recontent-published" }
    variable "sql_instance_name" { type = string default = "recontent-sql" }
    variable "db_name" { type = string default = "recontent" }
    variable "db_user" { type = string default = "recontent" }
    variable "db_tier" { type = string default = "db-custom-1-3840" } # 1 vCPU, 3.75GB
    """,
)

add(
    "infra/terraform/main.tf",
    f"""
    terraform {{
      required_providers {{
        google = {{ source = "hashicorp/google" version = "> 5.40" }}
        random = {{ source = "hashicorp/random" version = "> 3.6" }}
      }}
    }}

    provider "google" {{ project = var.project_id region = var.region }}

    resource "google_storage_bucket" "raw" {{
      name = var.raw_bucket
      location = var.region
      uniform_bucket_level_access = true
      lifecycle_rule {{
        action {{ type = "Delete" }}
        condition {{ age = 60 }}
      }}
    }}

    resource "google_storage_bucket" "processed" {{
      name = var.processed_bucket
      location = var.region
      uniform_bucket_level_access = true
    }}

    resource "google_storage_bucket" "published" {{
      name = var.published_bucket
      location = var.region
      uniform_bucket_level_access = true
    }}

    resource "google_pubsub_topic" "jobs" {{ name = "jobs" }}

    # Service Accounts
    resource "google_service_account" "api" {{
      account_id   = "recontent-api-sa"
      display_name = "recontent API service account"
    }}

    resource "google_service_account" "worker" {{
      account_id   = "recontent-worker-sa"
      display_name = "recontent Worker service account"
    }}

    # IAM (minimal; tighten in production)
    resource "google_project_iam_member" "api_storage" {{
      project = var.project_id
      role    = "roles/storage.objectAdmin"
      member  = "serviceAccount:${{google_service_account.api.email}}"
    }}

    resource "google_project_iam_member" "worker_storage" {{
      project = var.project_id
      role    = "roles/storage.objectAdmin"
      member  = "serviceAccount:${{google_service_account.worker.email}}"
    }}

    resource "google_project_iam_member" "api_pubsub_pub" {{
      project = var.project_id
      role    = "roles/pubsub.publisher"
      member  = "serviceAccount:${{google_service_account.api.email}}"
    }}

    resource "google_project_iam_member" "worker_pubsub_sub" {{
      project = var.project_id
      role    = "roles/pubsub.subscriber"
      member  = "serviceAccount:${{google_service_account.worker.email}}"
    }}

    resource "google_project_iam_member" "vertex_api" {{
      project = var.project_id
      role    = "roles/aiplatform.user"
      member  = "serviceAccount:${{google_service_account.worker.email}}"
    }}

    resource "google_project_iam_member" "cloudsql_client_api" {{
      project = var.project_id
      role    = "roles/cloudsql.client"
      member  = "serviceAccount:${{google_service_account.api.email}}"
    }}

    # Cloud SQL (Postgres 15)
    resource "google_sql_database_instance" "pg" {{
      name             = var.sql_instance_name
      database_version = "POSTGRES_15"
      region           = var.region
      deletion_protection = false

      settings {{
        tier = var.db_tier
        availability_type = "ZONAL"
        backup_configuration {{ enabled = true }}
        ip_configuration {{
          # Using the connector from Cloud Run; public IP is fine with connector
          ipv4_enabled = true
        }}
      }}
    }}

    resource "google_sql_database" "db" {{
      name     = var.db_name
      instance = google_sql_database_instance.pg.name
    }}

    resource "random_password" "db_password" {{ length = 20 special = true }}

    resource "google_sql_user" "dbuser" {{
      name     = var.db_user
      instance = google_sql_database_instance.pg.name
      password = random_password.db_password.result
    }}

    output "instance_connection_name" {{ value = google_sql_database_instance.pg.connection_name }}
    output "db_user" {{ value = google_sql_user.dbuser.name }}
    output "db_password" {{ value = random_password.db_password.result sensitive = true }}
    output "pubsub_topic" {{ value = google_pubsub_topic.jobs.name }}
    output "buckets" {{
      value = {{
        raw       = google_storage_bucket.raw.name
        processed = google_storage_bucket.processed.name
        published = google_storage_bucket.published.name
      }}
    }}
    """,
)

add(
    "infra/terraform/outputs.tf",
    """
    output "notes" {
      value = "After deploying Cloud Run worker, create a Pub/Sub push subscription to https://<worker-url>/pubsub using 'gcloud pubsub subscriptions create jobs-sub --topic=jobs --push-endpoint=... --push-auth-service-account=<worker-sa>'"
    }
    """,
)

add(
    "infra/terraform/README.md",
    f"""
    # Initialize & apply

    terraform init
    terraform apply -var="project_id={PROJECT_ID}" -var="region={REGION}"

    Outputs include:

    - instance_connection_name (for Cloud Run --add-cloudsql-instances)
    - db_user and db_password (use as env vars DB_USER/DB_PASSWORD on Cloud Run)
    - bucket names and topic

    Create Pub/Sub push subscription after you deploy the worker:

    gcloud pubsub subscriptions create jobs-sub \
      --topic=jobs \
      --push-endpoint="https://<worker-url>/pubsub" \
      --push-auth-service-account="recontent-worker-sa@{PROJECT_ID}.iam.gserviceaccount.com"
    """,
)

# ---------- Cloud Build ----------
add(
    "infra/cloudbuild/build-api.yaml",
    f"""
    steps:
    - name: gcr.io/cloud-builders/docker
      args: ["build","-t","gcr.io/$PROJECT_ID/recontent-api:$_TAG","."]
      dir: "."
    - name: gcr.io/cloud-builders/docker
      args: ["push","gcr.io/$PROJECT_ID/recontent-api:$_TAG"]
    - name: gcr.io/google.com/cloudsdktool/cloud-sdk
      args: [
        "gcloud","run","deploy","recontent-api",
        "--image","gcr.io/$PROJECT_ID/recontent-api:$_TAG",
        "--region","{REGION}","--allow-unauthenticated",
        "--service-account","recontent-api-sa@{PROJECT_ID}.iam.gserviceaccount.com",
        "--set-env-vars","GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION={REGION},GCS_BUCKET_RAW=recontent-raw,GCS_BUCKET_PROCESSED=recontent-processed,GCS_BUCKET_PUBLISHED=recontent-published,PUBSUB_TOPIC_JOBS=jobs,DB_INSTANCE_CONN_NAME={INSTANCE_CONN},DB_NAME=recontent,DB_USER=recontent,DB_PASSWORD=$(dbpass)",
        "--add-cloudsql-instances","{INSTANCE_CONN}"
      ]
    availableSecrets:
      secretManager:
      - versionName: projects/$PROJECT_ID/secrets/recontent-db-pass/versions/latest
        env: dbpass
    substitutions:
      _TAG: "v1"
    """,
)

add(
    "infra/cloudbuild/build-worker.yaml",
    f"""
    steps:
    - name: gcr.io/cloud-builders/docker
      args: ["build","-t","gcr.io/$PROJECT_ID/recontent-worker:$_TAG","."]
      dir: "."
    - name: gcr.io/cloud-builders/docker
      args: ["push","gcr.io/$PROJECT_ID/recontent-worker:$_TAG"]
    - name: gcr.io/google.com/cloudsdktool/cloud-sdk
      args: [
        "gcloud","run","deploy","recontent-worker",
        "--image","gcr.io/$PROJECT_ID/recontent-worker:$_TAG",
        "--region","{REGION}","--allow-unauthenticated",
        "--service-account","recontent-worker-sa@{PROJECT_ID}.iam.gserviceaccount.com",
        "--set-env-vars","GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION={REGION},GCS_BUCKET_PROCESSED=recontent-processed,MOCK_AI=1"
      ]
    substitutions:
      _TAG: "v1"
    """,
)

add(
    "infra/cloudbuild/triggers-notes.md",
    """
    Create two Cloud Build triggers (optional):

    - recontent-api: uses infra/cloudbuild/build-api.yaml
    - recontent-worker: uses infra/cloudbuild/build-worker.yaml

    Add Secret Manager secret recontent-db-pass with your DB password from Terraform output to avoid plaintext env vars.
    """,
)

# ---------- apps/web placeholder ----------
add(
    "apps/web/README.md",
    """
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
    """,
)

# ---------- write zip ----------
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for path, content in files.items():
        z.writestr(path, content)

with open("recontent.zip", "wb") as f:
    f.write(buf.getvalue())

print("Created recontent.zip with", len(files), "files.")
print("Next: unzip recontent.zip && cd recontent && follow README.md")
