"""
HeartBeat Engine - GCS Helper
Generate signed URLs for secure video delivery from GCS
"""

from datetime import timedelta
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# Lazy imports for GCS (avoid import overhead if not using media)
try:
    from google.cloud import storage
    from google.auth.exceptions import DefaultCredentialsError
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logger.warning("Google Cloud Storage not available. Install: pip install google-cloud-storage")


class GCSMediaHelper:
    """Helper for GCS signed URL generation and media operations"""
    
    def __init__(self, bucket_name: Optional[str] = None, cdn_domain: Optional[str] = None):
        """
        Initialize GCS helper.
        
        Args:
            bucket_name: GCS bucket name (default: env MEDIA_GCS_BUCKET)
            cdn_domain: Optional Cloud CDN domain (default: env MEDIA_CDN_DOMAIN)
        """
        if not GCS_AVAILABLE:
            raise RuntimeError("Google Cloud Storage library not installed")
        
        self.bucket_name = bucket_name or os.getenv("MEDIA_GCS_BUCKET", "heartbeat-media")
        self.cdn_domain = cdn_domain or os.getenv("MEDIA_CDN_DOMAIN")
        
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS Media Helper initialized: bucket={self.bucket_name}")
        except DefaultCredentialsError:
            logger.error("GCS credentials not found. Run: gcloud auth application-default login")
            raise
    
    def generate_signed_url(
        self,
        gcs_uri: str,
        expiration_minutes: int = 60,
        method: str = "GET"
    ) -> str:
        """
        Generate a signed URL for secure GCS access.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file)
            expiration_minutes: URL validity duration (default 60 min)
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Signed URL string
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        
        # Parse gs://bucket/path
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")
        
        bucket_name, blob_path = parts
        
        if bucket_name != self.bucket_name:
            logger.warning(f"URI bucket {bucket_name} != configured bucket {self.bucket_name}")
        
        blob = self.bucket.blob(blob_path)
        
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method=method,
        )
        
        # Optionally rewrite to CDN domain
        if self.cdn_domain:
            signed_url = signed_url.replace(
                f"storage.googleapis.com/{self.bucket_name}",
                self.cdn_domain
            )
        
        return signed_url
    
    def upload_file(
        self,
        local_path: str,
        gcs_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_path: Local file path
            gcs_path: Target path in GCS (without gs:// prefix)
            content_type: Optional MIME type
            
        Returns:
            GCS URI (gs://bucket/path)
        """
        blob = self.bucket.blob(gcs_path)
        
        if content_type:
            blob.upload_from_filename(local_path, content_type=content_type)
        else:
            blob.upload_from_filename(local_path)
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {local_path} to {gcs_uri}")
        return gcs_uri
    
    def delete_file(self, gcs_uri: str) -> bool:
        """
        Delete a file from GCS.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file)
            
        Returns:
            True if deleted, False if not found
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            return False
        
        bucket_name, blob_path = parts
        blob = self.bucket.blob(blob_path)
        
        if blob.exists():
            blob.delete()
            logger.info(f"Deleted {gcs_uri}")
            return True
        
        return False
    
    def get_public_url(self, gcs_uri: str) -> str:
        """
        Get public URL for a GCS object (if bucket is public).
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file)
            
        Returns:
            Public HTTPS URL
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")
        
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}")
        
        bucket_name, blob_path = parts
        
        if self.cdn_domain:
            return f"https://{self.cdn_domain}/{blob_path}"
        
        return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"

