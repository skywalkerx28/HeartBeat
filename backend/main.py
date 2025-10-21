"""
HeartBeat Engine - FastAPI Backend
Montreal Canadiens Advanced Analytics Assistant

FastAPI wrapper around the existing LangGraph orchestrator.
Provides HTTP API endpoints for the Next.js frontend.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure local project paths take precedence over site-packages
project_root = os.path.join(os.path.dirname(__file__), '..')
backend_dir = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from orchestrator.config.settings import UserRole, settings
from orchestrator.utils.state import UserContext

# Import API routes
from api.routes.auth import router as auth_router
from api.routes.query import router as query_router
from api.routes.analytics import router as analytics_router
from api.routes.clips import router as clips_router
from api.routes.market import router as market_router
from api.routes.nhl_proxy import router as nhl_proxy_router
from api.routes.analytics_gold import router as analytics_gold_router
from api.routes.predictions import router as predictions_router
from api.routes.profiles import router as profiles_router
from api.routes.team_profiles import router as team_profiles_router
from api.routes.prospects import router as prospects_router
from api.routes.search import router as search_router
from api.routes.news import router as news_router
# No legacy orchestrator injection required

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Orchestrator selection: OpenRouter only
USE_OPENROUTER = True

# Global orchestrator instance (legacy path removed)
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator
    
    # Startup
    logger.info("Starting HeartBeat Engine API...")
    
    # No legacy orchestrator initialization (OpenRouter path does not require it)

    # Validate configuration regardless of orchestrator flavor
    if settings.validate_config():
        logger.info("Configuration validation passed")
    else:
        logger.warning("Configuration validation failed - some features may not work")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HeartBeat Engine API...")

# Create FastAPI application
app = FastAPI(
    title="HeartBeat Engine API",
    description="Montreal Canadiens Advanced Analytics Assistant",
    version="2.1.0",
    lifespan=lifespan
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3008",
        "http://localhost:3009",
        "http://192.168.0.118:3000",
        "http://192.168.0.118:3008",
        "http://192.168.0.118:3009",
        "http://192.168.6.45:3000",    # Current network IP
        "http://192.168.6.45:3001",
        "http://192.168.6.45:3008",
        "http://192.168.6.45:3009",
        "http://10.121.114.200:3000",  # Previous network IP
        "http://10.121.114.200:3001",
        "http://10.121.114.200:3008",
        "http://10.121.114.200:3009"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth_router)
app.include_router(query_router)
app.include_router(analytics_router)
app.include_router(clips_router)
app.include_router(market_router)
app.include_router(nhl_proxy_router)
app.include_router(analytics_gold_router)
app.include_router(predictions_router)
app.include_router(profiles_router)
app.include_router(team_profiles_router)
app.include_router(prospects_router)
app.include_router(search_router)
app.include_router(news_router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "HeartBeat Engine API",
        "version": "2.1.0",
        "status": "online",
        "orchestrator_available": orchestrator is not None,
        "description": "Montreal Canadiens Advanced Analytics Assistant"
    }

@app.get("/api/v1/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "orchestrator_type": "openrouter",
        "openrouter_enabled": True,
        "classic_orchestrator": orchestrator is not None,
        "qwen3_orchestrator": None,
        "vertex_configured": bool(getattr(settings.vertex, 'index_endpoint', '')), 
        "data_directory_exists": os.path.exists(settings.parquet.data_directory),
        "configuration_valid": settings.validate_config(),
    }

if __name__ == "__main__":
    import uvicorn
    import os as _os
    port = int(_os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        log_level="info"
    )
