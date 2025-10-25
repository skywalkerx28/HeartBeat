"""
HeartBeat Engine - Media Models
SQLAlchemy models for production video clip metadata
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, BigInteger,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List, Optional

Base = declarative_base()


class Clip(Base):
    """Master clip metadata (assets in GCS)"""
    __tablename__ = "clips"
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_clip_status"
        ),
        CheckConstraint(
            "duration_s > 0 AND duration_s <= 300",
            name="ck_clip_duration"
        ),
        Index("ix_clips_player_id", "player_id"),
        Index("ix_clips_team_code", "team_code"),
        Index("ix_clips_game_id", "game_id"),
        Index("ix_clips_event_type", "event_type"),
        Index("ix_clips_created_at", "created_at", postgresql_using="btree", postgresql_ops={"created_at": "DESC"}),
        Index("ix_clips_status", "processing_status"),
        Index("ix_clips_composite", "player_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        {'schema': 'media'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    clip_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # Context
    player_id = Column(String(20), nullable=False)
    player_name = Column(String(255), nullable=True)
    team_code = Column(String(10), nullable=False)
    opponent_code = Column(String(10), nullable=True)
    game_id = Column(String(20), nullable=False)
    game_date = Column(Date, nullable=True)
    season = Column(String(10), nullable=True)
    period = Column(Integer, nullable=True)
    
    # Event
    event_type = Column(String(50), nullable=False)
    outcome = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)
    start_timecode_s = Column(Float, nullable=False)
    end_timecode_s = Column(Float, nullable=False)
    duration_s = Column(Float, nullable=False)
    
    # Processing
    source_gcs_uri = Column(String(512), nullable=True)
    processing_status = Column(String(50), nullable=False, default='pending')
    processing_time_s = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assets = relationship("ClipAsset", back_populates="clip", cascade="all, delete-orphan")
    tags = relationship("ClipTag", back_populates="clip", cascade="all, delete-orphan")
    
    def to_dict(self, include_assets: bool = False, include_tags: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "id": self.id,
            "clip_id": self.clip_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team_code": self.team_code,
            "opponent_code": self.opponent_code,
            "game_id": self.game_id,
            "game_date": self.game_date.isoformat() if self.game_date else None,
            "season": self.season,
            "period": self.period,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "zone": self.zone,
            "duration_s": self.duration_s,
            "processing_status": self.processing_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_assets and self.assets:
            result["assets"] = [a.to_dict() for a in self.assets]
        
        if include_tags and self.tags:
            result["tags"] = [t.tag for t in self.tags]
        
        return result
    
    def __repr__(self) -> str:
        return f"<Clip(clip_id='{self.clip_id}', player_id='{self.player_id}', event='{self.event_type}')>"


class ClipAsset(Base):
    """Asset variants (MP4, HLS, thumbnails) with GCS URIs"""
    __tablename__ = "clip_assets"
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('mp4', 'hls_playlist', 'hls_segment', 'thumbnail', 'thumbnail_grid', 'dash_manifest')",
            name="ck_asset_type"
        ),
        UniqueConstraint("clip_id", "asset_type", "gcs_uri", name="uq_clip_asset_type"),
        Index("ix_clip_assets_clip_id", "clip_id"),
        Index("ix_clip_assets_type", "asset_type"),
        {'schema': 'media'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    clip_id = Column(Integer, ForeignKey("media.clips.id", ondelete="CASCADE"), nullable=False)
    
    # Asset details
    asset_type = Column(String(20), nullable=False)
    gcs_uri = Column(String(512), nullable=False)
    cdn_path = Column(String(512), nullable=True)
    
    # Metadata
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_s = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    codec = Column(String(50), nullable=True)
    bitrate_kbps = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    clip = relationship("Clip", back_populates="assets")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "asset_type": self.asset_type,
            "gcs_uri": self.gcs_uri,
            "cdn_path": self.cdn_path,
            "file_size_bytes": self.file_size_bytes,
            "duration_s": self.duration_s,
            "width": self.width,
            "height": self.height,
            "codec": self.codec,
            "bitrate_kbps": self.bitrate_kbps,
        }
    
    def __repr__(self) -> str:
        return f"<ClipAsset(clip_id={self.clip_id}, type='{self.asset_type}')>"


class ClipTag(Base):
    """Searchable tags for clip categorization"""
    __tablename__ = "clip_tags"
    __table_args__ = (
        UniqueConstraint("clip_id", "tag", name="uq_clip_tag"),
        Index("ix_clip_tags_clip_id", "clip_id"),
        Index("ix_clip_tags_tag", "tag"),
        Index("ix_clip_tags_type", "tag_type"),
        {'schema': 'media'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    clip_id = Column(Integer, ForeignKey("media.clips.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False)
    tag_type = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    clip = relationship("Clip", back_populates="tags")
    
    def __repr__(self) -> str:
        return f"<ClipTag(clip_id={self.clip_id}, tag='{self.tag}')>"

