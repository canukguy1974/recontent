"""
Combination Agent API Router

Provides endpoints for multi-image analysis, combination suggestions,
and intelligent post generation workflows.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import json

from db.models import Asset, Job, JobType, User, JobStatus
from services.api.deps import get_db, get_current_user
from services.api.middleware.rate_limiting import require_post_combination_credits
from services.api.utils.credits import consume_credits, ActionType
from packages.common.pubsub import publish_job
from packages.common.logging import get_logger

router = APIRouter()
log = get_logger("combination-agent")

# Pydantic models for requests/responses
class AnalyzeImagesRequest(BaseModel):
    asset_ids: List[int]
    context: Optional[Dict[str, Any]] = {}
    purpose: Optional[str] = "general"  # "general", "social_media", "listing", "marketing"

class ImageAnalysisResult(BaseModel):
    image_id: int
    image_type: str
    features: List[str]
    quality_score: float
    confidence: float

class AnalyzeImagesResponse(BaseModel):
    analysis_id: str
    job_id: int
    status: str
    image_count: int
    estimated_completion: str
    
class AnalysisStatusResponse(BaseModel):
    job_id: int
    status: str
    analysis_id: Optional[str]
    progress: float  # 0.0 to 1.0
    results: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

class CombinationSuggestion(BaseModel):
    combination_id: str
    image_ids: List[int]
    purpose: str
    description: str
    confidence: float
    estimated_engagement: Optional[float] = None

class GetCombinationsResponse(BaseModel):
    analysis_id: str
    combinations: List[CombinationSuggestion]
    marketing_themes: List[str]
    target_audience: List[str]
    confidence: float

# Social Media Generation Models
class GenerateSocialRequest(BaseModel):
    analysis_job_id: int
    platforms: List[str] = ["instagram"]  # instagram, facebook, twitter, linkedin, pinterest, tiktok
    context: Optional[Dict[str, Any]] = {}
    
class SocialPostContent(BaseModel):
    caption: str
    hashtags: List[str]
    engagement_hooks: List[str]
    call_to_action: Optional[str] = None
    image_config: Dict[str, Any]
    scheduling_suggestions: List[str]

class SocialPost(BaseModel):
    post_id: str
    platform: str
    content: SocialPostContent
    asset_ids: List[int]
    performance_score: float
    estimated_reach: Optional[int] = None
    best_posting_times: List[str]

class GenerateSocialResponse(BaseModel):
    generation_id: str
    job_id: int
    status: str
    platforms: List[str]
    estimated_completion: str

class GetSocialPostsResponse(BaseModel):
    generation_id: str
    posts: List[SocialPost]
    total_posts: int
    platforms: List[str]
    generated_at: datetime


@router.post("/analyze", response_model=AnalyzeImagesResponse)
@require_post_combination_credits()
async def analyze_images(
    request: AnalyzeImagesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    usage_log=None
):
    """
    Analyze multiple images together to understand their relationships
    and generate intelligent combination suggestions
    """
    
    if len(request.asset_ids) < 2:
        raise HTTPException(400, "At least 2 images are required for analysis")
    
    if len(request.asset_ids) > 10:
        raise HTTPException(400, "Maximum 10 images allowed per analysis")
    
    # Verify all assets belong to the current user
    assets = db.query(Asset).filter(
        Asset.id.in_(request.asset_ids),
        Asset.owner_user_id == current_user.id
    ).all()
    
    if len(assets) != len(request.asset_ids):
        raise HTTPException(404, "One or more assets not found or not accessible")
    
    # Extract GCS URIs
    gcs_uris = [asset.gcs_uri for asset in assets]
    
    # Create job record
    job = Job(
        org_id=current_user.org_id,
        user_id=current_user.id,
        type=JobType.ANALYZE_SET,
        status=JobStatus.CREATED,
        input_data={
            "asset_ids": request.asset_ids,
            "gcs_uris": gcs_uris,
            "context": request.context,
            "purpose": request.purpose
        }
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Prepare job message for worker
    job_message = {
        "type": "analyze_set",
        "job_id": job.id,
        "org_id": current_user.org_id,
        "user_id": current_user.id,
        "asset_ids": request.asset_ids,
        "gcs_uris": gcs_uris,
        "context": request.context,
        "purpose": request.purpose
    }
    
    # Publish to worker queue
    try:
        publish_job(job_message)
        log.info(f"Published analyze_set job {job.id} for user {current_user.id}")
    except Exception as e:
        # Update job status to failed
        job.status = JobStatus.FAILED
        job.output_data = {"error": f"Failed to queue job: {str(e)}"}
        db.commit()
        raise HTTPException(500, f"Failed to queue analysis job: {str(e)}")
    
    # Generate analysis ID (will be set by worker, but we'll use job ID for now)
    analysis_id = f"job_{job.id}"
    
    return AnalyzeImagesResponse(
        analysis_id=analysis_id,
        job_id=job.id,
        status="pending",
        image_count=len(request.asset_ids),
        estimated_completion=f"{len(request.asset_ids) * 30} seconds"  # Rough estimate
    )


@router.get("/analysis/{job_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of an image analysis job"""
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.ANALYZE_SET
    ).first()
    
    if not job:
        raise HTTPException(404, "Analysis job not found")
    
    # Calculate progress based on status
    progress_map = {
        JobStatus.CREATED: 0.0,
        JobStatus.QUEUED: 0.1,
        JobStatus.RENDERING: 0.5,
        JobStatus.COMPLETE: 1.0,
        JobStatus.FAILED: 0.0
    }
    
    analysis_id = None
    results = None
    error = None
    
    if job.status == JobStatus.COMPLETE and job.output_data:
        analysis_id = job.output_data.get("analysis_id")
        results = job.output_data.get("full_analysis")
    elif job.status == JobStatus.FAILED and job.output_data:
        error = job.output_data.get("error")
    
    return AnalysisStatusResponse(
        job_id=job.id,
        status=job.status.value,
        analysis_id=analysis_id,
        progress=progress_map.get(job.status, 0.0),
        results=results,
        error=error,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.get("/analysis/{job_id}/combinations", response_model=GetCombinationsResponse)
async def get_combinations(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get suggested image combinations from a completed analysis"""
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.ANALYZE_SET
    ).first()
    
    if not job:
        raise HTTPException(404, "Analysis job not found")
    
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(400, f"Analysis not completed yet. Status: {job.status.value}")
    
    if not job.output_data or "full_analysis" not in job.output_data:
        raise HTTPException(404, "Analysis results not found")
    
    analysis_data = job.output_data["full_analysis"]
    analysis_id = job.output_data.get("analysis_id", f"job_{job.id}")
    
    # Extract combinations from analysis
    combinations = []
    for i, combo in enumerate(analysis_data.get("suggested_combinations", [])):
        combinations.append(CombinationSuggestion(
            combination_id=f"{analysis_id}_combo_{i}",
            image_ids=[job.input_data["asset_ids"][idx] for idx in combo.get("images", [])],
            purpose=combo.get("purpose", "general"),
            description=combo.get("description", "Image combination"),
            confidence=combo.get("confidence", 0.5),
            estimated_engagement=combo.get("estimated_engagement")
        ))
    
    return GetCombinationsResponse(
        analysis_id=analysis_id,
        combinations=combinations,
        marketing_themes=analysis_data.get("marketing_themes", []),
        target_audience=analysis_data.get("target_audience", []),
        confidence=analysis_data.get("overall_confidence", 0.0)
    )


@router.get("/analysis/history")
async def get_analysis_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's analysis history"""
    
    jobs = db.query(Job).filter(
        Job.user_id == current_user.id,
        Job.type == JobType.ANALYZE_SET
    ).order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "job_id": job.id,
            "analysis_id": job.output_data.get("analysis_id") if job.output_data else None,
            "status": job.status.value,
            "image_count": len(job.input_data.get("asset_ids", [])) if job.input_data else 0,
            "purpose": job.input_data.get("purpose") if job.input_data else "general",
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        for job in jobs
    ]


@router.delete("/analysis/{job_id}")
async def delete_analysis(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an analysis job and its results"""
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.ANALYZE_SET
    ).first()
    
    if not job:
        raise HTTPException(404, "Analysis job not found")
    
    # Note: In a production system, you might want to also delete
    # the analysis files from GCS
    
    db.delete(job)
    db.commit()
    
    return {"message": "Analysis deleted successfully"}


@router.post("/generate-social", response_model=GenerateSocialResponse)
@require_post_combination_credits()
async def generate_social_posts(
    request: GenerateSocialRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    usage_log=None
):
    """
    Generate platform-specific social media posts from an analysis
    """
    
    # Validate analysis job exists and is completed
    analysis_job = db.query(Job).filter(
        Job.id == request.analysis_job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.ANALYZE_SET
    ).first()
    
    if not analysis_job:
        raise HTTPException(404, "Analysis job not found")
    
    if analysis_job.status != JobStatus.COMPLETE:
        raise HTTPException(400, f"Analysis not completed. Status: {analysis_job.status.value}")
    
    if not analysis_job.output_data or "full_analysis" not in analysis_job.output_data:
        raise HTTPException(404, "Analysis results not found")
    
    # Validate platforms
    valid_platforms = ["instagram", "facebook", "twitter", "linkedin", "pinterest", "tiktok"]
    platforms = [p.lower() for p in request.platforms if p.lower() in valid_platforms]
    
    if not platforms:
        raise HTTPException(400, f"No valid platforms specified. Valid options: {valid_platforms}")
    
    # Get asset IDs from the analysis job
    asset_ids = analysis_job.input_data.get("asset_ids", [])
    
    # Create social media generation job
    social_job = Job(
        org_id=current_user.org_id,
        user_id=current_user.id,
        type=JobType.GENERATE_SOCIAL,
        status=JobStatus.CREATED,
        input_data={
            "analysis_job_id": request.analysis_job_id,
            "platforms": platforms,
            "context": request.context,
            "asset_ids": asset_ids,
            "analysis_data": analysis_job.output_data["full_analysis"]
        }
    )
    
    db.add(social_job)
    db.commit()
    db.refresh(social_job)
    
    # Prepare job message for worker
    job_message = {
        "type": "generate_social",
        "job_id": social_job.id,
        "org_id": current_user.org_id,
        "user_id": current_user.id,
        "analysis_job_id": request.analysis_job_id,
        "platforms": platforms,
        "context": request.context,
        "asset_ids": asset_ids,
        "analysis_data": analysis_job.output_data["full_analysis"]
    }
    
    # Publish to worker queue
    try:
        publish_job(job_message)
        log.info(f"Published generate_social job {social_job.id} for user {current_user.id}")
    except Exception as e:
        # Update job status to failed
        social_job.status = JobStatus.FAILED
        social_job.output_data = {"error": f"Failed to queue job: {str(e)}"}
        db.commit()
        raise HTTPException(500, f"Failed to queue social media generation job: {str(e)}")
    
    # Generate ID
    generation_id = f"gen_{social_job.id}"
    
    return GenerateSocialResponse(
        generation_id=generation_id,
        job_id=social_job.id,
        status="pending",
        platforms=platforms,
        estimated_completion=f"{len(platforms) * 45} seconds"
    )


@router.get("/social/{job_id}/status")
async def get_social_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a social media generation job"""
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.GENERATE_SOCIAL
    ).first()
    
    if not job:
        raise HTTPException(404, "Social media generation job not found")
    
    # Calculate progress based on status
    progress_map = {
        JobStatus.CREATED: 0.0,
        JobStatus.QUEUED: 0.1,
        JobStatus.RENDERING: 0.5,
        JobStatus.COMPLETE: 1.0,
        JobStatus.FAILED: 0.0
    }
    
    generation_id = None
    results = None
    error = None
    
    if job.status == JobStatus.COMPLETE and job.output_data:
        generation_id = job.output_data.get("generation_id")
        results = job.output_data.get("posts")
    elif job.status == JobStatus.FAILED and job.output_data:
        error = job.output_data.get("error")
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "generation_id": generation_id,
        "progress": progress_map.get(job.status, 0.0),
        "results": results,
        "error": error,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


@router.get("/social/{job_id}/posts", response_model=GetSocialPostsResponse)
async def get_social_posts(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get generated social media posts from a completed job"""
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.type == JobType.GENERATE_SOCIAL
    ).first()
    
    if not job:
        raise HTTPException(404, "Social media generation job not found")
    
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(400, f"Generation not completed yet. Status: {job.status.value}")
    
    if not job.output_data or "posts" not in job.output_data:
        raise HTTPException(404, "Generated posts not found")
    
    generation_data = job.output_data
    generation_id = generation_data.get("generation_id", f"gen_{job.id}")
    
    # Convert posts data to response format
    posts = []
    for post_data in generation_data["posts"]:
        post = SocialPost(
            post_id=post_data["post_id"],
            platform=post_data["platform"],
            content=SocialPostContent(**post_data["content"]),
            asset_ids=post_data["asset_ids"],
            performance_score=post_data["performance_score"],
            estimated_reach=post_data.get("estimated_reach"),
            best_posting_times=post_data.get("best_posting_times", [])
        )
        posts.append(post)
    
    return GetSocialPostsResponse(
        generation_id=generation_id,
        posts=posts,
        total_posts=len(posts),
        platforms=generation_data.get("platforms", []),
        generated_at=datetime.fromisoformat(generation_data.get("generated_at", datetime.now().isoformat()))
    )


@router.get("/social/history")
async def get_social_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's social media generation history"""
    
    jobs = db.query(Job).filter(
        Job.user_id == current_user.id,
        Job.type == JobType.GENERATE_SOCIAL
    ).order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "job_id": job.id,
            "generation_id": job.output_data.get("generation_id") if job.output_data else None,
            "status": job.status.value,
            "platforms": job.input_data.get("platforms", []) if job.input_data else [],
            "post_count": len(job.output_data.get("posts", [])) if job.output_data else 0,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        for job in jobs
    ]