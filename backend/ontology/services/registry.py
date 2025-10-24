"""
HeartBeat Engine - Schema Registry Service
NHL Advanced Analytics Platform

Manages ontology schema loading, versioning, and metadata access.
Enterprise-grade implementation with caching and performance optimization.
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime
import logging
import yaml
from pathlib import Path

from ..models.metadata import (
    SchemaVersion, ObjectTypeDef, PropertyDef, LinkTypeDef,
    ActionTypeDef, SecurityPolicy, PolicyRule
)
from ..schemas.validator import SchemaLoader, SchemaValidator

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Schema registry for managing ontology versions and metadata.
    
    Provides high-performance access to schema definitions with caching
    and efficient database queries.
    """
    
    def __init__(self, session: Session, schema_dir: Optional[Path] = None):
        """
        Initialize schema registry.
        
        Args:
            session: SQLAlchemy session for database operations
            schema_dir: Directory containing YAML schema files
        """
        self.session = session
        self.schema_loader = SchemaLoader(schema_dir)
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._active_version: Optional[str] = None
        
        logger.info("SchemaRegistry initialized")
    
    def load_schema_from_yaml(
        self,
        schema_path: Path,
        created_by: str,
        auto_publish: bool = False
    ) -> SchemaVersion:
        """
        Load schema from YAML file and persist to database.
        
        Args:
            schema_path: Path to YAML schema file
            created_by: User identifier who is loading the schema
            auto_publish: Automatically publish after loading
            
        Returns:
            Created SchemaVersion instance
            
        Raises:
            ValueError: If schema validation fails
        """
        logger.info(f"Loading schema from {schema_path}")
        
        # Load and validate YAML schema
        schema = self.schema_loader.load_schema()
        
        version_str = schema.get("version", "0.0.0")
        namespace = schema.get("namespace", "nhl.heartbeat")
        description = schema.get("description", "")
        
        # Check if version already exists
        existing = self.session.query(SchemaVersion).filter(
            SchemaVersion.version == version_str
        ).first()
        
        if existing:
            raise ValueError(f"Schema version {version_str} already exists")
        
        # Create schema version
        schema_version = SchemaVersion(
            version=version_str,
            namespace=namespace,
            description=description,
            created_by=created_by,
            status="draft",
            changelog=schema.get("metadata", {}).get("changelog", []),
            metadata_json=schema.get("metadata", {}),
            schema_snapshot=schema
        )
        
        self.session.add(schema_version)
        self.session.flush()
        
        # Load object types
        self._load_object_types(schema_version, schema.get("object_types", {}))
        
        # Load link types
        self._load_link_types(schema_version, schema.get("link_types", {}))
        
        # Load action types
        self._load_action_types(schema_version, schema.get("action_types", {}))
        
        # Load security policies
        self._load_security_policies(schema_version, schema.get("security_policies", {}))
        
        self.session.commit()
        
        logger.info(f"Schema {version_str} loaded successfully (ID: {schema_version.id})")
        
        if auto_publish:
            self.publish_schema(version_str, created_by)
        
        # Invalidate cache
        self._cache.clear()
        
        return schema_version
    
    def _load_object_types(
        self,
        schema_version: SchemaVersion,
        object_types: Dict[str, Any]
    ) -> None:
        """Load object type definitions into database"""
        for obj_name, obj_def in object_types.items():
            resolver = obj_def.get("resolver", {})
            
            obj_type = ObjectTypeDef(
                schema_version_id=schema_version.id,
                name=obj_name,
                description=obj_def.get("description", ""),
                primary_key=obj_def.get("primary_key", ""),
                resolver_backend=resolver.get("backend"),
                resolver_config=resolver,
                security_policy_ref=obj_def.get("security_policy")
            )
            
            self.session.add(obj_type)
            self.session.flush()
            
            # Load properties
            for prop_name, prop_def in obj_def.get("properties", {}).items():
                prop = PropertyDef(
                    object_type_id=obj_type.id,
                    name=prop_name,
                    property_type=prop_def.get("type", "string"),
                    required=prop_def.get("required", False),
                    description=prop_def.get("description", ""),
                    enum_values=prop_def.get("enum"),
                    default_value=prop_def.get("default"),
                    constraints=prop_def.get("constraints"),
                    metadata_json=prop_def
                )
                self.session.add(prop)
    
    def _load_link_types(
        self,
        schema_version: SchemaVersion,
        link_types: Dict[str, Any]
    ) -> None:
        """Load link type definitions into database"""
        for link_name, link_def in link_types.items():
            resolver = link_def.get("resolver", {})
            
            link_type = LinkTypeDef(
                schema_version_id=schema_version.id,
                name=link_name,
                description=link_def.get("description", ""),
                from_object=link_def.get("from_object", ""),
                to_object=link_def.get("to_object", ""),
                cardinality=link_def.get("cardinality", "one_to_many"),
                resolver_type=resolver.get("type"),
                resolver_config=resolver,
                security_policy_ref=link_def.get("security_policy")
            )
            
            self.session.add(link_type)
    
    def _load_action_types(
        self,
        schema_version: SchemaVersion,
        action_types: Dict[str, Any]
    ) -> None:
        """Load action type definitions into database"""
        for action_name, action_def in action_types.items():
            action_type = ActionTypeDef(
                schema_version_id=schema_version.id,
                name=action_name,
                description=action_def.get("description", ""),
                input_schema=action_def.get("input_schema", {}),
                preconditions=action_def.get("preconditions", []),
                effects=action_def.get("effects", []),
                security_policy_ref=action_def.get("security_policy", ""),
                timeout_seconds=action_def.get("timeout_seconds", 30),
                is_idempotent=action_def.get("is_idempotent", False)
            )
            
            self.session.add(action_type)
    
    def _load_security_policies(
        self,
        schema_version: SchemaVersion,
        policies: Dict[str, Any]
    ) -> None:
        """Load security policy definitions into database"""
        for policy_name, policy_def in policies.items():
            policy = SecurityPolicy(
                schema_version_id=schema_version.id,
                name=policy_name,
                description=policy_def.get("description", ""),
                target_type="global",
                metadata_json=policy_def
            )
            
            self.session.add(policy)
            self.session.flush()
            
            # Load policy rules
            for idx, rule_def in enumerate(policy_def.get("rules", [])):
                rule = PolicyRule(
                    policy_id=policy.id,
                    role=rule_def.get("role", ""),
                    access_level=rule_def.get("access", "none"),
                    scope=rule_def.get("scope"),
                    column_filters=rule_def.get("column_filters"),
                    row_filter_expr=rule_def.get("row_filter"),
                    conditions=rule_def.get("conditions"),
                    priority=100 - idx
                )
                self.session.add(rule)
    
    def publish_schema(self, version: str, published_by: str) -> SchemaVersion:
        """
        Publish a draft schema version.
        
        Args:
            version: Version string to publish
            published_by: User identifier who is publishing
            
        Returns:
            Published SchemaVersion
            
        Raises:
            ValueError: If version not found or not in draft status
        """
        schema_version = self.session.query(SchemaVersion).filter(
            SchemaVersion.version == version
        ).first()
        
        if not schema_version:
            raise ValueError(f"Schema version {version} not found")
        
        if schema_version.status != "draft":
            raise ValueError(f"Schema version {version} is not in draft status")
        
        # Deactivate current active version
        self.session.query(SchemaVersion).filter(
            SchemaVersion.is_active == True
        ).update({"is_active": False})
        
        # Publish and activate new version
        schema_version.status = "published"
        schema_version.is_active = True
        schema_version.published_at = datetime.utcnow()
        
        self.session.commit()
        
        logger.info(f"Schema {version} published and activated by {published_by}")
        
        # Invalidate cache
        self._cache.clear()
        self._active_version = version
        
        return schema_version
    
    def get_active_version(self) -> Optional[SchemaVersion]:
        """Get currently active schema version"""
        if self._active_version and self._active_version in self._cache:
            return self._cache[self._active_version].get("version_obj")
        
        schema_version = self.session.query(SchemaVersion).filter(
            SchemaVersion.is_active == True
        ).first()
        
        if schema_version:
            self._active_version = schema_version.version
        
        return schema_version
    
    def get_object_type(
        self,
        object_name: str,
        version: Optional[str] = None
    ) -> Optional[ObjectTypeDef]:
        """
        Get object type definition.
        
        Args:
            object_name: Object type name
            version: Schema version (uses active if not specified)
            
        Returns:
            ObjectTypeDef or None if not found
        """
        schema_version = self._get_version(version)
        if not schema_version:
            return None
        
        return self.session.query(ObjectTypeDef).filter(
            and_(
                ObjectTypeDef.schema_version_id == schema_version.id,
                ObjectTypeDef.name == object_name
            )
        ).first()
    
    def get_all_object_types(
        self,
        version: Optional[str] = None
    ) -> List[ObjectTypeDef]:
        """Get all object types for a schema version"""
        schema_version = self._get_version(version)
        if not schema_version:
            return []
        
        return self.session.query(ObjectTypeDef).filter(
            ObjectTypeDef.schema_version_id == schema_version.id
        ).all()
    
    def get_link_type(
        self,
        link_name: str,
        version: Optional[str] = None
    ) -> Optional[LinkTypeDef]:
        """Get link type definition"""
        schema_version = self._get_version(version)
        if not schema_version:
            return None
        
        return self.session.query(LinkTypeDef).filter(
            and_(
                LinkTypeDef.schema_version_id == schema_version.id,
                LinkTypeDef.name == link_name
            )
        ).first()
    
    def get_all_link_types(
        self,
        version: Optional[str] = None
    ) -> List[LinkTypeDef]:
        """Get all link types for a schema version"""
        schema_version = self._get_version(version)
        if not schema_version:
            return []
        
        return self.session.query(LinkTypeDef).filter(
            LinkTypeDef.schema_version_id == schema_version.id
        ).all()
    
    def get_action_type(
        self,
        action_name: str,
        version: Optional[str] = None
    ) -> Optional[ActionTypeDef]:
        """Get action type definition"""
        schema_version = self._get_version(version)
        if not schema_version:
            return None
        
        return self.session.query(ActionTypeDef).filter(
            and_(
                ActionTypeDef.schema_version_id == schema_version.id,
                ActionTypeDef.name == action_name
            )
        ).first()
    
    def get_security_policy(
        self,
        policy_name: str,
        version: Optional[str] = None
    ) -> Optional[SecurityPolicy]:
        """Get security policy definition"""
        schema_version = self._get_version(version)
        if not schema_version:
            return None
        
        return self.session.query(SecurityPolicy).filter(
            and_(
                SecurityPolicy.schema_version_id == schema_version.id,
                SecurityPolicy.name == policy_name
            )
        ).first()
    
    def list_versions(self) -> List[SchemaVersion]:
        """List all schema versions ordered by creation date"""
        return self.session.query(SchemaVersion).order_by(
            desc(SchemaVersion.created_at)
        ).all()
    
    def _get_version(self, version: Optional[str] = None) -> Optional[SchemaVersion]:
        """Get schema version (active if not specified)"""
        if version:
            return self.session.query(SchemaVersion).filter(
                SchemaVersion.version == version
            ).first()
        else:
            return self.get_active_version()

