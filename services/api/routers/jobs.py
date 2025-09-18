from fastapi import APIRouter, HTTPException
from google.cloud import pubsub_v1
from google.auth.exceptions import DefaultCredentialsError
import json
from packages.common.config import PUBSUB_TOPIC_JOBS, GOOGLE_CLOUD_PROJECT
from packages.common.schemas import CompositeJob

router = APIRouter()

@router.post("/jobs/composite")
def jobs_composite(job: CompositeJob):
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(GOOGLE_CLOUD_PROJECT, PUBSUB_TOPIC_JOBS)
        publisher.publish(topic_path, data=json.dumps(job.model_dump()).encode("utf-8"))
        return {"status": "queued"}
    except DefaultCredentialsError as e:
        raise HTTPException(501, f"GCP credentials not configured: {e}")
