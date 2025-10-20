"""
HeartBeat Engine - Identity Normalization
Canonical ID mapping and name normalization for hockey entities

Ensures consistent identity across all ontology objects and data sources.
"""

import re
import unicodedata
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# NHL Team Mappings
NHL_TEAM_CODES = {
    "ANA": {"full_name": "Anaheim Ducks", "aliases": ["Anaheim", "Ducks", "ANA"]},
    "BOS": {"full_name": "Boston Bruins", "aliases": ["Boston", "Bruins", "BOS"]},
    "BUF": {"full_name": "Buffalo Sabres", "aliases": ["Buffalo", "Sabres", "BUF"]},
    "CAR": {"full_name": "Carolina Hurricanes", "aliases": ["Carolina", "Hurricanes", "CAR", "Canes"]},
    "CBJ": {"full_name": "Columbus Blue Jackets", "aliases": ["Columbus", "Blue Jackets", "CBJ", "Jackets"]},
    "CGY": {"full_name": "Calgary Flames", "aliases": ["Calgary", "Flames", "CGY"]},
    "CHI": {"full_name": "Chicago Blackhawks", "aliases": ["Chicago", "Blackhawks", "CHI", "Hawks"]},
    "COL": {"full_name": "Colorado Avalanche", "aliases": ["Colorado", "Avalanche", "COL", "Avs"]},
    "DAL": {"full_name": "Dallas Stars", "aliases": ["Dallas", "Stars", "DAL"]},
    "DET": {"full_name": "Detroit Red Wings", "aliases": ["Detroit", "Red Wings", "DET", "Wings"]},
    "EDM": {"full_name": "Edmonton Oilers", "aliases": ["Edmonton", "Oilers", "EDM"]},
    "FLA": {"full_name": "Florida Panthers", "aliases": ["Florida", "Panthers", "FLA"]},
    "LAK": {"full_name": "Los Angeles Kings", "aliases": ["Los Angeles", "LA Kings", "Kings", "LAK", "LA"]},
    "MIN": {"full_name": "Minnesota Wild", "aliases": ["Minnesota", "Wild", "MIN"]},
    "MTL": {"full_name": "Montreal Canadiens", "aliases": ["Montreal", "Canadiens", "MTL", "Habs"]},
    "NJD": {"full_name": "New Jersey Devils", "aliases": ["New Jersey", "Devils", "NJD", "NJ"]},
    "NSH": {"full_name": "Nashville Predators", "aliases": ["Nashville", "Predators", "NSH", "Preds"]},
    "NYI": {"full_name": "New York Islanders", "aliases": ["NY Islanders", "Islanders", "NYI", "Isles"]},
    "NYR": {"full_name": "New York Rangers", "aliases": ["NY Rangers", "Rangers", "NYR"]},
    "OTT": {"full_name": "Ottawa Senators", "aliases": ["Ottawa", "Senators", "OTT", "Sens"]},
    "PHI": {"full_name": "Philadelphia Flyers", "aliases": ["Philadelphia", "Flyers", "PHI"]},
    "PIT": {"full_name": "Pittsburgh Penguins", "aliases": ["Pittsburgh", "Penguins", "PIT", "Pens"]},
    "SEA": {"full_name": "Seattle Kraken", "aliases": ["Seattle", "Kraken", "SEA"]},
    "SJS": {"full_name": "San Jose Sharks", "aliases": ["San Jose", "Sharks", "SJS", "SJ"]},
    "STL": {"full_name": "St. Louis Blues", "aliases": ["St Louis", "St. Louis", "Blues", "STL"]},
    "TBL": {"full_name": "Tampa Bay Lightning", "aliases": ["Tampa Bay", "Tampa", "Lightning", "TBL", "TB"]},
    "TOR": {"full_name": "Toronto Maple Leafs", "aliases": ["Toronto", "Maple Leafs", "TOR", "Leafs"]},
    "UTA": {"full_name": "Utah Hockey Club", "aliases": ["Utah", "UTA"]},
    "VAN": {"full_name": "Vancouver Canucks", "aliases": ["Vancouver", "Canucks", "VAN", "Nucks"]},
    "VGK": {"full_name": "Vegas Golden Knights", "aliases": ["Vegas", "Golden Knights", "VGK", "Knights"]},
    "WPG": {"full_name": "Winnipeg Jets", "aliases": ["Winnipeg", "Jets", "WPG"]},
    "WSH": {"full_name": "Washington Capitals", "aliases": ["Washington", "Capitals", "WSH", "Caps"]},
}


@dataclass
class NormalizedPlayer:
    """Normalized player identity."""
    nhl_player_id: Optional[int]
    full_name: str
    normalized_name: str
    first_name: str
    last_name: str


@dataclass
class NormalizedTeam:
    """Normalized team identity."""
    team_abbrev: str
    full_name: str
    short_name: str


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for consistent matching.
    
    - Lowercase
    - Remove diacritics (é -> e, ñ -> n)
    - Remove punctuation except hyphens and spaces
    - Collapse multiple spaces
    
    Examples:
        "Martin St. Louis" -> "martin st louis"
        "Mathieu Joseph" -> "mathieu joseph"
        "Pierre-Luc Dubois" -> "pierre-luc dubois"
    """
    
    # Convert to NFD (decomposed) form and remove combining marks
    nfd = unicodedata.normalize('NFD', name)
    without_diacritics = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Lowercase
    lower = without_diacritics.lower()
    
    # Remove punctuation except hyphens and spaces
    cleaned = re.sub(r'[^\w\s-]', '', lower)
    
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', cleaned).strip()
    
    return normalized


def parse_player_name(name: str) -> Tuple[str, str]:
    """
    Parse player name into first and last name.
    
    Handles:
    - "FirstName LastName"
    - "FirstName Middle LastName" -> "FirstName Middle", "LastName"
    - "LastName, FirstName" -> "FirstName", "LastName"
    
    Returns:
        (first_name, last_name)
    """
    
    name = name.strip()
    
    # Handle "LastName, FirstName" format
    if ',' in name:
        parts = name.split(',', 1)
        return parts[1].strip(), parts[0].strip()
    
    # Handle "FirstName LastName" format
    parts = name.split()
    if len(parts) == 1:
        return parts[0], parts[0]
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        # Multiple parts: treat last as last name, rest as first
        return ' '.join(parts[:-1]), parts[-1]


def normalize_team_abbrev(team_input: str) -> Optional[str]:
    """
    Normalize team input to official 3-letter abbreviation.
    
    Accepts:
    - 3-letter codes: "MTL", "TOR", "BOS"
    - Full names: "Montreal Canadiens", "Toronto Maple Leafs"
    - Short names: "Canadiens", "Leafs", "Habs"
    
    Returns:
        Official 3-letter code or None if not found
    """
    
    team_input_clean = team_input.strip().upper()
    
    # Direct match on 3-letter code
    if team_input_clean in NHL_TEAM_CODES:
        return team_input_clean
    
    # Match on full name or aliases
    team_input_lower = team_input.strip().lower()
    for code, info in NHL_TEAM_CODES.items():
        if team_input_lower == info['full_name'].lower():
            return code
        
        for alias in info['aliases']:
            if team_input_lower == alias.lower():
                return code
    
    logger.warning(f"Unknown team: {team_input}")
    return None


def get_team_full_name(team_abbrev: str) -> Optional[str]:
    """Get full team name from abbreviation."""
    info = NHL_TEAM_CODES.get(team_abbrev.upper())
    return info['full_name'] if info else None


def normalize_season_format(season_input: str) -> str:
    """
    Normalize season to YYYY-YYYY format.
    
    Accepts:
    - "2024-2025", "2024-25", "20242025", "2024"
    
    Returns:
        "YYYY-YYYY" format
    """
    
    season_input = season_input.strip()
    
    # Already in correct format
    if re.match(r'^\d{4}-\d{4}$', season_input):
        return season_input
    
    # Short format: 2024-25
    match = re.match(r'^(\d{4})-(\d{2})$', season_input)
    if match:
        start_year = match.group(1)
        end_year_short = match.group(2)
        end_year = start_year[:2] + end_year_short
        return f"{start_year}-{end_year}"
    
    # No separator: 20242025
    match = re.match(r'^(\d{4})(\d{4})$', season_input)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    # Single year: 2024 -> 2024-2025
    match = re.match(r'^(\d{4})$', season_input)
    if match:
        year = int(match.group(1))
        return f"{year}-{year + 1}"
    
    logger.warning(f"Could not normalize season: {season_input}")
    return season_input


def create_player_identity(
    player_name: str,
    nhl_player_id: Optional[int] = None
) -> NormalizedPlayer:
    """
    Create normalized player identity.
    
    Args:
        player_name: Player full name
        nhl_player_id: Optional NHL player ID
    
    Returns:
        NormalizedPlayer with all identity fields populated
    """
    
    first, last = parse_player_name(player_name)
    normalized = normalize_player_name(player_name)
    
    return NormalizedPlayer(
        nhl_player_id=nhl_player_id,
        full_name=player_name.strip(),
        normalized_name=normalized,
        first_name=first,
        last_name=last
    )


def create_team_identity(team_input: str) -> Optional[NormalizedTeam]:
    """
    Create normalized team identity.
    
    Args:
        team_input: Team name, abbreviation, or alias
    
    Returns:
        NormalizedTeam or None if team not found
    """
    
    team_abbrev = normalize_team_abbrev(team_input)
    if not team_abbrev:
        return None
    
    info = NHL_TEAM_CODES[team_abbrev]
    
    return NormalizedTeam(
        team_abbrev=team_abbrev,
        full_name=info['full_name'],
        short_name=info['aliases'][-1]  # Last alias is usually short name
    )


def validate_nhl_game_id(game_id: int) -> bool:
    """
    Validate NHL game ID format.
    
    Format: SSSSTTGGGG
    - SSSS: Season (2024 for 2024-25)
    - TT: Game type (01=preseason, 02=regular, 03=playoffs)
    - GGGG: Game number (0001-9999)
    
    Returns:
        True if valid format
    """
    
    game_id_str = str(game_id)
    
    if len(game_id_str) != 10:
        return False
    
    season_part = int(game_id_str[:4])
    type_part = int(game_id_str[4:6])
    game_num = int(game_id_str[6:])
    
    # Validate season (2000-2099)
    if season_part < 2000 or season_part > 2099:
        return False
    
    # Validate game type (01, 02, 03)
    if type_part not in [1, 2, 3]:
        return False
    
    # Validate game number
    if game_num < 1 or game_num > 9999:
        return False
    
    return True


def extract_season_from_game_id(game_id: int) -> str:
    """
    Extract season from NHL game ID.
    
    Example: 2024020001 -> "2024-2025"
    """
    
    game_id_str = str(game_id)
    if len(game_id_str) != 10:
        raise ValueError(f"Invalid game ID format: {game_id}")
    
    start_year = int(game_id_str[:4])
    return f"{start_year}-{start_year + 1}"


# Provenance tracking
@dataclass
class ProvenanceInfo:
    """Metadata for data provenance and lineage."""
    source_uri: str
    extraction_time: str  # ISO timestamp
    source_system: str  # "nhl_api", "capfriendly", "internal"
    model_version: Optional[str] = None
    feature_set_ref: Optional[str] = None
    transform_pipeline: Optional[str] = None


def create_provenance(
    source_uri: str,
    source_system: str = "internal",
    model_version: Optional[str] = None
) -> Dict[str, Any]:
    """Create provenance metadata dict for ontology objects."""
    
    from datetime import datetime
    
    return {
        "source_uri": source_uri,
        "extraction_time": datetime.utcnow().isoformat() + "Z",
        "source_system": source_system,
        "model_version": model_version,
        "feature_set_ref": None,
        "transform_pipeline": None
    }

