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
