# HeartBeat Ontology Metadata Service (OMS)

## Overview

The Ontology Metadata Service (OMS) is the foundation layer of the HeartBeat Engine, providing a digital twin of NHL organizations. It maps all entities, relationships, actions, and security policies into a unified, versioned, and governed semantic layer.

## Architecture

```
HeartBeat OMS Architecture
├── Schema Layer (YAML definitions)
│   ├── Object Types (Team, Player, Contract, etc.)
│   ├── Properties (attributes with types and constraints)
│   ├── Link Types (relationships between objects)
│   ├── Action Types (business operations)
│   └── Security Policies (RBAC/ABAC rules)
│
├── Metadata Service (FastAPI)
│   ├── Schema Registry (versioning, validation)
│   ├── Policy Engine (access control enforcement)
│   ├── Resolver System (data backend bindings)
│   └── API Endpoints (CRUD, traversal, actions)
│
├── OSDK Generator (Code Generation)
│   ├── TypeScript Client (frontend/src/ontology/)
│   └── Python Client (orchestrator/ontology_client/)
│
└── Runtime Layer
    ├── Object CRUD operations
    ├── Link traversal queries
    ├── Action execution with policy checks
    └── Audit trail and logging
```

## Design Principles

1. **Digital Twin Accuracy**: Precisely models NHL organizational structure from Owner to Player
2. **Strong Typing**: All entities, properties, and relationships are strongly typed
3. **Governance**: Versioned schemas with draft/review/publish workflows
4. **Security First**: Role-based and attribute-based access control at every layer
5. **Data Abstraction**: Resolvers bind ontology to BigQuery/Parquet without tight coupling
6. **Generated Clients**: Type-safe SDKs eliminate manual API integration

## Core Concepts

### Object Types
Entities in the NHL ecosystem with defined properties and constraints.

Examples:
- **Team**: NHL franchise with roster, management, and performance data
- **Player**: Active NHL roster player with contracts and statistics
- **Prospect**: Drafted or signed player not yet in NHL (tracked by scouts)
- **Manager**: Team management (GM, AGM, etc.)
- **Scout**: Personnel who evaluate prospects and opponents
- **Contract**: Player contract with salary cap and term details

### Link Types
First-class relationships between objects with cardinality and constraints.

Examples:
- Team → Players (one-to-many)
- Player → Contracts (one-to-many, time-based)
- Player → PerformanceStats (one-to-many)
- Scout → Prospects (many-to-many, with evaluation context)
- Manager → Team (many-to-one)

### Action Types
Governed business operations with preconditions, inputs, and effects.

Examples:
- `approveContract`: Manager approves player contract
- `assignScoutToProspect`: Assign scout to track prospect development
- `createInjuryReport`: Document player injury status
- `promoteProspectToRoster`: Move prospect to active NHL roster

### Security Policies

Role-based access control with granular permissions:

| Role     | Access Scope | Contracts | Scouting Notes | Tactical Analysis |
|----------|--------------|-----------|----------------|-------------------|
| Manager  | Full         | ✓         | ✓              | ✓                 |
| Scout    | Prospects    | ✗         | ✓              | Limited           |
| Analyst  | Team/League  | Limited   | ✗              | ✓                 |
| Player   | Self         | ✗         | ✗              | Limited           |
| Staff    | Basic        | ✗         | ✗              | ✗                 |

## Directory Structure

```
backend/ontology/
├── __init__.py
├── README.md
├── schemas/
│   ├── v0.1/
│   │   ├── schema.yaml           # Complete v0.1 ontology definition
│   │   ├── objects.yaml          # Object type definitions
│   │   ├── links.yaml            # Link type definitions
│   │   ├── actions.yaml          # Action type definitions
│   │   └── policies.yaml         # Security policy definitions
│   └── validator.py              # Schema validation logic
├── models/
│   ├── __init__.py
│   ├── metadata.py               # Metadata store models (SQLAlchemy)
│   ├── schema.py                 # Schema definition models
│   └── policy.py                 # Policy models
├── services/
│   ├── __init__.py
│   ├── registry.py               # Schema registry service
│   ├── policy_engine.py          # Policy enforcement engine
│   └── resolvers/
│       ├── __init__.py
│       ├── base.py               # Base resolver interface
│       ├── parquet_resolver.py   # Parquet data resolver
│       └── bigquery_resolver.py  # BigQuery data resolver
├── api/
│   ├── __init__.py
│   ├── routes.py                 # OMS API endpoints
│   └── dependencies.py           # FastAPI dependencies
├── codegen/
│   ├── __init__.py
│   ├── generator.py              # OSDK generator
│   ├── templates/
│   │   ├── typescript.jinja2     # TypeScript client template
│   │   └── python.jinja2         # Python client template
│   └── cli.py                    # Code generation CLI
└── migrations/
    └── 001_initial_schema.sql    # Database migration for metadata store
```

## Phase 0: Planning and Design (CURRENT)

### Objectives
- Define core NHL entities and relationships
- Establish security model and access control rules
- Create YAML schema definitions with validation
- Document ontology design decisions

### Deliverables
- Complete v0.1 schema definition in YAML
- Schema validator and loader
- OMS architecture documentation
- Integration plan with existing systems

## Phase 1: Core OMS Service (NEXT)

### Objectives
- Implement metadata registry with version control
- Build policy engine for RBAC/ABAC enforcement
- Create resolver system for Parquet/BigQuery
- Develop REST API for object/link/action operations
- Generate initial OSDK clients (TypeScript + Python)

## Phase 2: Actions and Audit (FUTURE)

### Objectives
- Implement action execution runtime
- Add precondition validation and effects
- Build comprehensive audit trail system
- Implement write resolvers with transaction support

## Phase 3: Versioning and Governance (FUTURE)

### Objectives
- Draft/review/publish workflow
- Schema diff and compatibility checking
- OSDK version pinning across services
- Migration tooling for schema evolution

## Phase 4: Advanced Features (FUTURE)

### Objectives
- BigQuery optimization with caching
- Column/row-level security enforcement
- Streaming subscriptions for live updates
- Performance monitoring and optimization

## Getting Started

Phase 0 is currently in progress. The v0.1 schema is being defined to accurately represent NHL organizational structures.

