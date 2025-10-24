"""
HeartBeat Engine - OMS REST API
NHL Advanced Analytics Platform

FastAPI REST API for Ontology Metadata Service.
Provides endpoints for schema management, object access, link traversal, and actions.
"""

from .routes import router as oms_router

__all__ = ["oms_router"]

