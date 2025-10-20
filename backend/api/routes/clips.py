"""
HeartBeat Engine - Video Clips Routes
Montreal Canadiens Advanced Analytics Assistant

API endpoints for serving video clips and thumbnails with role-based access control.

UPDATED: Now serves generated clips from data/clips/generated with range request support
"""

import os
import logging
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Header
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from orchestrator.utils.state import UserContext
from ..dependencies import get_current_user_context, get_user_context_allow_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clips", tags=["clips"])

# Path to generated clips and DuckDB index
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
GENERATED_CLIPS_DIR = WORKSPACE_ROOT / "data/clips/generated"

# Import DuckDB index
import sys
sys.path.append(str(WORKSPACE_ROOT / "orchestrator/tools"))
from clip_index_db import get_clip_index

# Get global index instance
clip_index = get_clip_index()


def _find_clip_by_id(clip_id: str) -> Optional[dict]:
    """Find a clip in the DuckDB index by clip_id"""
    return clip_index.find_by_clip_id(clip_id)

@router.get("/")
async def list_clips(
    player_id: Optional[str] = None,
    game_id: Optional[str] = None,
    event_type: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 100,
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    List available clips with optional filtering.
    
    Query parameters:
    - player_id: Filter by player ID
    - game_id: Filter by game ID
    - event_type: Filter by event type
    - team: Filter by team code
    - limit: Max results (default 100)
    
    Returns clip metadata from DuckDB index.
    """
    
    try:
        # Build query filters
        filters = {}
        if player_id:
            filters['player_ids'] = [player_id]
        if game_id:
            filters['game_ids'] = [game_id]
        if event_type:
            filters['event_types'] = [event_type]
        if team:
            filters['team_codes'] = [team]
        
        # Query DuckDB index
        all_clips = clip_index.query_clips(**filters, limit=limit)
        
        # Apply RBAC filtering
        clips_list = []
        for clip_data in all_clips:
            # Check access
            clip_meta = {
                'player_id': clip_data.get('player_id'),
                'team_code': clip_data.get('team_code')
            }
            
            if _user_can_access_clip_simple(user_context, clip_meta):
                clips_list.append({
                    'clip_id': clip_data['clip_id'],
                    'duration_s': clip_data.get('duration_s'),
                    'file_size_bytes': clip_data.get('file_size_bytes'),
                    'created_at': str(clip_data.get('created_at', '')),
                    'player_id': clip_data.get('player_id'),
                    'player_name': clip_data.get('player_name'),
                    'event_type': clip_data.get('event_type'),
                    'outcome': clip_data.get('outcome'),
                    'zone': clip_data.get('zone'),
                    'game_id': clip_data.get('game_id'),
                    'game_date': clip_data.get('game_date'),
                    'period': clip_data.get('period'),
                    'team_code': clip_data.get('team_code'),
                    'opponent_code': clip_data.get('opponent_code'),
                    'video_url': f"/api/v1/clips/{clip_data['clip_id']}/video",
                    'thumbnail_url': f"/api/v1/clips/{clip_data['clip_id']}/thumbnail"
                })
        
        logger.info(f"Listed {len(clips_list)} clips for user {user_context.role.value}")
        return {"clips": clips_list, "total": len(clips_list)}
        
    except Exception as e:
        logger.error(f"Error listing clips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clips"
        )

@router.get("/{clip_id}/video")
async def serve_video(
    clip_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    user_context: UserContext = Depends(get_user_context_allow_query)
):
    """
    Serve a video clip file with range request support for streaming.
    
    Supports HTTP Range requests for progressive video playback.
    """
    
    try:
        # Find the clip in our index
        clip_data = _find_clip_by_id(clip_id)
        
        if not clip_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # If HLS variant exists, prefer serving HLS playlist for better UX
        try:
            extra = clip_data.get('extra_metadata')
            hls_playlist = None
            if isinstance(extra, str) and extra:
                meta = json.loads(extra)
                hls_playlist = meta.get('hls_playlist')
            if hls_playlist and Path(hls_playlist).exists():
                # Redirect to playlist (frontend <video> can handle HLS via hls.js if needed)
                return FileResponse(
                    path=hls_playlist,
                    media_type="application/vnd.apple.mpegurl",
                    filename=f"{clip_id}.m3u8",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Content-Disposition": f"inline; filename={clip_id}.m3u8",
                    }
                )
        except Exception:
            pass

        # Get MP4 path
        video_path = Path(clip_data['output_path'])
        
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video file not found"
            )
        
        # Check user access permissions (prefer extra_metadata JSON; fallback to row fields)
        meta = {}
        try:
            extra = clip_data.get('extra_metadata')
            if isinstance(extra, str) and extra:
                meta = json.loads(extra)
        except Exception:
            meta = {}
        if not meta:
            meta = {
                'player_id': clip_data.get('player_id'),
                'team_code': clip_data.get('team_code'),
            }
        if not _user_can_access_clip_simple(user_context, meta):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Determine content type
        content_type = _get_content_type(video_path.suffix.lower())
        file_size = video_path.stat().st_size

        logger.info(f"Serving video {clip_id} to user {user_context.role.value}")

        # Parse range header (e.g., "bytes=0-" or "bytes=1000-2000")
        if range and isinstance(range, str) and range.startswith("bytes="):
            try:
                range_spec = range.split("=", 1)[1]
                start_s, end_s = range_spec.split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_size - 1
                start = max(0, start)
                end = min(file_size - 1, end)
                if start > end:
                    start = 0
                    end = file_size - 1
                chunk_size = (end - start) + 1

                def iter_file(path: Path, offset: int, length: int, buf_size: int = 1024 * 1024):
                    with open(path, 'rb') as f:
                        f.seek(offset)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(buf_size, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk

                headers = {
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(chunk_size),
                    "Cache-Control": "public, max-age=3600",
                    "Content-Disposition": f"inline; filename={clip_id}.mp4",
                }

                return StreamingResponse(
                    iter_file(video_path, start, chunk_size),
                    status_code=206,
                    media_type=content_type,
                    headers=headers,
                )
            except Exception as e:
                logger.debug(f"Range header parse failed, falling back to full file: {e}")

        # Fallback: serve full file
        return FileResponse(
            path=str(video_path),
            media_type=content_type,
            filename=f"{clip_id}.mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename={clip_id}.mp4",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving video {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve video"
        )

@router.get("/{clip_id}/thumbnail")
async def serve_thumbnail(
    clip_id: str,
    user_context: UserContext = Depends(get_user_context_allow_query)
):
    """
    Serve a video thumbnail image.
    
    Returns a thumbnail image for the video clip.
    """
    
    try:
        # Find the clip in our index
        clip_data = _find_clip_by_id(clip_id)
        
        if not clip_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Get thumbnail path
        thumbnail_path = Path(clip_data.get('thumbnail_path', ''))
        
        if not thumbnail_path.exists():
            logger.error(f"Thumbnail not found: {thumbnail_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found"
            )
        
        # Check user access permissions (prefer extra_metadata; fallback to row fields)
        meta = {}
        try:
            extra = clip_data.get('extra_metadata')
            if isinstance(extra, str) and extra:
                meta = json.loads(extra)
        except Exception:
            meta = {}
        if not meta:
            meta = {
                'player_id': clip_data.get('player_id'),
                'team_code': clip_data.get('team_code'),
            }
        if not _user_can_access_clip_simple(user_context, meta):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        logger.info(f"Serving thumbnail for clip {clip_id}")
        
        return FileResponse(
            path=str(thumbnail_path),
            media_type="image/jpeg",
            filename=f"thumb_{clip_id}.jpg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": f"inline; filename=thumb_{clip_id}.jpg"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve thumbnail"
        )

@router.get("/{clip_id}/metadata")
async def get_clip_metadata(
    clip_id: str,
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    Get detailed metadata for a specific clip.
    
    Returns comprehensive clip information.
    """
    
    try:
        # Find the clip in our index
        clip_data = _find_clip_by_id(clip_id)
        
        if not clip_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Check user access permissions
        metadata = clip_data.get('metadata', {})
        if not _user_can_access_clip_simple(user_context, metadata):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Compose detailed metadata (merge extra_metadata if present)
        extra = {}
        try:
            raw = clip_data.get('extra_metadata')
            if isinstance(raw, str) and raw:
                extra = json.loads(raw)
        except Exception:
            extra = {}
        merged_meta = {
            'player_id': clip_data.get('player_id'),
            'player_name': clip_data.get('player_name'),
            'team_code': clip_data.get('team_code'),
            'opponent_code': clip_data.get('opponent_code'),
            'event_type': clip_data.get('event_type'),
            'outcome': clip_data.get('outcome'),
            'zone': clip_data.get('zone'),
        }
        if isinstance(extra, dict):
            merged_meta.update({k: v for k, v in extra.items() if k not in merged_meta or merged_meta[k] is None})

        # Return detailed metadata
        return {
            "clip_id": clip_data['clip_id'],
            "output_path": clip_data['output_path'],
            "thumbnail_path": clip_data.get('thumbnail_path'),
            "duration_s": clip_data.get('duration_s'),
            "file_size_bytes": clip_data.get('file_size_bytes'),
            "created_at": clip_data.get('created_at'),
            "metadata": merged_meta
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata for clip {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clip metadata"
        )


def _user_can_access_clip_simple(user_context: UserContext, clip_metadata: dict) -> bool:
    """Check if user has access to a specific clip (simplified for generated clips)"""
    
    from orchestrator.config.settings import UserRole
    # Dev override to simplify media testing
    if os.getenv("CLIPS_OPEN_ACCESS", "0") == "1":
        return True
    
    # Staff and analysts have full access
    if user_context.role in [UserRole.COACH, UserRole.ANALYST, UserRole.STAFF, UserRole.SCOUT]:
        return True
    
    # Players can access their own clips
    if user_context.role == UserRole.PLAYER:
        user_player_id = user_context.preferences.get('player_id', '')
        clip_player_id = clip_metadata.get('player_id', '')
        
        # Compare player IDs (normalize to handle .0 suffix)
        user_id_normalized = str(user_player_id).replace('.0', '')
        clip_id_normalized = str(clip_player_id).replace('.0', '')
        
        return user_id_normalized == clip_id_normalized
    
    return False  # Default deny


@router.get("/stats")
async def get_index_stats(
    user_context: UserContext = Depends(get_current_user_context)
):
    """
    Get clip index statistics.
    
    Returns aggregate stats about all clips in the index.
    """
    try:
        stats = clip_index.get_stats()
        logger.info(f"Index stats requested by {user_context.role.value}")
        return stats
    except Exception as e:
        logger.error(f"Error getting index stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get index statistics"
        )


def _get_content_type(file_extension: str) -> str:
    """Get content type for video file"""
    
    content_types = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm"
    }
    
    return content_types.get(file_extension, "application/octet-stream")
