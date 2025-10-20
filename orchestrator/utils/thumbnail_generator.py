"""
HeartBeat Engine - Video Thumbnail Generator
Montreal Canadiens Advanced Analytics Assistant

Generates thumbnails from video clips for the clip retrieval system.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import tempfile

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """
    Generates thumbnails from video clips using ffmpeg and PIL.
    
    Features:
    - Extract frames from video at specified timestamps
    - Generate placeholder thumbnails when video processing fails
    - Military-style thumbnail overlays with hockey metadata
    - Efficient caching and file management
    """
    
    def __init__(self, thumbnails_directory: str = "data/clips/thumbnails"):
        self.thumbnails_dir = Path(thumbnails_directory)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        # Thumbnail settings
        self.thumbnail_size = (320, 180)  # 16:9 aspect ratio
        self.quality = 85
        self.frame_position = 5.0  # Extract frame at 5 seconds
        
        # Check if ffmpeg is available
        self.ffmpeg_available = self._check_ffmpeg_availability()
        
        if not self.ffmpeg_available:
            logger.warning("ffmpeg not available - using placeholder thumbnails only")
    
    def _check_ffmpeg_availability(self) -> bool:
        """Check if ffmpeg is available on the system"""
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    async def generate_thumbnail(
        self, 
        video_path: str, 
        clip_id: str,
        player_name: str = "",
        event_type: str = "",
        force_regenerate: bool = False
    ) -> Optional[str]:
        """
        Generate thumbnail for a video clip.
        
        Args:
            video_path: Path to the video file
            clip_id: Unique identifier for the clip
            player_name: Player name for overlay
            event_type: Event type for overlay
            force_regenerate: Force regeneration even if thumbnail exists
            
        Returns:
            Path to generated thumbnail file, or None if failed
        """
        
        try:
            # Generate thumbnail filename
            thumbnail_filename = f"{clip_id}.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_filename
            
            # Check if thumbnail already exists
            if thumbnail_path.exists() and not force_regenerate:
                logger.info(f"Thumbnail already exists: {thumbnail_path}")
                return str(thumbnail_path)
            
            # Verify video file exists
            if not Path(video_path).exists():
                logger.error(f"Video file not found: {video_path}")
                return await self._create_placeholder_thumbnail(
                    thumbnail_path, player_name, event_type
                )
            
            # Try to extract frame using ffmpeg
            if self.ffmpeg_available:
                success = await self._extract_video_frame(video_path, thumbnail_path)
                if success:
                    # Add overlay information
                    await self._add_thumbnail_overlay(
                        thumbnail_path, player_name, event_type
                    )
                    logger.info(f"Generated thumbnail: {thumbnail_path}")
                    return str(thumbnail_path)
            
            # Fallback to placeholder
            return await self._create_placeholder_thumbnail(
                thumbnail_path, player_name, event_type
            )
            
        except Exception as e:
            logger.error(f"Error generating thumbnail for {clip_id}: {str(e)}")
            return None
    
    async def _extract_video_frame(self, video_path: str, output_path: Path) -> bool:
        """Extract a frame from video using ffmpeg"""
        
        try:
            # FFmpeg command to extract frame
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(self.frame_position),  # Seek to position
                "-vframes", "1",  # Extract 1 frame
                "-vf", f"scale={self.thumbnail_size[0]}:{self.thumbnail_size[1]}",
                "-q:v", "2",  # High quality
                "-y",  # Overwrite output
                str(output_path)
            ]
            
            # Execute ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and output_path.exists():
                return True
            else:
                logger.warning(f"ffmpeg failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timeout during frame extraction")
            return False
        except Exception as e:
            logger.error(f"Frame extraction failed: {str(e)}")
            return False
    
    async def _create_placeholder_thumbnail(
        self, 
        output_path: Path, 
        player_name: str = "",
        event_type: str = ""
    ) -> str:
        """Create a placeholder thumbnail with military styling"""
        
        try:
            # Create image with military dark theme
            img = Image.new('RGB', self.thumbnail_size, color=(17, 24, 39))  # gray-900
            draw = ImageDraw.Draw(img)
            
            # Try to load a font (fallback to default if not available)
            try:
                # Try to use a monospace font for military look
                font_large = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 20)
                font_small = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 12)
            except (OSError, IOError):
                # Fallback to default font
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Draw borders for military look
            border_color = (75, 85, 99)  # gray-600
            draw.rectangle([2, 2, self.thumbnail_size[0]-3, self.thumbnail_size[1]-3], 
                         outline=border_color, width=2)
            
            # Draw MTL logo area (placeholder)
            logo_size = 40
            logo_x = (self.thumbnail_size[0] - logo_size) // 2
            logo_y = 30
            draw.rectangle([logo_x, logo_y, logo_x + logo_size, logo_y + logo_size], 
                         outline=(175, 30, 45), width=2)  # Red border
            draw.text((logo_x + 10, logo_y + 15), "MTL", fill=(175, 30, 45), font=font_small)
            
            # Draw player name
            if player_name:
                text_width = draw.textlength(player_name, font=font_small)
                text_x = (self.thumbnail_size[0] - text_width) // 2
                draw.text((text_x, 90), player_name, fill=(255, 255, 255), font=font_small)
            
            # Draw event type
            if event_type:
                event_upper = event_type.upper()
                text_width = draw.textlength(event_upper, font=font_small)
                text_x = (self.thumbnail_size[0] - text_width) // 2
                draw.text((text_x, 110), event_upper, fill=(156, 163, 175), font=font_small)
            
            # Draw "NO VIDEO" indicator
            no_video_text = "VIDEO CLIP"
            text_width = draw.textlength(no_video_text, font=font_small)
            text_x = (self.thumbnail_size[0] - text_width) // 2
            draw.text((text_x, 140), no_video_text, fill=(107, 114, 128), font=font_small)
            
            # Save thumbnail
            img.save(output_path, "JPEG", quality=self.quality)
            
            logger.info(f"Created placeholder thumbnail: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to create placeholder thumbnail: {str(e)}")
            
            # Create minimal fallback
            try:
                img = Image.new('RGB', self.thumbnail_size, color=(31, 41, 55))
                img.save(output_path, "JPEG", quality=70)
                return str(output_path)
            except Exception as fallback_error:
                logger.error(f"Even fallback thumbnail failed: {str(fallback_error)}")
                return None
    
    async def _add_thumbnail_overlay(
        self, 
        thumbnail_path: Path, 
        player_name: str = "",
        event_type: str = ""
    ) -> None:
        """Add military-style overlay to extracted video thumbnail"""
        
        try:
            # Open existing thumbnail
            img = Image.open(thumbnail_path)
            draw = ImageDraw.Draw(img)
            
            # Load font
            try:
                font_small = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 12)
            except (OSError, IOError):
                font_small = ImageFont.load_default()
            
            # Add semi-transparent overlay at bottom
            overlay_height = 30
            overlay_y = self.thumbnail_size[1] - overlay_height
            
            # Create overlay rectangle
            overlay = Image.new('RGBA', self.thumbnail_size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Draw bottom overlay
            overlay_draw.rectangle([0, overlay_y, self.thumbnail_size[0], self.thumbnail_size[1]], 
                                 fill=(0, 0, 0, 128))  # Semi-transparent black
            
            # Composite overlay
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            img = img.convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Add text overlay
            if player_name:
                draw.text((10, overlay_y + 5), player_name, 
                         fill=(255, 255, 255), font=font_small)
            
            if event_type:
                event_text = event_type.upper()
                text_width = draw.textlength(event_text, font=font_small)
                draw.text((self.thumbnail_size[0] - text_width - 10, overlay_y + 5), 
                         event_text, fill=(175, 30, 45), font=font_small)
            
            # Save with overlay
            img.save(thumbnail_path, "JPEG", quality=self.quality)
            
        except Exception as e:
            logger.error(f"Failed to add thumbnail overlay: {str(e)}")
            # Continue without overlay - original thumbnail is still usable
    
    def get_thumbnail_path(self, clip_id: str) -> Optional[str]:
        """Get path to existing thumbnail"""
        
        thumbnail_path = self.thumbnails_dir / f"{clip_id}.jpg"
        
        if thumbnail_path.exists():
            return str(thumbnail_path)
        
        return None
    
    def cleanup_old_thumbnails(self, max_age_days: int = 30) -> int:
        """Clean up old thumbnail files"""
        
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        cleaned_count = 0
        
        try:
            for thumbnail_file in self.thumbnails_dir.glob("*.jpg"):
                file_age = current_time - thumbnail_file.stat().st_mtime
                
                if file_age > max_age_seconds:
                    thumbnail_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old thumbnails")
                
        except Exception as e:
            logger.error(f"Error during thumbnail cleanup: {str(e)}")
        
        return cleaned_count

# Global thumbnail generator instance
thumbnail_generator = ThumbnailGenerator()
