"""
Social Media Post Generator Processor

Handles job processing for generating platform-specific social media posts
from image analysis results.
"""
import asyncio
from typing import Dict, Any, List
import json
from datetime import datetime

from services.worker.ai.social_media_generator import (
    SocialMediaGenerator, 
    SocialPlatform
)
from services.worker.ai.vertex_client import VertexAIClient
from packages.common.logging import get_logger

log = get_logger("social-media-processor")

async def run(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process social media post generation job
    
    Expected job_data:
    - job_id: int
    - analysis_job_id: int (job containing the analysis results)
    - platforms: List[str] (platform names to generate for)
    - context: Dict (additional context like business_type, brand_voice, etc.)
    - asset_ids: List[int]
    """
    
    job_id = job_data.get("job_id")
    analysis_job_id = job_data.get("analysis_job_id")
    platforms = job_data.get("platforms", ["instagram"])
    context = job_data.get("context", {})
    asset_ids = job_data.get("asset_ids", [])
    
    log.info(f"Processing social media generation job {job_id}")
    
    try:
        # Initialize clients
        vertex_client = VertexAIClient()
        generator = SocialMediaGenerator(vertex_client)
        
        # Parse platform strings to enum values
        platform_enums = []
        for platform_str in platforms:
            try:
                platform_enums.append(SocialPlatform(platform_str.lower()))
            except ValueError:
                log.warning(f"Unknown platform: {platform_str}")
                continue
        
        if not platform_enums:
            raise ValueError("No valid platforms specified")
        
        # Get analysis results from the analysis job
        # In a real system, this would query the database for the completed analysis job
        # For now, we'll simulate this by expecting analysis_data in the job_data
        analysis_data = job_data.get("analysis_data")
        if not analysis_data:
            raise ValueError("No analysis data provided")
        
        # Generate posts for all platforms
        log.info(f"Generating posts for platforms: {[p.value for p in platform_enums]}")
        posts = await generator.generate_posts(
            analysis_data=analysis_data,
            asset_ids=asset_ids,
            platforms=platform_enums,
            context=context
        )
        
        if not posts:
            raise ValueError("Failed to generate any posts")
        
        # Format results
        posts_data = []
        for post in posts:
            post_dict = {
                "post_id": post.post_id,
                "platform": post.platform.value,
                "content": {
                    "caption": post.content.caption,
                    "hashtags": post.content.hashtags,
                    "engagement_hooks": post.content.engagement_hooks,
                    "call_to_action": post.content.call_to_action,
                    "image_config": post.content.image_config,
                    "scheduling_suggestions": post.content.scheduling_suggestions
                },
                "asset_ids": post.asset_ids,
                "performance_score": post.performance_score,
                "estimated_reach": post.estimated_reach,
                "best_posting_times": post.best_posting_times
            }
            posts_data.append(post_dict)
        
        result = {
            "status": "completed",
            "generation_id": f"gen_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "posts": posts_data,
            "total_posts": len(posts_data),
            "platforms": [p.value for p in platform_enums],
            "context": context,
            "generated_at": datetime.now().isoformat()
        }
        
        log.info(f"Successfully generated {len(posts_data)} posts for job {job_id}")
        return result
        
    except Exception as e:
        log.error(f"Social media generation job {job_id} failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "job_id": job_id,
            "failed_at": datetime.now().isoformat()
        }