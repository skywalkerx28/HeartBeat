"""
HeartBeat.bot Configuration
NHL teams, data sources, and bot settings
"""

import os
from typing import Dict, List

# NHL API Configuration
NHL_API_BASE_URL = "https://api-web.nhle.com"
REQUEST_DELAY = 0.5  # Delay between requests in seconds

# All 32 NHL Teams (2024-25 Season)
NHL_TEAMS = {
    # Atlantic Division
    'MTL': {'name': 'Montreal Canadiens', 'id': 8},
    'TOR': {'name': 'Toronto Maple Leafs', 'id': 10},
    'BOS': {'name': 'Boston Bruins', 'id': 6},
    'BUF': {'name': 'Buffalo Sabres', 'id': 7},
    'OTT': {'name': 'Ottawa Senators', 'id': 9},
    'DET': {'name': 'Detroit Red Wings', 'id': 17},
    'FLA': {'name': 'Florida Panthers', 'id': 13},
    'TBL': {'name': 'Tampa Bay Lightning', 'id': 14},
    
    # Metropolitan Division
    'NYR': {'name': 'New York Rangers', 'id': 3},
    'NYI': {'name': 'New York Islanders', 'id': 2},
    'PHI': {'name': 'Philadelphia Flyers', 'id': 4},
    'WSH': {'name': 'Washington Capitals', 'id': 15},
    'CAR': {'name': 'Carolina Hurricanes', 'id': 12},
    'NJD': {'name': 'New Jersey Devils', 'id': 1},
    'CBJ': {'name': 'Columbus Blue Jackets', 'id': 29},
    'PIT': {'name': 'Pittsburgh Penguins', 'id': 5},
    
    # Central Division
    'COL': {'name': 'Colorado Avalanche', 'id': 21},
    'DAL': {'name': 'Dallas Stars', 'id': 25},
    'MIN': {'name': 'Minnesota Wild', 'id': 30},
    'NSH': {'name': 'Nashville Predators', 'id': 18},
    'STL': {'name': 'St. Louis Blues', 'id': 19},
    'WPG': {'name': 'Winnipeg Jets', 'id': 52},
    'CHI': {'name': 'Chicago Blackhawks', 'id': 16},
    'UTA': {'name': 'Utah Hockey Club', 'id': 59},
    
    # Pacific Division
    'VGK': {'name': 'Vegas Golden Knights', 'id': 54},
    'SEA': {'name': 'Seattle Kraken', 'id': 55},
    'LAK': {'name': 'Los Angeles Kings', 'id': 26},
    'SJS': {'name': 'San Jose Sharks', 'id': 28},
    'ANA': {'name': 'Anaheim Ducks', 'id': 24},
    'VAN': {'name': 'Vancouver Canucks', 'id': 23},
    'CGY': {'name': 'Calgary Flames', 'id': 20},
    'EDM': {'name': 'Edmonton Oilers', 'id': 22},
}

# NHL API Endpoints
NHL_ENDPOINTS = {
    'schedule': '/v1/club-schedule-season/{team}/{season}',
    'scoreboard': '/v1/score/{date}',
    'game_summary': '/v1/gamecenter/{game_id}/landing',
    'player_stats': '/v1/player/{player_id}/landing',
    'standings': '/v1/standings/{date}',
}

# CapWages Team URL Slugs (for depth chart scraping)
CAPWAGES_TEAM_SLUGS = {
    'MTL': 'montreal_canadiens',
    'TOR': 'toronto_maple_leafs',
    'BOS': 'boston_bruins',
    'BUF': 'buffalo_sabres',
    'OTT': 'ottawa_senators',
    'DET': 'detroit_red_wings',
    'FLA': 'florida_panthers',
    'TBL': 'tampa_bay_lightning',
    'NYR': 'new_york_rangers',
    'NYI': 'new_york_islanders',
    'PHI': 'philadelphia_flyers',
    'WSH': 'washington_capitals',
    'CAR': 'carolina_hurricanes',
    'NJD': 'new_jersey_devils',
    'CBJ': 'columbus_blue_jackets',
    'PIT': 'pittsburgh_penguins',
    'COL': 'colorado_avalanche',
    'DAL': 'dallas_stars',
    'MIN': 'minnesota_wild',
    'NSH': 'nashville_predators',
    'STL': 'st_louis_blues',
    'WPG': 'winnipeg_jets',
    'CHI': 'chicago_blackhawks',
    'UTA': 'utah_mammoth',
    'VGK': 'vegas_golden_knights',
    'SEA': 'seattle_kraken',
    'LAK': 'los_angeles_kings',
    'SJS': 'san_jose_sharks',
    'ANA': 'anaheim_ducks',
    'VAN': 'vancouver_canucks',
    'CGY': 'calgary_flames',
    'EDM': 'edmonton_oilers',
}

# News Sources Configuration
# Each team can have multiple trusted sources
NEWS_SOURCES: Dict[str, List[Dict[str, str]]] = {
    'default': [
        {
            'name': 'NHL Official',
            'url_pattern': 'https://www.nhl.com/{team}/news',
            'type': 'official'
        },
        {
            'name': 'DailyFaceoff',
            'url': 'https://www.dailyfaceoff.com/news/',
            'type': 'aggregator'
        }
    ],
    # Team-specific sources can be added here
    'MTL': [
        {
            'name': 'NHL Canadiens',
            'url': 'https://www.nhl.com/canadiens/news',
            'type': 'official'
        }
    ],
}

# Bot Settings
# Use absolute path for database to avoid relative path issues
from pathlib import Path
_ROOT_DIR = Path(__file__).parent.parent.parent
_DEFAULT_DB_PATH = str(_ROOT_DIR / 'data' / 'heartbeat_news.sqlite')

BOT_CONFIG = {
    'db_path': os.getenv('HEARTBEAT_NEWS_DB_PATH', _DEFAULT_DB_PATH),
    'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'openrouter_model': os.getenv('HEARTBEAT_ARTICLE_MODEL', 'anthropic/claude-3.5-sonnet'),
    'article_generation_temp': 0.3,
    'article_max_tokens': 2048,
    'max_retries': 3,
    'retry_delay': 60,  # seconds
}


