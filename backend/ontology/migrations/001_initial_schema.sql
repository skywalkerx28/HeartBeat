-- HeartBeat Engine - OMS Initial Schema Migration
-- NHL Advanced Analytics Platform
-- 
-- Creates all tables for Ontology Metadata Service with optimized indexes
-- for performance and referential integrity.

-- Schema Versions Table
CREATE TABLE IF NOT EXISTS oms_schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(50) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL DEFAULT 'nhl.heartbeat',
    description TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    
    changelog JSON,
    metadata_json JSON,
    schema_snapshot JSON,
    
    is_active BOOLEAN NOT NULL DEFAULT 0,
    published_at TIMESTAMP,
    
    CONSTRAINT ck_schema_version_status CHECK (status IN ('draft', 'review', 'published', 'deprecated'))
);

CREATE INDEX IF NOT EXISTS ix_schema_version_version ON oms_schema_versions(version);
CREATE INDEX IF NOT EXISTS ix_schema_version_status ON oms_schema_versions(status);
CREATE INDEX IF NOT EXISTS ix_schema_version_active ON oms_schema_versions(is_active, version);

-- Object Type Definitions
CREATE TABLE IF NOT EXISTS oms_object_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version_id INTEGER NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    primary_key VARCHAR(255) NOT NULL,
    
    resolver_backend VARCHAR(50),
    resolver_config JSON,
    
    security_policy_ref VARCHAR(255),
    
    metadata_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (schema_version_id) REFERENCES oms_schema_versions(id) ON DELETE CASCADE,
    CONSTRAINT uq_object_type_version_name UNIQUE (schema_version_id, name)
);

CREATE INDEX IF NOT EXISTS ix_object_type_schema_version ON oms_object_types(schema_version_id);
CREATE INDEX IF NOT EXISTS ix_object_type_name ON oms_object_types(name);
CREATE INDEX IF NOT EXISTS ix_object_type_resolver ON oms_object_types(resolver_backend);
CREATE INDEX IF NOT EXISTS ix_object_type_policy ON oms_object_types(security_policy_ref);

-- Property Definitions
CREATE TABLE IF NOT EXISTS oms_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_type_id INTEGER NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT 0,
    description TEXT,
    
    enum_values JSON,
    default_value VARCHAR(255),
    
    constraints JSON,
    metadata_json JSON,
    
    FOREIGN KEY (object_type_id) REFERENCES oms_object_types(id) ON DELETE CASCADE,
    CONSTRAINT uq_property_object_name UNIQUE (object_type_id, name),
    CONSTRAINT ck_property_type_valid CHECK (
        property_type IN ('string', 'integer', 'float', 'boolean', 'date', 'datetime', 'text', 'object', 'array')
    )
);

CREATE INDEX IF NOT EXISTS ix_property_object_type ON oms_properties(object_type_id);
CREATE INDEX IF NOT EXISTS ix_property_name ON oms_properties(name);
CREATE INDEX IF NOT EXISTS ix_property_type ON oms_properties(property_type);

-- Link Type Definitions
CREATE TABLE IF NOT EXISTS oms_link_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version_id INTEGER NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    from_object VARCHAR(255) NOT NULL,
    to_object VARCHAR(255) NOT NULL,
    cardinality VARCHAR(50) NOT NULL,
    
    resolver_type VARCHAR(50),
    resolver_config JSON,
    
    security_policy_ref VARCHAR(255),
    
    metadata_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (schema_version_id) REFERENCES oms_schema_versions(id) ON DELETE CASCADE,
    CONSTRAINT uq_link_type_version_name UNIQUE (schema_version_id, name),
    CONSTRAINT ck_link_cardinality_valid CHECK (
        cardinality IN ('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many')
    )
);

CREATE INDEX IF NOT EXISTS ix_link_type_schema_version ON oms_link_types(schema_version_id);
CREATE INDEX IF NOT EXISTS ix_link_type_name ON oms_link_types(name);
CREATE INDEX IF NOT EXISTS ix_link_type_from_object ON oms_link_types(from_object);
CREATE INDEX IF NOT EXISTS ix_link_type_to_object ON oms_link_types(to_object);
CREATE INDEX IF NOT EXISTS ix_link_type_objects ON oms_link_types(from_object, to_object);
CREATE INDEX IF NOT EXISTS ix_link_type_policy ON oms_link_types(security_policy_ref);

-- Action Type Definitions
CREATE TABLE IF NOT EXISTS oms_action_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version_id INTEGER NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    input_schema JSON NOT NULL,
    preconditions JSON,
    effects JSON,
    
    security_policy_ref VARCHAR(255) NOT NULL,
    
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    is_idempotent BOOLEAN NOT NULL DEFAULT 0,
    
    metadata_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (schema_version_id) REFERENCES oms_schema_versions(id) ON DELETE CASCADE,
    CONSTRAINT uq_action_type_version_name UNIQUE (schema_version_id, name),
    CONSTRAINT ck_action_timeout_range CHECK (timeout_seconds > 0 AND timeout_seconds <= 300)
);

CREATE INDEX IF NOT EXISTS ix_action_type_schema_version ON oms_action_types(schema_version_id);
CREATE INDEX IF NOT EXISTS ix_action_type_name ON oms_action_types(name);
CREATE INDEX IF NOT EXISTS ix_action_type_policy ON oms_action_types(security_policy_ref);

-- Security Policies
CREATE TABLE IF NOT EXISTS oms_security_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version_id INTEGER NOT NULL,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    target_type VARCHAR(50) NOT NULL,
    target_ref VARCHAR(255),
    
    metadata_json JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (schema_version_id) REFERENCES oms_schema_versions(id) ON DELETE CASCADE,
    CONSTRAINT uq_policy_version_name UNIQUE (schema_version_id, name),
    CONSTRAINT ck_policy_target_type CHECK (
        target_type IN ('object', 'link', 'action', 'property', 'global')
    )
);

CREATE INDEX IF NOT EXISTS ix_policy_schema_version ON oms_security_policies(schema_version_id);
CREATE INDEX IF NOT EXISTS ix_policy_name ON oms_security_policies(name);
CREATE INDEX IF NOT EXISTS ix_policy_target_type ON oms_security_policies(target_type);
CREATE INDEX IF NOT EXISTS ix_policy_target ON oms_security_policies(target_type, target_ref);

-- Policy Rules
CREATE TABLE IF NOT EXISTS oms_policy_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id INTEGER NOT NULL,
    
    role VARCHAR(50) NOT NULL,
    access_level VARCHAR(50) NOT NULL,
    scope VARCHAR(50),
    
    column_filters JSON,
    row_filter_expr TEXT,
    conditions JSON,
    
    priority INTEGER NOT NULL DEFAULT 100,
    
    FOREIGN KEY (policy_id) REFERENCES oms_security_policies(id) ON DELETE CASCADE,
    CONSTRAINT ck_rule_access_level CHECK (
        access_level IN ('none', 'read', 'full', 'execute', 'self_only')
    ),
    CONSTRAINT ck_rule_scope CHECK (
        scope IN ('all', 'team_scoped', 'self_only') OR scope IS NULL
    )
);

CREATE INDEX IF NOT EXISTS ix_rule_policy ON oms_policy_rules(policy_id);
CREATE INDEX IF NOT EXISTS ix_rule_role ON oms_policy_rules(role);
CREATE INDEX IF NOT EXISTS ix_rule_access_level ON oms_policy_rules(access_level);
CREATE INDEX IF NOT EXISTS ix_rule_role_access ON oms_policy_rules(role, access_level);

-- Audit Logs
CREATE TABLE IF NOT EXISTS oms_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id VARCHAR(255) NOT NULL,
    actor_role VARCHAR(50) NOT NULL,
    
    operation VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(255),
    
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    request_payload JSON,
    response_summary JSON,
    
    ip_address VARCHAR(50),
    user_agent VARCHAR(255),
    
    execution_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON oms_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_actor ON oms_audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_timestamp_actor ON oms_audit_logs(timestamp, actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_operation ON oms_audit_logs(operation);
CREATE INDEX IF NOT EXISTS ix_audit_success ON oms_audit_logs(success);
CREATE INDEX IF NOT EXISTS ix_audit_operation_success ON oms_audit_logs(operation, success);
CREATE INDEX IF NOT EXISTS ix_audit_target_type ON oms_audit_logs(target_type);
CREATE INDEX IF NOT EXISTS ix_audit_target_id ON oms_audit_logs(target_id);
CREATE INDEX IF NOT EXISTS ix_audit_target ON oms_audit_logs(target_type, target_id);

-- Performance optimization: Analyze tables for query planning
ANALYZE oms_schema_versions;
ANALYZE oms_object_types;
ANALYZE oms_properties;
ANALYZE oms_link_types;
ANALYZE oms_action_types;
ANALYZE oms_security_policies;
ANALYZE oms_policy_rules;
ANALYZE oms_audit_logs;

