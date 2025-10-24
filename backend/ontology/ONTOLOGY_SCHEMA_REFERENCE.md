# HeartBeat Ontology Schema v0.1 - Quick Reference

## NHL Organizational Structure

```
Owner
  │
  ├─► Team
       │
       ├─► Manager (GM, AGM, President)
       │
       ├─► Scout (Pro, Amateur, European, Analytics)
       │    │
       │    └─► Prospect (Many-to-Many Assignment)
       │         │
       │         └─► ScoutingReport
       │
       ├─► Analyst (Data, Video, Performance)
       │
       ├─► Player (Active NHL Roster)
       │    │
       │    ├─► Contract
       │    ├─► PerformanceStat
       │    └─► InjuryReport
       │
       ├─► Prospect (Owned Rights, Not NHL Roster)
       │    │
       │    └─► ScoutingReport
       │
       └─► Venue (Home Arena)
```

## Object Type Summary

| Object | Primary Key | Description | Resolver |
|--------|-------------|-------------|----------|
| **Owner** | ownerId | Team ownership group | BigQuery |
| **Manager** | managerId | GM, AGM, President, VP Hockey Ops | BigQuery |
| **Scout** | scoutId | Scouting personnel (Pro, Amateur, European) | BigQuery |
| **Analyst** | analystId | Analytics personnel (Data, Video, Performance) | BigQuery |
| **Team** | teamId | NHL franchise | BigQuery |
| **Player** | playerId | Active NHL roster player | BigQuery |
| **Prospect** | prospectId | Owned rights, not on NHL roster | BigQuery |
| **Contract** | contractId | Player contract with cap details | BigQuery |
| **PerformanceStat** | statId | Game/season statistics | Parquet |
| **Game** | gameId | NHL game | Parquet |
| **Venue** | venueId | NHL arena | BigQuery |
| **ScoutingReport** | reportId | Prospect evaluation by scout | BigQuery |
| **InjuryReport** | injuryId | Player injury tracking | BigQuery |

## Link Type Summary

| Link | From | To | Cardinality | Purpose |
|------|------|-----|-------------|---------|
| team_players | Team | Player | one-to-many | Active NHL roster |
| team_prospects | Team | Prospect | one-to-many | Owned prospect rights |
| team_managers | Team | Manager | one-to-many | Management personnel |
| team_scouts | Team | Scout | one-to-many | Scouting personnel |
| team_analysts | Team | Analyst | one-to-many | Analytics personnel |
| team_venue | Team | Venue | many-to-one | Home arena |
| player_contracts | Player | Contract | one-to-many | Contract history |
| player_performance | Player | PerformanceStat | one-to-many | Performance data |
| player_injuries | Player | InjuryReport | one-to-many | Injury history |
| scout_prospects | Scout | Prospect | many-to-many | Scout assignments |
| prospect_scouting_reports | Prospect | ScoutingReport | one-to-many | Evaluations |
| game_home_team | Game | Team | many-to-one | Home team |
| game_away_team | Game | Team | many-to-one | Away team |

## Action Type Summary

| Action | Allowed Roles | Preconditions | Effects |
|--------|---------------|---------------|---------|
| **approveContract** | Manager | Contract pending, Manager on same team | Update status, audit log, notifications |
| **assignScoutToProspect** | Manager, Director of Scouting | Same organization | Create assignment, notify scout |
| **createScoutingReport** | Scout | Assigned to prospect or team access | Create report, update status, notify director |
| **createInjuryReport** | Manager, Analyst, Staff | Team access | Create report, update roster status, notify staff |
| **promoteProspectToRoster** | Manager | Has contract, roster space | Create Player, update Prospect status, assign jersey |
| **updatePlayerRosterStatus** | Manager, Analyst | Team access | Update status, audit log, notify coaches |

## Security Policy Reference

### contract_visibility

| Role | Access | Scope | Column Filters |
|------|--------|-------|----------------|
| Manager | Full | Team | None |
| Owner | Full | Team | None |
| Analyst | Read | Team | totalValue, capHit, bonuses (HIDDEN) |
| Scout | None | - | - |
| Player | Self | Self | All financial fields (HIDDEN) |
| Staff | None | - | - |

### scouting_reports_access

| Role | Access | Scope | Notes |
|------|--------|-------|-------|
| Manager | Full | Team | Full read/write |
| Scout | Full | Team | Full read/write |
| Analyst | None | - | No access |
| Player | None | - | No access |
| Staff | None | - | No access |

### injury_reports_access

| Role | Access | Scope | Column Filters |
|------|--------|-------|----------------|
| Manager | Full | Team | None |
| Analyst | Read | Team | None |
| Scout | Read | Team | None |
| Player | Self | Self | injuryType, severity (HIDDEN) |
| Staff | Read | Team | None |

### performance_data_access

| Role | Access | Scope | Notes |
|------|--------|-------|-------|
| Manager | Full | All | League-wide access |
| Analyst | Full | All | League-wide access |
| Scout | Read | All | League-wide access |
| Player | Read | Self | Own stats only |
| Staff | Read | Team | Team data only |

### team_data_access

| Role | Access | Scope | Notes |
|------|--------|-------|-------|
| Manager | Full | Team | Full organizational access |
| Analyst | Read | Team | Read-only access |
| Scout | Read | Team | Read-only access |
| Player | Read | Team | Read-only access |
| Staff | Read | Team | Read-only access |

## Key Property Reference

### Player Properties

```yaml
playerId: string (required)
name: string (required)
teamId: string (required)
position: enum [C, LW, RW, D, G] (required)
jerseyNumber: integer
birthDate: date
height: integer (cm)
weight: integer (kg)
shootsCatches: enum [L, R]
draftYear: integer
draftRound: integer
draftOverall: integer
rosterStatus: enum [Active, Injured, Healthy Scratch, IR, LTIR, Suspended]
```

### Prospect Properties (Key Differences from Player)

```yaml
prospectId: string (required)
name: string (required)
nhlTeamId: string (required)           # Team that owns rights
currentLeague: string                   # AHL, Junior, European, etc.
currentTeam: string                     # Current team name
contractStatus: enum [Entry Level, Unsigned Draft Pick, AHL Contract, European Rights]
developmentStatus: enum [Junior, College, AHL, European Pro, NHL Ready]
```

**Critical Distinction**: Prospect represents players whose rights are owned by an NHL team but who are NOT on the NHL roster. This includes drafted players still developing and undrafted free agent signings.

### Contract Properties

```yaml
contractId: string (required)
playerId: string (required)
teamId: string (required)
contractType: enum [Entry Level, Standard, Extension, PTO, AHL]
startDate: date (required)
endDate: date (required)
totalValue: float (USD)                 # RESTRICTED: Managers only
annualCapHit: float (USD)               # RESTRICTED: Managers, Analysts (limited)
signingBonus: float (USD)               # RESTRICTED: Managers only
performanceBonus: float (USD)           # RESTRICTED: Managers only
hasNMC: boolean                         # No-movement clause
hasNTC: boolean                         # No-trade clause
isExpiring: boolean
yearsSigned: integer
```

### ScoutingReport Properties

```yaml
reportId: string (required)
scoutId: string (required)
prospectId: string (required)
reportDate: date (required)
gameAttended: string
overallGrade: enum [A+, A, A-, B+, B, B-, C+, C, C-, D]
skillsRating: object (JSON)             # Detailed skills breakdown
notes: text (required)                  # RESTRICTED: Scouts/Managers only
recommendations: text
nhlReadiness: enum [NHL Ready, 1-2 Years, 2-3 Years, 3+ Years, Unlikely]
```

## Resolver Backend Strategy

### BigQuery Tables (Relational Data)

```
core.owners
core.managers
core.scouts
core.analysts
core.teams
core.players
core.prospects
core.contracts
core.venues
core.scouting_reports
core.injury_reports
core.scout_prospect_assignments (join table)
```

### Parquet Files (Analytics Data)

```
analytics/player_stats.parquet
analytics/games.parquet
```

## Usage Examples

### TypeScript (Frontend - Future OSDK)

```typescript
import { osdk } from '@/ontology';

// Load team with roster
const team = await osdk.Team.byPrimaryKey('MTL');
const players = await team.players();
const prospects = await team.prospects();

// Load player with contracts and stats
const player = await osdk.Player.byPrimaryKey('8478398');
const contracts = await player.contracts();
const stats = await player.performance({ season: '2024-25' });

// Scout creates report (policy enforced)
const report = await osdk.Actions.createScoutingReport({
  scoutId: user.id,
  prospectId: 'prospect_001',
  overallGrade: 'B+',
  notes: 'Strong skating, developing defensive game',
  nhlReadiness: '1-2 Years'
});
```

### Python (Orchestrator - Future OSDK)

```python
from orchestrator.ontology_client import osdk

# Load team structure
team = osdk.Team.by_primary_key('MTL')
managers = team.managers()
scouts = team.scouts()
prospects = team.prospects()

# Scout workflow
for prospect in prospects:
    reports = prospect.scouting_reports()
    latest = reports[0] if reports else None
    if latest:
        print(f"{prospect.name}: {latest.overallGrade} ({latest.nhlReadiness})")

# Manager approves contract (policy enforced)
result = osdk.Actions.approveContract(
    contractId='contract_123',
    approverId=user.user_id,
    notes='Approved for 2024-25 season'
)
```

## Validation

### Run Schema Validator

```bash
python3 -m backend.ontology.schemas.validator backend/ontology/schemas/v0.1/schema.yaml
```

### Expected Output

```
✓ Schema validation successful!
  Version: 0.1.0
  Object types: 13
  Link types: 13
  Action types: 6
  Security policies: 12
```

## Schema File Location

**Primary Schema**: `backend/ontology/schemas/v0.1/schema.yaml`

**Validator**: `backend/ontology/schemas/validator.py`

**Documentation**: `backend/ontology/README.md`

**Implementation Guide**: `backend/ontology/OMS_IMPLEMENTATION_GUIDE.md`

---

**Version**: 0.1.0  
**Status**: Phase 0 Complete - Ready for Phase 1 Implementation  
**Last Updated**: 2025-10-24

