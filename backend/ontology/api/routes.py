"""
HeartBeat Engine - OMS REST API Routes
NHL Advanced Analytics Platform

FastAPI endpoints for Ontology Metadata Service operations.
Enterprise-grade API with policy enforcement, audit logging, and performance optimization.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path as PathParam
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import time

from ..services.registry import SchemaRegistry
from ..services.policy_engine import PolicyEngine, PolicyDecision
from ..services.resolvers import BaseResolver
from ..models.metadata import SchemaVersion, ObjectTypeDef, LinkTypeDef, ActionTypeDef, AuditLog
from orchestrator.utils.state import UserContext
from .dependencies import (
    get_db,
    get_schema_registry,
    get_policy_engine,
    get_resolver,
    get_current_user_context
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontology/v1", tags=["ontology"])


# Request/Response Models

class ObjectResponse(BaseModel):
    """Response model for object data"""
    object_type: str
    object_id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ObjectListResponse(BaseModel):
    """Response model for object list"""
    object_type: str
    objects: List[Dict[str, Any]]
    count: int
    limit: Optional[int]
    offset: Optional[int]


class LinkTraversalResponse(BaseModel):
    """Response model for link traversal"""
    from_object_type: str
    from_object_id: str
    link_type: str
    to_object_type: str
    related_objects: List[Dict[str, Any]]
    count: int


class ActionExecuteRequest(BaseModel):
    """Request model for action execution"""
    inputs: Dict[str, Any] = Field(..., description="Action input parameters")


class ActionExecuteResponse(BaseModel):
    """Response model for action execution"""
    success: bool
    action_type: str
    result: Optional[Dict[str, Any]] = None
    message: str
    execution_time_ms: int


class SchemaVersionResponse(BaseModel):
    """Response model for schema version"""
    id: int
    version: str
    namespace: str
    status: str
    is_active: bool
    created_at: datetime
    published_at: Optional[datetime]


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


# Schema Management Endpoints

@router.get(
    "/schema/versions",
    response_model=List[SchemaVersionResponse],
    summary="List schema versions",
    description="Get all ontology schema versions with metadata"
)
async def list_schema_versions(
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> List[SchemaVersionResponse]:
    """List all schema versions"""
    try:
        versions = registry.list_versions()
        
        return [
            SchemaVersionResponse(
                id=v.id,
                version=v.version,
                namespace=v.namespace,
                status=v.status,
                is_active=v.is_active,
                created_at=v.created_at,
                published_at=v.published_at
            )
            for v in versions
        ]
    except Exception as e:
        logger.error(f"Error listing schema versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/schema/versions/{version}",
    response_model=SchemaVersionResponse,
    summary="Get schema version details",
    description="Retrieve detailed information about a specific schema version"
)
async def get_schema_version(
    version: str = PathParam(..., description="Schema version string"),
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> SchemaVersionResponse:
    """Get specific schema version"""
    try:
        db_version = registry.session.query(SchemaVersion).filter(
            SchemaVersion.version == version
        ).first()
        
        if not db_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema version {version} not found"
            )
        
        return SchemaVersionResponse(
            id=db_version.id,
            version=db_version.version,
            namespace=db_version.namespace,
            status=db_version.status,
            is_active=db_version.is_active,
            created_at=db_version.created_at,
            published_at=db_version.published_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema version {version}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/schema/active",
    response_model=SchemaVersionResponse,
    summary="Get active schema version",
    description="Retrieve the currently active schema version"
)
async def get_active_schema_version(
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> SchemaVersionResponse:
    """Get active schema version"""
    try:
        active = registry.get_active_version()
        
        if not active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active schema version found"
            )
        
        return SchemaVersionResponse(
            id=active.id,
            version=active.version,
            namespace=active.namespace,
            status=active.status,
            is_active=active.is_active,
            created_at=active.created_at,
            published_at=active.published_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active schema version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Metadata Query Endpoints

@router.get(
    "/meta/objects",
    summary="List object types",
    description="Get all object type definitions from active schema"
)
async def list_object_types(
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> List[Dict[str, Any]]:
    """List all object types"""
    try:
        object_types = registry.get_all_object_types()
        return [obj.to_dict() for obj in object_types]
    except Exception as e:
        logger.error(f"Error listing object types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/meta/objects/{object_type}",
    summary="Get object type definition",
    description="Retrieve detailed definition for a specific object type"
)
async def get_object_type_definition(
    object_type: str = PathParam(..., description="Object type name"),
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> Dict[str, Any]:
    """Get object type definition"""
    try:
        obj_def = registry.get_object_type(object_type)
        
        if not obj_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object type {object_type} not found"
            )
        
        return obj_def.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting object type {object_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/meta/links",
    summary="List link types",
    description="Get all link type definitions from active schema"
)
async def list_link_types(
    registry: SchemaRegistry = Depends(get_schema_registry),
    user: UserContext = Depends(get_current_user_context)
) -> List[Dict[str, Any]]:
    """List all link types"""
    try:
        link_types = registry.get_all_link_types()
        return [link.to_dict() for link in link_types]
    except Exception as e:
        logger.error(f"Error listing link types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Object Data Access Endpoints

@router.get(
    "/objects/{object_type}/{object_id}",
    response_model=ObjectResponse,
    summary="Get object by ID",
    description="Retrieve single object with policy enforcement"
)
async def get_object_by_id(
    object_type: str = PathParam(..., description="Object type name"),
    object_id: str = PathParam(..., description="Object primary key value"),
    properties: Optional[str] = Query(None, description="Comma-separated list of properties to retrieve"),
    registry: SchemaRegistry = Depends(get_schema_registry),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    user: UserContext = Depends(get_current_user_context),
    db: Session = Depends(get_db)
) -> ObjectResponse:
    """Get object by ID with policy enforcement"""
    start_time = time.perf_counter()
    
    try:
        # Get object type definition
        obj_def = registry.get_object_type(object_type)
        if not obj_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object type {object_type} not found"
            )
        
        # Get security policy
        policy = None
        if obj_def.security_policy_ref:
            policy = registry.get_security_policy(obj_def.security_policy_ref)
        
        # Evaluate access
        decision = policy_engine.evaluate_access(
            user_context=user,
            operation="read",
            target_type="object",
            target_id=object_id,
            policy=policy
        )
        
        if not decision.allowed:
            _record_audit(db, user, "get_object", object_type, object_id, False, decision.reason)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason
            )
        
        # Get resolver
        backend = obj_def.resolver_backend or "bigquery"
        resolver = get_resolver(backend)
        
        # Parse properties
        prop_list = properties.split(",") if properties else None
        
        # Fetch data
        data = resolver.get_by_id_cached(object_type, object_id, prop_list)
        
        if not data:
            _record_audit(db, user, "get_object", object_type, object_id, False, "Object not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object {object_type}/{object_id} not found"
            )
        
        # Apply column filters
        filtered_data = policy_engine.apply_column_filters(data, decision.column_filters)
        
        # Record successful access
        execution_time = int((time.perf_counter() - start_time) * 1000)
        _record_audit(db, user, "get_object", object_type, object_id, True, None, execution_time)
        
        return ObjectResponse(
            object_type=object_type,
            object_id=object_id,
            data=filtered_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting object {object_type}/{object_id}: {e}")
        _record_audit(db, user, "get_object", object_type, object_id, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/objects/{object_type}",
    response_model=ObjectListResponse,
    summary="Query objects by filter",
    description="Retrieve multiple objects matching filters with policy enforcement"
)
async def query_objects(
    object_type: str = PathParam(..., description="Object type name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    properties: Optional[str] = Query(None, description="Comma-separated properties"),
    registry: SchemaRegistry = Depends(get_schema_registry),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    user: UserContext = Depends(get_current_user_context),
    db: Session = Depends(get_db)
) -> ObjectListResponse:
    """Query objects with filters"""
    start_time = time.perf_counter()
    
    try:
        # Get object type definition
        obj_def = registry.get_object_type(object_type)
        if not obj_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object type {object_type} not found"
            )
        
        # Get security policy
        policy = None
        if obj_def.security_policy_ref:
            policy = registry.get_security_policy(obj_def.security_policy_ref)
        
        # Evaluate access
        decision = policy_engine.evaluate_access(
            user_context=user,
            operation="list",
            target_type="object",
            policy=policy
        )
        
        if not decision.allowed:
            _record_audit(db, user, "query_objects", object_type, None, False, decision.reason)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason
            )
        
        # Build filters from row filter (team scoping, self-only, etc.)
        filters = {}
        # In production, parse decision.row_filter into filter dict
        # For now, just empty filters
        
        # Get resolver
        backend = obj_def.resolver_backend or "bigquery"
        resolver = get_resolver(backend)
        
        # Parse properties
        prop_list = properties.split(",") if properties else None
        
        # Fetch data
        objects = resolver.get_by_filter(
            object_type=object_type,
            filters=filters,
            properties=prop_list,
            limit=limit,
            offset=offset
        )
        
        # Apply column filters to each object
        filtered_objects = [
            policy_engine.apply_column_filters(obj, decision.column_filters)
            for obj in objects
        ]
        
        # Record success
        execution_time = int((time.perf_counter() - start_time) * 1000)
        _record_audit(db, user, "query_objects", object_type, None, True, None, execution_time)
        
        return ObjectListResponse(
            object_type=object_type,
            objects=filtered_objects,
            count=len(filtered_objects),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying objects {object_type}: {e}")
        _record_audit(db, user, "query_objects", object_type, None, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Link Traversal Endpoint

@router.get(
    "/objects/{object_type}/{object_id}/links/{link_type}",
    response_model=LinkTraversalResponse,
    summary="Traverse link",
    description="Navigate from one object to related objects via link with policy enforcement"
)
async def traverse_link(
    object_type: str = PathParam(..., description="Source object type"),
    object_id: str = PathParam(..., description="Source object ID"),
    link_type: str = PathParam(..., description="Link type name"),
    limit: int = Query(100, ge=1, le=1000),
    properties: Optional[str] = Query(None, description="Properties to retrieve from target objects"),
    registry: SchemaRegistry = Depends(get_schema_registry),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    user: UserContext = Depends(get_current_user_context),
    db: Session = Depends(get_db)
) -> LinkTraversalResponse:
    """Traverse link to related objects"""
    start_time = time.perf_counter()
    
    try:
        # Get link definition
        link_def = registry.get_link_type(link_type)
        if not link_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Link type {link_type} not found"
            )
        
        # Validate source object type
        if link_def.from_object != object_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Link {link_type} does not start from {object_type}"
            )
        
        # Get security policy for link
        policy = None
        if link_def.security_policy_ref:
            policy = registry.get_security_policy(link_def.security_policy_ref)
        
        # Evaluate access
        decision = policy_engine.evaluate_access(
            user_context=user,
            operation="read",
            target_type="link",
            policy=policy
        )
        
        if not decision.allowed:
            _record_audit(db, user, "traverse_link", f"{object_type}:{link_type}", object_id, False, decision.reason)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason
            )
        
        # Get target object definition to determine resolver
        target_obj_def = registry.get_object_type(link_def.to_object)
        if not target_obj_def:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Target object type {link_def.to_object} not found"
            )
        
        # Get resolver (use target object's resolver backend)
        backend = target_obj_def.resolver_backend or "bigquery"
        resolver = get_resolver(backend)
        
        # Parse properties
        prop_list = properties.split(",") if properties else None
        
        # Traverse link
        related_objects = resolver.traverse_link(
            from_object_type=object_type,
            from_object_id=object_id,
            link_type=link_type,
            to_object_type=link_def.to_object,
            link_config=link_def.resolver_config or {},
            properties=prop_list,
            limit=limit
        )
        
        # Apply column filters
        filtered_objects = [
            policy_engine.apply_column_filters(obj, decision.column_filters)
            for obj in related_objects
        ]
        
        # Record success
        execution_time = int((time.perf_counter() - start_time) * 1000)
        _record_audit(db, user, "traverse_link", f"{object_type}:{link_type}", object_id, True, None, execution_time)
        
        return LinkTraversalResponse(
            from_object_type=object_type,
            from_object_id=object_id,
            link_type=link_type,
            to_object_type=link_def.to_object,
            related_objects=filtered_objects,
            count=len(filtered_objects)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error traversing link {object_type}/{object_id} -> {link_type}: {e}")
        _record_audit(db, user, "traverse_link", f"{object_type}:{link_type}", object_id, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Helper Functions

def _record_audit(
    db: Session,
    user: UserContext,
    operation: str,
    target_type: str,
    target_id: Optional[str],
    success: bool,
    error_message: Optional[str],
    execution_time_ms: Optional[int] = None
) -> None:
    """Record audit log entry"""
    try:
        audit = AuditLog(
            actor_id=user.user_id,
            actor_role=user.role.value,
            operation=operation,
            target_type=target_type,
            target_id=target_id,
            success=success,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        db.rollback()

