"""
HeartBeat Player ID to Name Mapper
Maps player IDs to readable names throughout the system
"""

import pandas as pd
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PlayerMapper:
    """Handles all player ID to name conversions using nhl_rosters_latest.parquet"""
    
    def __init__(self, roster_parquet_path: Optional[Path] = None):
        """
        Initialize with player mapping from Parquet file
        
        Args:
            roster_parquet_path: Path to nhl_rosters_latest.parquet (defaults to data/processed/rosters/nhl_rosters_latest.parquet)
        """
        self.player_map = {}
        self.player_positions = {}
        self.player_teams = {}
        self.reverse_map = {}  # name -> id
        
        # Default to the nhl_rosters_latest.parquet file
        if roster_parquet_path is None:
            roster_parquet_path = Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/rosters/nhl_rosters_latest.parquet')
        
        self._load_mapping_from_parquet(roster_parquet_path)
    
    def _load_mapping_from_parquet(self, path: Path):
        """Load player mapping from Parquet file with enhanced structure"""
        try:
            # Load the Parquet file
            players_df = pd.read_parquet(path)
            logger.info(f"Loading player mappings from {path}")
            logger.info(f"Available columns: {players_df.columns.tolist()}")
            
            # Expected columns: nhl_player_id, first_name, last_name, full_name, team_abbrev, position
            for _, row in players_df.iterrows():
                reference_id = str(row.get('nhl_player_id', ''))
                first_name = str(row.get('first_name', '')).strip()
                last_name = str(row.get('last_name', '')).strip()
                full_name = str(row.get('full_name', '')).strip()
                team_abbrev = str(row.get('team_abbrev', ''))
                
                if reference_id and full_name:
                    # Store full name as primary mapping
                    self.player_map[reference_id] = full_name
                    self.reverse_map[full_name.lower()] = reference_id
                    
                    # Also map first/last name combinations for flexibility
                    if first_name and last_name:
                        alternate_name = f"{first_name} {last_name}"
                        if alternate_name != full_name:
                            self.reverse_map[alternate_name.lower()] = reference_id
                    
                    # Store team info from roster data
                    self.player_teams[reference_id] = team_abbrev if team_abbrev else 'Unknown'
                    
                    # Store position from roster data
                    position = str(row.get('position', 'Unknown'))
                    self.player_positions[reference_id] = position if position else 'Unknown'
            
            logger.info(f"✓ Loaded {len(self.player_map)} player mappings from nhl_rosters_latest.parquet")
            
            # Log sample mappings
            sample_players = list(self.player_map.items())[:5]
            for player_id, name in sample_players:
                team = self.player_teams.get(player_id, 'Unknown')
                position = self.player_positions.get(player_id, 'Unknown')
                logger.info(f"  {player_id} → {name} ({team} - {position})")
            
        except Exception as e:
            logger.error(f"Error loading player mapping from Parquet: {e}")
            # Fallback to empty mappings
            self._load_fallback_mappings()
    
    def _extract_team_from_filename(self, filename: str, player_id: str) -> str:
        """Extract team information from the first seen filename"""
        if not filename:
            return 'Unknown'
        
        try:
            # Filename pattern: playsequence-YYYYMMDD-NHL-TEAMvsTEAM-season-game.csv
            parts = filename.split('-')
            if len(parts) >= 4 and 'vs' in parts[3]:
                teams = parts[3].split('vs')
                if len(teams) == 2:
                    team1, team2 = teams[0], teams[1]
                    
                    # If one team is MTL, assign player to the other team (opponent)
                    # Unless we know this is an MTL player ID
                    if team1 == 'MTL':
                        return team2 if not self._is_known_mtl_player(player_id) else 'MTL'
                    elif team2 == 'MTL':
                        return team1 if not self._is_known_mtl_player(player_id) else 'MTL'
                    else:
                        # Neither team is MTL, default to first team
                        return team1
            
        except Exception:
            pass
        
        return 'Unknown'
    
    def _is_known_mtl_player(self, player_id: str) -> bool:
        """Check if this is a known MTL player based on common IDs"""
        # Key MTL player IDs that we know for sure
        mtl_core_ids = {
            '8480018', '8481540', '8483515', '8476875', '8482087', 
            '8481523', '8476469', '8476479', '8478470', '8481618',
            '8481593', '8482964', '8478133', '8483457', '8482111',
            '8481093', '8482487'
        }
        return player_id in mtl_core_ids
    
    def _load_fallback_mappings(self):
        """Load fallback mappings if CSV fails"""
        logger.warning("Loading fallback player mappings")
        self.player_map = MTL_PLAYER_FALLBACK.copy()
        self.reverse_map = {v.lower(): k for k, v in MTL_PLAYER_FALLBACK.items()}
        for player_id in MTL_PLAYER_FALLBACK.keys():
            self.player_teams[player_id] = 'MTL'
            self.player_positions[player_id] = 'Unknown'
    
    def id_to_name(self, player_id: str) -> str:
        """
        Convert player ID to name
        
        Args:
            player_id: Player ID to convert
            
        Returns:
            Player name or original ID if not found
        """
        return self.player_map.get(str(player_id), f"Player_{player_id}")
    
    def ids_to_names(self, player_ids: List[str]) -> List[str]:
        """
        Convert list of player IDs to names
        
        Args:
            player_ids: List of player IDs
            
        Returns:
            List of player names
        """
        return [self.id_to_name(pid) for pid in player_ids]
    
    def name_to_id(self, player_name: str) -> Optional[str]:
        """
        Convert player name to ID
        
        Args:
            player_name: Player name
            
        Returns:
            Player ID or None if not found
        """
        return self.reverse_map.get(player_name)
    
    def format_line(self, player_ids: List[str], separator: str = " - ") -> str:
        """
        Format a line of players with names
        
        Args:
            player_ids: List of player IDs
            separator: String to separate names
            
        Returns:
            Formatted string with player names
        """
        names = self.ids_to_names(player_ids)
        return separator.join(names)
    
    def format_deployment(self, forwards: List[str], defense: List[str]) -> Dict[str, List[str]]:
        """
        Format a complete deployment with names
        
        Args:
            forwards: List of forward IDs
            defense: List of defense IDs
            
        Returns:
            Dictionary with formatted names
        """
        return {
            'forwards': self.ids_to_names(forwards),
            'defense': self.ids_to_names(defense),
            'forwards_str': self.format_line(forwards),
            'defense_str': self.format_line(defense)
        }
    
    def get_player_info(self, player_id: str) -> Dict[str, str]:
        """
        Get complete player information
        
        Args:
            player_id: Player ID
            
        Returns:
            Dictionary with name, position, team
        """
        return {
            'id': player_id,
            'name': self.id_to_name(player_id),
            'position': self.player_positions.get(player_id, 'Unknown'),
            'team': self.player_teams.get(player_id, 'Unknown')
        }
    
    def get_mtl_players(self) -> Dict[str, List[str]]:
        """Get all Montreal Canadiens players by position"""
        mtl_forwards = []
        mtl_defense = []
        mtl_goalies = []
        
        for player_id, team in self.player_teams.items():
            if team == 'MTL':
                position = self.player_positions.get(player_id, '')
                name = self.player_map.get(player_id, player_id)
                
                if position == 'F' or position in ['C', 'LW', 'RW']:
                    mtl_forwards.append(f"{name} ({player_id})")
                elif position == 'D':
                    mtl_defense.append(f"{name} ({player_id})")
                elif position == 'G':
                    mtl_goalies.append(f"{name} ({player_id})")
        
        return {
            'forwards': sorted(mtl_forwards),
            'defense': sorted(mtl_defense),
            'goalies': sorted(mtl_goalies)
        }
    
    def display_matchup(self, mtl_players: List[str], opp_players: List[str], opp_team: str = "OPP") -> str:
        """
        Display a matchup with formatted names
        
        Args:
            mtl_players: List of MTL player IDs
            opp_players: List of opponent player IDs
            opp_team: Opponent team code
            
        Returns:
            Formatted matchup string
        """
        mtl_names = self.ids_to_names(mtl_players)
        opp_names = self.ids_to_names(opp_players)
        
        return f"MTL: {', '.join(mtl_names)}\nvs\n{opp_team}: {', '.join(opp_names)}"


# Common player ID mappings for Montreal Canadiens (2024-2025)
# These are fallback mappings if parquet file is unavailable
MTL_PLAYER_FALLBACK = {
    "8480018": "Nick Suzuki",
    "8481540": "Cole Caufield", 
    "8483515": "Juraj Slafkovsky",
    "8476875": "Mike Matheson",
    "8482087": "Kaiden Guhle",
    "8480829": "Kirby Dach",
    "8476469": "Josh Anderson",
    "8476479": "Brendan Gallagher",
    "8482719": "Alex Newhook",
    "8475848": "David Savard",
    "8478470": "Sam Montembeault",
    "8476932": "Jake Allen",
    "8480012": "Christian Dvorak",
    "8476967": "Arber Xhekaj",
    "8477494": "Joel Armia",
    "8482116": "Jordan Harris",
    "8479376": "Jake Evans",
    "8480707": "Oliver Kapanen",
    "8481697": "Jayden Struble",
    "8479400": "Mitchell Stephens",
    "8480802": "Lane Hutson"
}


def get_mapper(roster_parquet_path: Optional[Path] = None) -> PlayerMapper:
    """
    Get a PlayerMapper instance using nhl_rosters_latest.parquet
    
    Args:
        roster_parquet_path: Optional path to nhl_rosters_latest.parquet (defaults to data/processed/rosters/nhl_rosters_latest.parquet)
        
    Returns:
        PlayerMapper instance
    """
    return PlayerMapper(roster_parquet_path)
