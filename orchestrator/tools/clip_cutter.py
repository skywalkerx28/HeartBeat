#!/usr/bin/env python3
"""
FFmpeg Clip Cutter for Hockey Video Segments
Cuts precise segments from period MP4s with bounded parallelism

PRODUCTION: Uses DuckDB index for thread-safe metadata storage
"""

import subprocess
import shlex
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time

# Import DuckDB index
try:
    from .clip_index_db import DuckDBClipIndex, ClipIndexEntry, get_clip_index
except ImportError:
    from clip_index_db import DuckDBClipIndex, ClipIndexEntry, get_clip_index


@dataclass
class ClipCutRequest:
    """Request to cut a clip from a source video"""
    source_video: Path
    start_seconds: float
    end_seconds: float
    output_path: Path
    clip_id: str
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> float:
        """Clip duration in seconds"""
        return self.end_seconds - self.start_seconds
    
    def validate(self) -> bool:
        """Validate the cut request"""
        if not self.source_video.exists():
            return False
        if self.start_seconds < 0:
            return False
        if self.end_seconds <= self.start_seconds:
            return False
        if self.duration > 300:  # Max 5 minutes per clip
            return False
        return True


@dataclass
class ClipCutResult:
    """Result of a clip cutting operation"""
    success: bool
    clip_id: str
    output_path: Optional[Path]
    thumbnail_path: Optional[Path]
    duration_s: Optional[float]
    file_size_bytes: Optional[int]
    processing_time_s: float
    error_message: Optional[str] = None


class FFmpegClipCutter:
    """
    Cuts video clips using FFmpeg with quality and performance optimization
    
    PRODUCTION: Thread-safe with DuckDB index
    """
    
    def __init__(
        self, 
        output_base_dir: str = "/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/generated",
        max_workers: int = 2,
        ffmpeg_preset: str = "ultrafast",
        crf: int = 20,
        use_duckdb: bool = True,
        max_clip_duration_s: int = 120,
        enable_stream_copy_fallback: bool = True,
        enable_hls: bool = True,
        hls_segment_time: int = 2
    ):
        """
        Args:
            output_base_dir: Base directory for generated clips
            max_workers: Max parallel FFmpeg threads (default 3)
            ffmpeg_preset: FFmpeg encoding preset (ultrafast, faster, fast, medium)
            crf: Constant Rate Factor for quality (18-28, lower = better)
            use_duckdb: Use DuckDB index (True) or legacy JSON (False)
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.ffmpeg_preset = ffmpeg_preset
        self.crf = crf
        self.use_duckdb = use_duckdb
        self.max_clip_duration_s = max_clip_duration_s
        self.enable_stream_copy_fallback = enable_stream_copy_fallback
        self.enable_hls = enable_hls
        self.hls_segment_time = hls_segment_time
        
        # Initialize index (DuckDB or JSON fallback)
        if use_duckdb:
            self.db_index = get_clip_index()
        else:
            self.index_file = self.output_base_dir / "clip_index.json"
            self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load clip index from disk (JSON fallback)"""
        if hasattr(self, 'index_file') and self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_index(self):
        """Save clip index to disk (JSON fallback - deprecated)"""
        if not self.use_duckdb and hasattr(self, 'index_file'):
            try:
                with open(self.index_file, 'w') as f:
                    json.dump(self.index, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to save clip index: {e}")
    
    def _get_clip_hash(self, source_video: Path, start_s: float, end_s: float) -> str:
        """Generate deterministic hash for clip caching"""
        key = f"{source_video.name}:{start_s:.2f}:{end_s:.2f}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def _check_cache(self, clip_hash: str) -> Optional[Dict]:
        """Check if clip already exists in cache"""
        if self.use_duckdb:
            cached = self.db_index.find_by_hash(clip_hash)
            if cached and Path(cached['output_path']).exists():
                return cached
            return None
        else:
            # JSON fallback
            if clip_hash in self.index:
                cached = self.index[clip_hash]
                if Path(cached['output_path']).exists():
                    return cached
            return None
    
    def _clamp_to_video_bounds(self, source_video: Path, start_s: float, end_s: float) -> tuple[float, float]:
        """
        Clamp start/end times to video duration
        Returns: (clamped_start, clamped_end)
        """
        # Get video duration using ffprobe
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(source_video)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            
            # Clamp values
            start_s = max(0.0, start_s)
            end_s = min(duration, end_s)
            
            # Ensure we have at least 0.1s clip
            if end_s <= start_s:
                end_s = min(start_s + 0.1, duration)
            
            return start_s, end_s
        except Exception as e:
            print(f"Warning: Could not determine video duration: {e}")
            # Return original values if probe fails
            return start_s, end_s
    
    def cut_clip(self, request: ClipCutRequest, force: bool = False) -> ClipCutResult:
        """
        Cut a single clip from source video
        
        Args:
            request: ClipCutRequest with source, timestamps, output
            force: Force re-cutting even if cached
        
        Returns:
            ClipCutResult with success status and paths
        """
        start_time = time.time()
        
        # Validate request
        if not request.validate():
            return ClipCutResult(
                success=False,
                clip_id=request.clip_id,
                output_path=None,
                thumbnail_path=None,
                duration_s=None,
                file_size_bytes=None,
                processing_time_s=time.time() - start_time,
                error_message="Invalid clip request"
            )
        
        # Check cache
        if not force:
            clip_hash = self._get_clip_hash(request.source_video, request.start_seconds, request.end_seconds)
            cached = self._check_cache(clip_hash)
            if cached:
                print(f"Cache hit for {request.clip_id}")
                return ClipCutResult(
                    success=True,
                    clip_id=request.clip_id,
                    output_path=Path(cached['output_path']),
                    thumbnail_path=Path(cached['thumbnail_path']) if cached.get('thumbnail_path') else None,
                    duration_s=cached['duration_s'],
                    file_size_bytes=cached['file_size_bytes'],
                    processing_time_s=time.time() - start_time
                )
        
        # Clamp to video bounds
        start_s, end_s = self._clamp_to_video_bounds(
            request.source_video,
            request.start_seconds,
            request.end_seconds
        )
        # Cap duration for reliability
        duration = min(end_s - start_s, float(self.max_clip_duration_s))
        
        # Ensure output directory exists
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prefer stream copy for long shifts to avoid long re-encodes
        is_shift = isinstance(request.metadata, dict) and request.metadata.get('mode') == 'shift'
        # Prefer copy for all shifts to maximize reliability and speed
        prefer_copy = bool(is_shift)

        # Build FFmpeg command for cutting (re-encode path)
        # Use input seeking for speed + re-encode for exact segment
        cmd_reencode = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-ss', str(start_s),
            '-i', str(request.source_video),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', self.ffmpeg_preset,
            '-crf', str(self.crf),
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-pix_fmt', 'yuv420p',
            '-y',
            str(request.output_path)
        ]
        # Dynamic timeout scaled by requested duration (re-encode is slower)
        timeout_reencode = int(min(600, max(60, duration * 2.0)))
        
        try:
            # Optionally try copy-first for long shifts
            if prefer_copy and self.enable_stream_copy_fallback:
                preroll = 2.0 if start_s >= 2.0 else 0.0
                copy_start = max(0.0, start_s - preroll)
                copy_duration = min(duration + preroll, float(self.max_clip_duration_s))
                tmp_copy_pref = request.output_path.with_suffix('.copy.pref.tmp.mp4')
                cmd_copy_pref = [
                    'ffmpeg','-hide_banner','-loglevel','error',
                    '-ss', str(copy_start),
                    '-i', str(request.source_video),
                    '-t', str(copy_duration),
                    '-c','copy','-movflags','+faststart','-avoid_negative_ts','1',
                    '-y', str(tmp_copy_pref)
                ]
                timeout_copy_pref = int(min(300, max(60, copy_duration * 1.2)))
                subprocess.run(cmd_copy_pref, capture_output=True, text=True, check=True, timeout=timeout_copy_pref)
                tmp_copy_pref.replace(request.output_path)
            else:
                # Run FFmpeg re-encode
                result = subprocess.run(
                    cmd_reencode,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=timeout_reencode
                )
            
            # Generate thumbnail (5s into clip or midpoint if shorter)
            thumbnail_path = request.output_path.with_suffix('.jpg')
            thumb_time = min(5.0, duration / 2.0)
            
            thumb_cmd = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-ss', str(thumb_time),
                '-i', str(request.output_path),
                '-frames:v', '1',
                '-qscale:v', '2',  # Quality (2-5 is good)
                '-y',
                str(thumbnail_path)
            ]
            
            subprocess.run(thumb_cmd, capture_output=True, check=True, timeout=10)
            
            # Optional: Generate HLS playlist (from the freshly written MP4)
            hls_playlist_path = None
            if self.enable_hls:
                try:
                    hls_dir = request.output_path.parent / f"hls_{request.output_path.stem}"
                    hls_dir.mkdir(parents=True, exist_ok=True)
                    hls_playlist_path = hls_dir / "playlist.m3u8"
                    hls_segment_pattern = hls_dir / "seg_%03d.ts"
                    hls_cmd = [
                        'ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-i', str(request.output_path),
                        '-c', 'copy',
                        '-start_number', '0',
                        '-hls_time', str(self.hls_segment_time),
                        '-hls_playlist_type', 'vod',
                        '-hls_segment_filename', str(hls_segment_pattern),
                        str(hls_playlist_path)
                    ]
                    subprocess.run(hls_cmd, capture_output=True, text=True, check=True, timeout=60)
                except Exception:
                    hls_playlist_path = None
            
            # Get file size
            file_size = request.output_path.stat().st_size
            
            # Update index (DuckDB or JSON)
            clip_hash = self._get_clip_hash(request.source_video, request.start_seconds, request.end_seconds)
            
            if self.use_duckdb:
                # Create DuckDB index entry
                metadata = request.metadata or {}
                if hls_playlist_path:
                    try:
                        metadata['hls_playlist'] = str(hls_playlist_path)
                    except Exception:
                        pass
                index_entry = ClipIndexEntry(
                    clip_id=request.clip_id,
                    clip_hash=clip_hash,
                    output_path=str(request.output_path),
                    thumbnail_path=str(thumbnail_path),
                    source_video=str(request.source_video),
                    start_timecode_s=start_s,
                    end_timecode_s=end_s,
                    duration_s=duration,
                    game_id=metadata.get('game_id', 'unknown'),
                    game_date=metadata.get('game_id', 'unknown')[:8] if metadata.get('game_id') else '20250101',
                    season=metadata.get('season', '2025-2026'),
                    period=metadata.get('period', 1),
                    player_id=metadata.get('player_id', ''),
                    player_name=metadata.get('player_name'),
                    team_code=metadata.get('team_code', ''),
                    opponent_code=metadata.get('opponent_code', ''),
                    event_type=metadata.get('event_type', ''),
                    outcome=metadata.get('outcome'),
                    zone=metadata.get('zone'),
                    file_size_bytes=file_size,
                    processing_time_s=time.time() - start_time,
                    cache_hit=False,
                    extra_metadata=json.dumps(metadata) if metadata else None
                )
                
                # Insert into DuckDB (queued, thread-safe)
                self.db_index.insert_clip(index_entry, block=False)
            else:
                # JSON fallback
                self.index[clip_hash] = {
                    'clip_id': request.clip_id,
                    'output_path': str(request.output_path),
                    'thumbnail_path': str(thumbnail_path),
                    'duration_s': duration,
                    'file_size_bytes': file_size,
                    'created_at': time.time(),
                    'metadata': request.metadata
                }
                self._save_index()
            
            return ClipCutResult(
                success=True,
                clip_id=request.clip_id,
                output_path=request.output_path,
                thumbnail_path=thumbnail_path,
                duration_s=duration,
                file_size_bytes=file_size,
                processing_time_s=time.time() - start_time
            )
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            # Fallback: fast stream copy (keyframe aligned)
            if not self.enable_stream_copy_fallback:
                return ClipCutResult(
                    success=False,
                    clip_id=request.clip_id,
                    output_path=None,
                    thumbnail_path=None,
                    duration_s=None,
                    file_size_bytes=None,
                    processing_time_s=time.time() - start_time,
                    error_message=f"FFmpeg re-encode failed: {getattr(e, 'stderr', str(e))}"
                )

            # Try copy with slight pre-roll to hit keyframe
            preroll = 2.0 if start_s >= 2.0 else 0.0
            copy_start = max(0.0, start_s - preroll)
            copy_duration = min(duration + preroll, float(self.max_clip_duration_s))

            tmp_copy = request.output_path.with_suffix('.copy.tmp.mp4')
            cmd_copy = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-ss', str(copy_start),
                '-i', str(request.source_video),
                '-t', str(copy_duration),
                '-c', 'copy',
                '-movflags', '+faststart',
                '-avoid_negative_ts', '1',
                '-y', str(tmp_copy)
            ]
            try:
                timeout_copy = int(min(300, max(60, copy_duration * 1.2)))
                subprocess.run(cmd_copy, capture_output=True, text=True, check=True, timeout=timeout_copy)
                # Rename temp to final
                tmp_copy.replace(request.output_path)

                # Generate thumbnail and index (same as success flow)
                thumbnail_path = request.output_path.with_suffix('.jpg')
                thumb_time = min(5.0, copy_duration / 2.0)
                thumb_cmd = [
                    'ffmpeg','-hide_banner','-loglevel','error','-ss', str(thumb_time),
                    '-i', str(request.output_path),
                    '-frames:v','1','-qscale:v','2','-y', str(thumbnail_path)
                ]
                subprocess.run(thumb_cmd, capture_output=True, check=True, timeout=10)

                # Optional HLS packaging from MP4
                hls_playlist_path = None
                if self.enable_hls:
                    try:
                        hls_dir = request.output_path.parent / f"hls_{request.output_path.stem}"
                        hls_dir.mkdir(parents=True, exist_ok=True)
                        hls_playlist_path = hls_dir / "playlist.m3u8"
                        hls_segment_pattern = hls_dir / "seg_%03d.ts"
                        hls_cmd = [
                            'ffmpeg', '-hide_banner', '-loglevel', 'error',
                            '-i', str(request.output_path),
                            '-c', 'copy',
                            '-start_number', '0',
                            '-hls_time', str(self.hls_segment_time),
                            '-hls_playlist_type', 'vod',
                            '-hls_segment_filename', str(hls_segment_pattern),
                            str(hls_playlist_path)
                        ]
                        subprocess.run(hls_cmd, capture_output=True, text=True, check=True, timeout=60)
                    except Exception:
                        hls_playlist_path = None

                file_size = request.output_path.stat().st_size

                clip_hash = self._get_clip_hash(request.source_video, request.start_seconds, request.end_seconds)
                if self.use_duckdb:
                    metadata = request.metadata or {}
                    if hls_playlist_path:
                        try:
                            metadata['hls_playlist'] = str(hls_playlist_path)
                        except Exception:
                            pass
                    index_entry = ClipIndexEntry(
                        clip_id=request.clip_id,
                        clip_hash=clip_hash,
                        output_path=str(request.output_path),
                        thumbnail_path=str(thumbnail_path),
                        source_video=str(request.source_video),
                        start_timecode_s=copy_start,
                        end_timecode_s=copy_start + copy_duration,
                        duration_s=copy_duration,
                        game_id=metadata.get('game_id', 'unknown'),
                        game_date=metadata.get('game_id', 'unknown')[:8] if metadata.get('game_id') else '20250101',
                        season=metadata.get('season', '2025-2026'),
                        period=metadata.get('period', 1),
                        player_id=metadata.get('player_id', ''),
                        player_name=metadata.get('player_name'),
                        team_code=metadata.get('team_code', ''),
                        opponent_code=metadata.get('opponent_code', ''),
                        event_type=metadata.get('event_type', ''),
                        outcome=metadata.get('outcome'),
                        zone=metadata.get('zone'),
                        file_size_bytes=file_size,
                        processing_time_s=time.time() - start_time,
                        cache_hit=False,
                        extra_metadata=json.dumps(metadata) if metadata else None
                    )
                    self.db_index.insert_clip(index_entry, block=False)

                return ClipCutResult(
                    success=True,
                    clip_id=request.clip_id,
                    output_path=request.output_path,
                    thumbnail_path=thumbnail_path,
                    duration_s=copy_duration,
                    file_size_bytes=file_size,
                    processing_time_s=time.time() - start_time
                )

            except Exception as e2:
                return ClipCutResult(
                    success=False,
                    clip_id=request.clip_id,
                    output_path=None,
                    thumbnail_path=None,
                    duration_s=None,
                    file_size_bytes=None,
                    processing_time_s=time.time() - start_time,
                    error_message=f"FFmpeg re-encode failed then copy fallback failed: {str(e2)}"
                )
        except Exception as e:
            return ClipCutResult(
                success=False,
                clip_id=request.clip_id,
                output_path=None,
                thumbnail_path=None,
                duration_s=None,
                file_size_bytes=None,
                processing_time_s=time.time() - start_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def cut_clips_parallel(self, requests: List[ClipCutRequest], force: bool = False) -> List[ClipCutResult]:
        """
        Cut multiple clips in parallel with bounded workers
        
        PRODUCTION: Uses ThreadPoolExecutor for shared DuckDB access
        
        Args:
            requests: List of ClipCutRequest
            force: Force re-cutting even if cached
        
        Returns:
            List of ClipCutResult in same order as requests
        """
        results = [None] * len(requests)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_idx = {
                executor.submit(self.cut_clip, req, force): idx
                for idx, req in enumerate(requests)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    results[idx] = result
                    
                    status = "OK" if result.success else "FAIL"
                    suffix = ""
                    if not result.success and getattr(result, 'error_message', None):
                        suffix = f" - {result.error_message[:180]}"
                    print(f"[{status}] {result.clip_id} ({result.processing_time_s:.1f}s){suffix}")
                    
                except Exception as e:
                    print(f"Worker exception for request {idx}: {e}")
                    results[idx] = ClipCutResult(
                        success=False,
                        clip_id=requests[idx].clip_id,
                        output_path=None,
                        thumbnail_path=None,
                        duration_s=None,
                        file_size_bytes=None,
                        processing_time_s=0,
                        error_message=f"Worker exception: {str(e)}"
                    )
        
        return results


def main():
    """Demo: cut a test clip"""
    cutter = FFmpegClipCutter(max_workers=2)
    
    # Test clip from MTL vs CHI period 1
    source = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/clips/2025-2026/team/MTL/p1-20251011-NHL-MTLvsCHI-20252026-20031.mp4")
    
    # Cut a clip from 220s to 228s (8-second clip from our earlier query)
    request = ClipCutRequest(
        source_video=source,
        start_seconds=220.0,
        end_seconds=228.0,
        output_path=Path(cutter.output_base_dir) / "test" / "clip_test_220s_dzone_exit.mp4",
        clip_id="test_clip_220s",
        metadata={
            "game_id": "20031",
            "period": 1,
            "event_type": "CONTROLLED EXIT FROM DZ",
            "player_id": "8473422"
        }
    )
    
    print(f"\nCutting test clip...")
    print(f"Source: {request.source_video.name}")
    print(f"Time: {request.start_seconds}s - {request.end_seconds}s ({request.duration}s)")
    print(f"Output: {request.output_path}")
    
    result = cutter.cut_clip(request)
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Output: {result.output_path}")
        print(f"  Thumbnail: {result.thumbnail_path}")
        print(f"  Duration: {result.duration_s:.2f}s")
        print(f"  File size: {result.file_size_bytes / 1024:.1f} KB")
        print(f"  Processing time: {result.processing_time_s:.2f}s")
    else:
        print(f"  Error: {result.error_message}")


if __name__ == "__main__":
    main()

