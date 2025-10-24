"""
HeartBeat Engine - Ontology Schema Validator
NHL Advanced Analytics Platform

Validates and loads ontology schema definitions from YAML files.
Ensures schema integrity, type safety, and policy consistency.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    location: str
    message: str
    suggestion: Optional[str] = None


class SchemaValidator:
    """Validates ontology schema definitions"""
    
    VALID_PROPERTY_TYPES = {
        "string", "integer", "float", "boolean", "date", "datetime", 
        "text", "object", "array"
    }
    
    VALID_CARDINALITIES = {
        "one_to_one", "one_to_many", "many_to_one", "many_to_many"
    }
    
    VALID_ACCESS_LEVELS = {
        "none", "read", "full", "execute", "self_only"
    }
    
    VALID_SCOPES = {
        "all", "team_scoped", "self_only"
    }
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.object_types: Set[str] = set()
        self.link_types: Set[str] = set()
        self.action_types: Set[str] = set()
        self.policies: Set[str] = set()
    
    def validate_schema(self, schema: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate complete ontology schema.
        
        Args:
            schema: Parsed YAML schema dictionary
            
        Returns:
            List of validation issues found
        """
        self.issues = []
        self.object_types = set()
        self.link_types = set()
        self.action_types = set()
        self.policies = set()
        
        # Validate schema metadata
        self._validate_metadata(schema.get("metadata", {}))
        
        # Validate object types
        if "object_types" in schema:
            self._validate_object_types(schema["object_types"])
        else:
            self._add_error("schema", "Missing required 'object_types' section")
        
        # Validate link types
        if "link_types" in schema:
            self._validate_link_types(schema["link_types"])
        else:
            self._add_warning("schema", "No 'link_types' defined")
        
        # Validate action types
        if "action_types" in schema:
            self._validate_action_types(schema["action_types"])
        else:
            self._add_warning("schema", "No 'action_types' defined")
        
        # Validate security policies
        if "security_policies" in schema:
            self._validate_security_policies(schema["security_policies"])
        else:
            self._add_warning("schema", "No 'security_policies' defined")
        
        return self.issues
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate schema metadata section"""
        required_fields = ["author", "created", "status"]
        for field in required_fields:
            if field not in metadata:
                self._add_warning(
                    "metadata",
                    f"Missing recommended metadata field: {field}"
                )
    
    def _validate_object_types(self, object_types: Dict[str, Any]) -> None:
        """Validate all object type definitions"""
        for obj_name, obj_def in object_types.items():
            self.object_types.add(obj_name)
            self._validate_object_type(obj_name, obj_def)
    
    def _validate_object_type(self, name: str, definition: Dict[str, Any]) -> None:
        """Validate single object type definition"""
        location = f"object_types.{name}"
        
        # Check required fields
        if "primary_key" not in definition:
            self._add_error(location, "Missing required 'primary_key' field")
        
        if "properties" not in definition:
            self._add_error(location, "Missing required 'properties' field")
            return
        
        # Validate primary key exists in properties
        primary_key = definition.get("primary_key")
        properties = definition.get("properties", {})
        
        if primary_key and primary_key not in properties:
            self._add_error(
                location,
                f"Primary key '{primary_key}' not found in properties",
                f"Add property definition for '{primary_key}'"
            )
        
        # Validate each property
        for prop_name, prop_def in properties.items():
            self._validate_property(f"{location}.properties.{prop_name}", prop_def)
        
        # Validate resolver if present
        if "resolver" in definition:
            self._validate_resolver(f"{location}.resolver", definition["resolver"])
        
        # Validate security policy reference
        if "security_policy" in definition:
            policy_ref = definition["security_policy"]
            # Will validate reference later after all policies are loaded
    
    def _validate_property(self, location: str, definition: Dict[str, Any]) -> None:
        """Validate property definition"""
        if "type" not in definition:
            self._add_error(location, "Missing required 'type' field")
            return
        
        prop_type = definition["type"]
        if prop_type not in self.VALID_PROPERTY_TYPES:
            self._add_error(
                location,
                f"Invalid property type: {prop_type}",
                f"Valid types: {', '.join(self.VALID_PROPERTY_TYPES)}"
            )
        
        # Validate enum values if present
        if "enum" in definition:
            if not isinstance(definition["enum"], list):
                self._add_error(location, "Property 'enum' must be a list")
            elif len(definition["enum"]) == 0:
                self._add_warning(location, "Empty enum list")
    
    def _validate_resolver(self, location: str, resolver: Dict[str, Any]) -> None:
        """Validate data resolver configuration"""
        if "backend" not in resolver:
            self._add_error(location, "Missing required 'backend' field in resolver")
            return
        
        backend = resolver["backend"]
        if backend not in {"bigquery", "parquet", "api", "computed"}:
            self._add_warning(
                location,
                f"Unknown backend type: {backend}",
                "Valid backends: bigquery, parquet, api, computed"
            )
        
        # Backend-specific validation
        if backend == "bigquery" and "table" not in resolver:
            self._add_error(location, "BigQuery resolver missing 'table' field")
        
        if backend == "parquet" and "path" not in resolver:
            self._add_error(location, "Parquet resolver missing 'path' field")
    
    def _validate_link_types(self, link_types: Dict[str, Any]) -> None:
        """Validate all link type definitions"""
        for link_name, link_def in link_types.items():
            self.link_types.add(link_name)
            self._validate_link_type(link_name, link_def)
    
    def _validate_link_type(self, name: str, definition: Dict[str, Any]) -> None:
        """Validate single link type definition"""
        location = f"link_types.{name}"
        
        # Check required fields
        required = ["from_object", "to_object", "cardinality"]
        for field in required:
            if field not in definition:
                self._add_error(location, f"Missing required field: {field}")
        
        # Validate object references
        from_obj = definition.get("from_object")
        to_obj = definition.get("to_object")
        
        if from_obj and from_obj not in self.object_types:
            self._add_error(
                location,
                f"Link references unknown object type: {from_obj}",
                f"Define object type '{from_obj}' before referencing it"
            )
        
        if to_obj and to_obj not in self.object_types:
            self._add_error(
                location,
                f"Link references unknown object type: {to_obj}",
                f"Define object type '{to_obj}' before referencing it"
            )
        
        # Validate cardinality
        cardinality = definition.get("cardinality")
        if cardinality and cardinality not in self.VALID_CARDINALITIES:
            self._add_error(
                location,
                f"Invalid cardinality: {cardinality}",
                f"Valid cardinalities: {', '.join(self.VALID_CARDINALITIES)}"
            )
        
        # Validate resolver
        if "resolver" not in definition:
            self._add_warning(location, "Link type missing resolver configuration")
        else:
            self._validate_link_resolver(
                f"{location}.resolver",
                definition["resolver"]
            )
    
    def _validate_link_resolver(self, location: str, resolver: Dict[str, Any]) -> None:
        """Validate link resolver configuration"""
        if "type" not in resolver:
            self._add_error(location, "Missing required 'type' field")
            return
        
        resolver_type = resolver["type"]
        if resolver_type == "foreign_key":
            if "from_field" not in resolver or "to_field" not in resolver:
                self._add_error(
                    location,
                    "Foreign key resolver requires 'from_field' and 'to_field'"
                )
        elif resolver_type == "join_table":
            if "table" not in resolver:
                self._add_error(location, "Join table resolver requires 'table' field")
        else:
            self._add_warning(location, f"Unknown resolver type: {resolver_type}")
    
    def _validate_action_types(self, action_types: Dict[str, Any]) -> None:
        """Validate all action type definitions"""
        for action_name, action_def in action_types.items():
            self.action_types.add(action_name)
            self._validate_action_type(action_name, action_def)
    
    def _validate_action_type(self, name: str, definition: Dict[str, Any]) -> None:
        """Validate single action type definition"""
        location = f"action_types.{name}"
        
        # Check required fields
        if "input_schema" not in definition:
            self._add_warning(location, "Action missing 'input_schema' definition")
        
        if "preconditions" not in definition:
            self._add_warning(location, "Action missing 'preconditions' (security risk)")
        
        if "effects" not in definition:
            self._add_info(location, "Action missing 'effects' documentation")
        
        # Validate input schema
        if "input_schema" in definition:
            for param_name, param_def in definition["input_schema"].items():
                self._validate_property(
                    f"{location}.input_schema.{param_name}",
                    param_def
                )
    
    def _validate_security_policies(self, policies: Dict[str, Any]) -> None:
        """Validate all security policy definitions"""
        for policy_name, policy_def in policies.items():
            self.policies.add(policy_name)
            self._validate_security_policy(policy_name, policy_def)
    
    def _validate_security_policy(self, name: str, definition: Dict[str, Any]) -> None:
        """Validate single security policy definition"""
        location = f"security_policies.{name}"
        
        if "rules" not in definition:
            self._add_error(location, "Policy missing 'rules' field")
            return
        
        rules = definition["rules"]
        if not isinstance(rules, list):
            self._add_error(location, "Policy 'rules' must be a list")
            return
        
        # Validate each rule
        for idx, rule in enumerate(rules):
            rule_location = f"{location}.rules[{idx}]"
            
            if "role" not in rule:
                self._add_error(rule_location, "Rule missing 'role' field")
            
            if "access" not in rule:
                self._add_error(rule_location, "Rule missing 'access' field")
            else:
                access = rule["access"]
                if access not in self.VALID_ACCESS_LEVELS:
                    self._add_error(
                        rule_location,
                        f"Invalid access level: {access}",
                        f"Valid levels: {', '.join(self.VALID_ACCESS_LEVELS)}"
                    )
            
            if "scope" in rule:
                scope = rule["scope"]
                if scope not in self.VALID_SCOPES:
                    self._add_warning(
                        rule_location,
                        f"Unknown scope: {scope}",
                        f"Valid scopes: {', '.join(self.VALID_SCOPES)}"
                    )
    
    def _add_error(self, location: str, message: str, suggestion: Optional[str] = None):
        """Add error-level validation issue"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            location=location,
            message=message,
            suggestion=suggestion
        ))
    
    def _add_warning(self, location: str, message: str, suggestion: Optional[str] = None):
        """Add warning-level validation issue"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            location=location,
            message=message,
            suggestion=suggestion
        ))
    
    def _add_info(self, location: str, message: str, suggestion: Optional[str] = None):
        """Add info-level validation issue"""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            location=location,
            message=message,
            suggestion=suggestion
        ))


class SchemaLoader:
    """Loads and validates ontology schemas from YAML files"""
    
    def __init__(self, schema_directory: Optional[Path] = None):
        if schema_directory is None:
            schema_directory = Path(__file__).parent / "v0.1"
        self.schema_directory = Path(schema_directory)
        self.validator = SchemaValidator()
    
    def load_schema(self, version: str = "0.1") -> Dict[str, Any]:
        """
        Load and validate ontology schema.
        
        Args:
            version: Schema version to load
            
        Returns:
            Validated schema dictionary
            
        Raises:
            FileNotFoundError: If schema file not found
            ValueError: If schema validation fails with errors
        """
        schema_file = self.schema_directory / "schema.yaml"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        logger.info(f"Loading ontology schema from {schema_file}")
        
        # Load YAML
        with open(schema_file, 'r') as f:
            schema = yaml.safe_load(f)
        
        # Validate schema
        issues = self.validator.validate_schema(schema)
        
        # Log validation results
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in issues if i.severity == ValidationSeverity.INFO]
        
        if errors:
            logger.error(f"Schema validation failed with {len(errors)} errors:")
            for issue in errors:
                logger.error(f"  [{issue.location}] {issue.message}")
                if issue.suggestion:
                    logger.error(f"    Suggestion: {issue.suggestion}")
            raise ValueError(f"Schema validation failed with {len(errors)} errors")
        
        if warnings:
            logger.warning(f"Schema validation completed with {len(warnings)} warnings:")
            for issue in warnings:
                logger.warning(f"  [{issue.location}] {issue.message}")
        
        if infos:
            logger.info(f"Schema validation info ({len(infos)} items):")
            for issue in infos:
                logger.info(f"  [{issue.location}] {issue.message}")
        
        logger.info(f"Schema loaded successfully: v{schema.get('version', 'unknown')}")
        logger.info(f"  Object types: {len(schema.get('object_types', {}))}")
        logger.info(f"  Link types: {len(schema.get('link_types', {}))}")
        logger.info(f"  Action types: {len(schema.get('action_types', {}))}")
        logger.info(f"  Security policies: {len(schema.get('security_policies', {}))}")
        
        return schema
    
    def get_object_types(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract object types from schema"""
        return schema.get("object_types", {})
    
    def get_link_types(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract link types from schema"""
        return schema.get("link_types", {})
    
    def get_action_types(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract action types from schema"""
        return schema.get("action_types", {})
    
    def get_security_policies(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security policies from schema"""
        return schema.get("security_policies", {})


def validate_schema_file(schema_path: Path) -> bool:
    """
    Validate a schema file and print results.
    
    Args:
        schema_path: Path to schema YAML file
        
    Returns:
        True if validation passed (no errors), False otherwise
    """
    try:
        loader = SchemaLoader(schema_path.parent)
        schema = loader.load_schema()
        
        print(f"\n✓ Schema validation successful!")
        print(f"  Version: {schema.get('version')}")
        print(f"  Object types: {len(schema.get('object_types', {}))}")
        print(f"  Link types: {len(schema.get('link_types', {}))}")
        print(f"  Action types: {len(schema.get('action_types', {}))}")
        print(f"  Security policies: {len(schema.get('security_policies', {}))}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Schema validation failed:")
        print(f"  {str(e)}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        schema_file = Path(sys.argv[1])
        success = validate_schema_file(schema_file)
        sys.exit(0 if success else 1)
    else:
        print("Usage: python validator.py <path-to-schema.yaml>")
        sys.exit(1)

