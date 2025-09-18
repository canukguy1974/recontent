import os

def env(name: str, default: str | None = None, cast=str):
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {name}")
    return cast(val) if cast is not None and val is not None else val

GOOGLE_CLOUD_PROJECT = env("GOOGLE_CLOUD_PROJECT", "recontent-472506")
GOOGLE_CLOUD_LOCATION = env("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET_RAW = env("GCS_BUCKET_RAW", "recontent-raw")
BUCKET_PROCESSED = env("GCS_BUCKET_PROCESSED", "recontent-processed")
BUCKET_PUBLISHED = env("GCS_BUCKET_PUBLISHED", "recontent-published")
PUBSUB_TOPIC_JOBS = env("PUBSUB_TOPIC_JOBS", "jobs")
MOCK_AI = env("MOCK_AI", "1") == "1"
GEMINI_IMAGE_MODEL_ID = env("GEMINI_IMAGE_MODEL_ID", "gemini-2.5-flash-image-preview")
GEMINI_TEXT_MODEL_ID = env("GEMINI_TEXT_MODEL_ID", "gemini-2.5-flash")
IMAGEN_MODEL_ID = env("IMAGEN_MODEL_ID", "imagen-3.0")

DB_INSTANCE_CONN_NAME = env("DB_INSTANCE_CONN_NAME", "recontent-472506:us-central1:recontent-sql")
DB_NAME = env("DB_NAME", "recontent")
DB_USER = env("DB_USER", "recontent")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")  # allow empty in local MOCK
