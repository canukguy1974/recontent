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
