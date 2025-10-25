"""
HeartBeat Engine - Media Repository
Production-grade data access layer for clip metadata
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, date
import logging

from .models import Clip, ClipAsset, ClipTag

logger = logging.getLogger(__name__)


class ClipRepository:
    """Repository for clip metadata operations"""
    
    def __init__(self, session: Session):
        """Initialize repository with database session"""
        self.session = session
    
    def create_clip(
        self,
        clip_id: str,
        player_id: str,
        team_code: str,
        game_id: str,
        event_type: str,
        start_timecode_s: float,
        end_timecode_s: float,
        duration_s: float,
        **kwargs
    ) -> Clip:
        """Create a new clip record"""
        clip = Clip(
            clip_id=clip_id,
            player_id=player_id,
            team_code=team_code,
            game_id=game_id,
            event_type=event_type,
            start_timecode_s=start_timecode_s,
            end_timecode_s=end_timecode_s,
            duration_s=duration_s,
            **kwargs
        )
        self.session.add(clip)
        self.session.commit()
        self.session.refresh(clip)
        logger.info(f"Created clip: {clip_id}")
        return clip
    
    def get_clip_by_id(self, clip_id: str) -> Optional[Clip]:
        """Get clip by external clip_id"""
        return self.session.query(Clip).filter(Clip.clip_id == clip_id).first()
    
    def get_clip_by_pk(self, pk: int) -> Optional[Clip]:
        """Get clip by primary key"""
        return self.session.query(Clip).filter(Clip.id == pk).first()
    
    def list_clips(
        self,
        player_id: Optional[str] = None,
        team_code: Optional[str] = None,
        game_id: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Clip]:
        """List clips with optional filters"""
        query = self.session.query(Clip)
        
        if player_id:
            query = query.filter(Clip.player_id == player_id)
        if team_code:
            query = query.filter(Clip.team_code == team_code)
        if game_id:
            query = query.filter(Clip.game_id == game_id)
        if event_type:
            query = query.filter(Clip.event_type == event_type)
        if status:
            query = query.filter(Clip.processing_status == status)
        
        query = query.order_by(desc(Clip.created_at))
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def update_clip_status(
        self,
        clip_id: str,
        status: str,
        error_message: Optional[str] = None,
        processing_time_s: Optional[float] = None
    ) -> Optional[Clip]:
        """Update clip processing status"""
        clip = self.get_clip_by_id(clip_id)
        if clip:
            clip.processing_status = status
            if error_message:
                clip.error_message = error_message
            if processing_time_s:
                clip.processing_time_s = processing_time_s
            self.session.commit()
            self.session.refresh(clip)
            logger.info(f"Updated clip {clip_id} status to {status}")
        return clip
    
    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip (cascades to assets and tags)"""
        clip = self.get_clip_by_id(clip_id)
        if clip:
            self.session.delete(clip)
            self.session.commit()
            logger.info(f"Deleted clip: {clip_id}")
            return True
        return False
    
    # Asset operations
    def add_asset(
        self,
        clip_id: int,
        asset_type: str,
        gcs_uri: str,
        **kwargs
    ) -> ClipAsset:
        """Add an asset to a clip"""
        asset = ClipAsset(
            clip_id=clip_id,
            asset_type=asset_type,
            gcs_uri=gcs_uri,
            **kwargs
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        logger.info(f"Added {asset_type} asset to clip {clip_id}: {gcs_uri}")
        return asset
    
    def get_clip_assets(self, clip_id: int, asset_type: Optional[str] = None) -> List[ClipAsset]:
        """Get all assets for a clip, optionally filtered by type"""
        query = self.session.query(ClipAsset).filter(ClipAsset.clip_id == clip_id)
        if asset_type:
            query = query.filter(ClipAsset.asset_type == asset_type)
        return query.all()
    
    # Tag operations
    def add_tag(
        self,
        clip_id: int,
        tag: str,
        tag_type: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> ClipTag:
        """Add a tag to a clip"""
        clip_tag = ClipTag(
            clip_id=clip_id,
            tag=tag,
            tag_type=tag_type,
            confidence=confidence
        )
        self.session.add(clip_tag)
        self.session.commit()
        self.session.refresh(clip_tag)
        logger.info(f"Added tag '{tag}' to clip {clip_id}")
        return clip_tag
    
    def get_clip_tags(self, clip_id: int) -> List[ClipTag]:
        """Get all tags for a clip"""
        return self.session.query(ClipTag).filter(ClipTag.clip_id == clip_id).all()
    
    def search_by_tags(self, tags: List[str], limit: int = 100) -> List[Clip]:
        """Search clips by tags (OR match)"""
        return (
            self.session.query(Clip)
            .join(ClipTag)
            .filter(ClipTag.tag.in_(tags))
            .distinct()
            .order_by(desc(Clip.created_at))
            .limit(limit)
            .all()
        )

