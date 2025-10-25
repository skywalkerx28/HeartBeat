"""
HeartBeat Engine - Video Clips API v2
Production-grade clip management with Cloud SQL + GCS

Architecture:
- Metadata: Cloud SQL Postgres (media schema)
- Assets: GCS bucket with signed URLs
- RBAC: Policy enforcement via UserContext
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from orchestrator.utils.state import UserContext
from orchestrator.config.settings import UserRole
from backend.api.dependencies import get_current_user_context
from backend.media.repository import ClipRepository
from backend.media.gcs_helper import GCSMediaHelper
from backend.media.models import Clip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/clips", tags=["clips-v2"])

# Database configuration (reuse main DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL not set; clips_v2 API will not be available")

# Session factory
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine) if engine else None

# GCS helper (lazy init)
_gcs_helper: Optional[GCSMediaHelper] = None


def get_gcs_helper() -> GCSMediaHelper:
    """Get or create GCS helper instance"""
    global _gcs_helper
    if _gcs_helper is None:
        _gcs_helper = GCSMediaHelper()
    return _gcs_helper


def get_db_session() -> Session:
    """FastAPI dependency for database session"""
    if not SessionLocal:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_clip_access(user_context: UserContext, clip: Clip) -> bool:
    """Check if user has access to a clip (RBAC)"""
    
    # Dev override
    if os.getenv("CLIPS_OPEN_ACCESS", "0") == "1":
        return True
    
    # Staff, analysts, coaches, scouts have full access
    if user_context.role in [UserRole.COACH, UserRole.ANALYST, UserRole.STAFF, UserRole.SCOUT]:
        return True
    
    # Players can access their own clips
    if user_context.role == UserRole.PLAYER:
        user_player_id = str(user_context.preferences.get('player_id', '')).replace('.0', '')
        clip_player_id = str(clip.player_id).replace('.0', '')
        return user_player_id == clip_player_id
    
    return False


@router.get("/")
async def list_clips(
    player_id: Optional[str] = Query(None),
    team_code: Optional[str] = Query(None),
    game_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    List clips with optional filters.
    
    Query params:
    - player_id: Filter by player
    - team_code: Filter by team
    - game_id: Filter by game
    - event_type: Filter by event type
    - status: Filter by processing status
    - limit: Max results (1-500, default 100)
    - offset: Pagination offset
    
    Returns clip metadata with asset URLs (signed).
    """
    try:
        repo = ClipRepository(session)
        gcs = get_gcs_helper()
        
        clips = repo.list_clips(
            player_id=player_id,
            team_code=team_code,
            game_id=game_id,
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Filter by RBAC and build response
        results = []
        for clip in clips:
            if not check_clip_access(user_context, clip):
                continue
            
            clip_dict = clip.to_dict(include_assets=True)
            
            # Generate signed URLs for assets
            if clip.assets:
                for i, asset in enumerate(clip.assets):
                    try:
                        signed_url = gcs.generate_signed_url(asset.gcs_uri, expiration_minutes=60)
                        clip_dict["assets"][i]["signed_url"] = signed_url
                    except Exception as e:
                        logger.warning(f"Failed to generate signed URL for {asset.gcs_uri}: {e}")
                        clip_dict["assets"][i]["signed_url"] = None
            
            results.append(clip_dict)
        
        logger.info(f"Listed {len(results)} clips for user {user_context.role.value}")
        return {"clips": results, "total": len(results), "limit": limit, "offset": offset}
        
    except Exception as e:
        logger.error(f"Error listing clips: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list clips"
        )


@router.get("/{clip_id}")
async def get_clip(
    clip_id: str,
    session: Session = Depends(get_db_session),
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    Get a single clip by ID with signed asset URLs.
    
    Returns full clip metadata including assets and tags.
    """
    try:
        repo = ClipRepository(session)
        gcs = get_gcs_helper()
        
        clip = repo.get_clip_by_id(clip_id)
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Check access
        if not check_clip_access(user_context, clip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Build response with signed URLs
        clip_dict = clip.to_dict(include_assets=True, include_tags=True)
        
        if clip.assets:
            for i, asset in enumerate(clip.assets):
                try:
                    signed_url = gcs.generate_signed_url(asset.gcs_uri, expiration_minutes=60)
                    clip_dict["assets"][i]["signed_url"] = signed_url
                except Exception as e:
                    logger.warning(f"Failed to generate signed URL for {asset.gcs_uri}: {e}")
                    clip_dict["assets"][i]["signed_url"] = None
        
        logger.info(f"Served clip {clip_id} to user {user_context.role.value}")
        return clip_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clip {clip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clip"
        )


@router.get("/stats/overview")
async def get_stats(
    session: Session = Depends(get_db_session),
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    Get clip statistics.
    
    Returns aggregate counts and metadata about the clip library.
    """
    try:
        from sqlalchemy import func
        from backend.media.models import Clip as ClipModel
        
        # Total clips
        total = session.query(func.count(ClipModel.id)).scalar()
        
        # By status
        by_status = session.query(
            ClipModel.processing_status,
            func.count(ClipModel.id)
        ).group_by(ClipModel.processing_status).all()
        
        # By event type (top 10)
        by_event = session.query(
            ClipModel.event_type,
            func.count(ClipModel.id)
        ).group_by(ClipModel.event_type).order_by(func.count(ClipModel.id).desc()).limit(10).all()
        
        return {
            "total_clips": total,
            "by_status": {status: count for status, count in by_status},
            "top_event_types": {event: count for event, count in by_event}
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stats"
        )


@router.get("/health")
async def health_check(session: Session = Depends(get_db_session)):
    """
    Health check for media system (no auth required).
    
    Returns database connectivity and bucket configuration.
    """
    try:
        from sqlalchemy import func, text
        from backend.media.models import Clip as ClipModel
        
        # Test DB connection
        total_clips = session.query(func.count(ClipModel.id)).scalar()
        
        # Test GCS connection
        gcs_configured = bool(os.getenv("MEDIA_GCS_BUCKET"))
        gcs_bucket = os.getenv("MEDIA_GCS_BUCKET", "not-set")
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_clips": total_clips,
            "gcs_configured": gcs_configured,
            "gcs_bucket": gcs_bucket,
            "cdn_domain": os.getenv("MEDIA_CDN_DOMAIN", "not-set")
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

