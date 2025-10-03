"""
HeartBeat Line Matchup Data Processor
Extracts deployment events and matchup data from play-by-play sequences
Professionnal NHL analytics
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sklearn.linear_model import BayesianRidge
from sklearn.preprocessing import StandardScaler

# Configure logging for professional deployment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import performance diagnostics for memory monitoring
try:
    from performance_diagnostics import MemoryProfiler, PatternStructureDiagnostics
    DIAGNOSTICS_AVAILABLE = True
except ImportError:
    DIAGNOSTICS_AVAILABLE = False
    logger.warning("Performance diagnostics not available - continuing without memory monitoring")

# MEMORY MANAGEMENT: Configuration for rest pattern storage
MAX_REST_PATTERNS_PER_CONTEXT = 100  # Cap per player/situation/team context
EWMA_ALPHA = 0.3  # Exponential weighted moving average decay factor

# PLAYER-VS-PLAYER MATCHUP: Memory and recency management
MAX_MATCHUPS_PER_PLAYER = 50  # Cap matchup history per player
MATCHUP_EWMA_ALPHA = 0.2  # Recency weighting for player matchups
MIN_MATCHUP_FREQUENCY = 3  # Minimum occurrences to keep a matchup
TOP_N_MATCHUPS_PER_PLAYER = 25  # Keep only top N most frequent matchups per player

@dataclass
class DeploymentEvent:
    """Represents a single deployment event with full context"""
    # Required fields (no defaults)
    game_id: str
    event_id: int
    period: int
    period_time: float
    game_time: float
    zone_start: str  # OZ, DZ, NZ
    strength_state: str  # 5v5, 5v4, 4v5, etc.
    score_differential: int
    time_bucket: str  # early, middle, late
    stoppage_type: str  # faceoff, icing, offside, penalty, goal
    home_team: str
    away_team: str
    last_change_team: str
    opponent_team: str = ""  # TEAM-AWARE: Track which team MTL is facing
    season: str = "unknown"  # Season (e.g., "2023-2024") extracted from filename
    
    # Optional fields with defaults
    game_seconds: float = 0.0  # Total game seconds elapsed: (period-1)*1200 + period_time
    game_bucket: str = "early"  # early/middle/late based on total game time
    decision_role: int = 0  # 1 if MTL decides (has last change), 0 if opponent decides
    
    # Phase flags for high-leverage situations
    is_period_late: bool = False  # True if period_time >= 17:00 (1020s)
    is_game_late: bool = False    # True if game_seconds >= 55:00 (3300s)
    is_late_pk: bool = False      # True if PK situation + late period
    is_late_pp: bool = False      # True if PP situation + late period
    is_close_and_late: bool = False  # True if close game (±1 goal) + late game
    
    # On-ice players (IDs)
    mtl_forwards: List[str] = field(default_factory=list)
    mtl_defense: List[str] = field(default_factory=list)
    mtl_goalie: str = ""
    
    opp_forwards: List[str] = field(default_factory=list)
    opp_defense: List[str] = field(default_factory=list)
    opp_goalie: str = ""
    
    # Fatigue/rest metrics
    mtl_time_since_last: Dict[str, float] = field(default_factory=dict)
    opp_time_since_last: Dict[str, float] = field(default_factory=dict)
    # Dual rest tracking per player
    mtl_rest_real: Dict[str, float] = field(default_factory=dict)  # timecode-based real elapsed rest
    mtl_rest_game: Dict[str, float] = field(default_factory=dict)  # game-clock rest
    opp_rest_real: Dict[str, float] = field(default_factory=dict)
    opp_rest_game: Dict[str, float] = field(default_factory=dict)
    
    # Previous deployment info
    prev_mtl_forwards: List[str] = field(default_factory=list)
    prev_opp_forwards: List[str] = field(default_factory=list)


class PlayByPlayProcessor:
    """Processes play-by-play data to extract matchup information with predictive chain tracking"""
    
    def __init__(self, data_path: Path, player_mapping_path: Path):
        self.data_path = Path(data_path)
        self.player_mapping_path = Path(player_mapping_path)
        self.player_map = self._load_player_mapping()
        
        # Create player ID → team mapping for correct roster assignment
        self.player_team_map = {}
        if not self.player_map.empty and 'Current Team' in self.player_map.columns:
            for _, row in self.player_map.iterrows():
                player_id = str(row.get('reference_id', ''))
                team = str(row.get('Current Team', '')).strip()
                if player_id and team:
                    self.player_team_map[player_id] = team
            logger.info(f"✓ Pre-loaded team assignments for {len(self.player_team_map)} players")
        
        self.deployment_events = []
        self.matchup_matrix = {}  # player_id -> {opponent_id -> time_together}
        
        # Initialize exact TOI tracking attributes
        self.player_exact_toi = {}
        self.player_shift_sequences = {}
        
        # TEAM-AWARE: Advanced temporal pattern tracking for ALL players per opponent team
        self.player_rest_patterns = defaultdict(lambda: defaultdict(list))  # Legacy: global patterns
        self.team_player_rest_patterns = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # NEW: [opponent_team][player][situation] = [rest_times]
        self.player_return_intervals = defaultdict(list)
        self.line_rotation_chains = []
        self.situation_specific_rest = defaultdict(lambda: defaultdict(list))
        
        # CRITICAL: Track opponent-specific patterns across multiple games
        self.opponent_specific_matchups = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # Format: [opponent_team][our_player][their_player] = total_time_on_ice
        
        # PLAYER-VS-PLAYER: Direct matchup frequency tracking with EWMA weighting
        # Global matchup counts (all situations) - now using weighted counts
        self.player_matchup_counts = defaultdict(float)
        # Format: (mtl_player, opponent_player) -> weighted_count
        
        # Last-change-aware matchup counts with recency weighting
        self.last_change_player_matchups = defaultdict(float)
        # Format: (mtl_player, opponent_player, last_change_team, team_making_change) -> weighted_count
        
        # Situation-specific player matchups with EWMA
        self.situation_player_matchups = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # Format: (mtl_player, opponent_player, situation) -> weighted_count
        
        # Track game timestamps for recency weighting
        self.matchup_timestamps = defaultdict(list)  # matchup_key -> [timestamps]
        
        # Track game-by-game progression against same opponent with recency weighting
        self.game_sequence_vs_opponent = defaultdict(list)
        # Format: [opponent_team] = [(game_id, date, matchup_data), ...]
        
        # NEW: Recency weighting parameters for exponential decay
        self.recency_decay_lambda = 0.05  # λ for w_i = exp(-λ * days_ago)
        self.game_dates = {}  # game_id -> date for recency calculation
        
        # Track EVERY player that appears in ANY CSV
        self.all_players_tracked = set()
        self.player_team_mapping = {}  # player_id -> team
        
        # Player experience tracking for hierarchical priors
        self.player_nhl_games = defaultdict(int)
        self.rookie_threshold = 10
        
        # Bayesian regression for context-aware rest modeling
        from sklearn.linear_model import HuberRegressor
        self.bayesian_rest_model = HuberRegressor(
            epsilon=1.35,  # Huber parameter for outlier robustness
            max_iter=200,
            alpha=0.001,   # L2 regularization
            fit_intercept=True
        )
        self.rest_context_scaler = StandardScaler()
        self.rest_training_data = []  # Store for Bayesian model training
        
        # Pre-seed NHL experience and team mapping from CSV after all attributes are initialized
        self._preseed_player_data()
        
        # PERFORMANCE: Initialize diagnostics for memory monitoring
        if DIAGNOSTICS_AVAILABLE:
            self.memory_profiler = MemoryProfiler()
            self.pattern_diagnostics = PatternStructureDiagnostics()
            self.memory_profiler.take_snapshot("DataProcessor Initialized")
            logger.info("Performance diagnostics enabled for DataProcessor")
        else:
            self.memory_profiler = None
            self.pattern_diagnostics = None
    
    def _add_rest_pattern_with_recency(self, pattern_dict: Dict, team_key: str, 
                                      player_id: str, situation: str, rest_value: float):
        """
        Add rest pattern with capping and recency weighting to prevent memory bloat
        
        Args:
            pattern_dict: The team_player_rest_patterns dictionary
            team_key: Team context key (e.g., 'MTL_vs_TOR', 'MTL_general')
            player_id: Player identifier
            situation: Game situation (e.g., '5v5', '5v4')
            rest_value: Rest time in seconds
        """
        # Get or create the pattern list for this context
        pattern_list = pattern_dict[team_key][player_id][situation]
        
        # Add new value
        pattern_list.append(rest_value)
        
        # Apply capping and recency weighting if needed
        if len(pattern_list) > MAX_REST_PATTERNS_PER_CONTEXT:
            # EWMA-weighted trimming: Keep recent values with higher weight
            # Convert to numpy for efficient computation
            values = np.array(pattern_list)
            
            # Create recency weights (more recent = higher weight)
            n = len(values)
            weights = np.array([EWMA_ALPHA * (1 - EWMA_ALPHA) ** (n - 1 - i) for i in range(n)])
            weights = weights / weights.sum()  # Normalize
            
            # Select top weighted values to keep
            weighted_indices = np.argsort(weights)[-MAX_REST_PATTERNS_PER_CONTEXT:]
            pattern_dict[team_key][player_id][situation] = [pattern_list[i] for i in sorted(weighted_indices)]

    def _compute_mtl_score_diff(self, row: pd.Series, home_team: str, away_team: str) -> int:
        """Compute score differential from MTL perspective for any row.
        Rules:
        - Prefer CSV provided score differential (scoreDifferential/scoreDiff) and orient to MTL:
          if action team is Montreal → keep sign; else → invert sign.
        - Fallback: if home/away scores exist, compute mtl_score - opp_score based on home/away labels.
        - Else return 0.
        """
        raw = None
        if 'scoreDifferential' in row and pd.notna(row['scoreDifferential']):
            raw = row['scoreDifferential']
        elif 'scoreDiff' in row and pd.notna(row['scoreDiff']):
            raw = row['scoreDiff']

        # Determine action team name if available
        action_team = str(row.get('team', row.get('teamName', '')))

        if raw is not None and raw != "":
            try:
                raw_int = int(raw)
            except Exception:
                # Some feeds store as float-like strings
                try:
                    raw_int = int(float(raw))
                except Exception:
                    raw_int = 0

            if 'Montreal' in action_team:
                return raw_int
            else:
                return -raw_int

        # Fallback by reconstructing from scores if present
        home_score = row.get('homeScore')
        away_score = row.get('awayScore')
        if pd.notna(home_score) and pd.notna(away_score):
            try:
                home_score = int(home_score)
                away_score = int(away_score)
                mtl_is_home = 'MTL' in home_team or 'Montreal' in home_team
                mtl_score = home_score if mtl_is_home else away_score
                opp_score = away_score if mtl_is_home else home_score
                return int(mtl_score - opp_score)
            except Exception:
                return 0

        return 0
        
    def _load_player_mapping(self) -> pd.DataFrame:
        """Load player ID to name mapping from CSV file"""
        try:
            players = pd.read_csv(self.player_mapping_path)
            logger.info(f"✓ Loaded {len(players)} player mappings from {self.player_mapping_path}")
            return players
        except Exception as e:
            logger.warning(f"Could not load player mappings from {self.player_mapping_path}: {e}")
            return pd.DataFrame()
    
    def parse_on_ice_refs(self, refs_str: str) -> List[str]:
        """Parse tab-separated player IDs from on-ice reference string"""
        if pd.isna(refs_str) or refs_str == "":
            return []
        # Clean and split by tabs or commas
        refs = str(refs_str).strip()
        if '\t' in refs:
            return [ref.strip() for ref in refs.split('\t') if ref.strip()]
        elif ',' in refs:
            return [ref.strip() for ref in refs.split(',') if ref.strip()]
        return []
    
    def determine_home_away(self, filename: str) -> Tuple[str, str]:
        """Extract home and away teams from filename pattern"""
        # Pattern: TORvsMTL means TOR is visiting MTL, so MTL is home (has last change)
        # Pattern: MTLvsBOS means MTL is visiting BOS, so BOS is home (has last change)
        import re
        match = re.search(r'-([A-Z]{3})vs([A-Z]{3})-', filename)
        if match:
            away = match.group(1)  # First team is visiting
            home = match.group(2)  # Second team is home
            return home, away
        return "", ""
    
    def extract_season(self, filename: str) -> str:
        """
        Extract season from filename
        Pattern: playsequence-YYYYMMDD-NHL-TEAMvsTEAM-SEASON-game.csv
        Example: playsequence-20240113-NHL-EDMvsMTL-20232024-20660.csv -> "2023-2024"
        """
        try:
            parts = filename.split('-')
            if len(parts) >= 6:
                season_raw = parts[4]  # e.g., "20232024"
                if len(season_raw) == 8 and season_raw.isdigit():
                    # Format as "2023-2024"
                    return f"{season_raw[:4]}-{season_raw[4:]}"
        except Exception as e:
            logger.warning(f"Could not extract season from {filename}: {e}")
        return "unknown"
    
    def extract_game_date(self, filename: str) -> datetime:
        """Extract game date from filename for recency weighting"""
        # Pattern: playsequence-YYYYMMDD-NHL-TEAMvsTEAM-season-game.csv
        import re
        match = re.search(r'-(\d{8})-', filename)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                pass
        
        # Fallback: use current date
        return datetime.now()
    
    def _preseed_player_data(self) -> None:
        """Pre-seed NHL experience and team data from CSV to avoid training bias"""
        
        if self.player_map.empty:
            return
        
        # Pre-seed NHL experience from CSV
        if 'Experience' in self.player_map.columns:
            experience_loaded = 0
            for _, row in self.player_map.iterrows():
                pid = str(row['reference_id'])
                experience = int(row['Experience']) if pd.notna(row['Experience']) else 0
                self.player_nhl_games[pid] = experience
                experience_loaded += 1
            
            logger.info(f"✓ Pre-seeded NHL experience for {experience_loaded} players")
            if experience_loaded > 0:
                logger.info(f"  Range: {min(self.player_nhl_games.values())} - {max(self.player_nhl_games.values())} games")
        
        # Pre-load current team mapping
        if 'Current Team' in self.player_map.columns:
            teams_loaded = 0
            for _, row in self.player_map.iterrows():
                pid = str(row['reference_id'])
                team = str(row['Current Team']) if pd.notna(row['Current Team']) else 'Unknown'
                self.player_team_mapping[pid] = team
                teams_loaded += 1
            
            logger.info(f"✓ Pre-loaded team assignments for {teams_loaded} players")
    
    def calculate_recency_weight(self, game_date: datetime, reference_date: Optional[datetime] = None) -> float:
        """Calculate recency weight using exponential decay"""
        if reference_date is None:
            reference_date = datetime.now()
        
        days_ago = (reference_date - game_date).days
        # Exponential decay: w_i = exp(-λ * Δd_i)
        weight = np.exp(-self.recency_decay_lambda * max(0, days_ago))
        return weight
    
    def get_time_bucket(self, period: int, period_time: float) -> str:
        """Categorize time into early/middle/late buckets"""
        minutes = period_time / 60.0
        if minutes < 7:
            return "early"
        elif minutes < 14:
            return "middle"
        else:
            return "late"
    
    def get_game_bucket(self, game_seconds: float) -> str:
        """Categorize total game time into early/middle/late buckets"""
        if game_seconds < 1200:  # First period (0-20 min)
            return "early"
        elif game_seconds < 3000:  # First 50 minutes (P1 + most of P2)
            return "middle"
        else:  # Late in P2, P3, OT
            return "late"
    
    def _parse_timecode_to_seconds(self, timecode: str) -> float:
        """Convert timecode HH:MM:SS:FF to seconds"""
        if pd.isna(timecode) or not timecode:
            return 0.0
        try:
            # Format is typically HH:MM:SS:FF (frames)
            parts = str(timecode).split(':')
            if len(parts) >= 3:
                hours = int(parts[0])
                minutes = int(parts[1]) 
                seconds = int(parts[2])
                frames = int(parts[3]) if len(parts) > 3 else 0
                return hours * 3600 + minutes * 60 + seconds + frames / 30.0  # Assume 30fps
            return 0.0
        except:
            return 0.0
    
    def _build_shift_tracking(self, df: pd.DataFrame, 
                             player_shift_starts: Dict, 
                             player_shift_lengths: Dict,
                             player_rest_starts: Dict,
                             last_change_team: str,
                             last_rest_real_by_player: Dict,
                             last_rest_game_by_player: Dict):
        """Build exact time-on-ice computation from sequential player appearances"""
        
        prev_on_ice = {'team': set(), 'opposing': set()}
        player_last_situation = {}  # Track what situation player was in
        line_deployment_sequence = []  # Track full deployment sequence
        
        # CRITICAL: Exact TOI computation data structures
        player_exact_toi = defaultdict(float)  # Total exact time on ice per player
        player_shift_sequences = defaultdict(list)  # Complete shift history per player
        player_appearance_start = {}  # When player started current appearance sequence
        
        # STOPPAGE TRACKING: Track stoppage events and durations
        last_whistle_time = None  # Track last whistle/stoppage
        last_stoppage_type = 'unknown'  # Type of last stoppage
        current_stoppage_duration = 0.0  # Duration of current stoppage
        
        for idx, row in df.iterrows():
            # CRITICAL: Use correct time columns for mathematical precision
            current_timecode = self._parse_timecode_to_seconds(row.get('timecode', ''))  # Real elapsed time
            period_time = float(row.get('periodTime', 0))  # Game clock (0-1200)
            game_time = float(row.get('gameTime', 0))  # Total action time
            period = int(row.get('period', 1))
            
            # Get previous row for exact time computation
            prev_game_time = 0.0
            prev_period_time = 0.0
            prev_timecode = 0.0
            
            if idx > 0:
                prev_row = df.iloc[idx - 1]
                prev_game_time = float(prev_row.get('gameTime', 0))
                prev_period_time = float(prev_row.get('periodTime', 0))
                prev_timecode = self._parse_timecode_to_seconds(prev_row.get('timecode', ''))

            # Accumulate real-time rest for all players currently resting
            # Uses timecode delta to capture stoppages and real elapsed time
            delta_timecode = current_timecode - prev_timecode
            if delta_timecode < 0 or delta_timecode > 3600:
                delta_timecode = 0.0  # Guard against period resets or anomalies
            if delta_timecode > 0:
                for pid in list(player_rest_starts.keys()):
                    rd = player_rest_starts.get(pid)
                    if isinstance(rd, dict):
                        rd['real_accum'] = rd.get('real_accum', 0.0) + delta_timecode
                    else:
                        # Backward-compat: convert scalar start to dict and start accumulating
                        player_rest_starts[pid] = {
                            'timecode_off': float(rd) if rd is not None else current_timecode,
                            'period_time_off': prev_period_time,
                            'game_time_off': prev_game_time,
                            'period_off': period,
                            'real_accum': delta_timecode
                        }
            
            # STOPPAGE DETECTION: Track whistles, penalties, icing, etc.
            event_type = row.get('type', '').lower()
            event_name = row.get('name', '').lower()
            
            # Detect stoppage events
            is_stoppage_event = False
            stoppage_type = 'play'  # Default to continuous play
            
            if event_type in ['none'] and 'whistle' in event_name:
                is_stoppage_event = True
                stoppage_type = 'whistle'
            elif event_type == 'icing' or 'icing' in event_name:
                is_stoppage_event = True
                stoppage_type = 'icing'
            elif event_type in ['penalty', 'penaltydrawn'] or 'penalty' in event_name:
                is_stoppage_event = True
                stoppage_type = 'penalty'
            elif 'timeout' in event_name or 'timeout' in event_type:
                is_stoppage_event = True
                stoppage_type = 'timeout'
            elif event_type == 'faceoff' or 'faceoff' in event_name:
                is_stoppage_event = True
                stoppage_type = 'faceoff'
            
            # Calculate stoppage duration if this is a resumption of play
            if last_whistle_time is not None and not is_stoppage_event:
                # Play has resumed - calculate stoppage duration
                current_stoppage_duration = current_timecode - last_whistle_time
                current_stoppage_duration = max(0.0, min(current_stoppage_duration, 300.0))  # Cap at 5 minutes
            
            # Update stoppage tracking
            if is_stoppage_event:
                last_whistle_time = current_timecode
                last_stoppage_type = stoppage_type
                current_stoppage_duration = 0.0  # Reset during stoppage
            
            # Get current on-ice players for both teams
            team_forwards = self.parse_on_ice_refs(row.get('teamForwardsOnIceRefs', ''))
            team_defense = self.parse_on_ice_refs(row.get('teamDefencemenOnIceRefs', ''))
            opp_forwards = self.parse_on_ice_refs(row.get('opposingTeamForwardsOnIceRefs', ''))
            opp_defense = self.parse_on_ice_refs(row.get('opposingTeamDefencemenOnIceRefs', ''))
            
            current_on_ice = {
                'team': set(team_forwards + team_defense),
                'opposing': set(opp_forwards + opp_defense)
            }
            
            # MATHEMATICAL PRECISION: Exact TOI computation from sequential appearances
            all_current_players = set(team_forwards + team_defense + opp_forwards + opp_defense)
            
            # Calculate exact time elapsed since previous event
            if idx > 0:
                # Use game_time for action time (accumulates to 3600s per game)
                time_elapsed = game_time - prev_game_time
                
                # Handle period boundaries in game_time calculation
                if time_elapsed < 0:  # Period boundary crossed
                    time_elapsed = 0.0  # Skip invalid transitions
                elif time_elapsed > 300:  # Sanity check (>5 min is likely period break)
                    time_elapsed = 0.0  # Skip period breaks
                
                # Add time to ALL players who were on ice during this interval
                for player in prev_on_ice['team'].union(prev_on_ice['opposing']):
                    if player and time_elapsed > 0:
                        player_exact_toi[player] += time_elapsed
                        
                        # Track if player was continuously on ice
                        if player in player_appearance_start:
                            # Player continues on ice - accumulate time
                            pass
                        else:
                            # Player started appearing - mark start
                            player_appearance_start[player] = prev_game_time
            
            # Track players starting/ending appearances
            all_prev_players = prev_on_ice['team'].union(prev_on_ice['opposing'])
            
            # Players ending their shift (no longer on ice)
            players_ending_shift = all_prev_players - all_current_players
            for player in players_ending_shift:
                if player in player_appearance_start:
                    # Calculate exact shift length
                    shift_start_time = player_appearance_start[player]
                    shift_length = game_time - shift_start_time
                    
                    if shift_length > 0 and shift_length < 300:  # Valid shift
                        player_shift_sequences[player].append({
                            'start_game_time': shift_start_time,
                            'end_game_time': game_time,
                            'shift_length': shift_length,
                            'period': period,
                            'situation': row.get('strengthState', '5v5'),
                            'score_diff': row.get('scoreDiff', 0),
                            'start_period_time': player_appearance_start.get(f"{player}_period_time", prev_period_time),
                            'end_period_time': period_time
                        })
                        
                        # Store in legacy format for compatibility
                        if player not in player_shift_lengths:
                            player_shift_lengths[player] = []
                        player_shift_lengths[player].append(shift_length)
                    
                    # Remove from tracking
                    del player_appearance_start[player]
                    if f"{player}_period_time" in player_appearance_start:
                        del player_appearance_start[f"{player}_period_time"]
                
                # Track rest start with enhanced data for Bayesian modeling
                player_rest_starts[player] = {
                    'timecode_off': current_timecode,
                    'period_time_off': period_time,
                    'game_time_off': game_time,
                    'period_off': period,
                    'situation_when_left': row.get('strengthState', '5v5'),
                    'zone_when_left': row.get('zone', 'nz'),
                    'score_when_left': row.get('scoreDiff', 0),
                    'home_team': self.current_opponent if hasattr(self, 'current_opponent') else '',
                    'has_last_change': last_change_team == 'MTL',
                    'real_accum': 0.0
                }
            
            # Players starting their shift (newly on ice)
            players_starting_shift = all_current_players - all_prev_players
            for player in players_starting_shift:
                if player:
                    # Mark appearance start
                    player_appearance_start[player] = game_time
                    player_appearance_start[f"{player}_period_time"] = period_time
                    
                    # Calculate rest time if they were previously off
                    if player in player_rest_starts:
                        rest_data = player_rest_starts[player]
                        real_rest_time = rest_data.get('real_accum', current_timecode - rest_data['timecode_off'])
                        
                        # Store detailed rest pattern
                        rest_record = {
                            'real_rest_seconds': real_rest_time,
                            'game_clock_rest': period_time - rest_data['period_time_off'],
                            'situation_returned_to': row.get('strengthState', '5v5'),
                            'period': period,
                            'score_state': int(row.get('scoreDiff', 0)) if pd.notna(row.get('scoreDiff', np.nan)) else 0,
                            'zone_returned_to': row.get('zone', 'nz')
                        }
                        self.player_rest_patterns[player][rest_data['situation_when_left']].append(rest_record)
                        
                        # ENHANCED FATIGUE MODELING: Dual rest calculation (real-time + game-time)
                        # Calculate both rest signals for comprehensive fatigue modeling
                        
                        # Within-period rest calculations
                        if rest_data.get('period_off', period) == period:
                            # Same period - calculate both rest signals
                            rest_real_s = rest_data.get('real_accum', current_timecode - rest_data['timecode_off'])
                            rest_game_s = period_time - rest_data['period_time_off']    # Game clock time
                            intermission_flag = 0
                            intermission_real_s = 0.0
                            
                            # Validate within-period rest calculations
                            if rest_real_s < 0 or rest_game_s < 0:
                                continue  # Skip invalid negative rest
                        else:
                            # Across periods - handle intermission
                            rest_real_s = 0.0  # Don't carry timecode across period resets
                            rest_game_s = period_time  # New period game time
                            intermission_flag = 1
                            intermission_real_s = 1080.0  # Standard NHL intermission: 18 minutes
                            
                        # Persist computed rest values for event building
                        last_rest_real_by_player[player] = rest_real_s
                        last_rest_game_by_player[player] = rest_game_s
                        
                        # Skip if no meaningful rest occurred
                        if rest_real_s == 0 and rest_game_s == 0 and intermission_flag == 0:
                            continue
                        
                        # ENHANCED PREDICTORS: Comprehensive fatigue and context features
                        last_shift_length = game_time - rest_data['game_time_off'] if 'game_time_off' in rest_data else 45.0
                        
                        # Shift counting
                        player_shifts = player_shift_sequences.get(player, [])
                        shift_count_this_period = len([s for s in player_shifts if s.get('period') == period])
                        shift_count_game = len(player_shifts)
                        
                        # Time-on-ice tracking
                        toi_past_5min = sum(s.get('shift_length', 0) for s in player_shifts
                                           if s.get('end_game_time', 0) > game_time - 300)  # Past 5 minutes
                        
                        # Rolling 20-minute TOI window 
                        toi_past_20min = sum(s.get('shift_length', 0) for s in player_shifts
                                            if s.get('end_game_time', 0) > game_time - 1200)  # Past 20 minutes
                        
                        # Cumulative game TOI
                        cumulative_toi_game = sum(s.get('shift_length', 0) for s in player_shifts)
                        
                        # EWMA calculations for shift patterns
                        recent_shift_lengths = [s.get('shift_length', 45) for s in player_shifts[-5:]]  # Last 5 shifts
                        recent_rest_lengths = []
                        
                        # Calculate rest lengths from shift sequence
                        for i in range(1, len(player_shifts)):
                            if player_shifts[i].get('period') == player_shifts[i-1].get('period'):
                                rest_between = player_shifts[i].get('start_game_time', 0) - player_shifts[i-1].get('end_game_time', 0)
                                if 0 < rest_between < 600:  # Valid rest (up to 10 minutes)
                                    recent_rest_lengths.append(rest_between)
                        
                        # EWMA with decay factor of 0.3
                        ewma_shift_length = 45.0
                        ewma_rest_length = 90.0
                        
                        if recent_shift_lengths:
                            weights = np.array([0.3 ** i for i in range(len(recent_shift_lengths))])
                            weights = weights / weights.sum()
                            ewma_shift_length = np.average(recent_shift_lengths, weights=weights)
                            
                        if recent_rest_lengths:
                            weights = np.array([0.3 ** i for i in range(len(recent_rest_lengths[-5:]))])
                            weights = weights / weights.sum()
                            ewma_rest_length = np.average(recent_rest_lengths[-5:], weights=weights)
                        
                        # CONTEXT FEATURES: Game situation and environment
                        # Period and timing context
                        period_index = period
                        time_remaining_in_period = max(0.0, 1200.0 - period_time)  # Seconds remaining in period
                        
                        # Game state context
                        score_diff = row.get('scoreDiff', 0)
                        home_away_flag = 1.0 if rest_data.get('home_team') == 'MTL' else 0.0
                        strength_state = row.get('strengthState', '5v5')
                        
                        # Last change and faceoff context
                        last_change_control = 1.0 if rest_data.get('has_last_change', False) else 0.0
                        upcoming_faceoff_zone = row.get('zone', 'nz')
                        
                        # STOPPAGE CONTEXT: Real stoppage data extracted from CSV
                        # Use actual tracked stoppage information
                        stoppage_type_numeric = {
                            'play': 0.0, 'whistle': 1.0, 'faceoff': 2.0, 'penalty': 3.0, 
                            'icing': 4.0, 'timeout': 5.0, 'unknown': 0.5
                        }.get(last_stoppage_type, 0.0)
                        
                        actual_stoppage_duration = current_stoppage_duration
                        
                        # Encoded zone and strength features
                        zone_left_numeric = {'oz': 1.0, 'nz': 0.0, 'dz': -1.0}.get(rest_data.get('zone_when_left', 'nz'), 0.0)
                        strength_left_numeric = {
                            '5v5': 0.0, '5v4': 1.0, '4v5': -1.0, '4v4': 0.5, '3v3': 1.5
                        }.get(rest_data.get('situation_when_left', '5v5'), 0.0)
                        
                        # Zone when returned
                        zone_returned_numeric = {'oz': 1.0, 'nz': 0.0, 'dz': -1.0}.get(upcoming_faceoff_zone, 0.0)
                        strength_returned_numeric = {
                            '5v5': 0.0, '5v4': 1.0, '4v5': -1.0, '4v4': 0.5, '3v3': 1.5
                        }.get(strength_state, 0.0)
                        
                        # Calculate previous shifts mean (last 2 shifts for compatibility)
                        recent_shifts = [s.get('shift_length', 45) for s in player_shifts[-2:]]
                        prev_2_shifts_mean = np.mean(recent_shifts) if recent_shifts else 45.0
                        
                        # COMPREHENSIVE CONTEXT FEATURES: Enhanced fatigue and game situation modeling
                        # ROBUST NORMALIZATION: Clamp outliers before normalization to prevent extreme values
                        context_features = [
                            # Period and timing (4 features)
                            min(period_index / 3.0, 2.0),                          # Normalized period (capped at 2.0)
                            min(period_time / 1200.0, 2.0),                        # Normalized time in period (capped)
                            min(time_remaining_in_period / 1200.0, 2.0),           # Normalized time remaining (capped)
                            1.0 if period == 3 and period_time > 1000 else 0.0,    # Late game flag
                            
                            # Game state context (5 features)
                            max(-2.0, min(score_diff / 5.0, 2.0)),                 # Normalized score difference (capped ±2.0)
                            1.0 if abs(score_diff) <= 1 else 0.0,                  # Close game flag
                            home_away_flag,                                         # Home/away (1/0)
                            max(-2.0, min(strength_left_numeric, 2.0)),             # Strength when left ice (capped)
                            max(-2.0, min(strength_returned_numeric, 2.0)),         # Strength when returning (capped)
                            
                            # Zone and positioning (2 features)
                            max(-2.0, min(zone_left_numeric, 2.0)),                 # Zone when left ice (capped)
                            max(-2.0, min(zone_returned_numeric, 2.0)),             # Zone when returning (capped)
                            
                            # Shift patterns and fatigue (8 features) - ROBUST CAPPING
                            max(0.1, min(last_shift_length / 90.0, 3.0)),           # Last shift length (capped 0.1-3.0)
                            max(0.1, min(prev_2_shifts_mean / 60.0, 3.0)),          # Previous 2 shifts average (capped)
                            max(0.1, min(ewma_shift_length / 90.0, 3.0)),           # EWMA shift length (capped)
                            max(0.1, min(ewma_rest_length / 120.0, 5.0)),           # EWMA rest length (capped)
                            min(shift_count_this_period / 20.0, 2.0),               # Shifts this period (capped)
                            min(shift_count_game / 30.0, 2.0),                      # Total shifts in game (capped)
                            min(toi_past_5min / 300.0, 2.0),                        # TOI past 5min (capped)
                            min(toi_past_20min / 1200.0, 2.0),                      # TOI past 20min (capped)
                            
                            # Cumulative load (2 features)
                            min(cumulative_toi_game / 1800.0, 2.0),                 # Total game TOI (capped)
                            1.0 if cumulative_toi_game > 900 else 0.0,              # Heavy usage flag (>15min)
                            
                            # Strategic context (3 features)  
                            last_change_control,                                     # Has last change (1/0)
                            min(stoppage_type_numeric / 5.0, 1.0),                  # Stoppage type (capped 0-1)
                            min(actual_stoppage_duration / 120.0, 2.0),             # Real stoppage duration (capped)
                        ]
                        
                        # Store comprehensive rest training data with dual rest signals
                        self.rest_training_data.append({
                            'player_id': player,
                            'context_features': context_features,
                            
                            # Dual rest signals for enhanced fatigue modeling
                            'rest_real_s': rest_real_s,                 # Real elapsed time (includes stoppages)
                            'rest_game_s': rest_game_s,                 # Game clock time 
                            'intermission_flag': intermission_flag,     # 1 if across periods, 0 if within period
                            'intermission_real_s': intermission_real_s, # 1080s for intermissions, 0 otherwise
                            
                            # Legacy compatibility (use game clock rest as primary target)
                            'rest_seconds': rest_game_s if intermission_flag == 0 else rest_game_s,
                            
                            # Enhanced shift and TOI metrics for validation/analysis
                            'shift_count_this_period': shift_count_this_period,
                            'shift_count_game': shift_count_game,
                            'cumulative_toi_game': cumulative_toi_game,
                            'toi_past_20min': toi_past_20min,
                            'ewma_shift_length': ewma_shift_length,
                            'ewma_rest_length': ewma_rest_length,
                            
                            # Situational context
                            'situation_left': rest_data['situation_when_left'],
                            'situation_returned': strength_state,
                            'period': period_index,
                            'score_diff': score_diff,
                            
                            # STOPPAGE CONTEXT: Real stoppage data from CSV extraction
                            'last_stoppage_type': last_stoppage_type,
                            'stoppage_duration': actual_stoppage_duration
                        })
                        
                        self.player_return_intervals[player].append(rest_game_s)
                        del player_rest_starts[player]
            
            # Track deployment for rotation chains
            if opp_forwards and opp_defense:
                deployment_key = f"{'|'.join(sorted(opp_forwards))}_{'|'.join(sorted(opp_defense))}"
                line_deployment_sequence.append({
                    'deployment': deployment_key,
                    'game_time': game_time,
                    'period_time': period_time,
                    'timecode': current_timecode,
                    'period': period,
                    'situation': row.get('strengthState', '5v5')
                })
            
            prev_on_ice = current_on_ice
        
        # Store exact TOI data for mathematical precision in class attributes
        self.player_exact_toi.update(player_exact_toi)
        self.player_shift_sequences.update(player_shift_sequences)
        
        # Shift sequences successfully extracted and accumulated across all games
        
        # Analyze rotation chains
        self._analyze_rotation_chains(line_deployment_sequence)
        
        # Log exact TOI statistics
        if player_exact_toi:
            total_toi_values = list(player_exact_toi.values())
            logger.debug(f"Exact TOI computed for {len(player_exact_toi)} players")
            logger.debug(f"  Total TOI range: {np.min(total_toi_values):.1f}s - {np.max(total_toi_values):.1f}s")
            logger.debug(f"  Average TOI per player: {np.mean(total_toi_values):.1f}s")
        
        logger.debug(f"Tracked {len(player_shift_sequences)} players with complete shift sequences")
        logger.debug(f"Extracted {len(self.player_rest_patterns)} player rest patterns")
    
    def _analyze_rotation_chains(self, deployment_sequence: List[Dict]) -> None:
        """Analyze deployment sequences to extract rotation patterns"""
        
        if len(deployment_sequence) < 2:
            return
        
        # Track transitions between deployments
        for i in range(len(deployment_sequence) - 1):
            curr = deployment_sequence[i]
            next_deploy = deployment_sequence[i + 1]
            
            # Calculate time between deployments
            time_between = next_deploy['timecode'] - curr['timecode']
            
            # Store rotation chain
            self.line_rotation_chains.append({
                'from': curr['deployment'],
                'to': next_deploy['deployment'],
                'real_time_between': time_between,
                'game_time_between': next_deploy['game_time'] - curr['game_time'],
                'situation_from': curr['situation'],
                'situation_to': next_deploy['situation'],
                'period': curr['period']
            })
    
    def extract_predictive_patterns(self) -> Dict:
        """Extract predictive patterns for ALL players from processed data"""
        
        patterns = {
            'player_specific_rest': {},
            'situation_transitions': {},
            'line_rotation_probabilities': {},
            'return_time_distributions': {},
            'total_players_tracked': len(self.all_players_tracked),
            'opponent_aggregated_matchups': {},
            'team_aware_rest_patterns': {}  # TEAM-AWARE: Per-opponent rest patterns
        }
        
        # CRITICAL: Calculate rest patterns for EVERY player that appeared in ANY game
        for player in self.all_players_tracked:
            if player in self.player_rest_patterns:
                patterns['player_specific_rest'][player] = {}
                
                for situation, rest_events in self.player_rest_patterns[player].items():
                    if rest_events:
                        real_rest_times = [e['real_rest_seconds'] for e in rest_events]
                        patterns['player_specific_rest'][player][situation] = {
                            'mean': np.mean(real_rest_times),
                            'std': np.std(real_rest_times),
                            'min': np.min(real_rest_times),
                            'max': np.max(real_rest_times),
                            'median': np.median(real_rest_times),
                            'percentile_25': np.percentile(real_rest_times, 25),
                            'percentile_75': np.percentile(real_rest_times, 75),
                            'samples': len(real_rest_times)
                        }
            else:
                # Even players with no specific rest data get default values
                patterns['player_specific_rest'][player] = {
                    '5v5': {'mean': 90.0, 'std': 15.0, 'median': 90.0, 'samples': 0}
                }
        
        # Calculate rotation probabilities
        rotation_counts = defaultdict(lambda: defaultdict(int))
        for chain in self.line_rotation_chains:
            rotation_counts[chain['from']][chain['to']] += 1
        
        # Convert to probabilities
        for from_line, to_lines in rotation_counts.items():
            total = sum(to_lines.values())
            patterns['line_rotation_probabilities'][from_line] = {
                to_line: count/total for to_line, count in to_lines.items()
            }
        
        # Calculate return time distributions for ALL players
        for player in self.all_players_tracked:
            if player in self.player_return_intervals and self.player_return_intervals[player]:
                intervals = self.player_return_intervals[player]
                patterns['return_time_distributions'][player] = {
                    'mean': np.mean(intervals),
                    'std': np.std(intervals),
                    'percentile_25': np.percentile(intervals, 25),
                    'percentile_50': np.percentile(intervals, 50),
                    'percentile_75': np.percentile(intervals, 75),
                    'percentile_90': np.percentile(intervals, 90),
                    'samples': len(intervals)
                }
            else:
                # Default for players without specific data
                patterns['return_time_distributions'][player] = {
                    'mean': 90.0, 'std': 15.0, 'percentile_50': 90.0, 'samples': 0
                }
        
        # CRITICAL: Aggregate matchups by opponent team WITH RECENCY WEIGHTING
        reference_date = datetime.now()  # Use current date as reference for recency
        
        for opponent, matchup_data in self.opponent_specific_matchups.items():
            patterns['opponent_aggregated_matchups'][opponent] = {}
            
            for mtl_player, opp_players in matchup_data.items():
                # Apply recency weighting to each matchup
                weighted_total = 0.0
                weighted_matchups = {}
                
                for opp_player, time_data in opp_players.items():
                    if isinstance(time_data, dict) and 'time_together' in time_data:
                        # New format with game_id and date
                        time_together = time_data['time_together']
                        game_date = time_data.get('game_date', reference_date)
                        recency_weight = self.calculate_recency_weight(game_date, reference_date)
                        
                        weighted_time = time_together * recency_weight
                        weighted_matchups[opp_player] = weighted_time
                        weighted_total += weighted_time
                    else:
                        # Legacy format (raw time values)
                        time_together = float(time_data) if time_data else 0.0
                        # Assume average recency weight if no date available
                        default_weight = 0.7  # Moderate recency weight
                        weighted_time = time_together * default_weight
                        weighted_matchups[opp_player] = weighted_time
                        weighted_total += weighted_time
                
                # Calculate recency-weighted percentages
                patterns['opponent_aggregated_matchups'][opponent][mtl_player] = {
                    opp_player: (weighted_time / weighted_total * 100) if weighted_total > 0 else 0
                    for opp_player, weighted_time in weighted_matchups.items()
                }
        
        # Add player experience tracking for hierarchical priors
        patterns['player_experience'] = {}
        rookie_count = 0
        veteran_count = 0
        
        for player_id in self.all_players_tracked:
            games_played = self.player_nhl_games.get(player_id, 0)
            is_rookie = games_played < self.rookie_threshold
            
            patterns['player_experience'][player_id] = {
                'nhl_games': games_played,
                'is_rookie': is_rookie,
                'experience_weight': 0.3 if is_rookie else 1.0  # Lower weight for rookies
            }
            
            if is_rookie:
                rookie_count += 1
            else:
                veteran_count += 1
        
        logger.info(f"Extracted patterns for {patterns['total_players_tracked']} total players")
        logger.info(f"  - {veteran_count} veterans (≥{self.rookie_threshold} games)")
        logger.info(f"  - {rookie_count} rookies (<{self.rookie_threshold} games)")
        
        # Log experience distribution for validation
        if veteran_count + rookie_count > 0:
            avg_experience = np.mean([self.player_nhl_games.get(p, 0) for p in self.all_players_tracked])
            logger.info(f"  - Average NHL experience: {avg_experience:.1f} games")
        
        # Count unique opponents discovered across all games
        unique_opponents = set()
        for event in self.deployment_events:
            if hasattr(event, 'opponent_team') and event.opponent_team:
                unique_opponents.add(event.opponent_team)
        
        logger.info(f"Unique opponents discovered: {len(unique_opponents)} teams")
        logger.info(f"  Opponents: {sorted(list(unique_opponents))}")
        logger.info(f"Opponent-specific matchups tracked for {len(patterns['opponent_aggregated_matchups'])} teams")
        logger.info(f"Recency weighting applied to all opponent aggregations")
        
        # TEAM-AWARE: Extract per-opponent team rest patterns
        for opponent_team, team_players in self.team_player_rest_patterns.items():
            patterns['team_aware_rest_patterns'][opponent_team] = {}
            
            for player, situations in team_players.items():
                patterns['team_aware_rest_patterns'][opponent_team][player] = {}
                
                for situation, rest_times in situations.items():
                    if rest_times:
                        patterns['team_aware_rest_patterns'][opponent_team][player][situation] = {
                            'mean': np.mean(rest_times),
                            'std': np.std(rest_times) if len(rest_times) > 1 else 0.0,
                            'median': np.median(rest_times),
                            'percentile_25': np.percentile(rest_times, 25) if len(rest_times) >= 4 else np.mean(rest_times),
                            'percentile_75': np.percentile(rest_times, 75) if len(rest_times) >= 4 else np.mean(rest_times),
                            'samples': len(rest_times)
                        }
        
        logger.info(f"Team-aware rest patterns extracted for {len(patterns['team_aware_rest_patterns'])} opponent teams")
        
        return patterns
    
    def _update_opponent_matchups_with_recency(self, mtl_player: str, opp_player: str, 
                                              opponent_team: str, shift_time: float, 
                                              game_date: datetime) -> None:
        """Update opponent matchups with recency data for weighted aggregation"""
        
        if opponent_team not in self.opponent_specific_matchups:
            self.opponent_specific_matchups[opponent_team] = defaultdict(lambda: defaultdict(dict))
        
        # Initialize nested structure if needed
        if mtl_player not in self.opponent_specific_matchups[opponent_team]:
            self.opponent_specific_matchups[opponent_team][mtl_player] = defaultdict(dict)
        
        # Accumulate time together with game metadata
        if opp_player not in self.opponent_specific_matchups[opponent_team][mtl_player]:
            self.opponent_specific_matchups[opponent_team][mtl_player][opp_player] = {
                'time_together': 0.0,
                'game_date': game_date,
                'games_count': 0
            }
        
        # Add shift time to total
        matchup_data = self.opponent_specific_matchups[opponent_team][mtl_player][opp_player]
        matchup_data['time_together'] += shift_time
        matchup_data['games_count'] += 1
        matchup_data['game_date'] = game_date  # Keep most recent date
    
    def train_bayesian_rest_model(self) -> None:
        """Train robust Huber regression model for context-aware rest prediction"""
        
        if len(self.rest_training_data) < 50:
            logger.warning("Insufficient data for rest model training")
            return
        
        # Prepare training data with enhanced features
        X = []  # Context features
        y = []  # Rest times
        
        for record in self.rest_training_data:
            X.append(record['context_features'])
            y.append(record['rest_seconds'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Filter outliers using IQR method (more conservative than hard capping)
        q1, q3 = np.percentile(y, [25, 75])
        iqr = q3 - q1
        lower_bound = max(15.0, q1 - 1.5 * iqr)  # At least 15s minimum
        upper_bound = q3 + 3.0 * iqr  # More generous upper bound (allows 5+ min rests)
        
        # Keep samples within reasonable bounds
        valid_mask = (y >= lower_bound) & (y <= upper_bound)
        X_filtered = X[valid_mask]
        y_filtered = y[valid_mask]
        
        logger.info(f"Filtered {len(y) - len(y_filtered)} outliers from {len(y)} samples")
        logger.info(f"Rest time bounds: {lower_bound:.1f}s - {upper_bound:.1f}s")
        logger.info(f"Median rest: {np.median(y_filtered):.1f}s")
        
        # Scale features for better convergence
        X_scaled = self.rest_context_scaler.fit_transform(X_filtered)
        
        # Train robust Huber regression
        self.bayesian_rest_model.fit(X_scaled, y_filtered)
        
        # Log model performance
        score = self.bayesian_rest_model.score(X_scaled, y_filtered)
        
        logger.info(f"✓ Trained robust rest model:")
        logger.info(f"  Training samples: {len(y_filtered)} (filtered from {len(y)})")
        logger.info(f"  R² score: {score:.4f}")
        logger.info(f"  Huber epsilon: {self.bayesian_rest_model.epsilon}")
        logger.info(f"  Alpha regularization: {self.bayesian_rest_model.alpha}")
        
        # Calculate prediction intervals for validation
        y_pred = self.bayesian_rest_model.predict(X_scaled)
        residuals = y_filtered - y_pred
        rmse = np.sqrt(np.mean(residuals**2))
        mae = np.mean(np.abs(residuals))
        
        logger.info(f"  RMSE: {rmse:.2f} seconds")
        logger.info(f"  MAE: {mae:.2f} seconds")
        
        # Log percentiles of predictions
        logger.info(f"  Rest prediction range: {np.min(y_pred):.1f}s - {np.max(y_pred):.1f}s")
        
        # Store residuals std for uncertainty estimation
        self._training_residuals_std = np.std(residuals)
    
    def predict_context_aware_rest(self, context_features: List[float]) -> Tuple[float, float]:
        """
        Predict expected rest time and uncertainty using robust regression
        
        Args:
            context_features: Enhanced feature vector with 15 dimensions
        
        Returns:
            Tuple of (predicted_mean, predicted_std)
        """
        
        if not hasattr(self.bayesian_rest_model, 'coef_'):
            # Model not trained, return global defaults
            return 90.0, 20.0
        
        X = np.array(context_features).reshape(1, -1)
        X_scaled = self.rest_context_scaler.transform(X)
        
        # Robust prediction
        mean_pred = self.bayesian_rest_model.predict(X_scaled)[0]
        
        # Estimate uncertainty from residuals during training
        if hasattr(self, '_training_residuals_std'):
            std_pred = self._training_residuals_std
        else:
            # Default uncertainty estimate
            std_pred = 20.0
        
        # Ensure reasonable predictions (no artificial capping per user request)
        mean_pred = max(15.0, mean_pred)  # Minimum 15s rest
        std_pred = np.clip(std_pred, 5.0, 60.0)  # Reasonable uncertainty bounds
        
        return float(mean_pred), float(std_pred)
    
    def process_game(self, game_file: Path) -> List[DeploymentEvent]:
        """Process a single game file to extract deployment events"""
        logger.info(f"Processing game: {game_file.name}")
        
        try:
            df = pd.read_csv(game_file)
            home_team, away_team = self.determine_home_away(game_file.name)
            last_change_team = home_team  # Home team has last change
            
            # VALIDATION: Ensure consistency of last change rule (should always be home team)
            if last_change_team != home_team:
                logger.warning(f"Last change team inconsistency detected in {game_file.name}: {last_change_team} != {home_team}")
                last_change_team = home_team  # Remediation: enforce home team rule
            
            # Extract game date and season for recency weighting and roster management
            game_date = self.extract_game_date(game_file.name)
            season = self.extract_season(game_file.name)
            logger.debug(f"Extracted season '{season}' from {game_file.name}")
            
            # Determine opponent team
            opponent_team = away_team if home_team == 'MTL' else home_team
            game_id = df.loc[0, 'gameReferenceId'] if 'gameReferenceId' in df.columns else game_file.stem
            
            # Store game date for recency calculations
            self.game_dates[game_id] = game_date
            
            # Set current game context for recency tracking
            self.current_game_date = game_date
            self.current_opponent = opponent_team
            
            events = []
            
            # CRITICAL: Track ALL players that appear in this game
            players_in_game = set()
            
            # Scan entire CSV to identify ALL players
            for col in ['teamForwardsOnIceRefs', 'teamDefencemenOnIceRefs',
                       'opposingTeamForwardsOnIceRefs', 'opposingTeamDefencemenOnIceRefs']:
                if col in df.columns:
                    for refs in df[col].dropna():
                        player_ids = self.parse_on_ice_refs(refs)
                        players_in_game.update(player_ids)
                        self.all_players_tracked.update(player_ids)
            
            # Track NHL experience for hierarchical priors (incremental on top of pre-seeded values)
            for player_id in players_in_game:
                self.player_nhl_games[player_id] += 1  # Increment from pre-seeded base
            
            logger.info(f"  Tracking {len(players_in_game)} unique players in this game")
            
            # Initialize exact TOI tracking attributes BEFORE processing
            if not hasattr(self, 'player_exact_toi'):
                self.player_exact_toi = {}
            if not hasattr(self, 'player_shift_sequences'):
                self.player_shift_sequences = {}
            
            # Track shift details using both period time and timecode
            player_shift_starts = {}  # player_id -> (period_time, timecode)
            player_shift_lengths = {}  # player_id -> list of shift lengths
            player_rest_starts = {}  # player_id -> timecode when they came off ice
            
            # Track last computed rest values for persistence
            last_rest_real_by_player = {}  # player_id -> last computed real rest
            last_rest_game_by_player = {}  # player_id -> last computed game rest
            
            # Initialize shift tracking for ALL players in game
            for player_id in players_in_game:
                if player_id not in player_shift_lengths:
                    player_shift_lengths[player_id] = []
            
            # Process all events to build shift tracking
            self._build_shift_tracking(df, player_shift_starts, player_shift_lengths, player_rest_starts, last_change_team, last_rest_real_by_player, last_rest_game_by_player)
            
            # Identify faceoff events and subsequent deployments
            faceoff_indices = df[df['type'] == 'faceoff'].index
            
            for idx in faceoff_indices:
                row = df.loc[idx]
                
                # Create deployment event
                # Compute MTL-centric score differential
                mtl_score_diff = self._compute_mtl_score_diff(row, home_team, away_team)
                
                # Determine decision role (who is making deployment decision)
                decision_role = 1 if last_change_team == 'MTL' else 0
                
                # Calculate game-level timing metrics
                period_num = int(row['period'])
                period_time_val = float(row['periodTime'])
                game_seconds = (period_num - 1) * 1200.0 + period_time_val
                game_bucket = self.get_game_bucket(game_seconds)
                
                # Calculate late-period/game binary flags
                is_period_late = period_time_val >= 1020.0  # >= 17:00 in period
                is_game_late = game_seconds >= 3300.0       # >= 55:00 total game time
                
                # Calculate high-leverage situation flags
                strength_state = str(row['manpowerSituation']) if pd.notna(row['manpowerSituation']) else '5v5'
                is_pk_situation = strength_state in ['4v5', 'penaltyKill']
                is_pp_situation = strength_state in ['5v4', 'powerPlay']
                is_close_game = abs(mtl_score_diff) <= 1
                
                is_late_pk = is_pk_situation and is_period_late
                is_late_pp = is_pp_situation and is_period_late
                is_close_and_late = is_close_game and is_game_late

                event = DeploymentEvent(
                    game_id=str(row['gameReferenceId']),
                    event_id=int(row['id']),
                    period=period_num,
                    period_time=period_time_val,
                    game_time=float(row['gameTime']),
                    game_seconds=game_seconds,
                    game_bucket=game_bucket,
                    is_period_late=is_period_late,
                    is_game_late=is_game_late,
                    is_late_pk=is_late_pk,
                    is_late_pp=is_late_pp,
                    is_close_and_late=is_close_and_late,
                    zone_start=str(row['zone']) if pd.notna(row['zone']) else 'nz',
                    strength_state=strength_state,
                    score_differential=mtl_score_diff,
                    time_bucket=self.get_time_bucket(period_num, period_time_val),
                    stoppage_type='faceoff',
                    home_team=home_team,
                    away_team=away_team,
                    last_change_team=last_change_team,
                    opponent_team=opponent_team,  # TEAM-AWARE: Add opponent team tracking
                    season=season,  # Per-season roster tracking
                    decision_role=decision_role
                )
                
                # DYNAMIC CSV COLUMN MAPPING APPROACH:
                # Keep columns separate to determine which contains MTL players
                team_forwards = self.parse_on_ice_refs(row['teamForwardsOnIceRefs'])
                opp_forwards_csv = self.parse_on_ice_refs(row['opposingTeamForwardsOnIceRefs'])
                team_defense = self.parse_on_ice_refs(row['teamDefencemenOnIceRefs'])
                opp_defense_csv = self.parse_on_ice_refs(row['opposingTeamDefencemenOnIceRefs'])
                
                # Parse goalies
                team_goalie = str(row['teamGoalieOnIceRef']) if pd.notna(row['teamGoalieOnIceRef']) else ""
                opp_goalie_raw = str(row['opposingTeamGoalieOnIceRef']) if pd.notna(row['opposingTeamGoalieOnIceRef']) else ""
                
                # Count MTL players in each column to determine which column contains MTL
                # The CSV columns flip dynamically based on possession/context
                team_fwd_mtl_count = sum(1 for p in team_forwards if p in self.player_team_map and self.player_team_map[p] == 'MTL')
                opp_fwd_mtl_count = sum(1 for p in opp_forwards_csv if p in self.player_team_map and self.player_team_map[p] == 'MTL')
                
                team_def_mtl_count = sum(1 for p in team_defense if p in self.player_team_map and self.player_team_map[p] == 'MTL')
                opp_def_mtl_count = sum(1 for p in opp_defense_csv if p in self.player_team_map and self.player_team_map[p] == 'MTL')
                
                # DIAGNOSTIC: Log first few events to verify logic
                if not hasattr(self, '_logged_diagnostic_count'):
                    self._logged_diagnostic_count = 0
                
                if self._logged_diagnostic_count < 5:
                    logger.info(f"DIAGNOSTIC [{self._logged_diagnostic_count}] - Game: {game_file.name[:30]}")
                    logger.info(f"  Home: {home_team}, Away: {away_team}")
                    logger.info(f"  team_forwards: {team_forwards}")
                    logger.info(f"  opp_forwards_csv: {opp_forwards_csv}")
                    logger.info(f"  team_def: {team_defense}")
                    logger.info(f"  opp_def_csv: {opp_defense_csv}")
                    logger.info(f"  MTL counts -> team_fwd: {team_fwd_mtl_count}, opp_fwd: {opp_fwd_mtl_count}, team_def: {team_def_mtl_count}, opp_def: {opp_def_mtl_count}")
                    logger.info(f"  player_team_map size: {len(self.player_team_map)}")
                    # Sample a few players to see their team assignments
                    sample_players = list(set(team_forwards + opp_forwards_csv))[:3]
                    for p in sample_players:
                        team = self.player_team_map.get(p, 'NOT_IN_MAP')
                        logger.info(f"    Player {p} -> {team}")
                    self._logged_diagnostic_count += 1
                
                # Assign based on which column has more MTL players
                if team_fwd_mtl_count + team_def_mtl_count >= opp_fwd_mtl_count + opp_def_mtl_count:
                    # teamForwardsOnIce contains MTL players
                    event.mtl_forwards = [p for p in team_forwards if p in self.player_team_map and self.player_team_map[p] == 'MTL']
                    event.opp_forwards = [p for p in opp_forwards_csv if p in self.player_team_map and self.player_team_map[p] != 'MTL']
                    event.mtl_defense = [p for p in team_defense if p in self.player_team_map and self.player_team_map[p] == 'MTL']
                    event.opp_defense = [p for p in opp_defense_csv if p in self.player_team_map and self.player_team_map[p] != 'MTL']
                else:
                    # opposingTeamForwardsOnIce contains MTL players (columns are flipped)
                    event.mtl_forwards = [p for p in opp_forwards_csv if p in self.player_team_map and self.player_team_map[p] == 'MTL']
                    event.opp_forwards = [p for p in team_forwards if p in self.player_team_map and self.player_team_map[p] != 'MTL']
                    event.mtl_defense = [p for p in opp_defense_csv if p in self.player_team_map and self.player_team_map[p] == 'MTL']
                    event.opp_defense = [p for p in team_defense if p in self.player_team_map and self.player_team_map[p] != 'MTL']
                
                # Assign goalies
                if team_goalie and team_goalie in self.player_team_map:
                    if self.player_team_map[team_goalie] == 'MTL':
                        event.mtl_goalie = team_goalie
                        event.opp_goalie = opp_goalie_raw
                    else:
                        event.mtl_goalie = opp_goalie_raw
                        event.opp_goalie = team_goalie
                else:
                    # Fallback if goalie not in map
                    event.mtl_goalie = team_goalie if 'MTL' in home_team else opp_goalie_raw
                    event.opp_goalie = opp_goalie_raw if 'MTL' in home_team else team_goalie
                
                # Calculate rest times using proper timecode tracking
                current_timecode = self._parse_timecode_to_seconds(row.get('timecode', ''))
                
                for player_id in event.mtl_forwards + event.mtl_defense:
                    # Use persisted rest values computed during shift tracking
                    if player_id in last_rest_real_by_player:
                        rest_real_s = last_rest_real_by_player[player_id]
                        rest_game_s = last_rest_game_by_player.get(player_id, 0.0)
                        
                        # Persist per-player dual rest
                        event.mtl_time_since_last[player_id] = rest_real_s
                        event.mtl_rest_real[player_id] = rest_real_s
                        event.mtl_rest_game[player_id] = rest_game_s
                        
                        # BIDIRECTIONAL: Collect comprehensive MTL player patterns
                        situation = event.strength_state  # 5v5, 5v4, 4v5, etc.
                        
                        # 1. MTL vs specific opponent (how MTL players rest vs TOR, vs BOS, etc.)
                        mtl_vs_opponent_key = f"MTL_vs_{opponent_team}"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, mtl_vs_opponent_key, player_id, situation, rest_real_s)
                        
                        # 2. MTL general patterns (how MTL players typically rest - baseline)
                        mtl_general_key = "MTL_general"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, mtl_general_key, player_id, situation, rest_real_s)
                        
                        # 3. MTL home vs away patterns (venue-specific behavior)
                        venue = "home" if event.home_team == "MTL" else "away"
                        mtl_venue_key = f"MTL_{venue}"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, mtl_venue_key, player_id, situation, rest_real_s)
                    else:
                        # No prior shift tracked for this player -> omit from aggregates
                        pass
                
                for player_id in event.opp_forwards + event.opp_defense:
                    # Use persisted rest values computed during shift tracking
                    if player_id in last_rest_real_by_player:
                        rest_real_s = last_rest_real_by_player[player_id]
                        rest_game_s = last_rest_game_by_player.get(player_id, 0.0)
                        
                        event.opp_time_since_last[player_id] = rest_real_s
                        event.opp_rest_real[player_id] = rest_real_s
                        event.opp_rest_game[player_id] = rest_game_s
                        
                        # BIDIRECTIONAL: Collect comprehensive opponent player patterns
                        situation = event.strength_state
                        
                        # 1. Opponent team general patterns (how TOR players typically rest)
                        opponent_team_key = f"{opponent_team}_players"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, opponent_team_key, player_id, situation, rest_real_s)
                        
                        # 2. Opponent vs MTL patterns (how TOR players rest specifically vs MTL)
                        opponent_vs_mtl_key = f"{opponent_team}_vs_MTL"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, opponent_vs_mtl_key, player_id, situation, rest_real_s)
                        
                        # 3. Opponent home vs away patterns (venue-specific opponent behavior)
                        venue = "home" if event.home_team == opponent_team else "away"
                        opponent_venue_key = f"{opponent_team}_{venue}"
                        self._add_rest_pattern_with_recency(self.team_player_rest_patterns, opponent_venue_key, player_id, situation, rest_real_s)
                    else:
                        # No prior shift tracked for this player -> omit from aggregates
                        pass
                
                events.append(event)
                
                # Update matchup matrix
                self._update_matchup_matrix(event)
            
            logger.info(f"Extracted {len(events)} deployment events from {game_file.name}")
            return events
            
        except Exception as e:
            logger.error(f"Error processing {game_file.name}: {e}")
            return []
    
    def _update_matchup_matrix(self, event: DeploymentEvent) -> None:
        """Update the matchup matrix focusing on opponent response patterns"""
        
        # Focus on opponent choices when they have last change advantage
        opponent_has_last_change = (event.last_change_team != 'MTL')
        
        if not hasattr(self, 'opp_response_matrix'):
            self.opp_response_matrix = {}  # opponent choices when they have last change
            self.opp_vs_mtl_forwards = {}  # opponent forwards vs MTL forwards
            self.opp_defense_vs_mtl = {}   # opponent defense vs MTL players
        
        # Track opponent forward lines vs MTL forward lines (weight by recent shift duration)
        for opp_fwd in event.opp_forwards:
            if opp_fwd not in self.opp_vs_mtl_forwards:
                self.opp_vs_mtl_forwards[opp_fwd] = {}
            
            for mtl_fwd in event.mtl_forwards:
                if mtl_fwd not in self.opp_vs_mtl_forwards[opp_fwd]:
                    self.opp_vs_mtl_forwards[opp_fwd][mtl_fwd] = 0.0
                recent_shifts = self.player_shift_sequences.get(opp_fwd, [])
                last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                weight = max(0.5, min(last_shift_len / 60.0, 3.0))
                self.opp_vs_mtl_forwards[opp_fwd][mtl_fwd] += weight
        
        # Track opponent defense pairs vs MTL forwards (weight by recent shift duration)
        for opp_def in event.opp_defense:
            if opp_def not in self.opp_defense_vs_mtl:
                self.opp_defense_vs_mtl[opp_def] = {}
            
            for mtl_fwd in event.mtl_forwards:
                if mtl_fwd not in self.opp_defense_vs_mtl[opp_def]:
                    self.opp_defense_vs_mtl[opp_def][mtl_fwd] = 0.0
                recent_shifts = self.player_shift_sequences.get(opp_def, [])
                last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                weight = max(0.5, min(last_shift_len / 60.0, 3.0))
                self.opp_defense_vs_mtl[opp_def][mtl_fwd] += weight
        
        # When opponent has last change, track their response patterns
        if opponent_has_last_change:
            mtl_lineup_key = f"F:{'|'.join(sorted(event.mtl_forwards))}_D:{'|'.join(sorted(event.mtl_defense))}"
            opp_response_key = f"F:{'|'.join(sorted(event.opp_forwards))}_D:{'|'.join(sorted(event.opp_defense))}"
            
            if mtl_lineup_key not in self.opp_response_matrix:
                self.opp_response_matrix[mtl_lineup_key] = {}
            
            if opp_response_key not in self.opp_response_matrix[mtl_lineup_key]:
                self.opp_response_matrix[mtl_lineup_key][opp_response_key] = 0.0
            
            # Weight response by mean recent opponent shift duration across involved players
            involved = list(event.opp_forwards) + list(event.opp_defense)
            weights = []
            for pid in involved:
                recent_shifts = self.player_shift_sequences.get(pid, [])
                last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                weights.append(max(0.5, min(last_shift_len / 60.0, 3.0)))
            mean_weight = float(np.mean(weights)) if weights else 1.0
            self.opp_response_matrix[mtl_lineup_key][opp_response_key] += mean_weight
        else:
            # MTL has last change: track MTL response patterns (mirror structure)
            if not hasattr(self, 'mtl_response_matrix'):
                self.mtl_response_matrix = {}
                self.mtl_vs_opp_forwards = {}
                self.mtl_defense_vs_opp_forwards = {}

            # MTL forwards vs Opponent forwards (weight by MTL last shift)
            for mtl_fwd in event.mtl_forwards:
                if mtl_fwd not in self.mtl_vs_opp_forwards:
                    self.mtl_vs_opp_forwards[mtl_fwd] = {}
                for opp_fwd in event.opp_forwards:
                    if opp_fwd not in self.mtl_vs_opp_forwards[mtl_fwd]:
                        self.mtl_vs_opp_forwards[mtl_fwd][opp_fwd] = 0.0
                    recent_shifts = self.player_shift_sequences.get(mtl_fwd, [])
                    last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                    weight = max(0.5, min(last_shift_len / 60.0, 3.0))
                    self.mtl_vs_opp_forwards[mtl_fwd][opp_fwd] += weight

            # MTL defense vs Opponent forwards (weight by MTL defense last shift)
            for mtl_def in event.mtl_defense:
                if mtl_def not in self.mtl_defense_vs_opp_forwards:
                    self.mtl_defense_vs_opp_forwards[mtl_def] = {}
                for opp_fwd in event.opp_forwards:
                    if opp_fwd not in self.mtl_defense_vs_opp_forwards[mtl_def]:
                        self.mtl_defense_vs_opp_forwards[mtl_def][opp_fwd] = 0.0
                    recent_shifts = self.player_shift_sequences.get(mtl_def, [])
                    last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                    weight = max(0.5, min(last_shift_len / 60.0, 3.0))
                    self.mtl_defense_vs_opp_forwards[mtl_def][opp_fwd] += weight

            # Record MTL response matrix keyed by opponent lineup
            opp_lineup_key = f"F:{'|'.join(sorted(event.opp_forwards))}_D:{'|'.join(sorted(event.opp_defense))}"
            mtl_response_key = f"F:{'|'.join(sorted(event.mtl_forwards))}_D:{'|'.join(sorted(event.mtl_defense))}"
            if opp_lineup_key not in self.mtl_response_matrix:
                self.mtl_response_matrix[opp_lineup_key] = {}
            if mtl_response_key not in self.mtl_response_matrix[opp_lineup_key]:
                self.mtl_response_matrix[opp_lineup_key][mtl_response_key] = 0.0
            involved_mtl = list(event.mtl_forwards) + list(event.mtl_defense)
            weights_mtl = []
            for pid in involved_mtl:
                recent_shifts = self.player_shift_sequences.get(pid, [])
                last_shift_len = recent_shifts[-1].get('shift_length', 45.0) if recent_shifts else 45.0
                weights_mtl.append(max(0.5, min(last_shift_len / 60.0, 3.0)))
            mean_weight_mtl = float(np.mean(weights_mtl)) if weights_mtl else 1.0
            self.mtl_response_matrix[opp_lineup_key][mtl_response_key] += mean_weight_mtl
        
        # Keep the original matrix for general matchup tracking
        mtl_players = event.mtl_forwards + event.mtl_defense
        opp_players = event.opp_forwards + event.opp_defense
        
        # PLAYER-VS-PLAYER: Track direct matchup counts for candidate generation
        self._update_player_matchup_counts(event, mtl_players, opp_players)
        
        # Calculate shift length for this event
        shift_length = max(30.0, min(120.0, 45.0))  # Default shift length, will be refined
        
        # Get opponent team name
        opponent_team = event.away_team if event.home_team == 'MTL' else event.home_team
        
        # Get game date for recency weighting
        game_date = self.game_dates.get(event.game_id, datetime.now())
        
        for mtl_player in mtl_players:
            if mtl_player not in self.matchup_matrix:
                self.matchup_matrix[mtl_player] = {}
            
            for opp_player in opp_players:
                if opp_player not in self.matchup_matrix[mtl_player]:
                    self.matchup_matrix[mtl_player][opp_player] = 0
                self.matchup_matrix[mtl_player][opp_player] += 1
                
                # Update opponent-specific matchups with recency data
                self._update_opponent_matchups_with_recency(
                    mtl_player, opp_player, opponent_team, shift_length, game_date
                )
    
    def _update_player_matchup_counts(self, event: DeploymentEvent, mtl_players: List[str], opp_players: List[str]) -> None:
        """
        Update player-vs-player matchup counts for candidate generation priors
        
        This tracks:
        1. Global matchup frequencies (any situation)
        2. Last-change-aware matchup patterns
        3. Situation-specific matchup patterns (5v5, 5v4, etc.)
        
        Args:
            event: Current deployment event
            mtl_players: List of MTL players on ice
            opp_players: List of opponent players on ice
        """
        situation = event.strength_state
        last_change_team = getattr(event, 'last_change_team', None)
        team_making_change = getattr(event, 'team_making_change', None)
        
        # If we have last_change_team but not team_making_change, infer it
        # In most cases, both teams make changes, but the one with last change gets the advantage
        if last_change_team and not team_making_change:
            # Default assumption: both teams are making changes, record both perspectives
            team_making_change = last_change_team  # Record from the perspective of who has the advantage
        
        # Get current game timestamp for recency weighting
        current_time = getattr(event, 'game_time', 0.0)
        
        # Track every MTL vs opponent player pairing with EWMA and capping
        for mtl_player in mtl_players:
            for opp_player in opp_players:
                
                # 1. GLOBAL: Track overall matchup frequency with EWMA
                matchup_key = (mtl_player, opp_player)
                self._update_matchup_with_ewma(
                    self.player_matchup_counts, matchup_key, current_time
                )
                
                # 2. LAST-CHANGE-AWARE: Track tactical matchup patterns
                if last_change_team and team_making_change:
                    last_change_key = (mtl_player, opp_player, last_change_team, team_making_change)
                    self._update_matchup_with_ewma(
                        self.last_change_player_matchups, last_change_key, current_time
                    )
                
                # 3. SITUATION-SPECIFIC: Track by game situation (5v5, PP, PK, etc.)
                situation_pair_key = (mtl_player, opp_player)
                self._update_matchup_with_ewma(
                    self.situation_player_matchups[situation_pair_key], situation, current_time
                )
        
        # Log progress periodically
        total_matchups = sum(self.player_matchup_counts.values())
        if total_matchups > 0 and total_matchups % 1000 == 0:
            logger.debug(f"Processed {total_matchups} player-vs-player matchups")
    
    def _update_matchup_with_ewma(self, matchup_dict: Dict, key: tuple, current_time: float) -> None:
        """
        Update matchup count with EWMA recency weighting and apply capping
        
        Args:
            matchup_dict: Dictionary to update (player_matchup_counts, etc.)
            key: Matchup key (tuple)
            current_time: Current game timestamp
        """
        # Track timestamps for this matchup
        self.matchup_timestamps[key].append(current_time)
        
        # Apply EWMA weighting: recent matchups get higher weight
        if key in matchup_dict:
            # Decay existing count and add new weighted occurrence
            matchup_dict[key] = (matchup_dict[key] * (1 - MATCHUP_EWMA_ALPHA)) + MATCHUP_EWMA_ALPHA
        else:
            # First occurrence
            matchup_dict[key] = 1.0
        
        # Apply capping: keep only recent timestamps
        if len(self.matchup_timestamps[key]) > MAX_MATCHUPS_PER_PLAYER:
            # Keep only the most recent timestamps
            self.matchup_timestamps[key] = self.matchup_timestamps[key][-MAX_MATCHUPS_PER_PLAYER:]
    
    def _prune_low_frequency_matchups(self) -> None:
        """
        Remove matchups with very low frequency to prevent memory bloat
        Called periodically during processing
        """
        # Prune global matchup counts
        keys_to_remove = [
            key for key, count in self.player_matchup_counts.items() 
            if count < MIN_MATCHUP_FREQUENCY
        ]
        for key in keys_to_remove:
            del self.player_matchup_counts[key]
            if key in self.matchup_timestamps:
                del self.matchup_timestamps[key]
        
        # Prune last-change-aware matchups
        keys_to_remove = [
            key for key, count in self.last_change_player_matchups.items() 
            if count < MIN_MATCHUP_FREQUENCY
        ]
        for key in keys_to_remove:
            del self.last_change_player_matchups[key]
        
        # Prune situation-specific matchups (nested structure requires special handling)
        for player_pair in list(self.situation_player_matchups.keys()):
            situations_to_remove = [
                situation for situation, count in self.situation_player_matchups[player_pair].items()
                if count < MIN_MATCHUP_FREQUENCY
            ]
            for situation in situations_to_remove:
                del self.situation_player_matchups[player_pair][situation]
            
            # Remove empty player pairs
            if not self.situation_player_matchups[player_pair]:
                del self.situation_player_matchups[player_pair]
        
        if keys_to_remove:
            logger.debug(f"Pruned {len(keys_to_remove)} low-frequency matchups")
    
    def _prune_to_top_n_per_player(self) -> None:
        """
        Advanced pruning: Keep only top-N most frequent matchups per player
        This focuses on the most meaningful player interactions while managing memory
        """
        logger.info("Performing top-N pruning of player matchups...")
        
        # Track statistics
        original_global_count = len(self.player_matchup_counts)
        original_last_change_count = len(self.last_change_player_matchups)
        
        # 1. GLOBAL MATCHUPS: Group by MTL player and keep top-N opponents
        mtl_player_matchups = defaultdict(list)
        for (mtl_player, opp_player), count in self.player_matchup_counts.items():
            mtl_player_matchups[mtl_player].append((opp_player, count))
        
        # Keep only top-N per MTL player
        pruned_global = {}
        for mtl_player, matchups in mtl_player_matchups.items():
            # Sort by count (descending) and keep top-N
            top_matchups = sorted(matchups, key=lambda x: x[1], reverse=True)[:TOP_N_MATCHUPS_PER_PLAYER]
            for opp_player, count in top_matchups:
                pruned_global[(mtl_player, opp_player)] = count
        
        self.player_matchup_counts = defaultdict(float, pruned_global)
        
        # 2. LAST-CHANGE MATCHUPS: Similar approach but with more complex keys
        mtl_player_last_change = defaultdict(list)
        for key, count in self.last_change_player_matchups.items():
            if len(key) >= 2:  # Ensure key has at least mtl_player, opp_player
                mtl_player = key[0]  # First element is MTL player
                mtl_player_last_change[mtl_player].append((key, count))
        
        # Keep only top-N per MTL player for last-change matchups
        pruned_last_change = {}
        for mtl_player, matchups in mtl_player_last_change.items():
            top_matchups = sorted(matchups, key=lambda x: x[1], reverse=True)[:TOP_N_MATCHUPS_PER_PLAYER]
            for key, count in top_matchups:
                pruned_last_change[key] = count
        
        self.last_change_player_matchups = defaultdict(float, pruned_last_change)
        
        # 3. SITUATION-SPECIFIC MATCHUPS: Keep top-N situations per player pair
        for player_pair in list(self.situation_player_matchups.keys()):
            situation_counts = list(self.situation_player_matchups[player_pair].items())
            if len(situation_counts) > TOP_N_MATCHUPS_PER_PLAYER:
                # Keep top-N situations for this player pair
                top_situations = sorted(situation_counts, key=lambda x: x[1], reverse=True)[:TOP_N_MATCHUPS_PER_PLAYER]
                self.situation_player_matchups[player_pair] = defaultdict(float, dict(top_situations))
        
        # Log pruning statistics
        new_global_count = len(self.player_matchup_counts)
        new_last_change_count = len(self.last_change_player_matchups)
        
        logger.info(f"Top-N pruning complete:")
        
        # Calculate reduction percentages safely
        global_reduction = (
            100 * (original_global_count - new_global_count) / original_global_count
            if original_global_count > 0 else 0.0
        )
        last_change_reduction = (
            100 * (original_last_change_count - new_last_change_count) / original_last_change_count
            if original_last_change_count > 0 else 0.0
        )
        
        logger.info(f"  Global matchups: {original_global_count} → {new_global_count} "
                   f"({global_reduction:.1f}% reduction)")
        logger.info(f"  Last-change matchups: {original_last_change_count} → {new_last_change_count} "
                   f"({last_change_reduction:.1f}% reduction)")
        
        # Update matchup timestamps to remove pruned entries
        if hasattr(self, 'matchup_timestamps'):
            pruned_keys = set(self.player_matchup_counts.keys())
            self.matchup_timestamps = {
                key: timestamp for key, timestamp in self.matchup_timestamps.items() 
                if key in pruned_keys
            }
    
    def process_all_games(self) -> pd.DataFrame:
        """Process all game files and return comprehensive dataset"""
        game_files = list(self.data_path.glob("playsequence-*.csv"))
        logger.info(f"Found {len(game_files)} game files to process")
        
        all_events = []
        for i, game_file in enumerate(game_files):
            events = self.process_game(game_file)
            all_events.extend(events)
            self.deployment_events.extend(events)
            
        # Prune low-frequency matchups every 10 games to prevent memory bloat
        if (i + 1) % 10 == 0:
            self._prune_low_frequency_matchups()
            
            # PERFORMANCE: Take memory snapshot every 10 games
            if self.memory_profiler and (i + 1) % 50 == 0:  # Every 50 games for detailed snapshot
                components = {
                    'team_rest_patterns': self.team_player_rest_patterns,
                    'player_matchups': self.player_matchup_counts,
                    'last_change_matchups': self.last_change_player_matchups,
                    'situation_matchups': self.situation_player_matchups
                }
                self.memory_profiler.take_snapshot(f"After {i+1} games processed", components)
        
        # PERFORMANCE: Apply final top-N pruning to focus on most meaningful matchups
        self._prune_to_top_n_per_player()
        
        # Convert to DataFrame for analysis
        df_events = pd.DataFrame([self._event_to_dict(e) for e in all_events])
        logger.info(f"Processed {len(all_events)} total deployment events")
        
        # PERFORMANCE: Final diagnostics and memory analysis
        if self.memory_profiler and self.pattern_diagnostics:
            final_components = {
                'team_rest_patterns': self.team_player_rest_patterns,
                'player_matchups': self.player_matchup_counts,
                'last_change_matchups': self.last_change_player_matchups,
                'situation_matchups': self.situation_player_matchups,
                'deployment_events': self.deployment_events
            }
            
            self.memory_profiler.take_snapshot("Processing Complete", final_components)
            
            # Analyze pattern structures
            pattern_analysis = self.pattern_diagnostics.analyze_data_processor(self)
            self.pattern_diagnostics.log_pattern_diagnostics(pattern_analysis)
            
            # Log memory summary
            self.memory_profiler.log_summary()

        return df_events
    
    def _event_to_dict(self, event: DeploymentEvent) -> Dict:
        """Convert DeploymentEvent to dictionary for DataFrame"""
        # Robust team-level aggregates using medians with minimum contributors
        def robust_aggregate(values: Dict[str, float]) -> Optional[float]:
            arr = np.array(list(values.values()), dtype=float)
            arr = arr[~np.isnan(arr)] if arr.size else arr
            if arr.size < 2:
                return None
            # Clip to reasonable hockey rest ranges for game-clock signal when used
            return float(np.median(arr))

        return {
            'game_id': event.game_id,
            'event_id': event.event_id,
            'period': event.period,
            'period_time': event.period_time,
            'game_time': event.game_time,
            'game_seconds': event.game_seconds,
            'game_bucket': event.game_bucket,
            'is_period_late': event.is_period_late,
            'is_game_late': event.is_game_late,
            'is_late_pk': event.is_late_pk,
            'is_late_pp': event.is_late_pp,
            'is_close_and_late': event.is_close_and_late,
            'zone_start': event.zone_start,
            'strength_state': event.strength_state,
            'score_differential': event.score_differential,
            'time_bucket': event.time_bucket,
            'stoppage_type': event.stoppage_type,
            'home_team': event.home_team,
            'away_team': event.away_team,
            'last_change_team': event.last_change_team,
            'opponent_team': event.opponent_team,  # TEAM-AWARE: Include opponent team in DataFrame
            'season': event.season,  # Per-season roster tracking
            'decision_role': event.decision_role,
            'mtl_forwards': '|'.join(event.mtl_forwards),
            'mtl_defense': '|'.join(event.mtl_defense),
            'opp_forwards': '|'.join(event.opp_forwards),
            'opp_defense': '|'.join(event.opp_defense),
            'mtl_has_last_change': event.last_change_team == 'MTL',
            'opp_has_last_change': event.last_change_team != 'MTL',  # Critical for training
            # Team-level rest aggregates (real-time based medians)
            'mtl_avg_rest': robust_aggregate(event.mtl_time_since_last),
            'opp_avg_rest': robust_aggregate(event.opp_time_since_last),
            'mtl_min_rest': (float(np.min(list(event.mtl_time_since_last.values())))
                             if len(event.mtl_time_since_last) >= 2 else None),
            'opp_min_rest': (float(np.min(list(event.opp_time_since_last.values())))
                             if len(event.opp_time_since_last) >= 2 else None),
            # Persist per-player dual rest maps for auditability
            'mtl_rest_real_map': json.dumps(event.mtl_rest_real) if event.mtl_rest_real else None,
            'mtl_rest_game_map': json.dumps(event.mtl_rest_game) if event.mtl_rest_game else None,
            'opp_rest_real_map': json.dumps(event.opp_rest_real) if event.opp_rest_real else None,
            'opp_rest_game_map': json.dumps(event.opp_rest_game) if event.opp_rest_game else None
        }
    
    def get_line_combinations(self, min_together: int = 10) -> Dict[str, pd.DataFrame]:
        """Extract frequently used line combinations"""
        forward_combos = {}
        defense_pairs = {}
        
        for event in self.deployment_events:
            # MTL forward combinations
            if len(event.mtl_forwards) >= 3:
                combo_key = '|'.join(sorted(event.mtl_forwards))
                forward_combos[combo_key] = forward_combos.get(combo_key, 0) + 1
            
            # MTL defense pairs
            if len(event.mtl_defense) >= 2:
                pair_key = '|'.join(sorted(event.mtl_defense))
                defense_pairs[pair_key] = defense_pairs.get(pair_key, 0) + 1
        
        # Filter by minimum occurrences
        forward_df = pd.DataFrame(
            [(k, v) for k, v in forward_combos.items() if v >= min_together],
            columns=['combination', 'occurrences']
        ).sort_values('occurrences', ascending=False)
        
        defense_df = pd.DataFrame(
            [(k, v) for k, v in defense_pairs.items() if v >= min_together],
            columns=['pair', 'occurrences']
        ).sort_values('occurrences', ascending=False)
        
        return {'forwards': forward_df, 'defense': defense_df}
    
    def get_shift_data(self) -> Dict[str, Dict]:
        """Extract shift length data for feature engineering"""
        shift_summary = {
            'avg_shift_lengths': {},
            'total_shifts': {},
            'shift_distributions': {}
        }
        
        # Calculate shift statistics from tracked data
        if hasattr(self, 'player_shift_lengths'):
            for player, shifts in self.player_shift_lengths.items():
                if shifts:
                    shift_summary['avg_shift_lengths'][player] = np.mean(shifts)
                    shift_summary['total_shifts'][player] = len(shifts)
                    shift_summary['shift_distributions'][player] = shifts
        
        return shift_summary
    
    def save_processed_data(self, output_path: Path) -> None:
        """Save processed deployment events to parquet for efficiency"""
        df = pd.DataFrame([self._event_to_dict(e) for e in self.deployment_events])
        
        # Save as parquet with compression
        output_file = output_path / 'deployment_events.parquet'
        df.to_parquet(output_file, compression='zstd', index=False)
        logger.info(f"Saved {len(df)} deployment events to {output_file}")
        
        # Save shift length data for accurate matchup calculations
        if hasattr(self, 'player_shift_lengths'):
            import pickle
            shift_file = output_path / 'shift_lengths.pkl'
            shift_data = self.get_shift_data()
            with open(shift_file, 'wb') as f:
                pickle.dump(shift_data, f)
            logger.info(f"Saved shift length data for {len(shift_data['avg_shift_lengths'])} players")
        
        # Save general matchup matrix
        matchup_file = output_path / 'matchup_matrix.parquet'
        matchup_df = pd.DataFrame([
            {'mtl_player': mtl, 'opp_player': opp, 'time_together': time}
            for mtl, opps in self.matchup_matrix.items()
            for opp, time in opps.items()
        ])
        matchup_df.to_parquet(matchup_file, compression='zstd', index=False)
        logger.info(f"Saved matchup matrix with {len(matchup_df)} player pairs")
        
        # PLAYER-VS-PLAYER: Save enhanced matchup patterns with format version v2.1
        self._save_player_matchup_patterns(output_path)
        
        # Save opponent response matrix (when they have last change)
        if hasattr(self, 'opp_response_matrix'):
            opp_response_file = output_path / 'opp_response_patterns.parquet'
            response_df = pd.DataFrame([
                {'mtl_lineup': mtl_lineup, 'opp_response': opp_response, 'frequency': freq}
                for mtl_lineup, responses in self.opp_response_matrix.items()
                for opp_response, freq in responses.items()
            ])
            response_df.to_parquet(opp_response_file, compression='zstd', index=False)
            logger.info(f"Saved opponent response patterns with {len(response_df)} combinations")
        
        # Save opponent forwards vs MTL forwards matrix
        if hasattr(self, 'opp_vs_mtl_forwards'):
            opp_fwd_file = output_path / 'opp_forwards_vs_mtl.parquet'
            opp_fwd_df = pd.DataFrame([
                {'opp_forward': opp_fwd, 'mtl_forward': mtl_fwd, 'matchups': count}
                for opp_fwd, mtl_fwds in self.opp_vs_mtl_forwards.items()
                for mtl_fwd, count in mtl_fwds.items()
            ])
            opp_fwd_df.to_parquet(opp_fwd_file, compression='zstd', index=False)
            logger.info(f"Saved opponent forwards vs MTL matrix with {len(opp_fwd_df)} matchups")
        
        # Save opponent defense vs MTL matrix
        if hasattr(self, 'opp_defense_vs_mtl'):
            opp_def_file = output_path / 'opp_defense_vs_mtl.parquet'
            opp_def_df = pd.DataFrame([
                {'opp_defense': opp_def, 'mtl_forward': mtl_fwd, 'matchups': count}
                for opp_def, mtl_fwds in self.opp_defense_vs_mtl.items()
                for mtl_fwd, count in mtl_fwds.items()
            ])
            opp_def_df.to_parquet(opp_def_file, compression='zstd', index=False)
            logger.info(f"Saved opponent defense vs MTL matrix with {len(opp_def_df)} matchups")
        
        # Save line combinations
        combos = self.get_line_combinations()
        combos['forwards'].to_parquet(output_path / 'mtl_forward_combos.parquet', index=False)
        combos['defense'].to_parquet(output_path / 'mtl_defense_pairs.parquet', index=False)
        logger.info("Saved line combinations and defense pairs")


# Main DataProcessor class for compatibility with training engine
class DataProcessor(PlayByPlayProcessor):
    """Main data processor with predictive chain capabilities"""
    
    def __init__(self, data_path: Optional[Path] = None, player_mapping_path: Optional[Path] = None):
        # Use default paths if not provided
        if data_path is None:
            data_path = Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/raw/mtl_play_by_play')
        if player_mapping_path is None:
            # Use the new player_ids.csv file by default
            player_mapping_path = Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/dim/player_ids.csv')
        
        super().__init__(data_path, player_mapping_path)
        
        # Initialize additional tracking for compatibility
        self.player_shift_lengths = {}
        
        # NEW: Enhanced matchup tracking with recency
        self.current_game_date = None
        self.current_opponent = None
        
    def process_game(self, game_file: Path) -> List[DeploymentEvent]:
        """Process game and extract predictive patterns"""
        
        events = super().process_game(game_file)
        
        # Store shift lengths for feature engineering
        if hasattr(self, 'player_shift_lengths_temp'):
            self.player_shift_lengths.update(self.player_shift_lengths_temp)
        
        return events
    
    def get_shift_data(self) -> Dict[str, Dict]:
        """Extract comprehensive shift data including predictive patterns"""
        
        shift_summary = {
            'avg_shift_lengths': {},
            'total_shifts': {},
            'shift_distributions': {},
            'rest_patterns': self.extract_predictive_patterns()
        }
        
        # Calculate shift statistics
        for player, shifts in self.player_shift_lengths.items():
            if shifts:
                shift_summary['avg_shift_lengths'][player] = np.mean(shifts)
                shift_summary['total_shifts'][player] = len(shifts)
                shift_summary['shift_distributions'][player] = shifts
        
        return shift_summary
    
    def _event_to_dict(self, event: DeploymentEvent) -> Dict:
        """Convert DeploymentEvent to dictionary for DataFrame (enhanced version)."""
        # Robust team-level aggregates using medians with minimum contributors
        def robust_aggregate(values: Dict[str, float]) -> Optional[float]:
            arr = np.array(list(values.values()), dtype=float)
            if arr.size == 0:
                return None
            # Filter NaNs and negligible values (<1s treated as missing)
            arr = arr[~np.isnan(arr)]
            arr = arr[arr > 1.0]
            if arr.size < 2:
                return None
            return float(np.median(arr))

        return {
            'game_id': event.game_id,
            'event_id': event.event_id,
            'period': event.period,
            'period_time': event.period_time,
            'game_time': event.game_time,
            'game_seconds': event.game_seconds,
            'game_bucket': event.game_bucket,
            'is_period_late': event.is_period_late,
            'is_game_late': event.is_game_late,
            'is_late_pk': event.is_late_pk,
            'is_late_pp': event.is_late_pp,
            'is_close_and_late': event.is_close_and_late,
            'zone_start': event.zone_start,
            'strength_state': event.strength_state,
            'score_differential': event.score_differential,
            'time_bucket': event.time_bucket,
            'stoppage_type': event.stoppage_type,
            'home_team': event.home_team,
            'away_team': event.away_team,
            'last_change_team': event.last_change_team,
            'opponent_team': event.opponent_team,  # TEAM-AWARE: Include opponent team in DataFrame
            'season': event.season,  # Per-season roster tracking
            'decision_role': event.decision_role,
            'mtl_forwards': '|'.join(event.mtl_forwards) if event.mtl_forwards else '',
            'mtl_defense': '|'.join(event.mtl_defense) if event.mtl_defense else '',
            'opp_forwards': '|'.join(event.opp_forwards) if event.opp_forwards else '',
            'opp_defense': '|'.join(event.opp_defense) if event.opp_defense else '',
            'mtl_goalie': event.mtl_goalie,
            'opp_goalie': event.opp_goalie,
            'mtl_has_last_change': event.last_change_team == 'MTL',
            'opp_has_last_change': event.last_change_team != 'MTL',
            # Team-level rest aggregates (robust medians; None if <2 contributors)
            'mtl_avg_rest': robust_aggregate(event.mtl_time_since_last),
            'opp_avg_rest': robust_aggregate(event.opp_time_since_last),
            'mtl_min_rest': (float(np.min([v for v in event.mtl_time_since_last.values() if not np.isnan(v) and v > 1.0]))
                             if len([v for v in event.mtl_time_since_last.values() if not np.isnan(v) and v > 1.0]) >= 2 else None),
            'opp_min_rest': (float(np.min([v for v in event.opp_time_since_last.values() if not np.isnan(v) and v > 1.0]))
                             if len([v for v in event.opp_time_since_last.values() if not np.isnan(v) and v > 1.0]) >= 2 else None),
            # Persist per-player dual rest maps for auditability
            'mtl_rest_real_map': json.dumps(event.mtl_rest_real) if event.mtl_rest_real else None,
            'mtl_rest_game_map': json.dumps(event.mtl_rest_game) if event.mtl_rest_game else None,
            'opp_rest_real_map': json.dumps(event.opp_rest_real) if event.opp_rest_real else None,
            'opp_rest_game_map': json.dumps(event.opp_rest_game) if event.opp_rest_game else None
        }
    
    def _save_player_matchup_patterns(self, output_path: Path) -> None:
        """
        Save player-vs-player matchup patterns with format version v2.1
        
        Saves:
        1. Global player matchup counts
        2. Last-change-aware matchup patterns
        3. Situation-specific matchup patterns
        4. Metadata for backward compatibility
        """
        import json
        
        # Prepare data for serialization with format version
        matchup_data = {
            'format_version': '2.1',  # Player-vs-player matchup format
            'creation_timestamp': pd.Timestamp.now().isoformat(),
            'total_global_matchups': len(self.player_matchup_counts),
            'total_last_change_matchups': len(self.last_change_player_matchups),
            'total_situation_matchups': len(self.situation_player_matchups),
            
            # Convert tuple keys to strings for JSON serialization
            'global_matchup_counts': {
                f"{key[0]}__vs__{key[1]}": count 
                for key, count in self.player_matchup_counts.items()
            },
            
            'last_change_matchup_counts': {
                f"{key[0]}__vs__{key[1]}__lc_{key[2]}__tm_{key[3]}": count 
                for key, count in self.last_change_player_matchups.items()
            },
            
            'situation_matchup_counts': {
                f"{key[0]}__vs__{key[1]}__sit_{situation}": count
                for key, situation_dict in self.situation_player_matchups.items()
                for situation, count in situation_dict.items()
            },
            # MTL-side matrices
            'mtl_response_matrix': getattr(self, 'mtl_response_matrix', {}),
            'mtl_vs_opp_forwards': getattr(self, 'mtl_vs_opp_forwards', {}),
            'mtl_defense_vs_opp_forwards': getattr(self, 'mtl_defense_vs_opp_forwards', {})
        }
        
        # Save as JSON with compression
        matchup_patterns_file = output_path / 'player_matchup_patterns_v2.1.json'
        with open(matchup_patterns_file, 'w') as f:
            json.dump(matchup_data, f, indent=2, default=str)
        
        logger.info(f"Saved player-vs-player matchup patterns v2.1:")
        logger.info(f"  - {len(self.player_matchup_counts)} global matchups")
        logger.info(f"  - {len(self.last_change_player_matchups)} last-change matchups")
        logger.info(f"  - {len(self.situation_player_matchups)} situation-specific matchups")
        logger.info(f"  - File: {matchup_patterns_file}")
    
    def load_player_matchup_patterns(self, input_path: Path) -> bool:
        """
        Load player-vs-player matchup patterns with backward compatibility
        
        Returns:
            bool: True if patterns were loaded successfully
        """
        import json
        
        # Try to load v2.1 format first
        v21_file = input_path / 'player_matchup_patterns_v2.1.json'
        if v21_file.exists():
            try:
                with open(v21_file, 'r') as f:
                    data = json.load(f)
                
                # Validate format version
                if data.get('format_version') != '2.1':
                    logger.warning(f"Unexpected format version: {data.get('format_version')}")
                    return False
                
                # Restore tuple keys from string format
                self.player_matchup_counts.clear()
                for key_str, count in data.get('global_matchup_counts', {}).items():
                    parts = key_str.split('__vs__')
                    if len(parts) == 2:
                        key = (parts[0], parts[1])
                        self.player_matchup_counts[key] = float(count)
                
                self.last_change_player_matchups.clear()
                for key_str, count in data.get('last_change_matchup_counts', {}).items():
                    # Parse: "player1__vs__player2__lc_team__tm_team"
                    parts = key_str.split('__')
                    if len(parts) >= 6:  # player1, vs, player2, lc_team, tm_team
                        key = (parts[0], parts[2], parts[3][3:], parts[4][3:])  # Remove lc_ and tm_ prefixes
                        self.last_change_player_matchups[key] = float(count)
                
                self.situation_player_matchups.clear()
                for key_str, count in data.get('situation_matchup_counts', {}).items():
                    # Parse: "player1__vs__player2__sit_situation" -> nested structure
                    parts = key_str.split('__')
                    if len(parts) >= 4:
                        player_pair = (parts[0], parts[2])  # (mtl_player, opp_player)
                        situation = parts[3][4:]  # Remove sit_ prefix
                        self.situation_player_matchups[player_pair][situation] = float(count)
                
                logger.info(f"Loaded player-vs-player matchup patterns v2.1:")
                logger.info(f"  - {len(self.player_matchup_counts)} global matchups")
                logger.info(f"  - {len(self.last_change_player_matchups)} last-change matchups")
                logger.info(f"  - {len(self.situation_player_matchups)} situation-specific matchups")
                
                return True
                
            except Exception as e:
                logger.error(f"Error loading player matchup patterns v2.1: {e}")
                return False
        
        logger.info("No player-vs-player matchup patterns found to load")
        return False


