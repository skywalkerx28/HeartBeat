"""
Player Name to ID Mapper
Maps player names from contract data to NHL player IDs in unified roster
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class PlayerMapper:
    """Maps player names to NHL player IDs using the unified roster"""
    
    def __init__(self, roster_path: str = 'data/processed/rosters/unified_roster_historical.json'):
        self.roster_path = Path(roster_path)
        self.players = []
        self.name_to_player = {}
        self.load_roster()
    
    def load_roster(self):
        """Load unified roster and create lookup indices"""
        try:
            with open(self.roster_path, 'r') as f:
                data = json.load(f)
            
            self.players = data.get('players', [])
            
            # Create name lookup index
            for player in self.players:
                # Index by full name (normalized)
                full_name = self.normalize_name(player['name'])
                self.name_to_player[full_name] = player
                
                # Index by "FirstName LastName" format
                first_last = f"{player['firstName']} {player['lastName']}"
                first_last_norm = self.normalize_name(first_last)
                if first_last_norm not in self.name_to_player:
                    self.name_to_player[first_last_norm] = player
                
                # Index by "LastName, FirstName" format
                last_first = f"{player['lastName']}, {player['firstName']}"
                last_first_norm = self.normalize_name(last_first)
                if last_first_norm not in self.name_to_player:
                    self.name_to_player[last_first_norm] = player
            
            logger.info(f"Loaded {len(self.players)} players from roster")
            logger.info(f"Created {len(self.name_to_player)} name lookup entries")
            
        except Exception as e:
            logger.error(f"Failed to load roster from {self.roster_path}: {e}")
            raise
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize player name for matching
        - Remove numbers and # symbols (e.g., "Sidney#87 Crosby" -> "sidney crosby")
        - Convert to lowercase
        - Remove extra whitespace
        - Remove punctuation except hyphens
        """
        if not name:
            return ""
        
        # Remove jersey numbers (e.g., #87, #87_, etc.)
        name = re.sub(r'#\d+\w*', '', name)
        
        # Remove non-alphanumeric except spaces, hyphens, and apostrophes
        name = re.sub(r"[^a-zA-Z\s\-']", ' ', name)
        
        # Normalize whitespace
        name = ' '.join(name.split())
        
        # Lowercase
        name = name.lower().strip()
        
        return name
    
    def find_player_exact(self, name: str) -> Optional[Dict]:
        """Find player by exact name match (after normalization)"""
        normalized = self.normalize_name(name)
        return self.name_to_player.get(normalized)
    
    def find_player_fuzzy(self, name: str, threshold: float = 0.85) -> Optional[Tuple[Dict, float]]:
        """
        Find player using fuzzy string matching
        
        Args:
            name: Player name to search
            threshold: Minimum similarity score (0-1)
        
        Returns:
            Tuple of (player_dict, similarity_score) or None
        """
        normalized = self.normalize_name(name)
        
        best_match = None
        best_score = 0.0
        
        for roster_name, player in self.name_to_player.items():
            # Calculate similarity using SequenceMatcher
            score = SequenceMatcher(None, normalized, roster_name).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = player
        
        if best_match:
            return (best_match, best_score)
        
        return None
    
    def find_player_by_last_name(self, name: str) -> List[Dict]:
        """
        Find players matching the last name
        Useful when only partial name is available
        """
        # Extract last name (assumes last word is last name)
        normalized = self.normalize_name(name)
        parts = normalized.split()
        if not parts:
            return []
        
        last_name = parts[-1]
        
        matches = []
        for player in self.players:
            player_last = self.normalize_name(player['lastName'])
            if last_name in player_last or player_last in last_name:
                matches.append(player)
        
        return matches
    
    def map_player(self, capwages_name: str, team_code: Optional[str] = None) -> Optional[Dict]:
        """
        Map a CapWages player name to NHL player ID
        
        Args:
            capwages_name: Player name from CapWages (e.g., "Sidney#87 Crosby")
            team_code: Optional team code to narrow down results
        
        Returns:
            Player dict with id, name, team, etc. or None
        """
        # Try exact match first
        player = self.find_player_exact(capwages_name)
        if player:
            logger.debug(f"Exact match: '{capwages_name}' -> {player['name']} (ID: {player['id']})")
            return player
        
        # Try fuzzy match
        fuzzy_result = self.find_player_fuzzy(capwages_name, threshold=0.85)
        if fuzzy_result:
            player, score = fuzzy_result
            logger.info(f"Fuzzy match ({score:.2f}): '{capwages_name}' -> {player['name']} (ID: {player['id']})")
            
            # If team code provided, verify it matches
            if team_code and player.get('currentTeam') != team_code:
                logger.warning(f"Team mismatch: found {player.get('currentTeam')}, expected {team_code}")
            
            return player
        
        # Try last name match with team filter
        if team_code:
            last_name_matches = self.find_player_by_last_name(capwages_name)
            team_matches = [p for p in last_name_matches if p.get('currentTeam') == team_code]
            
            if len(team_matches) == 1:
                player = team_matches[0]
                logger.info(f"Last name + team match: '{capwages_name}' -> {player['name']} (ID: {player['id']})")
                return player
        
        logger.warning(f"No match found for: '{capwages_name}' (team: {team_code})")
        return None
    
    def get_player_by_id(self, player_id: int) -> Optional[Dict]:
        """Get player by NHL player ID"""
        for player in self.players:
            if player['id'] == player_id:
                return player
        return None


# Global singleton instance
_mapper_instance = None


def get_player_mapper() -> PlayerMapper:
    """Get or create the global PlayerMapper instance"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = PlayerMapper()
    return _mapper_instance


def map_player_name_to_id(capwages_name: str, team_code: Optional[str] = None) -> Optional[int]:
    """
    Convenience function to map a CapWages player name to NHL player ID
    
    Args:
        capwages_name: Player name from CapWages (e.g., "Sidney#87 Crosby")
        team_code: Optional team code to narrow down results
    
    Returns:
        NHL player ID or None
    """
    mapper = get_player_mapper()
    player = mapper.map_player(capwages_name, team_code)
    return player['id'] if player else None


def get_player_info(capwages_name: str, team_code: Optional[str] = None) -> Optional[Dict]:
    """
    Get full player information from CapWages name
    
    Args:
        capwages_name: Player name from CapWages
        team_code: Optional team code to narrow down results
    
    Returns:
        Player dict with id, name, team, position, etc. or None
    """
    mapper = get_player_mapper()
    return mapper.map_player(capwages_name, team_code)

