"""
HeartBeat Engine - LangGraph Orchestrator Configuration
Montreal Canadiens Advanced Analytics Assistant

Configuration settings for the LangGraph-based agent orchestrator.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class UserRole(Enum):
    """User roles for identity-aware data access"""
    COACH = "coach"
    PLAYER = "player"
    ANALYST = "analyst"
    STAFF = "staff"
    SCOUT = "scout"

@dataclass
class ModelConfig:
    """Model configuration for different deployment scenarios"""
    # Primary model (when training completes)
    primary_model_endpoint: str = ""  # SageMaker endpoint URL
    primary_model_name: str = "heartbeat-deepseek-r1-qwen-32b"
    
    # Fallback model for development/testing
    fallback_model: str = "gpt-4o-mini"  # For initial testing
    fallback_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Model parameters
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.95

@dataclass
class PineconeConfig:
    """Pinecone vector database configuration"""
    api_key: str = os.getenv("PINECONE_API_KEY", "")
    environment: str = "us-east-1"
    index_name: str = "heartbeat-unified-index"
    namespace: str = "mtl-2024-2025"
    top_k: int = 5
    score_threshold: float = 0.7

@dataclass
class ParquetConfig:
    """Parquet analytics configuration"""
    # Use environment variable or calculate absolute path from repo root
    data_directory: str = os.getenv("DATA_DIRECTORY", "")  # Will be set in __init__
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    max_query_results: int = 1000

@dataclass
class BigQueryConfig:
    """BigQuery configuration for GCP-native analytics"""
    enabled: bool = os.getenv("USE_BIGQUERY_ANALYTICS", "false").lower() == "true"
    project_id: str = os.getenv("GCP_PROJECT", "heartbeat-474020")
    dataset_core: str = os.getenv("BQ_DATASET_CORE", "core")
    dataset_raw: str = "raw"
    dataset_analytics: str = "analytics"
    dataset_ontology: str = "ontology"
    location: str = "us-east1"

@dataclass
class GCSConfig:
    """Google Cloud Storage configuration"""
    bucket_name: str = os.getenv("GCS_LAKE_BUCKET", "heartbeat-474020-lake")
    bronze_prefix: str = "bronze/"
    silver_prefix: str = "silver/"
    gold_prefix: str = "gold/"
    rag_prefix: str = "rag/"

@dataclass
class VertexConfig:
    """Vertex AI Vector Search configuration"""
    project_id: str = os.getenv("VERTEX_PROJECT", os.getenv("GCP_PROJECT", "heartbeat-474020"))
    location: str = os.getenv("VERTEX_LOCATION", os.getenv("GCP_REGION", "us-east1"))
    index_endpoint: str = os.getenv("VERTEX_INDEX_ENDPOINT", "")  # projects/*/locations/*/indexEndpoints/*
    deployed_index_id: str = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")
    embedding_model: str = os.getenv("VERTEX_EMBEDDING_MODEL", "text-embedding-005")

@dataclass
class OrchestrationConfig:
    """Core orchestration settings"""
    max_iterations: int = 10
    timeout_seconds: int = 30
    enable_debug_logging: bool = True
    
    # Tool execution settings
    enable_parallel_tools: bool = True
    max_parallel_tools: int = 3
    tool_timeout_seconds: int = 15
    
    # Response generation
    max_response_length: int = 2000
    require_citations: bool = True

class OrchestratorSettings:
    """Main settings class for HeartBeat orchestrator"""
    
    def __init__(self):
        self.model = ModelConfig()
        self.pinecone = PineconeConfig()
        self.parquet = ParquetConfig()
        self.orchestration = OrchestrationConfig()
        
        # GCP Phase 1 configurations
        self.bigquery = BigQueryConfig()
        self.gcs = GCSConfig()
        self.vertex = VertexConfig()
        
        # Vector backend selection
        self.vector_backend = os.getenv("VECTOR_BACKEND", "vertex")
        
        # OpenRouter environment-based settings
        self.openrouter = {
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "http_referer": os.getenv("OPENROUTER_HTTP_REFERER", ""),
            "app_title": os.getenv("OPENROUTER_APP_TITLE", "HeartBeat Engine"),
            "timeout": float(os.getenv("OPENROUTER_TIMEOUT", "30.0")),
        }
        # Resolve absolute paths to avoid CWD-dependent behavior
        from pathlib import Path
        # Repo root is two levels up from this file: orchestrator/config/settings.py
        repo_root = Path(__file__).resolve().parents[2]
        
        # Set data directory to absolute path
        if not self.parquet.data_directory:
            self.parquet.data_directory = str(repo_root / "data" / "processed")
        
        # Set clips base path
        default_clips_path = os.getenv("CLIPS_BASE_PATH", str(repo_root / "data" / "clips"))
        self.clips_base_path: str = default_clips_path
        
        # Role-based data access permissions
        self.role_permissions = {
            UserRole.COACH: {
                "data_scope": ["team", "player", "game", "strategy"],
                "advanced_metrics": True,
                "opponent_data": True,
                "tactical_analysis": True
            },
            UserRole.PLAYER: {
                "data_scope": ["personal", "team", "game"],
                "advanced_metrics": True,
                "opponent_data": False,
                "tactical_analysis": False
            },
            UserRole.ANALYST: {
                "data_scope": ["team", "player", "game", "league"],
                "advanced_metrics": True,
                "opponent_data": True,
                "tactical_analysis": True
            },
            UserRole.STAFF: {
                "data_scope": ["team", "game"],
                "advanced_metrics": False,
                "opponent_data": False,
                "tactical_analysis": False
            },
            UserRole.SCOUT: {
                "data_scope": ["player", "opponent", "league"],
                "advanced_metrics": True,
                "opponent_data": True,
                "tactical_analysis": True
            }
        }
    
    def get_user_permissions(self, role: UserRole) -> Dict[str, Any]:
        """Get permissions for a specific user role"""
        return self.role_permissions.get(role, self.role_permissions[UserRole.STAFF])
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        issues = []

        if not os.path.exists(self.parquet.data_directory):
            issues.append(f"Parquet data directory not found: {self.parquet.data_directory}")
        
        # At least one model path should be available (OpenRouter or fallback)
        if not self.openrouter.get("api_key") and not self.model.fallback_api_key and not self.model.primary_model_endpoint:
            issues.append("No OpenRouter API key, fallback API key, or primary model endpoint configured")
        
        if issues:
            print("Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        
        return True

# Global settings instance
settings = OrchestratorSettings()
