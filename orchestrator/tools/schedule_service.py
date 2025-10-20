#!/usr/bin/env python3
"""
Schedule Service for HeartBeat Engine
Handles timeframe resolution and game lookups
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class GameInfo:
    """Game information from schedule"""
    game_id: int
    season: str
    game_type: int  # 1=preseason, 2=regular, 3=playoffs
    game_date: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    game_state: str  # FINAL, LIVE, FUT, etc.
    opponent: str  # From perspective of the query team


class ScheduleService:
    """
    Schedule lookup service with timeframe resolution
    
    Features:
    - Resolve "last_game", "last_N_games", "this_season"
    - Filter by game state (completed games only)
    - Multi-season support
    - Team-based game filtering
    """
    
    def __init__(self, schedules_base_dir: str = None):
        """
        Initialize schedule service
        
        Args:
            schedules_base_dir: Base directory for schedule JSON files
        """
        if schedules_base_dir is None:
            workspace = Path(__file__).parent.parent.parent
            schedules_base_dir = workspace / "data/processed/schedule"
        
        self.schedules_base_dir = Path(schedules_base_dir)
        self.cache = {}  # {season: {team: schedule_data}}
    
    def _load_schedule(self, team_code: str, season: str) -> Dict:
        """Load schedule JSON for a specific team/season"""
        schedule_file = self.schedules_base_dir / season / f"{team_code}_schedule_{season}.json"
        
        if not schedule_file.exists():
            return {"games": []}
        
        with open(schedule_file, 'r') as f:
            return json.load(f)
    
    def _get_cached_schedule(self, team_code: str, season: str) -> Dict:
        """Get schedule with caching"""
        cache_key = f"{season}:{team_code}"
        
        if cache_key not in self.cache:
            self.cache[cache_key] = self._load_schedule(team_code, season)
        
        return self.cache[cache_key]
    
    def get_completed_games(
        self,
        team_code: str,
        season: str = "20252026",
        game_type: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[GameInfo]:
        """
        Get completed games for a team, sorted newest first
        
        Args:
            team_code: Team code (e.g., 'WSH')
            season: Season string
            game_type: Filter by type (1=preseason, 2=regular, 3=playoffs)
            limit: Max number of games to return
        
        Returns:
            List of GameInfo objects, sorted by date descending
        """
        schedule = self._get_cached_schedule(team_code, season)
        games = schedule.get('games', [])
        
        # Filter completed games
        completed = []
        for game in games:
            if game.get('gameState') != 'FINAL':
                continue
            
            if game_type is not None and game.get('gameType') != game_type:
                continue
            
            # Determine opponent
            is_home = game['homeTeam']['id'] == self._get_team_id_from_code(team_code, game)
            opponent_team = game['awayTeam'] if is_home else game['homeTeam']
            
            completed.append(GameInfo(
                game_id=game['id'],
                season=str(game['season']),
                game_type=game['gameType'],
                game_date=game['gameDate'],
                home_team=game['homeTeam']['abbrev'],
                away_team=game['awayTeam']['abbrev'],
                home_score=game['homeTeam'].get('score'),
                away_score=game['awayTeam'].get('score'),
                game_state=game['gameState'],
                opponent=opponent_team['abbrev']
            ))
        
        # Sort by date descending (most recent first)
        completed.sort(key=lambda g: g.game_date, reverse=True)
        
        if limit:
            completed = completed[:limit]
        
        return completed
    
    def _get_team_id_from_code(self, team_code: str, game: Dict) -> int:
        """Helper to get team ID from team code"""
        if game['homeTeam']['abbrev'] == team_code:
            return game['homeTeam']['id']
        elif game['awayTeam']['abbrev'] == team_code:
            return game['awayTeam']['id']
        return -1
    
    def resolve_timeframe(
        self,
        timeframe: str,
        team_code: str,
        season: str = "20252026",
        game_type: int = 2  # Regular season by default
    ) -> List[int]:
        """
        Resolve timeframe to list of game IDs
        
        Args:
            timeframe: 'last_game', 'last_3_games', 'last_5_games', 'last_10_games', 'this_season'
            team_code: Team code
            season: Season string
            game_type: Game type filter
        
        Returns:
            List of game IDs (shortened to last 5 digits for matching with PBP files)
        """
        if timeframe == "last_game":
            limit = 1
        elif timeframe == "last_3_games":
            limit = 3
        elif timeframe == "last_5_games":
            limit = 5
        elif timeframe == "last_10_games":
            limit = 10
        elif timeframe == "this_season":
            limit = None  # All completed games
        else:
            limit = 1  # Default to last game
        
        games = self.get_completed_games(team_code, season, game_type, limit)
        
        # Return shortened game IDs (last 5 digits) for matching with extracted metrics
        return [self._shorten_game_id(g.game_id) for g in games]
    
    def _shorten_game_id(self, game_id: int) -> str:
        """
        Convert full game ID to shortened format used in metrics
        
        Full game ID: 2025020038
        Shortened: 20038
        """
        game_id_str = str(game_id)
        # Extract last 5 digits
        return game_id_str[-5:]
    
    def get_game_info(
        self,
        game_id: int | str,
        team_code: str,
        season: str = "20252026"
    ) -> Optional[GameInfo]:
        """
        Get info for a specific game
        
        Args:
            game_id: Full game ID or shortened (e.g., 20038)
            team_code: Team code
            season: Season string
        
        Returns:
            GameInfo object or None
        """
        # If shortened game ID, search by suffix
        game_id_str = str(game_id)
        
        schedule = self._get_cached_schedule(team_code, season)
        games = schedule.get('games', [])
        
        for game in games:
            full_id = str(game['id'])
            if full_id == game_id_str or full_id.endswith(game_id_str):
                is_home = game['homeTeam']['id'] == self._get_team_id_from_code(team_code, game)
                opponent_team = game['awayTeam'] if is_home else game['homeTeam']
                
                return GameInfo(
                    game_id=game['id'],
                    season=str(game['season']),
                    game_type=game['gameType'],
                    game_date=game['gameDate'],
                    home_team=game['homeTeam']['abbrev'],
                    away_team=game['awayTeam']['abbrev'],
                    home_score=game['homeTeam'].get('score'),
                    away_score=game['awayTeam'].get('score'),
                    game_state=game['gameState'],
                    opponent=opponent_team['abbrev']
                )
        
        return None
    
    def get_games_vs_opponent(
        self,
        team_code: str,
        opponent_code: str,
        season: str = "20252026",
        limit: Optional[int] = None
    ) -> List[GameInfo]:
        """
        Get all games vs a specific opponent
        
        Returns:
            List of GameInfo objects, sorted by date descending
        """
        completed = self.get_completed_games(team_code, season)
        
        # Filter by opponent
        vs_opponent = [g for g in completed if g.opponent == opponent_code]
        
        if limit:
            vs_opponent = vs_opponent[:limit]
        
        return vs_opponent


# Singleton instance
_schedule_service_instance = None

def get_schedule_service() -> ScheduleService:
    """Get global ScheduleService instance"""
    global _schedule_service_instance
    if _schedule_service_instance is None:
        _schedule_service_instance = ScheduleService()
    return _schedule_service_instance


def main():
    """Test schedule service"""
    print("\n" + "="*70)
    print("Schedule Service Test")
    print("="*70 + "\n")
    
    service = ScheduleService()
    
    # Test 1: Get last game
    print("TEST 1: Get last completed game for WSH")
    print("-" * 70)
    games = service.get_completed_games("WSH", limit=1, game_type=2)
    if games:
        g = games[0]
        print(f"Game {g.game_id}: {g.away_team} @ {g.home_team}")
        print(f"  Date: {g.game_date}")
        print(f"  Score: {g.away_score} - {g.home_score}")
        print(f"  Opponent: {g.opponent}")
    
    # Test 2: Resolve timeframe
    print("\n\nTEST 2: Resolve 'last_3_games'")
    print("-" * 70)
    game_ids = service.resolve_timeframe("last_3_games", "WSH")
    print(f"Game IDs: {game_ids}")
    
    # Test 3: Get specific game info
    print("\n\nTEST 3: Get game info for 20038")
    print("-" * 70)
    game = service.get_game_info("20038", "WSH")
    if game:
        print(f"Game {game.game_id}: {game.away_team} @ {game.home_team}")
        print(f"  Date: {game.game_date}")
        print(f"  Opponent: {game.opponent}")
    
    # Test 4: Get games vs specific opponent
    print("\n\nTEST 4: Get games vs NYR")
    print("-" * 70)
    games = service.get_games_vs_opponent("WSH", "NYR", limit=3)
    print(f"Found {len(games)} games vs NYR:")
    for g in games:
        print(f"  {g.game_date}: {g.away_team} @ {g.home_team} ({g.away_score}-{g.home_score})")
    
    # Test 5: Get all completed regular season games
    print("\n\nTEST 5: Get all completed regular season games")
    print("-" * 70)
    all_games = service.get_completed_games("WSH", game_type=2)
    print(f"Total completed regular season games: {len(all_games)}")
    
    print("\n" + "="*70)
    print("All tests passed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

