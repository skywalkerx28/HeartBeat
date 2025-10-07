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
class OrchestrationConfig:
    """Core orchestration settings"""
    max_iterations: int = 10
    timeout_seconds: int = 30
    enable_debug_logging: bool = True
    
    # Tool execution settings
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
        
        if not self.pinecone.api_key:
            issues.append("Pinecone API key not configured")
        
        if not os.path.exists(self.parquet.data_directory):
            issues.append(f"Parquet data directory not found: {self.parquet.data_directory}")
        
        if not self.model.primary_model_endpoint and not self.model.fallback_api_key:
            issues.append("No model endpoint or fallback API key configured")
        
        if issues:
            print("Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        
        return True

# Global settings instance
settings = OrchestratorSettings()
