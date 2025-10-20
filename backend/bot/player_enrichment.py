"""
Player data enrichment from unified roster historical data

Matches players from depth charts to unified roster to add:
- NHL Player ID
- Birth date
- Birth country
- Height
- Weight
- Shoots/Catches
- Headshot URL
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Global cache for unified roster data
_UNIFIED_ROSTER_CACHE = None


def load_unified_roster() -> Dict[str, dict]:
    """
    Load unified roster historical data and build lookup dictionary
    
    Returns:
        Dict mapping normalized player names to player data
    """
    global _UNIFIED_ROSTER_CACHE
    
    if _UNIFIED_ROSTER_CACHE is not None:
        return _UNIFIED_ROSTER_CACHE
    
    roster_file = Path(__file__).parent.parent.parent / 'data' / 'processed' / 'rosters' / 'unified_roster_historical.json'
    
    if not roster_file.exists():
        logger.error(f"Unified roster file not found: {roster_file}")
        return {}
    
    logger.info(f"Loading unified roster from: {roster_file}")
    
    with open(roster_file, 'r') as f:
        data = json.load(f)
    
    players = data.get('players', [])
    logger.info(f"Loaded {len(players)} players from unified roster")
    
    # Build lookup dictionary
    # Key = normalized name (lowercase, no special chars)
    # Value = player data
    lookup = {}
    
    for player in players:
        player_id = player.get('id')
        full_name = player.get('name', '')
        first_name = player.get('firstName', '')
        last_name = player.get('lastName', '')
        
        if not full_name or not player_id:
            continue
        
        # Normalize name for matching
        normalized = normalize_player_name(full_name)
        
        # Store player data with both full name and last,first format
        player_data = {
            'player_id': player_id,
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': player.get('birthDate'),
            'birth_country': player.get('birthCountry'),
            'height_inches': player.get('heightInInches'),
            'weight_pounds': player.get('weightInPounds'),
            'shoots_catches': player.get('shootsCatches'),
            'headshot': player.get('headshot'),
            'position': player.get('position'),
            'current_team': player.get('currentTeam'),
        }
        
        # Add to lookup with multiple key formats
        lookup[normalized] = player_data
        
        # Also add "Last, First" format (common in depth charts)
        if last_name and first_name:
            last_first = normalize_player_name(f"{last_name}, {first_name}")
            lookup[last_first] = player_data
            
            # Also try "First Last" format
            first_last = normalize_player_name(f"{first_name} {last_name}")
            lookup[first_last] = player_data
    
    _UNIFIED_ROSTER_CACHE = lookup
    logger.info(f"Built lookup dictionary with {len(lookup)} name variations")
    
    return lookup


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for matching
    - Lowercase
    - Remove special characters (dots, dashes, apostrophes)
    - Strip whitespace
    """
    if not name:
        return ''
    
    # Lowercase
    name = name.lower()
    
    # Remove common special characters
    name = name.replace('.', '')
    name = name.replace('-', ' ')
    name = name.replace("'", '')
    name = name.replace("\u2019", '')  # Smart quote (unicode)
    
    # Normalize whitespace
    name = ' '.join(name.split())
    
    return name


def find_player_match(player_name: str, lookup: Dict[str, dict], min_similarity: float = 0.85) -> Optional[dict]:
    """
    Find matching player in unified roster
    
    Uses exact match first, then fuzzy matching if needed
    
    Args:
        player_name: Name from depth chart (e.g., "Greer, A.J." or "A.J. Greer")
        lookup: Unified roster lookup dictionary
        min_similarity: Minimum similarity score for fuzzy matching (0.0-1.0)
    
    Returns:
        Player data dict or None
    """
    if not player_name:
        return None
    
    normalized = normalize_player_name(player_name)
    
    # Try exact match
    if normalized in lookup:
        return lookup[normalized]
    
    # Try fuzzy matching on last name
    # Extract last name from "Last, First" or "First Last" format
    name_parts = normalized.split(',')
    if len(name_parts) == 2:
        # "Last, First" format
        last_name = name_parts[0].strip()
    else:
        # "First Last" format - take last word
        words = normalized.split()
        if len(words) >= 2:
            last_name = words[-1]
        else:
            last_name = normalized
    
    # Find candidates with matching last name
    candidates = []
    for key, player_data in lookup.items():
        if last_name in key:
            similarity = SequenceMatcher(None, normalized, key).ratio()
            if similarity >= min_similarity:
                candidates.append((similarity, player_data))
    
    if candidates:
        # Return best match
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_match = candidates[0][1]
        logger.debug(f"Fuzzy match: '{player_name}' -> '{best_match['full_name']}' (similarity: {candidates[0][0]:.2f})")
        return best_match
    
    logger.warning(f"No match found for player: {player_name}")
    return None


def enrich_depth_chart_player(player_data: dict, unified_roster_lookup: Optional[Dict[str, dict]] = None) -> dict:
    """
    Enrich a single depth chart player with unified roster data
    
    Args:
        player_data: Player dict from depth chart scraper
        unified_roster_lookup: Pre-loaded lookup dict (will load if None)
    
    Returns:
        Enriched player data dict
    """
    if unified_roster_lookup is None:
        unified_roster_lookup = load_unified_roster()
    
    player_name = player_data.get('player_name')
    if not player_name:
        return player_data
    
    match = find_player_match(player_name, unified_roster_lookup)
    
    if match:
        # Add unified roster fields
        player_data['player_id'] = match['player_id']
        player_data['birth_date'] = match['birth_date']
        player_data['birth_country'] = match['birth_country']
        player_data['height_inches'] = match['height_inches']
        player_data['weight_pounds'] = match['weight_pounds']
        player_data['shoots_catches'] = match['shoots_catches']
        player_data['headshot'] = match['headshot']
        
        logger.debug(f"Enriched: {player_name} -> ID {match['player_id']}")
    else:
        logger.warning(f"Could not enrich player: {player_name}")
    
    return player_data


def enrich_depth_chart_players(players: List[dict]) -> List[dict]:
    """
    Enrich multiple depth chart players
    
    Args:
        players: List of player dicts from depth chart scraper
    
    Returns:
        List of enriched player dicts
    """
    lookup = load_unified_roster()
    
    enriched = []
    matched = 0
    
    for player in players:
        enriched_player = enrich_depth_chart_player(player, lookup)
        enriched.append(enriched_player)
        
        if enriched_player.get('player_id'):
            matched += 1
    
    logger.info(f"Enriched {matched}/{len(players)} players with unified roster data")
    
    return enriched

