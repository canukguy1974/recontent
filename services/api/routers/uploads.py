from fastapi import APIRouter, Query, HTTPException
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError
import uuid
from packages.common.config import BUCKET_RAW

router = APIRouter()

@router.get("/upload-url")
def upload_url(org_id: int, content_type: str = Query("image/jpeg")):
    try:
        client = storage.Client()
    except DefaultCredentialsError as e:
        raise HTTPException(501, f"GCP credentials not configured: {e}")

    blob_name = f"org_{org_id}/{uuid.uuid4()}.jpg"
    blob = client.bucket(BUCKET_RAW).blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=600,
        method="PUT",
        content_type=content_type,
    )
    return {"url": url, "gcs_uri": f"gs://{BUCKET_RAW}/{blob_name}"}

@router.get("/view-url")
def view_url(gcs_uri: str):
    if not gcs_uri.startswith("gs://"):
        raise HTTPException(400, "gcs_uri must start with gs://")
    try:
        client = storage.Client()
    except DefaultCredentialsError as e:
        raise HTTPException(501, f"GCP credentials not configured: {e}")

    without_scheme = gcs_uri.replace("gs://", "", 1)
    parts = without_scheme.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(400, "gcs_uri must be in form gs://bucket/path")
    bucket_name, blob_path = parts[0], parts[1]

    blob = client.bucket(bucket_name).blob(blob_path)
    url = blob.generate_signed_url(version="v4", expiration=600, method="GET")
    return {"url": url}
