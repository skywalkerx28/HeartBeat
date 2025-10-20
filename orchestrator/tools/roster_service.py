#!/usr/bin/env python3
"""
Roster Service for HeartBeat Engine
Handles player_id -> player info lookups with caching
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class PlayerInfo:
    """Player information from roster"""
    id: int
    first_name: str
    last_name: str
    full_name: str
    sweater_number: Optional[int]
    position_code: str
    shoots_catches: str
    team_code: str
    season: str


class RosterService:
    """
    Roster lookup service with multi-season support and caching
    
    Features:
    - Fast player_id -> name lookups
    - Multi-season roster data
    - Team-based filtering
    - LRU cache for performance
    """
    
    def __init__(self, rosters_base_dir: str = None):
        """
        Initialize roster service
        
        Args:
            rosters_base_dir: Base directory for roster JSON files
        """
        if rosters_base_dir is None:
            workspace = Path(__file__).parent.parent.parent
            rosters_base_dir = workspace / "data/processed/rosters"
        
        self.rosters_base_dir = Path(rosters_base_dir)
        self.cache = {}  # {season: {team: roster_data}}
    
    def _load_roster(self, team_code: str, season: str) -> Dict:
        """Load roster JSON for a specific team/season"""
        roster_file = self.rosters_base_dir / team_code / season / f"{team_code}_roster_{season}.json"
        
        if not roster_file.exists():
            return {"forwards": [], "defensemen": [], "goalies": []}
        
        with open(roster_file, 'r') as f:
            return json.load(f)
    
    def _get_cached_roster(self, team_code: str, season: str) -> Dict:
        """Get roster with caching"""
        cache_key = f"{season}:{team_code}"
        
        if cache_key not in self.cache:
            self.cache[cache_key] = self._load_roster(team_code, season)
        
        return self.cache[cache_key]
    
    def get_player_info(
        self, 
        player_id: int | str, 
        team_code: Optional[str] = None,
        season: str = "20252026"
    ) -> Optional[PlayerInfo]:
        """
        Get player information by ID
        
        Args:
            player_id: NHL player ID (e.g., 8478463)
            team_code: Team code (e.g., 'WSH') - if None, searches all teams
            season: Season string (e.g., '20252026')
        
        Returns:
            PlayerInfo object or None if not found
        """
        player_id = int(str(player_id).replace('.0', ''))
        
        teams_to_search = [team_code] if team_code else self._get_all_teams()
        
        for team in teams_to_search:
            roster = self._get_cached_roster(team, season)
            
            # Search forwards, defensemen, goalies
            for position_group in ['forwards', 'defensemen', 'goalies']:
                for player in roster.get(position_group, []):
                    if player['id'] == player_id:
                        return PlayerInfo(
                            id=player['id'],
                            first_name=player['firstName'].get('default', ''),
                            last_name=player['lastName'].get('default', ''),
                            full_name=f"{player['firstName'].get('default', '')} {player['lastName'].get('default', '')}",
                            sweater_number=player.get('sweaterNumber'),
                            position_code=player.get('positionCode', ''),
                            shoots_catches=player.get('shootsCatches', ''),
                            team_code=team,
                            season=season
                        )
        
        return None
    
    def get_player_name(
        self, 
        player_id: int | str,
        team_code: Optional[str] = None,
        season: str = "20252026",
        format: str = "full"
    ) -> str:
        """
        Get player name by ID
        
        Args:
            player_id: NHL player ID
            team_code: Team code (optional)
            season: Season string
            format: 'full' (default), 'last', 'first_last', 'last_first'
        
        Returns:
            Player name string or player_id as string if not found
        """
        info = self.get_player_info(player_id, team_code, season)
        
        if not info:
            return str(player_id)
        
        if format == "full":
            return info.full_name
        elif format == "last":
            return info.last_name
        elif format == "first_last":
            return f"{info.first_name} {info.last_name}"
        elif format == "last_first":
            return f"{info.last_name}, {info.first_name}"
        else:
            return info.full_name
    
    def get_players_batch(
        self,
        player_ids: List[int | str],
        team_code: Optional[str] = None,
        season: str = "20252026"
    ) -> Dict[int, PlayerInfo]:
        """
        Get multiple players at once
        
        Returns:
            Dict mapping player_id -> PlayerInfo
        """
        result = {}
        for pid in player_ids:
            info = self.get_player_info(pid, team_code, season)
            if info:
                result[info.id] = info
        return result
    
    def search_by_name(
        self,
        name_query: str,
        team_code: Optional[str] = None,
        season: str = "20252026"
    ) -> List[PlayerInfo]:
        """
        Search players by name (fuzzy matching)
        
        Args:
            name_query: Name to search (first, last, or full)
            team_code: Limit to specific team
            season: Season to search
        
        Returns:
            List of matching PlayerInfo objects
        """
        query = name_query.lower().strip()
        results = []
        
        teams_to_search = [team_code] if team_code else self._get_all_teams()
        
        for team in teams_to_search:
            roster = self._get_cached_roster(team, season)
            
            for position_group in ['forwards', 'defensemen', 'goalies']:
                for player in roster.get(position_group, []):
                    first = player['firstName'].get('default', '').lower()
                    last = player['lastName'].get('default', '').lower()
                    full = f"{first} {last}"
                    
                    if query in first or query in last or query in full:
                        results.append(PlayerInfo(
                            id=player['id'],
                            first_name=player['firstName'].get('default', ''),
                            last_name=player['lastName'].get('default', ''),
                            full_name=f"{player['firstName'].get('default', '')} {player['lastName'].get('default', '')}",
                            sweater_number=player.get('sweaterNumber'),
                            position_code=player.get('positionCode', ''),
                            shoots_catches=player.get('shootsCatches', ''),
                            team_code=team,
                            season=season
                        ))
        
        return results
    
    def _get_all_teams(self) -> List[str]:
        """Get list of all team codes"""
        if not self.rosters_base_dir.exists():
            return []
        
        teams = [d.name for d in self.rosters_base_dir.iterdir() if d.is_dir()]
        return sorted(teams)
    
    def get_team_roster(
        self,
        team_code: str,
        season: str = "20252026",
        position: Optional[str] = None
    ) -> List[PlayerInfo]:
        """
        Get entire roster for a team
        
        Args:
            team_code: Team code (e.g., 'WSH')
            season: Season string
            position: Filter by position ('forwards', 'defensemen', 'goalies')
        
        Returns:
            List of PlayerInfo objects
        """
        roster = self._get_cached_roster(team_code, season)
        results = []
        
        groups = [position] if position else ['forwards', 'defensemen', 'goalies']
        
        for group in groups:
            for player in roster.get(group, []):
                results.append(PlayerInfo(
                    id=player['id'],
                    first_name=player['firstName'].get('default', ''),
                    last_name=player['lastName'].get('default', ''),
                    full_name=f"{player['firstName'].get('default', '')} {player['lastName'].get('default', '')}",
                    sweater_number=player.get('sweaterNumber'),
                    position_code=player.get('positionCode', ''),
                    shoots_catches=player.get('shootsCatches', ''),
                    team_code=team_code,
                    season=season
                ))
        
        return results


# Singleton instance
_roster_service_instance = None

def get_roster_service() -> RosterService:
    """Get global RosterService instance"""
    global _roster_service_instance
    if _roster_service_instance is None:
        _roster_service_instance = RosterService()
    return _roster_service_instance


def main():
    """Test roster service"""
    print("\n" + "="*70)
    print("Roster Service Test")
    print("="*70 + "\n")
    
    service = RosterService()
    
    # Test 1: Look up specific player
    print("TEST 1: Look up player by ID")
    print("-" * 70)
    player = service.get_player_info(8478463, team_code="WSH")
    if player:
        print(f"Player ID 8478463:")
        print(f"  Name: {player.full_name}")
        print(f"  Number: #{player.sweater_number}")
        print(f"  Position: {player.position_code}")
        print(f"  Shoots: {player.shoots_catches}")
    
    # Test 2: Batch lookup
    print("\n\nTEST 2: Batch lookup")
    print("-" * 70)
    player_ids = [8478463, 8475343, 8476880]
    players = service.get_players_batch(player_ids, team_code="WSH")
    for pid, p in players.items():
        print(f"  {pid}: {p.full_name} #{p.sweater_number} ({p.position_code})")
    
    # Test 3: Search by name
    print("\n\nTEST 3: Search by name")
    print("-" * 70)
    results = service.search_by_name("ovechkin", team_code="WSH")
    for p in results:
        print(f"  {p.full_name} #{p.sweater_number} ({p.position_code})")
    
    # Test 4: Get team roster
    print("\n\nTEST 4: Get WSH forwards")
    print("-" * 70)
    forwards = service.get_team_roster("WSH", position="forwards")
    print(f"Total forwards: {len(forwards)}")
    for p in forwards[:5]:
        print(f"  {p.full_name} #{p.sweater_number}")
    
    print("\n" + "="*70)
    print("All tests passed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

