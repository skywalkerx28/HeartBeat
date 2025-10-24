# HeartBeat Ontology Metadata Service (OMS) - Implementation Guide

## Executive Summary

The Ontology Metadata Service (OMS) is HeartBeat Engine's foundational layer, providing a digital twin of NHL organizations. It creates a unified, versioned, and governed semantic layer that grounds AI responses in accurate business context, enforces role-based security, and abstracts data access across BigQuery and Parquet backends.

**Architecture Inspiration**: Palantir Foundry's Ontology system

**Current Status**: Phase 0 Complete - Schema Definition and Validation

## Phase 0: Planning and Design ✓ COMPLETE

### Objectives Achieved

1. **Core NHL Entity Modeling**
   - 13 object types defined (Owner, Manager, Scout, Analyst, Player, Prospect, Team, Contract, Game, Venue, PerformanceStat, ScoutingReport, InjuryReport)
   - 13 link types establishing organizational relationships
   - 6 action types for governed business operations
   - 12 security policies with role-based access control

2. **Security Model Established**
   - **Manager**: Full access to all team data including contracts and scouting
   - **Scout**: Access to prospects and scouting reports, NO financial data
   - **Analyst**: Performance data and limited contract visibility
   - **Player**: Self-only access to performance, NO scouting reports on others
   - **Staff**: Basic team data, NO financials or scouting

3. **Schema Validation System**
   - Comprehensive YAML schema validator
   - Type safety checks for all properties
   - Link integrity validation
   - Policy consistency verification
   - Current schema: **VALIDATED** (13 objects, 13 links, 6 actions, 12 policies)

### Key Design Decisions

#### 1. Prospects vs Draft Picks

**Decision**: Use "Prospect" object type instead of "DraftPick"

**Rationale**: 
- Prospects are players whose rights are owned by an NHL team but who do not yet play in the NHL
- Includes both drafted players AND undrafted free agent signings
- Scouts track prospect development worldwide (Junior, College, AHL, European leagues)
- More accurate representation of organizational structure

#### 2. Scout-Prospect Relationship

**Implementation**: Many-to-many link type with assignment tracking

**Rationale**:
- Scouts are assigned to track multiple prospects
- Prospects may be evaluated by multiple scouts (primary scout, regional scout, director)
- Assignment table tracks priority level and assignment context
- Enables proper workload distribution across scouting staff

#### 3. Security Policy Granularity

**Implementation**: Column-level and row-level security with team scoping

**Rationale**:
- Managers see everything (contracts, salaries, scouting reports)
- Scouts see scouting data but NOT financial information (contracts hidden)
- Players see own performance but NOT scouting evaluations of others
- Analysts see performance data with limited contract details (cap hit visible, bonuses hidden)

#### 4. Data Resolver Strategy

**Implementation**: Dual backend support (BigQuery + Parquet)

**Rationale**:
- BigQuery for relational data (teams, players, contracts, rosters)
- Parquet for high-volume analytics (game events, performance stats)
- Resolver abstraction enables seamless backend switching
- Future support for API resolvers and computed properties

### Deliverables

1. **Complete v0.1 Schema** (`backend/ontology/schemas/v0.1/schema.yaml`)
   - 1,200+ lines of comprehensive ontology definition
   - All NHL organizational entities mapped
   - Full security policy specification

2. **Schema Validator** (`backend/ontology/schemas/validator.py`)
   - 600+ lines of validation logic
   - Type safety checking
   - Reference integrity validation
   - Security policy verification

3. **OMS Documentation** (`backend/ontology/README.md`)
   - Architecture overview
   - Design principles
   - Phase roadmap
   - Integration patterns

4. **This Implementation Guide**
   - Detailed technical specifications
   - Integration examples
   - Migration path from current implementation

## Ontology Schema Overview

### Object Types (13 Total)

#### Organizational Hierarchy
1. **Owner** - Team ownership group
2. **Manager** - GM, AGM, President, VP Hockey Ops
3. **Scout** - Pro, Amateur, European, Analytics scouts
4. **Analyst** - Data, Video, Performance analysts

#### Team and Roster
5. **Team** - NHL franchise with division/conference
6. **Player** - Active NHL roster player
7. **Prospect** - Owned rights, not yet on NHL roster

#### Performance and Statistics
8. **PerformanceStat** - Game and season statistics
9. **Game** - NHL game with score and metadata
10. **Venue** - Arena information

#### Contracts and Reports
11. **Contract** - Player contracts with cap implications
12. **ScoutingReport** - Prospect evaluation reports
13. **InjuryReport** - Player injury tracking

### Link Types (13 Total)

```
Team → Players (one-to-many)
Team → Prospects (one-to-many)
Team → Managers (one-to-many)
Team → Scouts (one-to-many)
Team → Analysts (one-to-many)
Team → Venue (many-to-one)

Player → Contracts (one-to-many)
Player → PerformanceStats (one-to-many)
Player → InjuryReports (one-to-many)

Prospect → ScoutingReports (one-to-many)
Scout ↔ Prospects (many-to-many with assignments)

Game → HomeTeam (many-to-one)
Game → AwayTeam (many-to-one)
```

### Action Types (6 Total)

1. **approveContract** - Manager approves player contract
2. **assignScoutToProspect** - Assign scout to track prospect
3. **createScoutingReport** - Scout evaluates prospect
4. **createInjuryReport** - Document player injury
5. **promoteProspectToRoster** - Move prospect to NHL roster
6. **updatePlayerRosterStatus** - Update player availability

Each action includes:
- Input schema validation
- Precondition checks (role, ownership, business rules)
- Effect documentation
- Security policy enforcement

### Security Policies (12 Total)

| Policy | Description | Manager | Scout | Analyst | Player | Staff |
|--------|-------------|---------|-------|---------|--------|-------|
| contract_visibility | Contract financial details | Full | None | Read (limited) | Self (limited) | None |
| scouting_reports_access | Prospect evaluations | Full | Full | None | None | None |
| injury_reports_access | Player injury details | Full | Read | Read | Self (limited) | Read |
| performance_data_access | Stats and analytics | Full | Read | Full | Self | Team |
| team_data_access | Organizational data | Full | Read | Read | Read | Read |
| scouting_assignments_access | Scout-prospect assignments | Full | Self | None | None | None |

## Integration with Current HeartBeat Engine

### Current State Assessment

**Existing Implementation**:
- Pydantic models in `backend/api/models/hockey.py`
- Simple enum-based roles in `backend/api/models/requests.py`
- Config-based RBAC in `orchestrator/config/settings.py`
- Direct Parquet/BigQuery queries in routes

**Gaps Identified**:
- No centralized metadata registry
- No schema versioning or governance
- No link traversal API
- No action execution framework with policy checks
- RBAC is static config, not data-driven
- No resolver abstraction (tight coupling to backends)
- No generated typed clients (manual API calls)

### Migration Path

#### Step 1: Parallel Operation (Non-Breaking)

Run OMS alongside existing Pydantic models:

```python
# Existing route (continues to work)
@router.get("/players/{player_id}")
async def get_player(player_id: str):
    # Direct Parquet query
    df = pd.read_parquet("data/processed/players.parquet")
    player = df[df.playerId == player_id].to_dict('records')[0]
    return player

# New OMS-powered route (added in parallel)
@router.get("/ontology/players/{player_id}")
async def get_player_ontology(
    player_id: str,
    user: UserContext = Depends(get_current_user_context)
):
    # OMS API with policy enforcement
    player = await oms_client.Player.by_primary_key(
        player_id,
        user_context=user
    )
    return player
```

#### Step 2: Gradual Migration

Migrate routes one at a time to OMS:

1. Start with profile pages (player, team, prospect)
2. Migrate analytics routes
3. Convert market/contract endpoints
4. Update orchestrator to use OMS client

#### Step 3: Deprecation

Once all routes migrated:
1. Mark old endpoints as deprecated
2. Remove Pydantic models
3. Clean up direct backend access
4. Standardize on OSDK clients

### Example Integration Patterns

#### Pattern 1: Direct OMS API Usage

```python
from backend.ontology.client import OntologyClient

@router.get("/teams/{team_id}/roster")
async def get_team_roster(
    team_id: str,
    user: UserContext = Depends(get_current_user_context)
):
    oms = OntologyClient()
    
    # Load team with policy enforcement
    team = await oms.get_object(
        object_type="Team",
        primary_key=team_id,
        user_context=user
    )
    
    # Traverse link to get players
    players = await oms.traverse_link(
        from_object=team,
        link_type="team_players",
        user_context=user
    )
    
    # Policy automatically filters based on user role
    # Manager sees all, Player sees teammates, Scout sees prospects
    return {
        "team": team,
        "roster": players
    }
```

#### Pattern 2: Generated OSDK Client (Future Phase 1)

```typescript
// TypeScript frontend code
import { osdk } from '@/ontology';

async function loadPlayerProfile(playerId: string) {
  // Type-safe client with auto-complete
  const player = await osdk.Player.byPrimaryKey(playerId);
  
  // Link traversal with strong typing
  const contracts = await player.contracts();
  const stats = await player.performance({ season: '2024-25' });
  
  // Policy enforcement happens server-side
  // UI receives only data user is allowed to see
  return {
    player,
    currentContract: contracts.find(c => c.isActive),
    seasonStats: stats
  };
}
```

#### Pattern 3: Action Execution

```python
from backend.ontology.client import OntologyClient

@router.post("/prospects/{prospect_id}/scouting-report")
async def create_scouting_report(
    prospect_id: str,
    report: ScoutingReportInput,
    user: UserContext = Depends(get_current_user_context)
):
    oms = OntologyClient()
    
    # Execute governed action
    result = await oms.execute_action(
        action_type="createScoutingReport",
        inputs={
            "scoutId": user.user_id,
            "prospectId": prospect_id,
            "reportDate": report.date,
            "overallGrade": report.grade,
            "notes": report.notes,
            "nhlReadiness": report.readiness
        },
        user_context=user
    )
    
    # Preconditions checked:
    # - User has Scout role
    # - Scout assigned to prospect or has team access
    
    # Effects executed:
    # - Scouting report record created
    # - Prospect development status updated
    # - Scouting director notified
    # - Audit log entry created
    
    return result
```

## Next Steps: Phase 1 Implementation

### Phase 1 Objectives

1. **OMS Service Implementation**
   - FastAPI service with metadata registry
   - PostgreSQL/SQLite backend for metadata storage
   - REST API for object/link/action operations
   - Policy engine with RBAC/ABAC enforcement

2. **Resolver System**
   - Base resolver interface
   - Parquet resolver (local file access)
   - BigQuery resolver (GCP integration)
   - Caching layer for performance

3. **OSDK Code Generation**
   - TypeScript client generator (frontend)
   - Python client generator (orchestrator)
   - Template-based codegen with Jinja2
   - Version pinning and compatibility checks

### Phase 1 Deliverables

1. `backend/ontology/service.py` - FastAPI OMS service
2. `backend/ontology/models/metadata.py` - SQLAlchemy metadata models
3. `backend/ontology/services/registry.py` - Schema registry
4. `backend/ontology/services/policy_engine.py` - Policy enforcement
5. `backend/ontology/services/resolvers/` - Data backend resolvers
6. `backend/ontology/api/routes.py` - OMS REST API
7. `backend/ontology/codegen/generator.py` - OSDK generator
8. `frontend/src/ontology/` - Generated TypeScript client
9. `orchestrator/ontology_client/` - Generated Python client

### Phase 1 Timeline

**Estimated Duration**: 2-3 weeks

1. Week 1: Metadata service + policy engine + resolvers
2. Week 2: REST API + integration tests + documentation
3. Week 3: OSDK codegen + client examples + migration guide

## Benefits of OMS Implementation

### 1. AI Grounding

**Before OMS**:
```
User: "What is Nick Suzuki's contract status?"
AI: "I don't have specific contract information."
```

**With OMS**:
```
User: "What is Nick Suzuki's contract status?"
AI queries ontology:
  Player(Nick Suzuki) → Contracts → Active contract
  Returns: Entry Level, $863K cap hit, expires 2026
AI: "Nick Suzuki is on an entry-level contract with an $863K 
     cap hit expiring in 2026. He'll be eligible for 
     extension after the 2025 season."
```

### 2. Security Enforcement

**Scenario**: Player logs in and asks about scouting reports

```python
# Player tries to access scouting reports
player_user = UserContext(role=UserRole.PLAYER, user_id="player_suzuki")

# OMS policy engine checks security_policies.scouting_reports_access
# Player role → access: "none"
# Request denied automatically

# Player CAN access own performance data
stats = await oms.Player.by_primary_key("8478398").performance()
# Returns stats (policy allows self-only access)
```

### 3. Consistent Data Access

**Before**: Routes have inconsistent data access patterns
```python
# Route A uses Parquet
df = pd.read_parquet("path/to/players.parquet")

# Route B uses BigQuery
query = "SELECT * FROM core.players"
df = client.query(query).to_dataframe()

# Route C uses NHL API
response = requests.get(f"https://api.nhl.com/players/{id}")
```

**With OMS**: Unified access pattern
```python
# All routes use ontology
player = await oms.Player.by_primary_key(player_id)

# Backend resolver handles data source transparently
# Easy to migrate from Parquet → BigQuery without changing code
```

### 4. Schema Evolution

**Scenario**: Add "Agent" entity for contract negotiations

```yaml
# Add to schema v0.2
Agent:
  description: "Player agent for contract negotiations"
  primary_key: "agentId"
  properties:
    agentId: { type: "string", required: true }
    name: { type: "string", required: true }
    agency: { type: "string" }
    
# Add link
player_agent:
  from_object: "Player"
  to_object: "Agent"
  cardinality: "many_to_one"
```

**Regenerate OSDK**:
```bash
python -m backend.ontology.codegen.cli generate --version 0.2
```

**TypeScript client automatically updated**:
```typescript
const player = await osdk.Player.byPrimaryKey('8478398');
const agent = await player.agent();  // New method!
```

## Validation and Testing

### Schema Validation

```bash
# Validate schema
python3 -m backend.ontology.schemas.validator backend/ontology/schemas/v0.1/schema.yaml

# Output:
✓ Schema validation successful!
  Version: 0.1.0
  Object types: 13
  Link types: 13
  Action types: 6
  Security policies: 12
```

### Integration Test Pattern

```python
# tests/ontology/test_oms_integration.py
async def test_scout_prospect_workflow():
    # Setup
    scout = UserContext(role=UserRole.SCOUT, user_id="scout_lapointe")
    manager = UserContext(role=UserRole.MANAGER, user_id="coach_martin")
    player = UserContext(role=UserRole.PLAYER, user_id="player_suzuki")
    
    # Manager assigns scout to prospect
    result = await oms.execute_action(
        "assignScoutToProspect",
        {"scoutId": "scout_lapointe", "prospectId": "prospect_001"},
        user_context=manager
    )
    assert result.success
    
    # Scout creates scouting report
    report = await oms.execute_action(
        "createScoutingReport",
        {
            "scoutId": "scout_lapointe",
            "prospectId": "prospect_001",
            "overallGrade": "B+",
            "notes": "Strong skating, needs work on defensive positioning"
        },
        user_context=scout
    )
    assert report.success
    
    # Player tries to access scouting report (should be denied)
    with pytest.raises(PermissionError):
        await oms.Prospect.by_primary_key("prospect_001", user_context=player)
            .scouting_reports()
```

## Conclusion

Phase 0 is complete with a comprehensive, validated NHL organizational ontology. The schema accurately models all entities from Owner to Player, establishes proper relationships, defines governed actions, and implements granular security policies.

**Key Achievements**:
- 13 object types covering entire NHL organizational structure
- Prospect entity properly represents drafted/signed players not on NHL roster
- Scout-prospect relationship enables proper development tracking
- Security policies ensure managers see everything, scouts see scouting data (not financials), players see own data only
- Schema validator confirms integrity and consistency
- Migration path defined for gradual OMS adoption

**Next Phase**: Implement OMS service with metadata registry, policy engine, resolvers, REST API, and OSDK code generation.

The ontology foundation is solid, production-ready, and ready for Phase 1 implementation.

