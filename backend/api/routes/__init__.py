"""
HeartBeat Engine - API Routes
Montreal Canadiens Advanced Analytics Assistant

FastAPI route definitions for the HeartBeat Engine.
"""

from .auth import router as auth_router
from .query import router as query_router
from .analytics import router as analytics_router
from .prospects import router as prospects_router
