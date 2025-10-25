"""
HeartBeat Engine - OMS Proof of Concept Routes
NHL Advanced Analytics Platform

Demonstration routes showing OMS integration with policy enforcement.
These routes replace direct data access with ontology-based access.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
import logging

from orchestrator.utils.state import UserContext
from backend.api.dependencies import get_current_user_context
from backend.ontology.api.dependencies import (
    get_schema_registry,
    get_policy_engine,
    get_resolver
)
from backend.ontology.services.registry import SchemaRegistry
from backend.ontology.services.policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oms-demo", tags=["oms-demo"])


class PlayerBasic(BaseModel):
    """Basic player information"""
    playerId: str
    name: str
    position: str
    jerseyNumber: Optional[int]
    teamId: str


class TeamRosterResponse(BaseModel):
    """Team roster response"""
    teamId: str
    teamName: str
    players: List[Dict[str, Any]]
    count: int
    user_role: str
    filtered_fields: List[str]


class PlayerProfileResponse(BaseModel):
    """Player profile response"""
    player: Dict[str, Any]
    contracts: List[Dict[str, Any]]
    stats: List[Dict[str, Any]]
    user_role: str
    policy_applied: str


@router.get(
    "/teams/{team_id}/roster",
    response_model=TeamRosterResponse,
    summary="Get team roster via OMS (Proof of Concept)",
    description="""
    Demonstrates OMS integration with policy enforcement.
    
    Different roles see different data:
    - Manager: Full access including contract details
    - Scout: Player data but NO contract financials
    - Player: Can see teammates but limited details
    - Staff: Basic roster information only
    """
)
async def get_team_roster_oms(
    team_id: str,
    user: UserContext = Depends(get_current_user_context),
    registry: SchemaRegistry = Depends(get_schema_registry),
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    """
    Get team roster using OMS with policy enforcement.
    
    This is a proof-of-concept showing:
    1. Schema-based object access
    2. Policy enforcement per user role
    3. Column-level filtering (hide sensitive data)
    4. Link traversal (Team → Players)
    """
    try:
        # Get Team object type definition
        team_def = registry.get_object_type("Team")
        if not team_def:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Team object type not found in schema"
            )
        
        # Get resolver for Team
        backend = team_def.resolver_backend or "bigquery"
        team_resolver = get_resolver(backend)
        
        # Fetch team data
        team_data = team_resolver.get_by_id_cached("Team", team_id)
        if not team_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found"
            )
        
        # Get team_players link definition
        link_def = registry.get_link_type("team_players")
        if not link_def:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="team_players link type not found in schema"
            )
        
        # Get security policy for players
        player_def = registry.get_object_type("Player")
        policy = None
        if player_def and player_def.security_policy_ref:
            policy = registry.get_security_policy(player_def.security_policy_ref)
        
        # Evaluate access for players
        decision = policy_engine.evaluate_access(
            user_context=user,
            operation="read",
            target_type="object",
            policy=policy
        )
        
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {decision.reason}"
            )
        
        # Get resolver for Player
        player_backend = player_def.resolver_backend or "bigquery"
        player_resolver = get_resolver(player_backend)
        
        # Traverse link to get players
        players = player_resolver.traverse_link(
            from_object_type="Team",
            from_object_id=team_id,
            link_type="team_players",
            to_object_type="Player",
            link_config=link_def.resolver_config or {}
        )
        
        # Apply column filters based on user role
        filtered_players = [
            policy_engine.apply_column_filters(player, decision.column_filters)
            for player in players
        ]
        
        logger.info(
            f"Team roster accessed: {team_id}, "
            f"user={user.user_id}, role={user.role.value}, "
            f"players={len(filtered_players)}, "
            f"filtered_fields={decision.column_filters}"
        )
        
        return TeamRosterResponse(
            teamId=team_id,
            teamName=team_data.get("name", team_id),
            players=filtered_players,
            count=len(filtered_players),
            user_role=user.role.value,
            filtered_fields=decision.column_filters or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team roster via OMS: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/players/{player_id}/profile",
    response_model=PlayerProfileResponse,
    summary="Get player profile via OMS (Proof of Concept)",
    description="""
    Demonstrates OMS link traversal and policy enforcement.
    
    Different roles see different contract details:
    - Manager: Full contract details including financials
    - Scout: Contract exists but NO financial details
    - Player (self): Basic contract info, NO salary details
    - Player (other): NO contract access
    """
)
async def get_player_profile_oms(
    player_id: str,
    user: UserContext = Depends(get_current_user_context),
    registry: SchemaRegistry = Depends(get_schema_registry),
    policy_engine: PolicyEngine = Depends(get_policy_engine)
):
    """
    Get player profile with contracts using OMS.
    
    Demonstrates:
    1. Object access with policy enforcement
    2. Link traversal (Player → Contracts)
    3. Role-based column filtering
    4. Self-only access for players
    """
    try:
        # Get Player definition
        player_def = registry.get_object_type("Player")
        if not player_def:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Player object type not found"
            )
        
        # Get resolver
        backend = player_def.resolver_backend or "bigquery"
        resolver = get_resolver(backend)
        
        # Fetch player data
        player_data = resolver.get_by_id_cached("Player", player_id)
        if not player_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found"
            )
        
        # Check self-only access for players
        if user.role.value == "player" and user.user_id != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Players can only access their own profile"
            )
        
        # Get contracts link
        link_def = registry.get_link_type("player_contracts")
        contract_def = registry.get_object_type("Contract")
        
        contracts = []
        policy_applied = "No contracts accessed"
        
        if link_def and contract_def:
            # Get contract policy
            contract_policy = None
            if contract_def.security_policy_ref:
                contract_policy = registry.get_security_policy(
                    contract_def.security_policy_ref
                )
            
            # Evaluate contract access
            contract_decision = policy_engine.evaluate_access(
                user_context=user,
                operation="read",
                target_type="object",
                policy=contract_policy
            )
            
            if contract_decision.allowed:
                # Traverse to contracts
                contract_backend = contract_def.resolver_backend or "bigquery"
                contract_resolver = get_resolver(contract_backend)
                
                raw_contracts = contract_resolver.traverse_link(
                    from_object_type="Player",
                    from_object_id=player_id,
                    link_type="player_contracts",
                    to_object_type="Contract",
                    link_config=link_def.resolver_config or {}
                )
                
                # Apply column filters
                contracts = [
                    policy_engine.apply_column_filters(c, contract_decision.column_filters)
                    for c in raw_contracts
                ]
                
                policy_applied = (
                    f"Role: {user.role.value}, "
                    f"Filtered: {contract_decision.column_filters or 'none'}"
                )
            else:
                policy_applied = f"Contracts hidden: {contract_decision.reason}"
        
        # Mock stats for now (would use real resolver in production)
        stats = []
        
        logger.info(
            f"Player profile accessed: {player_id}, "
            f"user={user.user_id}, role={user.role.value}, "
            f"contracts={len(contracts)}"
        )
        
        return PlayerProfileResponse(
            player=player_data,
            contracts=contracts,
            stats=stats,
            user_role=user.role.value,
            policy_applied=policy_applied
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player profile via OMS: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

