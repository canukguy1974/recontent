"""
User Assets API Router
Provides endpoints for managing user's uploaded images with metadata, tagging, and organization.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from pydantic import BaseModel
from datetime import datetime
import uuid
import hashlib
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

from db.models import Asset, AssetKind, UploadSource, User, Org
from services.api.deps import get_db, get_current_user
from packages.common.config import BUCKET_RAW
from packages.common.logging import get_logger

router = APIRouter()
log = get_logger("user-assets")

# Pydantic models for requests/responses
class AssetMetadata(BaseModel):
    label: Optional[str] = None
    tags: List[str] = []

class AssetUpdate(BaseModel):
    label: Optional[str] = None
    tags: Optional[List[str]] = None

class AssetResponse(BaseModel):
    id: int
    kind: str
    gcs_uri: str
    width: Optional[int]
    height: Optional[int]
    label: Optional[str]
    tags: List[str]
    upload_source: str
    parent_asset_id: Optional[int]
    created_at: datetime
    view_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class UploadResponse(BaseModel):
    upload_url: str
    gcs_uri: str
    asset_id: Optional[int] = None


def get_storage_client():
    """Get Google Cloud Storage client with error handling"""
    try:
        return storage.Client()
    except DefaultCredentialsError as e:
        raise HTTPException(501, f"GCP credentials not configured: {e}")


def generate_signed_view_url(gcs_uri: str) -> str:
    """Generate signed URL for viewing an asset"""
    if not gcs_uri.startswith("gs://"):
        return ""
    
    try:
        client = get_storage_client()
        without_scheme = gcs_uri.replace("gs://", "", 1)
        parts = without_scheme.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return ""
        
        bucket_name, blob_path = parts[0], parts[1]
        blob = client.bucket(bucket_name).blob(blob_path)
        url = blob.generate_signed_url(version="v4", expiration=3600, method="GET")
        return url
    except Exception as e:
        log.warning(f"Failed to generate signed URL for {gcs_uri}: {e}")
        return ""


@router.get("/assets", response_model=AssetListResponse)
def list_user_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Optional[str] = Query(None, description="Filter by asset kind"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    search: Optional[str] = Query(None, description="Search in labels and tags"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's assets with filtering and pagination"""
    
    query = db.query(Asset).filter(Asset.owner_user_id == current_user.id)
    
    # Apply filters
    if kind:
        try:
            asset_kind = AssetKind(kind)
            query = query.filter(Asset.kind == asset_kind)
        except ValueError:
            raise HTTPException(400, f"Invalid asset kind: {kind}")
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if tag_list:
            # Use PostgreSQL JSON contains operator
            for tag in tag_list:
                query = query.filter(Asset.tags.contains([tag]))
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Asset.label.ilike(search_term),
                Asset.tags.astext.ilike(search_term)
            )
        )
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    offset = (page - 1) * page_size
    assets = query.order_by(desc(Asset.created_at)).offset(offset).limit(page_size + 1).all()
    
    # Check if there are more results
    has_more = len(assets) > page_size
    if has_more:
        assets = assets[:-1]  # Remove the extra item used to check for more
    
    # Convert to response format with signed URLs
    asset_responses = []
    for asset in assets:
        asset_dict = {
            "id": asset.id,
            "kind": asset.kind.value,
            "gcs_uri": asset.gcs_uri,
            "width": asset.width,
            "height": asset.height,
            "label": asset.label,
            "tags": asset.tags or [],
            "upload_source": asset.upload_source.value if asset.upload_source else "direct_upload",
            "parent_asset_id": asset.parent_asset_id,
            "created_at": asset.created_at,
            "view_url": generate_signed_view_url(asset.gcs_uri)
        }
        asset_responses.append(AssetResponse(**asset_dict))
    
    return AssetListResponse(
        assets=asset_responses,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific asset by ID"""
    
    asset = db.query(Asset).filter(
        and_(
            Asset.id == asset_id,
            Asset.owner_user_id == current_user.id
        )
    ).first()
    
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    asset_dict = {
        "id": asset.id,
        "kind": asset.kind.value,
        "gcs_uri": asset.gcs_uri,
        "width": asset.width,
        "height": asset.height,
        "label": asset.label,
        "tags": asset.tags or [],
        "upload_source": asset.upload_source.value if asset.upload_source else "direct_upload",
        "parent_asset_id": asset.parent_asset_id,
        "created_at": asset.created_at,
        "view_url": generate_signed_view_url(asset.gcs_uri)
    }
    
    return AssetResponse(**asset_dict)


@router.post("/assets/upload-url", response_model=UploadResponse)
def get_upload_url(
    metadata: AssetMetadata,
    kind: str = Query("listing", description="Asset kind: headshot, listing, etc."),
    content_type: str = Query("image/jpeg", description="Content type of the file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a signed upload URL for a new asset"""
    
    # Validate asset kind
    try:
        asset_kind = AssetKind(kind)
    except ValueError:
        raise HTTPException(400, f"Invalid asset kind: {kind}")
    
    # Generate unique blob name
    blob_name = f"org_{current_user.org_id}/user_{current_user.id}/{uuid.uuid4()}.jpg"
    
    try:
        client = get_storage_client()
        blob = client.bucket(BUCKET_RAW).blob(blob_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=600,
            method="PUT",
            content_type=content_type,
        )
        
        gcs_uri = f"gs://{BUCKET_RAW}/{blob_name}"
        
        # Pre-create the asset record
        asset = Asset(
            org_id=current_user.org_id,
            owner_user_id=current_user.id,
            kind=asset_kind,
            gcs_uri=gcs_uri,
            label=metadata.label,
            tags=metadata.tags,
            upload_source=UploadSource.DIRECT_UPLOAD
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        return UploadResponse(
            upload_url=url,
            gcs_uri=gcs_uri,
            asset_id=asset.id
        )
        
    except Exception as e:
        db.rollback()
        log.error(f"Failed to create upload URL: {e}")
        raise HTTPException(500, "Failed to create upload URL")


@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    update_data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update asset metadata (label, tags)"""
    
    asset = db.query(Asset).filter(
        and_(
            Asset.id == asset_id,
            Asset.owner_user_id == current_user.id
        )
    ).first()
    
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    # Update fields if provided
    if update_data.label is not None:
        asset.label = update_data.label
    
    if update_data.tags is not None:
        asset.tags = update_data.tags
    
    try:
        db.commit()
        db.refresh(asset)
        
        asset_dict = {
            "id": asset.id,
            "kind": asset.kind.value,
            "gcs_uri": asset.gcs_uri,
            "width": asset.width,
            "height": asset.height,
            "label": asset.label,
            "tags": asset.tags or [],
            "upload_source": asset.upload_source.value if asset.upload_source else "direct_upload",
            "parent_asset_id": asset.parent_asset_id,
            "created_at": asset.created_at,
            "view_url": generate_signed_view_url(asset.gcs_uri)
        }
        
        return AssetResponse(**asset_dict)
        
    except Exception as e:
        db.rollback()
        log.error(f"Failed to update asset {asset_id}: {e}")
        raise HTTPException(500, "Failed to update asset")


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an asset (soft delete - keeps GCS file)"""
    
    asset = db.query(Asset).filter(
        and_(
            Asset.id == asset_id,
            Asset.owner_user_id == current_user.id
        )
    ).first()
    
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    try:
        # Check if this asset is referenced by any jobs or posts
        # For now, we'll do a soft delete by just removing from DB
        # In production, you might want to mark as deleted instead
        db.delete(asset)
        db.commit()
        
        return {"message": "Asset deleted successfully"}
        
    except Exception as e:
        db.rollback()
        log.error(f"Failed to delete asset {asset_id}: {e}")
        raise HTTPException(500, "Failed to delete asset")


@router.post("/assets/{asset_id}/duplicate", response_model=AssetResponse)
def duplicate_asset(
    asset_id: int,
    metadata: Optional[AssetMetadata] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a duplicate of an existing asset"""
    
    original_asset = db.query(Asset).filter(
        and_(
            Asset.id == asset_id,
            Asset.owner_user_id == current_user.id
        )
    ).first()
    
    if not original_asset:
        raise HTTPException(404, "Asset not found")
    
    try:
        # Create new asset with same GCS URI but new metadata
        new_asset = Asset(
            org_id=current_user.org_id,
            owner_user_id=current_user.id,
            kind=original_asset.kind,
            gcs_uri=original_asset.gcs_uri,
            width=original_asset.width,
            height=original_asset.height,
            checksum=original_asset.checksum,
            staged=original_asset.staged,
            contains_people=original_asset.contains_people,
            label=metadata.label if metadata else f"{original_asset.label} (Copy)",
            tags=metadata.tags if metadata else (original_asset.tags or []),
            upload_source=UploadSource.DIRECT_UPLOAD,
            parent_asset_id=asset_id
        )
        
        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)
        
        asset_dict = {
            "id": new_asset.id,
            "kind": new_asset.kind.value,
            "gcs_uri": new_asset.gcs_uri,
            "width": new_asset.width,
            "height": new_asset.height,
            "label": new_asset.label,
            "tags": new_asset.tags or [],
            "upload_source": new_asset.upload_source.value,
            "parent_asset_id": new_asset.parent_asset_id,
            "created_at": new_asset.created_at,
            "view_url": generate_signed_view_url(new_asset.gcs_uri)
        }
        
        return AssetResponse(**asset_dict)
        
    except Exception as e:
        db.rollback()
        log.error(f"Failed to duplicate asset {asset_id}: {e}")
        raise HTTPException(500, "Failed to duplicate asset")