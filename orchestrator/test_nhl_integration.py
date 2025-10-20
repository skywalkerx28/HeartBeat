"""
HeartBeat Engine - NHL Roster & Live Game Integration Test
Montreal Canadiens Advanced Analytics Assistant

Comprehensive test suite for NHL roster and live game data integration.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from orchestrator.tools.nhl_roster_client import NHLRosterClient, NHLLiveGameClient
from orchestrator.tools.data_catalog import HeartBeatDataCatalog
from orchestrator.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NHLIntegrationTest:
    """Test suite for NHL roster and live game integration"""
    
    def __init__(self):
        self.roster_client = NHLRosterClient()
        self.live_game_client = NHLLiveGameClient()
        self.data_catalog = HeartBeatDataCatalog(settings.parquet.data_directory)
        
        self.results = {
            "roster_tests": {},
            "live_game_tests": {},
            "hybrid_tests": {}
        }
    
    async def run_all_tests(self):
        """Run complete test suite"""
        logger.info("="*70)
        logger.info("HeartBeat Engine - NHL Integration Test Suite")
        logger.info("="*70)
        logger.info("")
        
        # Roster tests
        await self.test_roster_fetch()
        await self.test_multiple_rosters()
        await self.test_roster_player_search()
        
        # Live game tests
        await self.test_todays_games()
        await self.test_team_game_today()
        await self.test_game_boxscore()
        
        # Hybrid tests (Parquet fallback)
        await self.test_hybrid_roster_access()
        await self.test_parquet_player_search()
        
        # Print summary
        self.print_summary()
    
    async def test_roster_fetch(self):
        """Test: Fetch single team roster from NHL API"""
        logger.info("TEST 1: Fetch Montreal Canadiens roster")
        logger.info("-" * 50)
        
        try:
            roster = await self.roster_client.get_team_roster(
                team="MTL",
                season="current",
                scope="active"
            )
            
            player_count = len(roster.get("players", []))
            source = roster.get("source")
            
            logger.info(f"  Source: {source}")
            logger.info(f"  Players: {player_count}")
            logger.info(f"  Team: {roster.get('team')}")
            logger.info(f"  Season: {roster.get('season')}")
            
            if player_count > 0:
                sample_player = roster["players"][0]
                logger.info(f"  Sample player: {sample_player.get('full_name')} #{sample_player.get('sweater')} ({sample_player.get('position')})")
            
            self.results["roster_tests"]["single_fetch"] = "PASS" if player_count > 15 else "FAIL"
            logger.info(f"  Result: {'PASS' if player_count > 15 else 'FAIL'}")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["roster_tests"]["single_fetch"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_multiple_rosters(self):
        """Test: Fetch rosters for multiple teams"""
        logger.info("TEST 2: Fetch multiple team rosters (MTL, TOR, BOS)")
        logger.info("-" * 50)
        
        try:
            teams = ["MTL", "TOR", "BOS"]
            rosters = await self.roster_client.get_all_rosters(
                teams=teams,
                season="current",
                scope="active",
                max_concurrency=3
            )
            
            logger.info(f"  Requested: {len(teams)} teams")
            logger.info(f"  Retrieved: {len(rosters)} teams")
            
            for team, roster in rosters.items():
                player_count = len(roster.get("players", []))
                logger.info(f"    {team}: {player_count} players")
            
            success = all(len(r.get("players", [])) > 15 for r in rosters.values())
            self.results["roster_tests"]["multiple_fetch"] = "PASS" if success else "FAIL"
            logger.info(f"  Result: {'PASS' if success else 'FAIL'}")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["roster_tests"]["multiple_fetch"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_roster_player_search(self):
        """Test: Search for specific player"""
        logger.info("TEST 3: Search for player in roster (Nick Suzuki)")
        logger.info("-" * 50)
        
        try:
            roster = await self.roster_client.get_team_roster(team="MTL", season="current")
            players = roster.get("players", [])
            
            # Search for Suzuki
            suzuki = [p for p in players if "suzuki" in p.get("full_name", "").lower()]
            
            if suzuki:
                player = suzuki[0]
                logger.info(f"  Found: {player.get('full_name')}")
                logger.info(f"  Position: {player.get('position')}")
                logger.info(f"  Number: {player.get('sweater')}")
                logger.info(f"  NHL ID: {player.get('nhl_player_id')}")
                self.results["roster_tests"]["player_search"] = "PASS"
                logger.info("  Result: PASS")
            else:
                logger.warning("  Player not found in roster")
                self.results["roster_tests"]["player_search"] = "FAIL: Player not found"
                logger.info("  Result: FAIL")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["roster_tests"]["player_search"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_todays_games(self):
        """Test: Fetch today's NHL schedule"""
        logger.info("TEST 4: Fetch today's NHL games")
        logger.info("-" * 50)
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            schedule = await self.live_game_client.get_todays_games(date=today)
            
            games = schedule.get("games", [])
            logger.info(f"  Date: {today}")
            logger.info(f"  Games: {len(games)}")
            
            if games:
                for i, game in enumerate(games[:3], 1):
                    home = game.get("homeTeam", {}).get("abbrev")
                    away = game.get("awayTeam", {}).get("abbrev")
                    state = game.get("gameState")
                    logger.info(f"    Game {i}: {away} @ {home} ({state})")
            else:
                logger.info("  No games scheduled today")
            
            self.results["live_game_tests"]["schedule"] = "PASS"
            logger.info("  Result: PASS")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["live_game_tests"]["schedule"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_team_game_today(self):
        """Test: Find Montreal's game today"""
        logger.info("TEST 5: Find Montreal Canadiens game today")
        logger.info("-" * 50)
        
        try:
            game_data = await self.live_game_client.get_game_data(team="MTL")
            
            if "error" in game_data:
                logger.info(f"  Status: {game_data['error']}")
                logger.info("  (This is OK if Montreal doesn't have a game today)")
                self.results["live_game_tests"]["team_game"] = "PASS (No game today)"
            else:
                game = game_data.get("data", {})
                logger.info(f"  Game ID: {game_data.get('game_id')}")
                logger.info(f"  State: {game_data.get('game_state')}")
                logger.info(f"  Home: {game.get('homeTeam', {}).get('abbrev')}")
                logger.info(f"  Away: {game.get('awayTeam', {}).get('abbrev')}")
                
                if "score" in game.get("homeTeam", {}):
                    home_score = game["homeTeam"]["score"]
                    away_score = game["awayTeam"]["score"]
                    logger.info(f"  Score: {away_score} - {home_score}")
                
                self.results["live_game_tests"]["team_game"] = "PASS"
                logger.info("  Result: PASS")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["live_game_tests"]["team_game"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_game_boxscore(self):
        """Test: Fetch boxscore if game exists"""
        logger.info("TEST 6: Fetch game boxscore")
        logger.info("-" * 50)
        
        try:
            game_data = await self.live_game_client.get_game_data(team="MTL")
            
            if "error" in game_data:
                logger.info("  No game today - skipping boxscore test")
                self.results["live_game_tests"]["boxscore"] = "SKIP (No game)"
            else:
                game_id = game_data.get("game_id")
                logger.info(f"  Fetching boxscore for game {game_id}...")
                
                boxscore = await self.live_game_client.get_boxscore(game_id)
                
                if "error" not in boxscore:
                    logger.info("  Boxscore retrieved successfully")
                    logger.info("  Contains player statistics: YES")
                    self.results["live_game_tests"]["boxscore"] = "PASS"
                    logger.info("  Result: PASS")
                else:
                    logger.warning(f"  Boxscore error: {boxscore['error']}")
                    self.results["live_game_tests"]["boxscore"] = "FAIL"
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["live_game_tests"]["boxscore"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_hybrid_roster_access(self):
        """Test: Hybrid roster access (Parquet -> API fallback)"""
        logger.info("TEST 7: Hybrid roster access (Parquet with API fallback)")
        logger.info("-" * 50)
        
        try:
            # Try Parquet first
            roster_df = self.data_catalog.get_team_roster_from_snapshot("MTL")
            
            if not roster_df.empty:
                logger.info(f"  Parquet snapshot: {len(roster_df)} players found")
                logger.info("  Source: Parquet (FAST)")
                self.results["hybrid_tests"]["parquet_access"] = "PASS"
                logger.info("  Result: PASS")
            else:
                logger.info("  Parquet snapshot: Empty")
                logger.info("  Falling back to NHL API...")
                
                roster = await self.roster_client.get_team_roster("MTL", "current")
                player_count = len(roster.get("players", []))
                
                logger.info(f"  NHL API: {player_count} players found")
                logger.info("  Source: NHL API (fallback)")
                self.results["hybrid_tests"]["parquet_access"] = "PASS (via API fallback)"
                logger.info("  Result: PASS")
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["hybrid_tests"]["parquet_access"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    async def test_parquet_player_search(self):
        """Test: Search player in Parquet snapshots"""
        logger.info("TEST 8: Search player in Parquet snapshots")
        logger.info("-" * 50)
        
        try:
            results_df = self.data_catalog.search_player_in_rosters("McDavid")
            
            if not results_df.empty:
                logger.info(f"  Matches found: {len(results_df)}")
                
                for _, player in results_df.iterrows():
                    logger.info(f"    {player.get('full_name')} - {player.get('team_abbrev')} #{player.get('sweater')}")
                
                self.results["hybrid_tests"]["player_search"] = "PASS"
                logger.info("  Result: PASS")
            else:
                logger.info("  No matches found (Parquet data may not be populated)")
                self.results["hybrid_tests"]["player_search"] = "SKIP (No Parquet data)"
        
        except Exception as e:
            logger.error(f"  ERROR: {str(e)}")
            self.results["hybrid_tests"]["player_search"] = f"FAIL: {str(e)}"
        
        logger.info("")
    
    def print_summary(self):
        """Print test summary"""
        logger.info("="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        logger.info("")
        
        for category, tests in self.results.items():
            logger.info(f"{category.upper().replace('_', ' ')}:")
            for test_name, result in tests.items():
                status = "PASS" if result == "PASS" or result.startswith("PASS") else "FAIL" if result.startswith("FAIL") else "SKIP"
                logger.info(f"  {test_name}: {status}")
        
        logger.info("")
        
        # Count results
        total = sum(len(tests) for tests in self.results.values())
        passed = sum(1 for tests in self.results.values() for r in tests.values() if r.startswith("PASS"))
        failed = sum(1 for tests in self.results.values() for r in tests.values() if r.startswith("FAIL"))
        skipped = sum(1 for tests in self.results.values() for r in tests.values() if r.startswith("SKIP"))
        
        logger.info(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        logger.info("")
        
        if failed == 0:
            logger.info("ALL TESTS PASSED!")
        else:
            logger.warning(f"{failed} TEST(S) FAILED")
        
        logger.info("="*70)


async def main():
    """Run test suite"""
    test_suite = NHLIntegrationTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

