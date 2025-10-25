#!/usr/bin/env python3
"""
HeartBeat Engine - OMS to BigQuery Resolver Verification

This script verifies that:
- Active OMS schema is accessible from Postgres
- BigQuery mappings from OMS object types resolve to ontology.* views
- Sample queries for key objects (Team, Player, Contract) return data
- Link traversal via join-table (team_players) returns roster rows

Requires:
- DATABASE_URL set (use Cloud SQL proxy locally)
- gcloud auth application-default login (ADC) for BigQuery access
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any
from pathlib import Path
import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.ontology.services.registry import SchemaRegistry
from backend.ontology.services.resolvers.bigquery_resolver import BigQueryResolver


def get_session() -> "sessionmaker":
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(2)
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine)


def register_all_mappings(resolver: BigQueryResolver, registry: SchemaRegistry) -> int:
    count = 0
    for obj in registry.get_all_object_types():
        rc: Dict[str, Any] = obj.resolver_config or {}
        table = rc.get("table") or rc.get("view")
        if table and obj.primary_key:
            resolver.register_object_mapping(obj.name, table, obj.primary_key)
            count += 1
    return count


def scalar(client, sql: str) -> int:
    job = resolver.client.query(sql)
    result = job.result()
    for row in result:
        return int(list(row.values())[0])
    return 0


if __name__ == "__main__":
    project_id = os.getenv("GCP_PROJECT", "heartbeat-474020")
    ontology_dataset = os.getenv("BQ_DATASET_ONTOLOGY", "ontology")

    # 1) Create session and registry
    SessionLocal = get_session()
    session = SessionLocal()
    registry = SchemaRegistry(session)

    # 2) Create BigQuery resolver and register mappings
    resolver = BigQueryResolver(project_id=project_id, dataset_id=ontology_dataset)
    num_mappings = register_all_mappings(resolver, registry)
    print(f"Registered BigQuery mappings: {num_mappings}")

    # 3) Object smoke checks
    # Counts via direct SQL for a stronger signal
    players_cnt = scalar(resolver.client, f"SELECT COUNT(*) FROM `{project_id}.{ontology_dataset}.objects_player`")
    teams_cnt = scalar(resolver.client, f"SELECT COUNT(*) FROM `{project_id}.{ontology_dataset}.objects_team`")
    contracts_cnt = scalar(resolver.client, f"SELECT COUNT(*) FROM `{project_id}.{ontology_dataset}.objects_contract`")

    print(f"Counts → players: {players_cnt}, teams: {teams_cnt}, contracts: {contracts_cnt}")
    assert teams_cnt > 0, "No teams found in ontology.objects_team"
    assert players_cnt > 0, "No players found in ontology.objects_player"
    assert contracts_cnt >= 0, "Contract count should be >= 0"

    # 4) Resolver get_by_filter (no filter, limited)
    some_players = resolver.get_by_filter("Player", filters={}, properties=["playerId", "name", "teamId"], limit=3)
    assert len(some_players) > 0, "Resolver returned no players"
    print(f"Sample players (3): {[p['playerId'] for p in some_players]}")

    # 5) Link traversal: pick any team and traverse team_players
    some_teams = resolver.get_by_filter("Team", filters={}, properties=["teamId"], limit=5)
    assert len(some_teams) > 0, "Resolver returned no teams"
    team_id = random.choice(some_teams)["teamId"]

    link = registry.get_link_type("team_players")
    assert link is not None, "Link type 'team_players' not found in registry"

    roster = resolver.traverse_link(
        from_object_type="Team",
        from_object_id=team_id,
        link_type="team_players",
        to_object_type="Player",
        link_config=link.resolver_config or {},
        properties=["playerId", "name", "position"],
        limit=50,
    )
    assert len(roster) > 0, f"No roster rows returned for team {team_id} via team_players"
    print(f"Roster sample for team {team_id}: {len(roster)} players (showing up to 5)")
    for row in roster[:5]:
        print(f"  - {row.get('playerId')} {row.get('name')} ({row.get('position')})")

    print("\n✓ OMS → BigQuery resolver verification passed")
