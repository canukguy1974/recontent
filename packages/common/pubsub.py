import base64
import json
from fastapi import Request, HTTPException
from google.cloud import pubsub_v1
from google.auth.exceptions import DefaultCredentialsError
from packages.common.config import PUBSUB_TOPIC_JOBS, GOOGLE_CLOUD_PROJECT

async def parse_push(request: Request) -> dict:
    payload = await request.json()
    try:
        data = payload["message"]["data"]
        return json.loads(base64.b64decode(data).decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Bad Pub/Sub payload: {e}")

def publish_job(job_message: dict):
    """Publish a job message to the Pub/Sub topic"""
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(GOOGLE_CLOUD_PROJECT, PUBSUB_TOPIC_JOBS)
        publisher.publish(topic_path, data=json.dumps(job_message).encode("utf-8"))
    except DefaultCredentialsError as e:
        raise HTTPException(501, f"GCP credentials not configured: {e}")
