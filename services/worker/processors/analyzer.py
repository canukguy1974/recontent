"""
Multi-Image Analyzer Processor

Handles analyze_set job types to process multiple images together
and generate insights for intelligent content creation.
"""
import json
from typing import Dict, List, Any
from uuid import uuid4

from packages.common.gcs import upload_bytes
from packages.common.config import BUCKET_PROCESSED
from services.worker.ai.multi_image_analyzer import MultiImageAnalyzer


async def run(job: dict) -> dict:
    """
    Process an analyze_set job to analyze multiple images together
    
    Job format:
    {
        "type": "analyze_set",
        "org_id": 1,
        "user_id": 123,
        "asset_ids": [1, 2, 3],
        "gcs_uris": ["gs://bucket/img1.jpg", "gs://bucket/img2.jpg", ...],
        "context": {
            "property_type": "residential",
            "agent_name": "John Doe",
            "listing_price": 500000,
            ...
        }
    }
    
    Returns:
    {
        "status": "completed",
        "analysis_id": "set_abc123",
        "analysis_uri": "gs://bucket/analysis.json",
        "summary": {
            "image_count": 3,
            "confidence": 0.85,
            "primary_themes": ["luxury", "modern"],
            "suggested_combinations": 2
        }
    }
    """
    
    try:
        # Validate job data
        required_fields = ["asset_ids", "gcs_uris", "org_id", "user_id"]
        for field in required_fields:
            if field not in job:
                raise ValueError(f"Missing required field: {field}")
        
        asset_ids = job["asset_ids"]
        gcs_uris = job["gcs_uris"]
        context = job.get("context", {})
        
        if len(asset_ids) != len(gcs_uris):
            raise ValueError("Asset IDs and GCS URIs must be the same length")
        
        if len(gcs_uris) < 2:
            raise ValueError("Multi-image analysis requires at least 2 images")
        
        # Initialize analyzer
        analyzer = MultiImageAnalyzer()
        
        # Perform analysis
        analysis = await analyzer.analyze_image_set(asset_ids, gcs_uris, context)
        
        # Serialize and store analysis results
        analysis_data = analyzer.serialize_analysis(analysis)
        analysis_json = json.dumps(analysis_data, indent=2)
        
        # Upload analysis to GCS
        analysis_uri = f"gs://{BUCKET_PROCESSED}/org_{job['org_id']}/analysis_{uuid4().hex[:8]}.json"
        upload_bytes(analysis_uri, analysis_json.encode('utf-8'), content_type="application/json")
        
        # Prepare summary for quick access
        summary = {
            "image_count": len(analysis.images),
            "confidence": analysis.overall_confidence,
            "primary_themes": analysis.marketing_themes[:3],  # Top 3 themes
            "suggested_combinations": len(analysis.suggested_combinations)
        }
        
        return {
            "status": "completed",
            "analysis_id": analysis.set_id,
            "analysis_uri": analysis_uri,
            "summary": summary,
            "full_analysis": analysis_data  # Include full analysis in response
        }
        
    except Exception as e:
        print(f"Error in analyze_set processor: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "failed",
            "error": str(e),
            "analysis_id": None,
            "analysis_uri": None,
            "summary": None
        }