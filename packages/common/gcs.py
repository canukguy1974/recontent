from google.cloud import storage

_client = None

def client():
    global _client
    if not _client:
        _client = storage.Client()
    return _client

def download_bytes(gcs_uri: str) -> bytes:
    assert gcs_uri.startswith("gs://")
    # Parse gs://bucket-name/path/to/file.jpg
    uri_without_prefix = gcs_uri.replace("gs://", "")
    parts = uri_without_prefix.split("/", 1)  # Split into bucket and path
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ""
    blob = client().bucket(bucket_name).blob(blob_path)
    return blob.download_as_bytes()

def upload_bytes(gcs_uri: str, data: bytes, content_type="image/jpeg"):
    # Parse gs://bucket-name/path/to/file.jpg
    uri_without_prefix = gcs_uri.replace("gs://", "")
    parts = uri_without_prefix.split("/", 1)  # Split into bucket and path
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ""
    blob = client().bucket(bucket_name).blob(blob_path)
    blob.upload_from_string(data, content_type=content_type)
    return gcs_uri

def get_signed_url(gcs_uri: str, expiration_minutes: int = 60) -> str:
    """Generate a signed URL for accessing a GCS object"""
    from datetime import datetime, timedelta
    
    # Parse gs://bucket-name/path/to/file.jpg
    uri_without_prefix = gcs_uri.replace("gs://", "")
    parts = uri_without_prefix.split("/", 1)  # Split into bucket and path
    bucket_name = parts[0]
    blob_path = parts[1] if len(parts) > 1 else ""
    
    blob = client().bucket(bucket_name).blob(blob_path)
    
    # Generate signed URL with expiration
    expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    
    signed_url = blob.generate_signed_url(
        expiration=expiration_time,
        method="GET"
    )
    
    return signed_url
