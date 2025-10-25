"""
HeartBeat Engine - OMS Metadata Models
NHL Advanced Analytics Platform

SQLAlchemy models for storing ontology metadata with versioning and audit trails.
Production-grade implementation with PostgreSQL optimization (oms schema, JSONB).
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, ARRAY,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional
import json

Base = declarative_base()


class SchemaVersion(Base):
    """Schema version tracking with changelog and metadata"""
    __tablename__ = "schema_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'review', 'published', 'deprecated')",
            name="ck_schema_version_status"
        ),
        Index("ix_schema_version_active", "is_active", "version"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False, unique=True, index=True)
    namespace = Column(String(255), nullable=False, default="nhl.heartbeat")
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="draft", index=True)
    
    changelog = Column(JSONB, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    schema_snapshot = Column(JSONB, nullable=True)
    
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<SchemaVersion(version='{self.version}', status='{self.status}')>"


class ObjectTypeDef(Base):
    """Object type definitions with properties and resolver configuration"""
    __tablename__ = "object_types"
    __table_args__ = (
        UniqueConstraint("schema_version_id", "name", name="uq_object_type_version_name"),
        Index("ix_object_type_resolver", "resolver_backend"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version_id = Column(Integer, ForeignKey("oms.schema_versions.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    primary_key = Column(String(255), nullable=False)
    
    resolver_backend = Column(String(50), nullable=True)
    resolver_config = Column(JSONB, nullable=True)
    
    security_policy_ref = Column(String(255), nullable=True, index=True)
    
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    properties = relationship("PropertyDef", back_populates="object_type", cascade="all, delete-orphan")
    schema_version = relationship("SchemaVersion")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "primary_key": self.primary_key,
            "resolver": {
                "backend": self.resolver_backend,
                "config": self.resolver_config
            },
            "security_policy": self.security_policy_ref,
            "properties": [p.to_dict() for p in self.properties] if self.properties else []
        }
    
    def __repr__(self) -> str:
        return f"<ObjectTypeDef(name='{self.name}', pk='{self.primary_key}')>"


class PropertyDef(Base):
    """Property definitions for object types with type constraints"""
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("object_type_id", "name", name="uq_property_object_name"),
        CheckConstraint(
            "property_type IN ('string', 'integer', 'float', 'boolean', 'date', 'datetime', 'text', 'object', 'array')",
            name="ck_property_type_valid"
        ),
        Index("ix_property_type", "property_type"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    object_type_id = Column(Integer, ForeignKey("oms.object_types.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    property_type = Column(String(50), nullable=False)
    required = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)
    
    enum_values = Column(ARRAY(String), nullable=True)  # PostgreSQL array
    default_value = Column(String(255), nullable=True)
    
    constraints = Column(JSONB, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    
    object_type = relationship("ObjectTypeDef", back_populates="properties")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "name": self.name,
            "type": self.property_type,
            "required": self.required,
            "description": self.description
        }
        if self.enum_values:
            result["enum"] = self.enum_values
        if self.default_value:
            result["default"] = self.default_value
        if self.constraints:
            result["constraints"] = self.constraints
        return result
    
    def __repr__(self) -> str:
        return f"<PropertyDef(name='{self.name}', type='{self.property_type}')>"


class LinkTypeDef(Base):
    """Link type definitions establishing relationships between objects"""
    __tablename__ = "link_types"
    __table_args__ = (
        UniqueConstraint("schema_version_id", "name", name="uq_link_type_version_name"),
        CheckConstraint(
            "cardinality IN ('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many')",
            name="ck_link_cardinality_valid"
        ),
        Index("ix_link_type_objects", "from_object", "to_object"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version_id = Column(Integer, ForeignKey("oms.schema_versions.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    from_object = Column(String(255), nullable=False, index=True)
    to_object = Column(String(255), nullable=False, index=True)
    cardinality = Column(String(50), nullable=False)
    
    resolver_type = Column(String(50), nullable=True)
    resolver_config = Column(JSONB, nullable=True)
    
    security_policy_ref = Column(String(255), nullable=True, index=True)
    
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    schema_version = relationship("SchemaVersion")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "from_object": self.from_object,
            "to_object": self.to_object,
            "cardinality": self.cardinality,
            "resolver": {
                "type": self.resolver_type,
                "config": self.resolver_config
            },
            "security_policy": self.security_policy_ref
        }
    
    def __repr__(self) -> str:
        return f"<LinkTypeDef(name='{self.name}', {self.from_object} -> {self.to_object})>"


class ActionTypeDef(Base):
    """Action type definitions for governed business operations"""
    __tablename__ = "action_types"
    __table_args__ = (
        UniqueConstraint("schema_version_id", "name", name="uq_action_type_version_name"),
        CheckConstraint("timeout_seconds > 0 AND timeout_seconds <= 300", name="ck_action_timeout_range"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version_id = Column(Integer, ForeignKey("oms.schema_versions.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    input_schema = Column(JSONB, nullable=False)
    preconditions = Column(JSONB, nullable=True)
    effects = Column(JSONB, nullable=True)
    
    security_policy_ref = Column(String(255), nullable=False, index=True)
    
    timeout_seconds = Column(Integer, nullable=False, default=30)
    is_idempotent = Column(Boolean, nullable=False, default=False)
    
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    schema_version = relationship("SchemaVersion")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "preconditions": self.preconditions,
            "effects": self.effects,
            "security_policy": self.security_policy_ref,
            "timeout_seconds": self.timeout_seconds,
            "is_idempotent": self.is_idempotent
        }
    
    def __repr__(self) -> str:
        return f"<ActionTypeDef(name='{self.name}')>"


class SecurityPolicy(Base):
    """Security policy definitions with role-based rules"""
    __tablename__ = "security_policies"
    __table_args__ = (
        UniqueConstraint("schema_version_id", "name", name="uq_policy_version_name"),
        CheckConstraint(
            "target_type IN ('object', 'link', 'action', 'property', 'global')",
            name="ck_policy_target_type"
        ),
        Index("ix_policy_target", "target_type", "target_ref"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version_id = Column(Integer, ForeignKey("oms.schema_versions.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    target_type = Column(String(50), nullable=False)
    target_ref = Column(String(255), nullable=True)
    
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    rules = relationship("PolicyRule", back_populates="policy", cascade="all, delete-orphan")
    schema_version = relationship("SchemaVersion")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_type": self.target_type,
            "target_ref": self.target_ref,
            "rules": [r.to_dict() for r in self.rules] if self.rules else []
        }
    
    def __repr__(self) -> str:
        return f"<SecurityPolicy(name='{self.name}')>"


class PolicyRule(Base):
    """Individual policy rules within security policies"""
    __tablename__ = "policy_rules"
    __table_args__ = (
        CheckConstraint(
            "access_level IN ('none', 'read', 'full', 'execute', 'self_only')",
            name="ck_rule_access_level"
        ),
        CheckConstraint(
            "scope IN ('all', 'team_scoped', 'self_only') OR scope IS NULL",
            name="ck_rule_scope"
        ),
        Index("ix_rule_role_access", "role", "access_level"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("oms.security_policies.id"), nullable=False, index=True)
    
    role = Column(String(50), nullable=False, index=True)
    access_level = Column(String(50), nullable=False)
    scope = Column(String(50), nullable=True)
    
    column_filters = Column(JSONB, nullable=True)
    row_filter_expr = Column(Text, nullable=True)
    conditions = Column(JSONB, nullable=True)
    
    priority = Column(Integer, nullable=False, default=100)
    
    policy = relationship("SecurityPolicy", back_populates="rules")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "role": self.role,
            "access": self.access_level,
            "priority": self.priority
        }
        if self.scope:
            result["scope"] = self.scope
        if self.column_filters:
            result["column_filters"] = self.column_filters
        if self.row_filter_expr:
            result["row_filter"] = self.row_filter_expr
        if self.conditions:
            result["conditions"] = self.conditions
        return result
    
    def __repr__(self) -> str:
        return f"<PolicyRule(role='{self.role}', access='{self.access_level}')>"


class AuditLog(Base):
    """Audit trail for all OMS operations and data access"""
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_timestamp_actor", "timestamp", "actor_id"),
        Index("ix_audit_operation_success", "operation", "success"),
        Index("ix_audit_target", "target_type", "target_id"),
        {'schema': 'oms'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    actor_id = Column(String(255), nullable=False, index=True)
    actor_role = Column(String(50), nullable=False)
    
    operation = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=True, index=True)
    
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    request_payload = Column(JSONB, nullable=True)
    response_summary = Column(JSONB, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    execution_time_ms = Column(Integer, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "operation": self.operation,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms
        }
    
    def __repr__(self) -> str:
        return f"<AuditLog(actor='{self.actor_id}', operation='{self.operation}', success={self.success})>"
