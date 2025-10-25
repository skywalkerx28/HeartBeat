-- HeartBeat Engine - OMS Initial Schema Migration (PostgreSQL)
-- NHL Advanced Analytics Platform
-- 
-- Creates all tables for Ontology Metadata Service with optimized indexes
-- for performance and referential integrity.

-- Create OMS schema namespace
CREATE SCHEMA IF NOT EXISTS oms;

-- Schema Versions Table
CREATE TABLE IF NOT EXISTS oms.schema_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL DEFAULT 'nhl.heartbeat',
    description TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    
    changelog JSONB,
    metadata_json JSONB,
    schema_snapshot JSONB,
    
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMP,
    
    CONSTRAINT ck_schema_version_status CHECK (status IN ('draft', 'review', 'published', 'deprecated'))
);

CREATE INDEX IF NOT EXISTS ix_schema_version_version ON oms.schema_versions(version);
CREATE INDEX IF NOT EXISTS ix_schema_version_status ON oms.schema_versions(status);
CREATE INDEX IF NOT EXISTS ix_schema_version_active ON oms.schema_versions(is_active, version);
CREATE INDEX IF NOT EXISTS ix_schema_version_created_at ON oms.schema_versions(created_at DESC);

-- Object Type Definitions
CREATE TABLE IF NOT EXISTS oms.object_types (
    id SERIAL PRIMARY KEY,
    schema_version_id INTEGER NOT NULL REFERENCES oms.schema_versions(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    primary_key VARCHAR(100) NOT NULL,
    
    properties JSONB NOT NULL DEFAULT '{}',
    resolver_config JSONB,
    security_policy VARCHAR(100),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_object_type_schema_name UNIQUE (schema_version_id, name)
);

CREATE INDEX IF NOT EXISTS ix_object_type_name ON oms.object_types(name);
CREATE INDEX IF NOT EXISTS ix_object_type_schema_version ON oms.object_types(schema_version_id);
CREATE INDEX IF NOT EXISTS ix_object_type_policy ON oms.object_types(security_policy);

-- Property Definitions (Denormalized for fast property lookup)
CREATE TABLE IF NOT EXISTS oms.properties (
    id SERIAL PRIMARY KEY,
    object_type_id INTEGER NOT NULL REFERENCES oms.object_types(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    enum_values TEXT[],  -- PostgreSQL array for enum values
    
    CONSTRAINT uq_property_object_name UNIQUE (object_type_id, name)
);

CREATE INDEX IF NOT EXISTS ix_property_object_type ON oms.properties(object_type_id);
CREATE INDEX IF NOT EXISTS ix_property_name ON oms.properties(name);

-- Link Type Definitions
CREATE TABLE IF NOT EXISTS oms.link_types (
    id SERIAL PRIMARY KEY,
    schema_version_id INTEGER NOT NULL REFERENCES oms.schema_versions(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    from_object VARCHAR(100) NOT NULL,
    to_object VARCHAR(100) NOT NULL,
    cardinality VARCHAR(50) NOT NULL,
    
    resolver_config JSONB NOT NULL,
    security_policy VARCHAR(100),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_link_type_schema_name UNIQUE (schema_version_id, name),
    CONSTRAINT ck_link_cardinality CHECK (cardinality IN ('one_to_one', 'one_to_many', 'many_to_many'))
);

CREATE INDEX IF NOT EXISTS ix_link_type_name ON oms.link_types(name);
CREATE INDEX IF NOT EXISTS ix_link_type_from ON oms.link_types(from_object);
CREATE INDEX IF NOT EXISTS ix_link_type_to ON oms.link_types(to_object);
CREATE INDEX IF NOT EXISTS ix_link_type_schema_version ON oms.link_types(schema_version_id);

-- Action Type Definitions
CREATE TABLE IF NOT EXISTS oms.action_types (
    id SERIAL PRIMARY KEY,
    schema_version_id INTEGER NOT NULL REFERENCES oms.schema_versions(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    object_type VARCHAR(100) NOT NULL,
    
    input_parameters JSONB,
    output_properties JSONB,
    
    is_async BOOLEAN NOT NULL DEFAULT FALSE,
    timeout_seconds INTEGER,
    security_policy VARCHAR(100) NOT NULL,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_action_type_schema_name UNIQUE (schema_version_id, name)
);

CREATE INDEX IF NOT EXISTS ix_action_type_name ON oms.action_types(name);
CREATE INDEX IF NOT EXISTS ix_action_type_object ON oms.action_types(object_type);
CREATE INDEX IF NOT EXISTS ix_action_type_schema_version ON oms.action_types(schema_version_id);

-- Security Policy Definitions
CREATE TABLE IF NOT EXISTS oms.security_policies (
    id SERIAL PRIMARY KEY,
    schema_version_id INTEGER NOT NULL REFERENCES oms.schema_versions(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    enforcement_level VARCHAR(50) NOT NULL,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_security_policy_schema_name UNIQUE (schema_version_id, name),
    CONSTRAINT ck_enforcement_level CHECK (enforcement_level IN ('object', 'property', 'row'))
);

CREATE INDEX IF NOT EXISTS ix_security_policy_name ON oms.security_policies(name);
CREATE INDEX IF NOT EXISTS ix_security_policy_schema_version ON oms.security_policies(schema_version_id);

-- Policy Rules
CREATE TABLE IF NOT EXISTS oms.policy_rules (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL REFERENCES oms.security_policies(id) ON DELETE CASCADE,
    
    role VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    effect VARCHAR(20) NOT NULL,
    
    conditions JSONB,
    scope_filter JSONB,
    allowed_properties TEXT[],  -- PostgreSQL array for column-level filtering
    denied_properties TEXT[],   -- PostgreSQL array for column-level filtering
    
    priority INTEGER NOT NULL DEFAULT 100,
    
    CONSTRAINT ck_policy_action CHECK (action IN ('read', 'write', 'delete', 'execute')),
    CONSTRAINT ck_policy_effect CHECK (effect IN ('allow', 'deny'))
);

CREATE INDEX IF NOT EXISTS ix_policy_rule_policy ON oms.policy_rules(policy_id);
CREATE INDEX IF NOT EXISTS ix_policy_rule_role ON oms.policy_rules(role);
CREATE INDEX IF NOT EXISTS ix_policy_rule_action ON oms.policy_rules(action);
CREATE INDEX IF NOT EXISTS ix_policy_rule_priority ON oms.policy_rules(priority DESC);

-- Audit Log
CREATE TABLE IF NOT EXISTS oms.audit_log (
    id SERIAL PRIMARY KEY,
    
    event_type VARCHAR(100) NOT NULL,
    object_type VARCHAR(100),
    object_id VARCHAR(255),
    
    user_id VARCHAR(255) NOT NULL,
    user_role VARCHAR(100),
    
    action VARCHAR(50) NOT NULL,
    result VARCHAR(50) NOT NULL,
    
    policy_decisions JSONB,
    metadata JSONB,
    
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT ck_audit_result CHECK (result IN ('allowed', 'denied', 'error'))
);

CREATE INDEX IF NOT EXISTS ix_audit_event_type ON oms.audit_log(event_type);
CREATE INDEX IF NOT EXISTS ix_audit_object_type ON oms.audit_log(object_type);
CREATE INDEX IF NOT EXISTS ix_audit_user ON oms.audit_log(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON oms.audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_audit_result ON oms.audit_log(result);

-- Composite index for common audit queries
CREATE INDEX IF NOT EXISTS ix_audit_user_time ON oms.audit_log(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_audit_object_time ON oms.audit_log(object_type, object_id, timestamp DESC);

-- Comments for documentation
COMMENT ON SCHEMA oms IS 'Ontology Metadata Service - Schema and security definitions';
COMMENT ON TABLE oms.schema_versions IS 'Ontology schema versions with versioning and lifecycle management';
COMMENT ON TABLE oms.object_types IS 'Object type definitions (Player, Team, Contract, etc.)';
COMMENT ON TABLE oms.link_types IS 'Relationship definitions between objects';
COMMENT ON TABLE oms.action_types IS 'Governed action definitions';
COMMENT ON TABLE oms.security_policies IS 'Security policy definitions with RBAC/ABAC rules';
COMMENT ON TABLE oms.audit_log IS 'Audit trail for all OMS access and policy enforcement';

