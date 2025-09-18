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
