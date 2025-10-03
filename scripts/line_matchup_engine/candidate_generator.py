"""
HeartBeat Candidate Generator for Line Deployments
Generates realistic deployment candidates based on historical patterns
Professional-grade implementation for NHL analytics with Markov rotation priors
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
import logging
from pathlib import Path
from scipy.special import softmax
import pickle

logger = logging.getLogger(__name__)

@dataclass
class Candidate:
    """Represents a potential deployment candidate"""
    forwards: List[str]
    defense: List[str]
    probability_prior: float = 1.0  # Prior probability based on historical usage (after softmax)
    fatigue_score: float = 0.0
    chemistry_score: float = 0.0
    matchup_prior: float = 0.0  # Player-vs-player matchup familiarity score
    log_prior: float = 0.0  # Log-space prior before softmax normalization
    
    def to_dict(self) -> Dict:
        return {
            'forwards': self.forwards,
            'defense': self.defense,
            'probability_prior': self.probability_prior,
            'fatigue_score': self.fatigue_score,
            'chemistry_score': self.chemistry_score,
            'matchup_prior': self.matchup_prior
        }
    
    @property
    def key(self) -> str:
        """Unique identifier for this candidate"""
        return f"{'|'.join(sorted(self.forwards))}_{'|'.join(sorted(self.defense))}"


class CandidateGenerator:
    """
    Generates realistic deployment candidates for line matchup prediction
    Based on historical patterns, availability, and game situation
    Enhanced with Markov rotation priors and stochastic sampling
    """
    
    def __init__(self, historical_data: Optional[pd.DataFrame] = None):
        
        # Historical line combinations
        self.forward_combinations = Counter()
        self.defense_pairs = Counter()
        self.full_deployments = Counter()
        
        # Player pools by position
        self.forwards_pool = set()
        self.defense_pool = set()
        self.goalies_pool = set()
        
        # Special teams units
        self.powerplay_units = Counter()
        self.penalty_kill_units = Counter()
        
        # Chemistry and compatibility scores
        self.player_chemistry = defaultdict(float)
        
        # Coach tendencies
        self.coach_patterns = {
            'defensive_zone_starts': defaultdict(int),
            'offensive_zone_starts': defaultdict(int),
            'late_game_protecting': defaultdict(int),
            'late_game_trailing': defaultdict(int)
        }
        
        # Late-trust tracking for high-leverage situations
        self.late_trust_combinations = defaultdict(float)  # deployment_key -> late_usage_frequency
        self.trusted_late_players = set()  # players frequently used in late situations
        
        # NEW: Markov rotation priors - ρ_{k→j} with Dirichlet smoothing
        # Tracks probability of transitioning from deployment k to deployment j
        self.rotation_transitions = defaultdict(lambda: defaultdict(float))
        self.rotation_counts = defaultdict(int)
        
        # LAST-CHANGE-AWARE: Flattened tactical rotation priors with tuple keys
        # Format: (team, opponent, last_change_status, prev_deployment, next_deployment) -> prob
        # Example: ('MTL', 'TOR', 'MTL_has_change', 'Line1_D1', 'Line2_D2') -> 0.35
        # This captures: "How does MTL deploy vs TOR when MTL has last change?"
        self.last_change_rotation_transitions = defaultdict(float)  # Flattened with tuple keys
        self.last_change_rotation_counts = defaultdict(int)         # Flattened with tuple keys
        
        self.dirichlet_alpha = 0.25  # Smoothing parameter for sparse transitions
        
        # PLAYER-VS-PLAYER: Matchup priors for candidate evaluation
        # Loaded from data processor's serialized patterns - standardized flat structure
        self.player_matchup_counts = defaultdict(float)  # (mtl_player, opp_player) -> weighted_count
        self.last_change_player_matchups = defaultdict(float)  # (mtl_player, opp_player, last_change_team, team_making_change) -> weighted_count
        self.situation_player_matchups = defaultdict(lambda: defaultdict(float))  # (mtl_player, opp_player) -> {situation -> weighted_count}
        
        # TEAM-LAST-CHANGE MATRICES: Optional priors for MTL decision scenarios
        # Populated from DataProcessor serialization when available
        self.mtl_response_matrix = defaultdict(lambda: defaultdict(float))  # opp_lineup_key -> mtl_response_key -> weight
        self.mtl_vs_opp_forwards = defaultdict(lambda: defaultdict(float))  # mtl_fwd -> opp_fwd -> weight
        self.mtl_defense_vs_opp_forwards = defaultdict(lambda: defaultdict(float))  # mtl_def -> opp_fwd -> weight
        
        # Configuration for matchup prior computation
        self.enable_matchup_priors = True  # Toggle for matchup prior influence
        self.matchup_prior_weight = 0.15   # Weight for blending matchup priors
        self.min_matchup_threshold = 1.0   # Minimum matchup count to consider
        
        # NEW: Rare line tracking for stochastic sampling
        self.line_frequencies = Counter()
        self.rare_threshold = 5  # Lines seen less than this are "rare"
        self.sampling_temperature = 1.5  # Controls sampling distribution
        
        # NEW: Second unit tracking for special teams
        self.pp_second_units = Counter()
        self.pk_second_units = Counter()
        
        # PLAYER-LEVEL PROPENSITIES: Individual player deployment frequencies
        # Enables dynamic composition when exact line combos not in historical data
        self.player_deployment_counts = Counter()  # player_id -> deployment_count
        self.player_zone_preferences = defaultdict(lambda: defaultdict(int))  # player_id -> {zone -> count}
        
        # ========================================================================
        # ENHANCED MULTI-LAYER SITUATIONAL PROFILING
        # ========================================================================
        
        # PLAYER-LEVEL: Comprehensive situational deployment propensities
        self.player_by_strength = defaultdict(lambda: defaultdict(int))  # player_id -> {strength -> count}
        self.player_by_score_state = defaultdict(lambda: defaultdict(int))  # player_id -> {leading/tied/trailing -> count}
        self.player_by_game_phase = defaultdict(lambda: defaultdict(int))  # player_id -> {early/middle/late -> count}
        self.player_by_period = defaultdict(lambda: defaultdict(int))  # player_id -> {period -> count}
        self.player_rest_profile = defaultdict(lambda: {
            'rest_values': [],  # List of rest times when deployed
            'total_deployments': 0,
            'short_rest_count': 0,  # Deployed with <40s rest
            'long_rest_count': 0    # Deployed with >90s rest
        })
        self.player_leverage_trust = defaultdict(lambda: {
            'late_period_deployments': 0,  # Period time >= 17:00
            'late_game_deployments': 0,    # Game time >= 55:00
            'close_game_deployments': 0,   # Score diff <= 1
            'pk_late_deployments': 0,      # PK + late period
            'pp_late_deployments': 0,      # PP + late period
            'total_late_situations': 0,
            'total_close_situations': 0
        })
        
        # LINE-LEVEL: Forward trio situational patterns
        self.line_by_strength = defaultdict(lambda: defaultdict(int))  # fwd_key -> {strength -> count}
        self.line_by_zone = defaultdict(lambda: defaultdict(int))  # fwd_key -> {zone -> count}
        self.line_by_score_state = defaultdict(lambda: defaultdict(int))  # fwd_key -> {score_state -> count}
        self.line_by_game_phase = defaultdict(lambda: defaultdict(int))  # fwd_key -> {phase -> count}
        self.line_leverage_usage = defaultdict(lambda: {
            'late_period': 0,
            'late_game': 0,
            'close_game': 0,
            'total_deployments': 0
        })
        
        # PAIRING-LEVEL: Defense duo situational patterns
        self.pairing_by_strength = defaultdict(lambda: defaultdict(int))  # def_key -> {strength -> count}
        self.pairing_by_zone = defaultdict(lambda: defaultdict(int))  # def_key -> {zone -> count}
        self.pairing_by_score_state = defaultdict(lambda: defaultdict(int))  # def_key -> {score_state -> count}
        self.pairing_leverage_usage = defaultdict(lambda: {
            'late_period': 0,
            'late_game': 0,
            'close_game': 0,
            'total_deployments': 0
        })
        
        # TEAM-LEVEL: Coaching tendency profiles (by team)
        self.team_strength_tendencies = defaultdict(lambda: defaultdict(int))  # team -> {strength -> count}
        self.team_zone_tendencies = defaultdict(lambda: defaultdict(int))  # team -> {zone -> count}
        self.team_score_tendencies = defaultdict(lambda: defaultdict(int))  # team -> {score_state -> count}
        self.team_rotation_speed = defaultdict(lambda: {
            'short_shifts': 0,  # <30s shifts
            'medium_shifts': 0,  # 30-60s shifts
            'long_shifts': 0,    # >60s shifts
            'avg_rest': []       # List of rest times
        })
        
        if historical_data is not None:
            self.learn_from_history(historical_data)
    
    def _dict_to_candidate(self, cand: Dict) -> Candidate:
        """Convert dict candidate to Candidate dataclass, preserving matchup_prior if present."""
        if isinstance(cand, Candidate):
            return cand
        return Candidate(
            forwards=cand.get('forwards', []),
            defense=cand.get('defense', []),
            probability_prior=cand.get('probability_prior', 1.0),
            fatigue_score=cand.get('fatigue_score', 0.0),
            chemistry_score=cand.get('chemistry_score', 0.0),
            matchup_prior=cand.get('matchup_prior', 0.0)
        )
    
    def _normalize_zone(self, zone_value) -> str:
        """Normalize zone values to standard format (oz/nz/dz)"""
        if not zone_value or pd.isna(zone_value):
            return 'nz'
        
        zone_str = str(zone_value).lower().strip()
        
        # Map various zone formats to standard
        if zone_str in ['oz', 'offensive', 'off', 'o']:
            return 'oz'
        elif zone_str in ['dz', 'defensive', 'def', 'd']:
            return 'dz'
        elif zone_str in ['nz', 'neutral', 'neu', 'n', 'center', 'centre']:
            return 'nz'
        else:
            # Default to neutral zone for unknown values
            logger.debug(f"Unknown zone value '{zone_value}' normalized to 'nz'")
            return 'nz'
    
    def learn_from_history(self, data: pd.DataFrame):
        """Learn deployment patterns from historical data for ALL teams (MTL + opponents)"""
        
        logger.info(f"Learning from {len(data)} historical deployments")
        
        # Separate events by who has last change
        if 'opp_has_last_change' in data.columns:
            opp_last_change_events = data[data['opp_has_last_change'] == True]
        else:
            # Fallback if column doesn't exist
            opp_last_change_events = data  # Use all events
        
        if 'mtl_has_last_change' in data.columns:
            mtl_last_change_events = data[data['mtl_has_last_change'] == True]
        else:
            # Fallback if column doesn't exist  
            mtl_last_change_events = data  # Use all events
        
        logger.info(f"Opponent last change events: {len(opp_last_change_events)}")
        logger.info(f"MTL last change events: {len(mtl_last_change_events)}")
        
        # NEW: Learn Markov rotation sequences
        self._learn_rotation_sequences(data)
        
        # ========================================================================
        # LEARN FROM MTL DEPLOYMENTS (when MTL has last change)
        # ========================================================================
        for _, row in mtl_last_change_events.iterrows():
            # Parse MTL deployment (MTL has last change, so they're deciding)
            mtl_forwards = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_defense = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            
            # Extract situational context
            zone_raw = row.get('zone_start', 'nz')
            zone = self._normalize_zone(zone_raw)
            strength = row.get('strength_state', '5v5')
            score_diff = row.get('score_differential', 0)
            period = row.get('period', 2)
            period_time = row.get('periodTime', 600.0)
            game_seconds = (period - 1) * 1200.0 + period_time
            
            # Classify situational context
            score_state = 'leading' if score_diff > 0 else ('trailing' if score_diff < 0 else 'tied')
            game_phase = 'early' if game_seconds < 1200 else ('late' if game_seconds >= 2400 else 'middle')
            is_late_period = period_time >= 1020.0  # >= 17:00 in period
            is_late_game = game_seconds >= 3300.0   # >= 55:00 total game time
            is_close_game = abs(score_diff) <= 1
            
            # Track TEAM-LEVEL tendencies for MTL
            self.team_strength_tendencies['MTL'][strength] += 1
            self.team_zone_tendencies['MTL'][zone] += 1
            self.team_score_tendencies['MTL'][score_state] += 1
            
            if len(mtl_forwards) >= 3 and len(mtl_defense) >= 2:
                # Track MTL forward combinations
                fwd_key = '|'.join(sorted(mtl_forwards[:3]))
                self.forward_combinations[fwd_key] += 1
                
                # Track MTL defense pairs
                def_key = '|'.join(sorted(mtl_defense[:2]))
                self.defense_pairs[def_key] += 1
                
                # Track full deployments
                full_key = f"{fwd_key}_{def_key}"
                self.full_deployments[full_key] += 1
                
                # Track situational patterns with zone normalization
                deploy_key = f"{fwd_key}_{def_key}"
                if zone == 'dz':
                    self.coach_patterns['defensive_zone_starts'][deploy_key] += 1
                elif zone == 'oz':
                    self.coach_patterns['offensive_zone_starts'][deploy_key] += 1
                
                # LINE-LEVEL: Track forward trio situational patterns
                self.line_by_strength[fwd_key][strength] += 1
                self.line_by_zone[fwd_key][zone] += 1
                self.line_by_score_state[fwd_key][score_state] += 1
                self.line_by_game_phase[fwd_key][game_phase] += 1
                self.line_leverage_usage[fwd_key]['total_deployments'] += 1
                if is_late_period:
                    self.line_leverage_usage[fwd_key]['late_period'] += 1
                if is_late_game:
                    self.line_leverage_usage[fwd_key]['late_game'] += 1
                if is_close_game:
                    self.line_leverage_usage[fwd_key]['close_game'] += 1
                
                # PAIRING-LEVEL: Track defense duo situational patterns
                self.pairing_by_strength[def_key][strength] += 1
                self.pairing_by_zone[def_key][zone] += 1
                self.pairing_by_score_state[def_key][score_state] += 1
                self.pairing_leverage_usage[def_key]['total_deployments'] += 1
                if is_late_period:
                    self.pairing_leverage_usage[def_key]['late_period'] += 1
                if is_late_game:
                    self.pairing_leverage_usage[def_key]['late_game'] += 1
                if is_close_game:
                    self.pairing_leverage_usage[def_key]['close_game'] += 1
                
                # PLAYER-LEVEL: Track comprehensive individual patterns
                for player in mtl_forwards[:3] + mtl_defense[:2]:
                    # Basic propensities
                    self.player_deployment_counts[player] += 1
                    self.player_zone_preferences[player][zone] += 1
                    
                    # Situational propensities
                    self.player_by_strength[player][strength] += 1
                    self.player_by_score_state[player][score_state] += 1
                    self.player_by_game_phase[player][game_phase] += 1
                    self.player_by_period[player][period] += 1
                    
                    # Rest profile tracking (if available)
                    player_rest = row.get(f'mtl_time_since_last', {}).get(player, None) if isinstance(row.get('mtl_time_since_last'), dict) else None
                    if player_rest is not None and player_rest > 0:
                        self.player_rest_profile[player]['rest_values'].append(player_rest)
                        self.player_rest_profile[player]['total_deployments'] += 1
                        if player_rest < 40.0:
                            self.player_rest_profile[player]['short_rest_count'] += 1
                        elif player_rest > 90.0:
                            self.player_rest_profile[player]['long_rest_count'] += 1
                    
                    # Leverage/trust tracking
                    if is_late_period or is_late_game:
                        self.player_leverage_trust[player]['total_late_situations'] += 1
                        if is_late_period:
                            self.player_leverage_trust[player]['late_period_deployments'] += 1
                        if is_late_game:
                            self.player_leverage_trust[player]['late_game_deployments'] += 1
                        
                        # Special teams + late combinations
                        if '4v5' in strength or 'penaltyKill' in strength:
                            self.player_leverage_trust[player]['pk_late_deployments'] += 1
                        elif '5v4' in strength or 'powerPlay' in strength:
                            self.player_leverage_trust[player]['pp_late_deployments'] += 1
                    
                    if is_close_game:
                        self.player_leverage_trust[player]['total_close_situations'] += 1
                        self.player_leverage_trust[player]['close_game_deployments'] += 1
            
            # Update player pools with MTL players
            self.forwards_pool.update(mtl_forwards)
            self.defense_pool.update(mtl_defense)
            
            # Track MTL special teams
            if len(mtl_forwards) >= 3:
                fwd_key = '|'.join(sorted(mtl_forwards[:3]))
                if '5v4' in strength or 'powerPlay' in strength:
                    self.powerplay_units[fwd_key] += 1
                elif '4v5' in strength or 'penaltyKill' in strength:
                    self.penalty_kill_units[fwd_key] += 1
        
        # ========================================================================
        # LEARN FROM OPPONENT DEPLOYMENTS (when opponent has last change)
        # ========================================================================
        for _, row in opp_last_change_events.iterrows():
            # Parse opponent deployment (their response)
            opp_forwards = row['opp_forwards'].split('|') if row['opp_forwards'] else []
            opp_defense = row['opp_defense'].split('|') if row['opp_defense'] else []
            
            # Parse our lineup (what they're responding to)
            mtl_forwards = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_defense = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            
            # Extract situational context
            zone_raw = row.get('zone_start', 'nz')
            zone = self._normalize_zone(zone_raw)
            strength = row.get('strength_state', '5v5')
            score_diff = row.get('score_differential', 0)
            period = row.get('period', 2)
            period_time = row.get('periodTime', 600.0)
            game_seconds = (period - 1) * 1200.0 + period_time
            opponent_team = row.get('opponent_team', 'UNK')
            
            # Classify situational context (from opponent's perspective: flip score)
            opp_score_diff = -score_diff  # Opponent sees flipped score
            score_state = 'leading' if opp_score_diff > 0 else ('trailing' if opp_score_diff < 0 else 'tied')
            game_phase = 'early' if game_seconds < 1200 else ('late' if game_seconds >= 2400 else 'middle')
            is_late_period = period_time >= 1020.0  # >= 17:00 in period
            is_late_game = game_seconds >= 3300.0   # >= 55:00 total game time
            is_close_game = abs(opp_score_diff) <= 1
            
            # Track TEAM-LEVEL tendencies for opponent
            if opponent_team != 'UNK':
                self.team_strength_tendencies[opponent_team][strength] += 1
                self.team_zone_tendencies[opponent_team][zone] += 1
                self.team_score_tendencies[opponent_team][score_state] += 1
            
            if len(opp_forwards) >= 3 and len(opp_defense) >= 2:
                # Track opponent forward combinations
                fwd_key = '|'.join(sorted(opp_forwards[:3]))
                self.forward_combinations[fwd_key] += 1
                
                # Track opponent defense pairs
                def_key = '|'.join(sorted(opp_defense[:2]))
                self.defense_pairs[def_key] += 1
                
                # Track full deployments
                full_key = f"{fwd_key}_{def_key}"
                self.full_deployments[full_key] += 1
                
                # Track situational responses with zone normalization
                deploy_key = f"{fwd_key}_{def_key}"
                if zone == 'dz':
                    self.coach_patterns['defensive_zone_starts'][deploy_key] += 1
                elif zone == 'oz':
                    self.coach_patterns['offensive_zone_starts'][deploy_key] += 1
                
                # LINE-LEVEL: Track forward trio situational patterns
                self.line_by_strength[fwd_key][strength] += 1
                self.line_by_zone[fwd_key][zone] += 1
                self.line_by_score_state[fwd_key][score_state] += 1
                self.line_by_game_phase[fwd_key][game_phase] += 1
                self.line_leverage_usage[fwd_key]['total_deployments'] += 1
                if is_late_period:
                    self.line_leverage_usage[fwd_key]['late_period'] += 1
                if is_late_game:
                    self.line_leverage_usage[fwd_key]['late_game'] += 1
                if is_close_game:
                    self.line_leverage_usage[fwd_key]['close_game'] += 1
                
                # PAIRING-LEVEL: Track defense duo situational patterns
                self.pairing_by_strength[def_key][strength] += 1
                self.pairing_by_zone[def_key][zone] += 1
                self.pairing_by_score_state[def_key][score_state] += 1
                self.pairing_leverage_usage[def_key]['total_deployments'] += 1
                if is_late_period:
                    self.pairing_leverage_usage[def_key]['late_period'] += 1
                if is_late_game:
                    self.pairing_leverage_usage[def_key]['late_game'] += 1
                if is_close_game:
                    self.pairing_leverage_usage[def_key]['close_game'] += 1
                
                # PLAYER-LEVEL: Track comprehensive individual patterns
                for player in opp_forwards[:3] + opp_defense[:2]:
                    # Basic propensities
                    self.player_deployment_counts[player] += 1
                    self.player_zone_preferences[player][zone] += 1
                    
                    # Situational propensities
                    self.player_by_strength[player][strength] += 1
                    self.player_by_score_state[player][score_state] += 1
                    self.player_by_game_phase[player][game_phase] += 1
                    self.player_by_period[player][period] += 1
                    
                    # Rest profile tracking (if available)
                    player_rest = row.get(f'opp_time_since_last', {}).get(player, None) if isinstance(row.get('opp_time_since_last'), dict) else None
                    if player_rest is not None and player_rest > 0:
                        self.player_rest_profile[player]['rest_values'].append(player_rest)
                        self.player_rest_profile[player]['total_deployments'] += 1
                        if player_rest < 40.0:
                            self.player_rest_profile[player]['short_rest_count'] += 1
                        elif player_rest > 90.0:
                            self.player_rest_profile[player]['long_rest_count'] += 1
                    
                    # Leverage/trust tracking
                    if is_late_period or is_late_game:
                        self.player_leverage_trust[player]['total_late_situations'] += 1
                        if is_late_period:
                            self.player_leverage_trust[player]['late_period_deployments'] += 1
                        if is_late_game:
                            self.player_leverage_trust[player]['late_game_deployments'] += 1
                        
                        # Special teams + late combinations
                        if '4v5' in strength or 'penaltyKill' in strength:
                            self.player_leverage_trust[player]['pk_late_deployments'] += 1
                        elif '5v4' in strength or 'powerPlay' in strength:
                            self.player_leverage_trust[player]['pp_late_deployments'] += 1
                    
                    if is_close_game:
                        self.player_leverage_trust[player]['total_close_situations'] += 1
                        self.player_leverage_trust[player]['close_game_deployments'] += 1
            
            # Update player pools
            self.forwards_pool.update(opp_forwards)
            self.defense_pool.update(opp_defense)
            
            # Track special teams responses
            if len(opp_forwards) >= 3:
                fwd_key = '|'.join(sorted(opp_forwards[:3]))
            if '5v4' in strength or 'powerPlay' in strength:
                self.powerplay_units[fwd_key] += 1
            elif '4v5' in strength or 'penaltyKill' in strength:
                self.penalty_kill_units[fwd_key] += 1
        
        # ========================================================================
        # ALSO LEARN FROM GENERAL PATTERNS (weighted, both MTL and opponents)
        # ========================================================================
        for _, row in data.iterrows():
            # Learn from opponent deployments
            opp_forwards = row['opp_forwards'].split('|') if row['opp_forwards'] else []
            opp_defense = row['opp_defense'].split('|') if row['opp_defense'] else []
            
            if len(opp_forwards) >= 3 and len(opp_defense) >= 2:
                fwd_key = '|'.join(sorted(opp_forwards[:3]))
                def_key = '|'.join(sorted(opp_defense[:2]))
                full_key = f"{fwd_key}_{def_key}"
                
                # Add to general patterns (with lower weight for non-response events)
                has_last_change = row.get('opp_has_last_change', False) if 'opp_has_last_change' in data.columns else False
                weight = 1.0 if has_last_change else 0.5
                self.forward_combinations[fwd_key] += weight
                self.defense_pairs[def_key] += weight
                self.full_deployments[full_key] += weight
                
                # PLAYER-LEVEL: Track individual players (weighted)
                zone = self._normalize_zone(row.get('zone_start', 'nz'))
                for player in opp_forwards[:3] + opp_defense[:2]:
                    self.player_deployment_counts[player] += weight
                    self.player_zone_preferences[player][zone] += weight
            
            # Learn from MTL deployments (general patterns)
            mtl_forwards = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_defense = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            
            if len(mtl_forwards) >= 3 and len(mtl_defense) >= 2:
                fwd_key = '|'.join(sorted(mtl_forwards[:3]))
                def_key = '|'.join(sorted(mtl_defense[:2]))
                full_key = f"{fwd_key}_{def_key}"
                
                # Add to general patterns (with weight based on last change)
                has_last_change = row.get('mtl_has_last_change', False) if 'mtl_has_last_change' in data.columns else False
                weight = 1.0 if has_last_change else 0.5
                self.forward_combinations[fwd_key] += weight
                self.defense_pairs[def_key] += weight
                self.full_deployments[full_key] += weight
                
                # PLAYER-LEVEL: Track MTL individual players (weighted)
                zone = self._normalize_zone(row.get('zone_start', 'nz'))
                for player in mtl_forwards[:3] + mtl_defense[:2]:
                    self.player_deployment_counts[player] += weight
                    self.player_zone_preferences[player][zone] += weight
        
        # Calculate chemistry scores
        self._calculate_chemistry_scores()
        
        logger.info(f"Learned {len(self.forward_combinations)} forward combinations")
        logger.info(f"Learned {len(self.defense_pairs)} defense pairs")
        logger.info(f"Learned {len(self.player_deployment_counts)} individual player propensities")
        logger.info(f"Player pools: {len(self.forwards_pool)} F, {len(self.defense_pool)} D")
        
        # ENHANCED: Log multi-layer situational profiling
        logger.info(f"ENHANCED Situational Profiling:")
        logger.info(f"  Player-level: {len(self.player_by_strength)} players with strength patterns")
        logger.info(f"  Player-level: {len(self.player_by_score_state)} players with score-state patterns")
        logger.info(f"  Player-level: {len(self.player_rest_profile)} players with rest profiles")
        logger.info(f"  Player-level: {len(self.player_leverage_trust)} players with leverage-trust data")
        logger.info(f"  Line-level: {len(self.line_by_strength)} lines with situational patterns")
        logger.info(f"  Pairing-level: {len(self.pairing_by_strength)} pairings with situational patterns")
        logger.info(f"  Team-level: {len(self.team_strength_tendencies)} teams with coaching tendencies")
        
        # CRITICAL: Compute data-driven normalization factors after learning
        self._compute_normalization_factors()
    
    def _compute_normalization_factors(self):
        """
        Compute robust normalization factors from learned patterns using 95th percentile.
        This ensures proper scaling regardless of data volume (MTL with 3 seasons vs opponents).
        
        Uses 95th percentile instead of max to be robust to outliers.
        """
        logger.info("Computing data-driven normalization factors...")
        
        # Initialize normalization factors dictionary
        self.norm_factors = {}
        
        # 1. LINE HISTORY: Distribution of full deployment counts
        if self.full_deployments:
            line_history_values = [np.log1p(count) for count in self.full_deployments.values()]
            self.norm_factors['line_history'] = np.percentile(line_history_values, 95)
            logger.info(f"  Line history norm: {self.norm_factors['line_history']:.3f} (95th percentile of {len(line_history_values)} deployments)")
        else:
            self.norm_factors['line_history'] = 1.0
        
        # 2. PLAYER PROPENSITIES: Distribution of individual player deployment counts
        if self.player_deployment_counts:
            player_prop_values = [np.log1p(count) for count in self.player_deployment_counts.values()]
            self.norm_factors['player_propensity'] = np.percentile(player_prop_values, 95)
            logger.info(f"  Player propensity norm: {self.norm_factors['player_propensity']:.3f} (95th percentile of {len(player_prop_values)} players)")
        else:
            self.norm_factors['player_propensity'] = 1.0
        
        # 3. SITUATIONAL PATTERNS: Distribution of situational deployment counts
        # Collect all situational counts (strength, zone, score, etc.)
        situational_values = []
        
        # From player-level situational patterns
        for player_dict in self.player_by_strength.values():
            situational_values.extend([np.log1p(c) for c in player_dict.values()])
        for player_dict in self.player_by_score_state.values():
            situational_values.extend([np.log1p(c) for c in player_dict.values()])
        
        # From line-level situational patterns
        for line_dict in self.line_by_strength.values():
            situational_values.extend([np.log1p(c) for c in line_dict.values()])
        for line_dict in self.line_by_zone.values():
            situational_values.extend([np.log1p(c) for c in line_dict.values()])
        for line_dict in self.line_by_score_state.values():
            situational_values.extend([np.log1p(c) for c in line_dict.values()])
        
        # From pairing-level situational patterns
        for pairing_dict in self.pairing_by_strength.values():
            situational_values.extend([np.log1p(c) for c in pairing_dict.values()])
        for pairing_dict in self.pairing_by_zone.values():
            situational_values.extend([np.log1p(c) for c in pairing_dict.values()])
        
        if situational_values:
            self.norm_factors['situational'] = np.percentile(situational_values, 95)
            logger.info(f"  Situational pattern norm: {self.norm_factors['situational']:.3f} (95th percentile of {len(situational_values)} observations)")
        else:
            self.norm_factors['situational'] = 1.0
        
        # 4. CHEMISTRY: Distribution of pairwise chemistry scores
        if self.player_chemistry:
            chemistry_values = list(self.player_chemistry.values())
            self.norm_factors['chemistry'] = np.percentile(chemistry_values, 95)
            logger.info(f"  Chemistry norm: {self.norm_factors['chemistry']:.3f} (95th percentile of {len(chemistry_values)} pairs)")
        else:
            self.norm_factors['chemistry'] = 1.0
        
        # 5. ZONE PREFERENCES: Distribution of zone-specific deployments
        zone_pref_values = []
        for player_dict in self.player_zone_preferences.values():
            zone_pref_values.extend([np.log1p(c) for c in player_dict.values()])
        
        if zone_pref_values:
            self.norm_factors['zone'] = np.percentile(zone_pref_values, 95)
            logger.info(f"  Zone preference norm: {self.norm_factors['zone']:.3f} (95th percentile of {len(zone_pref_values)} observations)")
        else:
            self.norm_factors['zone'] = 1.0
        
        # 6. LEVERAGE/TRUST: Already in reasonable range (0-1), use small constant
        self.norm_factors['late_trust'] = 2.0  # Expect leverage scores 0-2
        
        # 7. MATCHUP PRIORS: Already normalized, use small constant
        self.norm_factors['matchup'] = 2.0
        
        # 8. FATIGUE: Already small (negative), no normalization needed
        self.norm_factors['fatigue'] = 1.0
        
        # Ensure no zero factors (would cause division by zero)
        for key in self.norm_factors:
            if self.norm_factors[key] <= 0:
                logger.warning(f"Zero normalization factor detected for {key}, setting to 1.0")
                self.norm_factors[key] = 1.0
        
        logger.info("Normalization factors computed successfully")
    
    def _calculate_chemistry_scores(self):
        """Calculate pairwise chemistry based on co-occurrence"""
        
        # Forward chemistry
        for combo_str, count in self.forward_combinations.items():
            players = combo_str.split('|')
            for i in range(len(players)):
                for j in range(i + 1, len(players)):
                    pair_key = tuple(sorted([players[i], players[j]]))
                    # Chemistry proportional to log of co-occurrence
                    self.player_chemistry[pair_key] += np.log1p(count)
        
        # Defense chemistry
        for pair_str, count in self.defense_pairs.items():
            players = pair_str.split('|')
            if len(players) >= 2:
                pair_key = tuple(sorted(players[:2]))
                self.player_chemistry[pair_key] += np.log1p(count)
        
        # Normalize chemistry scores
        if self.player_chemistry:
            max_chem = max(self.player_chemistry.values())
            for key in self.player_chemistry:
                self.player_chemistry[key] /= max_chem
    
    def _compute_player_level_prior(self, 
                                   forwards: List[str], 
                                   defense: List[str], 
                                   zone: str = 'nz',
                                   strength: str = '5v5',
                                   score_diff: int = 0,
                                   period: int = 1,
                                   time_remaining: float = 1200,
                                   opponent_deployment: Optional[List[str]] = None) -> float:
        """
        STATE-OF-THE-ART: Compute deployment prior using ALL multi-layer profiling factors
        
        Considers simultaneously (not as fallbacks):
        - Overall deployment frequency
        - Situational patterns (strength, score, period, zone)
        - Forward line chemistry
        - Defense pairing history
        - Player-vs-player matchup history (if opponent known)
        - Rest/fatigue propensity
        - Late-game trust factor
        
        Args:
            forwards: List of forward player IDs
            defense: List of defense player IDs
            zone: Zone context (oz/nz/dz)
            strength: Game strength (5v5, 5v4, etc.)
            score_diff: Score differential
            period: Current period
            time_remaining: Seconds remaining in period
            opponent_deployment: Opponent's predicted deployment (for matchup scoring)
            
        Returns:
            Composite prior probability (0-1 range after softmax normalization)
        """
        
        # Initialize score components
        scores = {
            'base_deployment': 0.0,
            'strength_situation': 0.0,
            'score_situation': 0.0,
            'period_pattern': 0.0,
            'zone_preference': 0.0,
            'line_chemistry': 0.0,
            'pairing_chemistry': 0.0,
            'matchup_advantage': 0.0,
            'late_game_trust': 0.0
        }
        
        # 1. BASE DEPLOYMENT FREQUENCY (weight: 0.15)
        for player in forwards + defense:
            freq = self.player_deployment_counts.get(player, 0)
            if freq > 0:
                scores['base_deployment'] += np.log1p(freq)
        if len(forwards) + len(defense) > 0:
            scores['base_deployment'] /= (len(forwards) + len(defense))
        
        # 2. STRENGTH-SPECIFIC DEPLOYMENT (weight: 0.20)
        for player in forwards + defense:
            strength_data = self.player_by_strength.get(player, {})
            strength_freq = strength_data.get(strength, 0)
            if strength_freq > 0:
                scores['strength_situation'] += np.log1p(strength_freq)
        if len(forwards) + len(defense) > 0:
            scores['strength_situation'] /= (len(forwards) + len(defense))
        
        # 3. SCORE STATE DEPLOYMENT (weight: 0.15)
        score_state = 'tied' if score_diff == 0 else ('leading' if score_diff > 0 else 'trailing')
        for player in forwards + defense:
            score_data = self.player_by_score_state.get(player, {})
            score_freq = score_data.get(score_state, 0)
            if score_freq > 0:
                scores['score_situation'] += np.log1p(score_freq)
        if len(forwards) + len(defense) > 0:
            scores['score_situation'] /= (len(forwards) + len(defense))
        
        # 4. PERIOD-SPECIFIC PATTERNS (weight: 0.10)
        for player in forwards + defense:
            period_data = self.player_by_period.get(player, {})
            period_freq = period_data.get(period, 0)
            if period_freq > 0:
                scores['period_pattern'] += np.log1p(period_freq)
        if len(forwards) + len(defense) > 0:
            scores['period_pattern'] /= (len(forwards) + len(defense))
        
        # 5. ZONE PREFERENCE (weight: 0.10)
        for player in forwards + defense:
            zone_data = self.player_zone_preferences.get(player, {})
            zone_freq = zone_data.get(zone, 0)
            total_zone = sum(zone_data.values())
            if total_zone > 0:
                zone_pref = zone_freq / total_zone
                scores['zone_preference'] += zone_pref
        if len(forwards) + len(defense) > 0:
            scores['zone_preference'] /= (len(forwards) + len(defense))
        
        # 6. FORWARD LINE CHEMISTRY (weight: 0.10)
        if len(forwards) >= 2:
            for i, p1 in enumerate(forwards):
                for p2 in forwards[i+1:]:
                    combo_key = tuple(sorted([p1, p2]))
                    chemistry = self.player_chemistry.get(combo_key, 0)
                    if chemistry > 0:
                        scores['line_chemistry'] += np.log1p(chemistry)
            # Normalize by number of pairs
            n_pairs = len(forwards) * (len(forwards) - 1) / 2
            if n_pairs > 0:
                scores['line_chemistry'] /= n_pairs
        
        # 7. DEFENSE PAIRING CHEMISTRY (weight: 0.10)
        if len(defense) >= 2:
            pair_key = '|'.join(sorted(defense))
            pairing_count = self.defense_pairs.get(pair_key, 0)
            if pairing_count > 0:
                scores['pairing_chemistry'] = np.log1p(pairing_count)
        
        # 8. PLAYER-VS-PLAYER MATCHUP ADVANTAGE (weight: 0.05)
        if opponent_deployment:
            for our_player in forwards + defense:
                for opp_player in opponent_deployment:
                    matchup_key = (our_player, opp_player)
                    matchup_count = self.player_matchup_counts.get(matchup_key, 0)
                    if matchup_count > 0:
                        scores['matchup_advantage'] += np.log1p(matchup_count)
            if len(forwards) + len(defense) > 0 and len(opponent_deployment) > 0:
                scores['matchup_advantage'] /= (len(forwards) + len(defense)) * len(opponent_deployment)
        
        # 9. LATE-GAME TRUST (weight: 0.05)
        if period >= 3 and time_remaining < 300:  # Last 5 minutes of 3rd period
            late_game_key = f"period_{period}_late"
            for player in forwards + defense:
                period_data = self.player_by_period.get(player, {})
                late_freq = period_data.get(late_game_key, 0)
                if late_freq > 0:
                    scores['late_game_trust'] += np.log1p(late_freq)
            if len(forwards) + len(defense) > 0:
                scores['late_game_trust'] /= (len(forwards) + len(defense))
        
        # WEIGHTED COMPOSITE SCORE
        weights = {
            'base_deployment': 0.15,
            'strength_situation': 0.20,
            'score_situation': 0.15,
            'period_pattern': 0.10,
            'zone_preference': 0.10,
            'line_chemistry': 0.10,
            'pairing_chemistry': 0.10,
            'matchup_advantage': 0.05,
            'late_game_trust': 0.05
        }
        
        composite_score = sum(scores[k] * weights[k] for k in scores.keys())
        
        # Return raw score (will be normalized via softmax later)
        return composite_score

    def generate_candidates(self,
                           game_situation: Dict,
                           available_players: Dict[str, List[str]],
                           rest_times: Dict[str, float],
                           max_candidates: int = 15,
                           previous_deployment: Optional[str] = None,
                           use_stochastic_sampling: bool = False,
                           opponent_team: Optional[str] = None,
                           last_change_team: Optional[str] = None,
                           team_making_change: str = 'MTL',
                           target_n_forwards: Optional[int] = None,
                           target_n_defense: Optional[int] = None) -> List[Candidate]:
        """
        Generate deployment candidates for current game situation
        Enhanced with Markov rotation priors and stochastic sampling
        
        Args:
            game_situation: Dict with keys like 'zone', 'strength', 'score_diff', 'period', 'time'
            available_players: Dict with 'forwards' and 'defense' lists of available player IDs
            rest_times: Dict mapping player_id to seconds since last shift
            max_candidates: Maximum number of candidates to return
            previous_deployment: Previous deployment key for Markov transitions
            use_stochastic_sampling: Enable rare-line boosting for training
            opponent_team: Opponent team name for matchup priors
            last_change_team: Team with last change advantage
            team_making_change: Team making the deployment decision
            target_n_forwards: Override number of forwards (for incomplete deployments)
            target_n_defense: Override number of defense (for incomplete deployments)
        
        Returns:
            List of Candidate objects sorted by likelihood
        """
        
        candidates = []
        
        # Extract situation
        zone = game_situation.get('zone', 'nz')
        strength = game_situation.get('strength', '5v5')
        score_diff = game_situation.get('score_diff', 0)
        period = game_situation.get('period', 1)
        time_remaining = game_situation.get('time_remaining', 1200)
        
        # Determine required players based on strength (allow override for incomplete deployments)
        if target_n_forwards is not None and target_n_defense is not None:
            n_forwards, n_defense = target_n_forwards, target_n_defense
            logger.debug(f"Using target formation: {n_forwards}F + {n_defense}D")
        else:
           n_forwards, n_defense = self._get_position_requirements(strength)
        
        # Generate based on strategy
        if strength in ['5v4', 'powerPlay']:
            candidates.extend(self._generate_powerplay_candidates(
                available_players, rest_times, n_forwards, n_defense
            ))
        elif strength in ['4v5', 'penaltyKill']:
            candidates.extend(self._generate_penalty_kill_candidates(
                available_players, rest_times, n_forwards, n_defense
            ))
        else:
            # Regular strength - use full situational context
            # Use exhaustive generation for validation (deterministic), sampling for training (stochastic)
            candidates.extend(self._generate_regular_candidates(
                available_players=available_players,
                rest_times=rest_times,
                n_forwards=n_forwards,
                n_defense=n_defense,
                zone=zone,
                strength=strength,
                score_diff=score_diff,
                period=period,
                time_remaining=time_remaining,
                opponent_deployment=None,  # Will be set in two-step prediction
                use_exhaustive=not use_stochastic_sampling  # Exhaustive for validation, sampling for training
            ))
        
        # NO MORE variations or emergency candidates!
        # We generate ALL possible combinations systematically,
        # so there's no need for supplementary generation methods.
        
        # Score and rank candidates
        scored_candidates = self._score_candidates(
            candidates, game_situation, rest_times, opponent_team, last_change_team, team_making_change
        )
        
        # Apply stochastic sampling BEFORE Markov boost (for probability consistency)
        if use_stochastic_sampling:
            scored_candidates = self.stochastic_rare_line_sample(
                scored_candidates, 
                n_samples=max_candidates * 2,  # Sample more then filter
                include_rare=True
            )
        
        # Apply LAST-CHANGE-AWARE rotation priors AFTER sampling
        if previous_deployment:
            scored_candidates = self.apply_markov_rotation_prior(
                scored_candidates, previous_deployment, opponent_team, 
                last_change_team, team_making_change
            )
        
        # Sort by prior probability (highest first)
        scored_candidates.sort(key=lambda c: c.probability_prior, reverse=True)
        
        # DIAGNOSTIC: Log generation stats
        n_fwd = len(scored_candidates[0].forwards) if scored_candidates else 0
        n_def = len(scored_candidates[0].defense) if scored_candidates else 0
        
        logger.debug(f"Generated and scored {len(scored_candidates)} unique {n_fwd}F+{n_def}D candidates")
        logger.debug(f"Returning top {min(max_candidates, len(scored_candidates))} by situational probability")
        
        # Return top N candidates by score
        # No deduplication needed - itertools.combinations guarantees uniqueness!
        return scored_candidates[:max_candidates]
    
    def _get_position_requirements(self, strength: str, allow_flexible: bool = False) -> Tuple[int, int]:
        """
        Get number of forwards and defense required for strength state
        
        Args:
            strength: Game situation strength
            allow_flexible: If True, returns a range rather than exact requirements
        
        Returns:
            Tuple of (n_forwards, n_defense) if allow_flexible=False
            Otherwise returns the standard requirements
        """
        
        requirements = {
            '5v5': (3, 2),
            'evenStrength': (3, 2),
            '5v4': (4, 1),  # Power play
            'powerPlay': (4, 1),
            '4v5': (2, 2),  # Penalty kill
            'penaltyKill': (2, 2),
            '4v4': (2, 2),
            '3v3': (2, 1),
            '6v5': (4, 2),  # Extra attacker
            '5v6': (3, 2),  # Opponent extra attacker
            # Flexible formations for incomplete data
            '4v3': (3, 1),
            '3v4': (2, 2),
            '3v2': (2, 1),
            '2v3': (1, 2),
            '2v2': (1, 1),
        }
        
        return requirements.get(strength, (3, 2))
    
    def _generate_regular_candidates(self,
                                    available_players: Dict,
                                    rest_times: Dict,
                                    n_forwards: int,
                                    n_defense: int,
                                    zone: str,
                                    strength: str = '5v5',
                                    score_diff: int = 0,
                                    period: int = 1,
                                    time_remaining: float = 1200,
                                    opponent_deployment: Optional[List[str]] = None,
                                    use_exhaustive: bool = False) -> List[Candidate]:
        """
        STATE-OF-THE-ART: DETERMINISTIC candidate generation with STOCHASTIC scoring
        
        Philosophy:
        - Candidate generation: EXHAUSTIVE (validation) or SAMPLED (training)
        - Candidate scoring: PROBABILISTIC and INTELLIGENT (multi-factor situational reasoning)
        - Model prediction: LEARNED and ADAPTIVE (neural network weights factors dynamically)
        
        Args:
            use_exhaustive: If True, generate ALL possible combinations (for validation).
                           If False, use efficient sampling (for training).
        """
        
        from itertools import combinations
        import random
        
        candidates = []
        available_forwards = available_players.get('forwards', [])
        available_defense = available_players.get('defense', [])
        
        if len(available_forwards) < n_forwards or len(available_defense) < n_defense:
            return candidates
        
        # STEP 1: Score each available player for this specific situation
        forward_scores = {}
        for player in available_forwards:
            score = 0.0
            
            # Base deployment frequency
            score += np.log1p(self.player_deployment_counts.get(player, 0)) * 0.2
            
            # Strength-specific deployment
            strength_data = self.player_by_strength.get(player, {})
            score += np.log1p(strength_data.get(strength, 0)) * 0.25
            
            # Score state deployment
            score_state = 'tied' if score_diff == 0 else ('leading' if score_diff > 0 else 'trailing')
            score_data = self.player_by_score_state.get(player, {})
            score += np.log1p(score_data.get(score_state, 0)) * 0.15
            
            # Period-specific
            period_data = self.player_by_period.get(player, {})
            score += np.log1p(period_data.get(period, 0)) * 0.15
            
            # Zone preference
            zone_data = self.player_zone_preferences.get(player, {})
            zone_freq = zone_data.get(zone, 0)
            total_zone = sum(zone_data.values())
            if total_zone > 0:
                score += (zone_freq / total_zone) * 0.15
            
            # Rest/fatigue consideration
            rest = rest_times.get(player, 90)
            if rest > 60:
                score += 0.1  # Bonus for well-rested
            elif rest < 30:
                score -= 0.2  # Penalty for tired
            
            forward_scores[player] = max(0.01, score)  # Ensure positive
        
        defense_scores = {}
        for player in available_defense:
            score = 0.0
            
            # Base deployment frequency
            score += np.log1p(self.player_deployment_counts.get(player, 0)) * 0.2
            
            # Strength-specific deployment
            strength_data = self.player_by_strength.get(player, {})
            score += np.log1p(strength_data.get(strength, 0)) * 0.25
            
            # Score state deployment
            score_state = 'tied' if score_diff == 0 else ('leading' if score_diff > 0 else 'trailing')
            score_data = self.player_by_score_state.get(player, {})
            score += np.log1p(score_data.get(score_state, 0)) * 0.15
            
            # Period-specific
            period_data = self.player_by_period.get(player, {})
            score += np.log1p(period_data.get(period, 0)) * 0.15
            
            # Zone preference
            zone_data = self.player_zone_preferences.get(player, {})
            zone_freq = zone_data.get(zone, 0)
            total_zone = sum(zone_data.values())
            if total_zone > 0:
                score += (zone_freq / total_zone) * 0.15
            
            # Rest/fatigue consideration
            rest = rest_times.get(player, 90)
            if rest > 60:
                score += 0.1  # Bonus for well-rested
            elif rest < 30:
                score -= 0.2  # Penalty for tired
            
            defense_scores[player] = max(0.01, score)
        
        # STEP 2: Generate candidates based on mode
        if use_exhaustive:
            # VALIDATION: Exhaustive generation - ALL possible combinations
            # Guarantees truth is in candidates if players are in roster
            forward_combinations = list(combinations(available_forwards, n_forwards))
            defense_combinations = list(combinations(available_defense, n_defense))
            
            for fwd_combo in forward_combinations:
                for def_combo in defense_combinations:
                    prior_score = self._compute_player_level_prior(
                        forwards=list(fwd_combo),
                        defense=list(def_combo),
                        zone=zone,
                        strength=strength,
                        score_diff=score_diff,
                        period=period,
                        time_remaining=time_remaining,
                        opponent_deployment=opponent_deployment
                    )
                    
                    candidates.append(Candidate(
                        forwards=list(fwd_combo),
                        defense=list(def_combo),
                        probability_prior=prior_score
                    ))
        else:
            # TRAINING: Efficient sampling - generate diverse sample quickly
            target_samples = 150
            seen_combos = set()
            attempts = 0
            
            while len(candidates) < target_samples and attempts < target_samples * 5:
                attempts += 1
                
                fwd_combo = tuple(random.sample(available_forwards, n_forwards))
                def_combo = tuple(random.sample(available_defense, n_defense))
                
                combo_key = (tuple(sorted(fwd_combo)), tuple(sorted(def_combo)))
                if combo_key in seen_combos:
                    continue
                seen_combos.add(combo_key)
                
                prior_score = self._compute_player_level_prior(
                    forwards=list(fwd_combo),
                    defense=list(def_combo),
                    zone=zone,
                    strength=strength,
                    score_diff=score_diff,
                    period=period,
                    time_remaining=time_remaining,
                    opponent_deployment=opponent_deployment
                )
                
                candidates.append(Candidate(
                    forwards=list(fwd_combo),
                    defense=list(def_combo),
                    probability_prior=prior_score
                ))
        
        return candidates
    
    def _generate_powerplay_candidates(self,
                                      available_players: Dict,
                                      rest_times: Dict,
                                      n_forwards: int,
                                      n_defense: int) -> List[Candidate]:
        """Generate power play unit candidates"""
        
        candidates = []
        available_forwards = available_players.get('forwards', [])
        available_defense = available_players.get('defense', [])
        
        # Use historical PP units
        for unit_str, count in self.powerplay_units.most_common(5):
            players = unit_str.split('|')
            
            if all(p in available_forwards for p in players):
                # PP typically uses 4F-1D
                defense = [d for d in available_defense 
                          if rest_times.get(d, 120) > 30][:n_defense]
                
                if len(defense) >= n_defense:
                    candidate = Candidate(
                        forwards=players[:n_forwards],
                        defense=defense,
                        probability_prior=np.log1p(count) * 1.5  # Boost PP units
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _generate_penalty_kill_candidates(self,
                                         available_players: Dict,
                                         rest_times: Dict,
                                         n_forwards: int,
                                         n_defense: int) -> List[Candidate]:
        """Generate penalty kill unit candidates"""
        
        candidates = []
        available_forwards = available_players.get('forwards', [])
        available_defense = available_players.get('defense', [])
        
        # Use historical PK units
        for unit_str, count in self.penalty_kill_units.most_common(5):
            players = unit_str.split('|')
            
            if len(players) >= n_forwards:
                forwards = [p for p in players[:n_forwards] 
                           if p in available_forwards]
                
                if len(forwards) == n_forwards:
                    # Strong defensive pairing for PK
                    defense = [d for d in available_defense 
                              if rest_times.get(d, 120) > 30][:n_defense]
                    
                    if len(defense) >= n_defense:
                        candidate = Candidate(
                            forwards=forwards,
                            defense=defense,
                            probability_prior=np.log1p(count) * 1.3  # Boost PK units
                        )
                        candidates.append(candidate)
        
        return candidates
    
    def _generate_variations(self,
                           base_candidates: List[Candidate],
                           available_players: Dict,
                           rest_times: Dict) -> List[Candidate]:
        """Generate variations of top candidates by swapping players"""
        
        variations = []
        available_forwards = available_players.get('forwards', [])
        available_defense = available_players.get('defense', [])
        
        for candidate in base_candidates:
            # Try swapping one forward
            for i, fwd in enumerate(candidate.forwards):
                for alt_fwd in available_forwards:
                    if alt_fwd not in candidate.forwards and rest_times.get(alt_fwd, 120) > 30:
                        new_forwards = candidate.forwards.copy()
                        new_forwards[i] = alt_fwd
                        
                        variation = Candidate(
                            forwards=new_forwards,
                            defense=candidate.defense.copy(),
                            probability_prior=candidate.probability_prior * 0.8
                        )
                        variations.append(variation)
                        break
            
            # Try swapping one defenseman
            for i, def_player in enumerate(candidate.defense):
                for alt_def in available_defense:
                    if alt_def not in candidate.defense and rest_times.get(alt_def, 120) > 30:
                        new_defense = candidate.defense.copy()
                        new_defense[i] = alt_def
                        
                        variation = Candidate(
                            forwards=candidate.forwards.copy(),
                            defense=new_defense,
                            probability_prior=candidate.probability_prior * 0.8
                        )
                        variations.append(variation)
                        break
        
        return variations[:5]  # Limit variations
    
    def _generate_emergency_candidates(self,
                                      available_players: Dict,
                                      rest_times: Dict,
                                      n_forwards: int,
                                      n_defense: int) -> List[Candidate]:
        """
        Generate emergency candidates for unusual situations
        Enhanced to generate many combinations using itertools for flexible formations
        """
        from itertools import combinations
        
        candidates = []
        available_forwards = available_players.get('forwards', [])
        available_defense = available_players.get('defense', [])
        
        # Check if we have enough players
        if len(available_forwards) < n_forwards or len(available_defense) < n_defense:
            return candidates
        
        # Generate many random combinations using random sampling
        # This is especially important for flexible formations (2F+1D, etc.)
        max_combinations = 50  # Generate up to 50 random combinations
        
        # MEMORY-SAFE: Use random sampling instead of exhaustive combinations
        # to avoid memory exhaustion with large rosters
        import random
        
        # Generate random forward combinations by sampling
        forward_combos = []
        for _ in range(min(max_combinations, 100)):  # Try up to 100 times
            if len(available_forwards) >= n_forwards:
                combo = tuple(random.sample(available_forwards, n_forwards))
                if combo not in forward_combos:  # Avoid duplicates
                    forward_combos.append(combo)
                if len(forward_combos) >= max_combinations:
                    break
        
        # Generate random defense combinations by sampling
        defense_combos = []
        for _ in range(min(max_combinations, 100)):  # Try up to 100 times
            if len(available_defense) >= n_defense:
                combo = tuple(random.sample(available_defense, n_defense))
                if combo not in defense_combos:  # Avoid duplicates
                    defense_combos.append(combo)
                if len(defense_combos) >= max_combinations:
                    break
        
        # Safety check
        if not forward_combos or not defense_combos:
            return candidates
        
        # Create candidates by pairing forward and defense combinations
        for i in range(min(max_combinations, len(forward_combos))):
            fwd_combo = forward_combos[i]
            def_combo = defense_combos[i % len(defense_combos)]
            
            candidate = Candidate(
                forwards=list(fwd_combo),
                defense=list(def_combo),
                probability_prior=0.1  # Low prior for emergency
            )
            candidates.append(candidate)
            
            if len(candidates) >= max_combinations:
                break
        
        return candidates
    
    def _score_candidates(self,
                         candidates: List[Candidate],
                         game_situation: Dict,
                         rest_times: Dict,
                         opponent_team: Optional[str] = None,
                         last_change_team: Optional[str] = None,
                         team_making_change: str = 'MTL') -> List[Candidate]:
        """
        Score candidates using simultaneous multi-factor weighting
        All factors are computed and weighted together, not as cascading fallbacks
        
        Factors:
        - Line history prior (from historical combinations)
        - Player-level propensities (individual deployment frequencies)
        - Chemistry (pairwise co-occurrence)
        - Zone preferences (line-level + player-level)
        - Fatigue penalties (rest times)
        - Late-game trust (high-leverage situations)
        - Matchup priors (player-vs-player history)
        """
        
        # DEBUG: Check if we have learned patterns for this team
        if not hasattr(self, '_mtl_scoring_debug_count'):
            self._mtl_scoring_debug_count = 0
        
        if team_making_change == 'MTL' and len(candidates) > 0 and self._mtl_scoring_debug_count < 5:
            sample_player = candidates[0].forwards[0] if candidates[0].forwards else None
            logger.warning(f"MTL SCORING DEBUG [{self._mtl_scoring_debug_count}]:")
            logger.warning(f"  Team making change: {team_making_change}")
            logger.warning(f"  Candidates to score: {len(candidates)}")
            logger.warning(f"  Sample player: {sample_player}")
            logger.warning(f"  Player in deployment_counts: {sample_player in self.player_deployment_counts}")
            if sample_player in self.player_deployment_counts:
                logger.warning(f"  Sample player deployment count: {self.player_deployment_counts[sample_player]}")
            logger.warning(f"  Total learned player propensities: {len(self.player_deployment_counts)}")
            logger.warning(f"  Total learned line combinations: {len(self.full_deployments)}")
            logger.warning(f"  Total learned forward combinations: {len(self.forward_combinations)}")
            logger.warning(f"  Total learned defense pairs: {len(self.defense_pairs)}")
            self._mtl_scoring_debug_count += 1
        
        # Extract game situation variables
        strength = game_situation.get('strength', '5v5')
        zone = game_situation.get('zone', 'nz')
        
        # High-leverage situation flags
        is_period_late = game_situation.get('is_period_late', False)
        is_game_late = game_situation.get('is_game_late', False)
        is_late_pk = game_situation.get('is_late_pk', False)
        is_late_pp = game_situation.get('is_late_pp', False)
        is_close_and_late = game_situation.get('is_close_and_late', False)
        
        scored = []
        
        for candidate in candidates:
            deploy_key = f"{'|'.join(sorted(candidate.forwards))}_{'|'.join(sorted(candidate.defense))}"
            all_players = candidate.forwards + candidate.defense
            
            # ========================================================================
            # SIMULTANEOUS MULTI-FACTOR SCORING (all factors weighted together)
            # ========================================================================
            
            # FACTOR 1: Line history prior (from historical exact combinations)
            line_history_score = 0.0
            if deploy_key in self.full_deployments:
                line_history_score = np.log1p(self.full_deployments[deploy_key])
            
            # FACTOR 2: Player-level propensities (individual deployment frequencies)
            player_propensity_score = 0.0
            player_count = 0
            for player in all_players:
                if player in self.player_deployment_counts:
                    player_propensity_score += np.log1p(self.player_deployment_counts[player])
                    player_count += 1
            if player_count > 0:
                player_propensity_score /= player_count  # Normalize by player count
            
            # FACTOR 2A: ENHANCED Situational player propensities
            situational_player_score = 0.0
            
            # Extract current game situation
            period = game_situation.get('period', 2)
            score_diff = game_situation.get('score_differential', 0)
            game_seconds = game_situation.get('game_seconds', 1200.0)
            score_state = 'leading' if score_diff > 0 else ('trailing' if score_diff < 0 else 'tied')
            game_phase = 'early' if game_seconds < 1200 else ('late' if game_seconds >= 2400 else 'middle')
            
            for player in all_players:
                # Strength-specific deployment propensity
                if strength in self.player_by_strength.get(player, {}):
                    strength_count = self.player_by_strength[player][strength]
                    total_count = sum(self.player_by_strength[player].values())
                    strength_ratio = strength_count / total_count if total_count > 0 else 0
                    situational_player_score += np.log1p(strength_ratio * 10)  # Scale for visibility
                
                # Score-state deployment propensity
                if score_state in self.player_by_score_state.get(player, {}):
                    score_count = self.player_by_score_state[player][score_state]
                    total_count = sum(self.player_by_score_state[player].values())
                    score_ratio = score_count / total_count if total_count > 0 else 0
                    situational_player_score += np.log1p(score_ratio * 10)
                
                # Game-phase deployment propensity
                if game_phase in self.player_by_game_phase.get(player, {}):
                    phase_count = self.player_by_game_phase[player][game_phase]
                    total_count = sum(self.player_by_game_phase[player].values())
                    phase_ratio = phase_count / total_count if total_count > 0 else 0
                    situational_player_score += np.log1p(phase_ratio * 10)
                
                # Rest profile matching (can player handle current rest?)
                player_current_rest = rest_times.get(player, 120)
                if player in self.player_rest_profile:
                    profile = self.player_rest_profile[player]
                    if len(profile['rest_values']) > 5:  # Need sufficient data
                        median_rest = np.median(profile['rest_values'])
                        # Boost if player is used to similar rest levels
                        rest_match = 1.0 - min(abs(player_current_rest - median_rest) / 60.0, 1.0)
                        situational_player_score += rest_match
                        
                        # Penalize if short rest but player not used to it
                        if player_current_rest < 40 and profile['short_rest_count'] < 3:
                            situational_player_score -= 0.5  # Penalize players not used to short rest
                
                # Leverage/trust in high-stakes situations
                if (is_period_late or is_game_late or is_close_and_late) and player in self.player_leverage_trust:
                    trust = self.player_leverage_trust[player]
                    if trust['total_late_situations'] > 5:  # Need sufficient data
                        late_usage_rate = trust['late_period_deployments'] / max(trust['total_late_situations'], 1)
                        situational_player_score += np.log1p(late_usage_rate * 10)
            
            # Normalize by player count
            if len(all_players) > 0:
                situational_player_score /= len(all_players)
            
            # FACTOR 2B: Line-level situational propensities
            fwd_key = '|'.join(sorted(candidate.forwards))
            line_situational_score = 0.0
            
            if fwd_key in self.line_by_strength:
                line_strength_count = self.line_by_strength[fwd_key].get(strength, 0)
                line_total = sum(self.line_by_strength[fwd_key].values())
                if line_total > 0:
                    line_situational_score += np.log1p((line_strength_count / line_total) * 10)
            
            if fwd_key in self.line_by_score_state:
                line_score_count = self.line_by_score_state[fwd_key].get(score_state, 0)
                line_total = sum(self.line_by_score_state[fwd_key].values())
                if line_total > 0:
                    line_situational_score += np.log1p((line_score_count / line_total) * 10)
            
            if fwd_key in self.line_leverage_usage:
                leverage = self.line_leverage_usage[fwd_key]
                if leverage['total_deployments'] > 5:
                    if is_period_late or is_game_late:
                        late_rate = leverage['late_period'] / leverage['total_deployments']
                        line_situational_score += np.log1p(late_rate * 10)
            
            # FACTOR 2C: Pairing-level situational propensities
            def_key = '|'.join(sorted(candidate.defense))
            pairing_situational_score = 0.0
            
            if def_key in self.pairing_by_strength:
                pair_strength_count = self.pairing_by_strength[def_key].get(strength, 0)
                pair_total = sum(self.pairing_by_strength[def_key].values())
                if pair_total > 0:
                    pairing_situational_score += np.log1p((pair_strength_count / pair_total) * 10)
            
            if def_key in self.pairing_by_score_state:
                pair_score_count = self.pairing_by_score_state[def_key].get(score_state, 0)
                pair_total = sum(self.pairing_by_score_state[def_key].values())
                if pair_total > 0:
                    pairing_situational_score += np.log1p((pair_score_count / pair_total) * 10)
            
            # FACTOR 3: Chemistry (pairwise co-occurrence)
            chemistry_score = 0.0
            for i in range(len(all_players)):
                for j in range(i + 1, len(all_players)):
                    pair = tuple(sorted([all_players[i], all_players[j]]))
                    chemistry_score += self.player_chemistry.get(pair, 0.0)
            candidate.chemistry_score = chemistry_score  # Store for later use
            
            # FACTOR 4: Zone preferences (line-level + player-level combined)
            zone_score = 0.0
            # Line-level zone preference
            if zone == 'dz' and deploy_key in self.coach_patterns['defensive_zone_starts']:
                zone_score += np.log1p(self.coach_patterns['defensive_zone_starts'][deploy_key])
            elif zone == 'oz' and deploy_key in self.coach_patterns['offensive_zone_starts']:
                zone_score += np.log1p(self.coach_patterns['offensive_zone_starts'][deploy_key])
            
            # Player-level zone preference (always computed, not fallback)
            player_zone_score = 0.0
            for player in all_players:
                zone_freq = self.player_zone_preferences.get(player, {}).get(zone, 0)
                if zone_freq > 0:
                    player_zone_score += np.log1p(zone_freq)
            zone_score += 0.5 * player_zone_score  # Weight player-level at 50% of line-level
            
            # FACTOR 5: Fatigue penalty (rest times)
            player_rest = [rest_times.get(p, 120) for p in all_players]
            min_rest = np.min(player_rest) if player_rest else 120
            avg_rest = np.mean(player_rest) if player_rest else 120
            fatigue_penalty = np.exp(-min_rest / 60)  # 0=fresh, 1=exhausted
            candidate.fatigue_score = fatigue_penalty  # Store for later use
            
            # FACTOR 6: Late-game trust (high-leverage situations)
            late_trust_score = 0.0
            if is_period_late or is_game_late:
                # Line-level late trust
                if deploy_key in self.late_trust_combinations:
                    late_trust_score += self.late_trust_combinations[deploy_key]
                
                # Player-level trust
                trusted_count = sum(1 for p in all_players if p in self.trusted_late_players)
                late_trust_score += 0.2 * trusted_count
            
            # Special teams high-leverage adjustments
            if is_late_pk:
                late_trust_score += 0.5  # Strong boost for late PK
            if is_late_pp:
                late_trust_score += 0.3  # Moderate boost for late PP
            if is_close_and_late:
                late_trust_score += 0.2 * chemistry_score  # Extra chemistry weight
            
            # FACTOR 7: Player-vs-player matchup prior (when opponent deployment known)
            matchup_score = 0.0
            opponent_players = game_situation.get('current_opponent_players', [])
            if opponent_players and self.enable_matchup_priors:
                matchup_score = self.compute_matchup_prior(
                    candidate_players=all_players,
                    opponent_players=opponent_players,
                    opponent_team=opponent_team,
                    last_change_team=last_change_team,
                    team_making_change=team_making_change,
                    situation=strength
                )
                candidate.matchup_prior = matchup_score  # Store for debugging
            else:
                candidate.matchup_prior = 0.0
            
            # ========================================================================
            # COMBINE ALL FACTORS WITH EXPLICIT WEIGHTS (log-space)
            # ========================================================================
            
            # ROBUST NORMALIZATION: Use data-driven factors computed from learned patterns
            # Each factor is normalized by its 95th percentile from the training data
            # This automatically adapts to data volume (MTL 3 seasons vs opponents 9-18 games)
            
            # Apply data-driven normalization to each factor
            line_history_norm = line_history_score / self.norm_factors['line_history'] if line_history_score > 0 else 0.0
            player_propensity_norm = player_propensity_score / self.norm_factors['player_propensity'] if player_propensity_score > 0 else 0.0
            situational_player_norm = situational_player_score / self.norm_factors['situational'] if situational_player_score > 0 else 0.0
            line_situational_norm = line_situational_score / self.norm_factors['situational'] if line_situational_score > 0 else 0.0
            pairing_situational_norm = pairing_situational_score / self.norm_factors['situational'] if pairing_situational_score > 0 else 0.0
            chemistry_norm = chemistry_score / self.norm_factors['chemistry'] if chemistry_score > 0 else 0.0
            zone_norm = zone_score / self.norm_factors['zone'] if zone_score > 0 else 0.0
            late_trust_norm = late_trust_score / self.norm_factors['late_trust']  # Already in reasonable range
            matchup_norm = matchup_score / self.norm_factors['matchup']  # Already in reasonable range
            fatigue_norm = fatigue_penalty / self.norm_factors['fatigue']  # Keep as-is (already small)
            
            # Weight configuration (tuned for balance across factors)
            w_line_history = 1.5              # Line combination history
            w_player_propensity = 1.2         # Individual player deployment frequency
            w_situational_player = 1.0        # ENHANCED: Situational player propensities
            w_line_situational = 1.0          # ENHANCED: Line situational propensities
            w_pairing_situational = 1.0       # ENHANCED: Pairing situational propensities
            w_chemistry = 0.8                 # Pairwise player chemistry
            w_zone = 0.6                      # Zone preference (line + player)
            w_late_trust = 0.7                # High-leverage situation trust
            w_matchup = 0.5                   # Player-vs-player matchup history
            
            # Fatigue penalty (negative contribution)
            w_fatigue = -2.0                  # Strong penalty for tired players
            
            # Combine NORMALIZED scores in log-space (additive)
            # Now log_prior should be in range [0, ~8] instead of [20, 30]
            log_prior = (
                w_line_history * line_history_norm +
                w_player_propensity * player_propensity_norm +
                w_situational_player * situational_player_norm +
                w_line_situational * line_situational_norm +
                w_pairing_situational * pairing_situational_norm +
                w_chemistry * chemistry_norm +
                w_zone * zone_norm +
                w_late_trust * late_trust_norm +
                w_matchup * matchup_norm +
                w_fatigue * fatigue_norm
            )
            
            # DEBUG: Log MTL candidate scoring BEFORE exp() conversion
            if team_making_change == 'MTL' and len(scored) < 2:
                logger.debug(f"MTL CANDIDATE SCORING (before exp):")
                logger.debug(f"  Players: {all_players[:3]}")
                logger.debug(f"  log_prior: {log_prior:.6f}")
                logger.debug(f"  line_history: {line_history_score:.6f}")
                logger.debug(f"  player_prop: {player_propensity_score:.6f}")
                logger.debug(f"  situational: {situational_player_score:.6f}")
                logger.debug(f"  fatigue: {fatigue_penalty:.6f}")
            
            # Store log_prior for softmax normalization
            candidate.log_prior = log_prior
            scored.append(candidate)
        
        # ========================================================================
        # SOFTMAX NORMALIZATION: Convert log-space scores to valid probabilities
        # ========================================================================
        # This ensures all candidate priors sum to 1.0 (true probability distribution)
        # and handles numerical stability by subtracting max before exp()
        
        if scored:
            # Extract log priors
            log_priors = np.array([c.log_prior for c in scored])
            
            # Numerically stable softmax: subtract max to prevent overflow
            max_log_prior = np.max(log_priors)
            exp_priors = np.exp(log_priors - max_log_prior)
            
            # Normalize to sum to 1.0
            sum_exp_priors = np.sum(exp_priors)
            if sum_exp_priors > 0:
                normalized_priors = exp_priors / sum_exp_priors
            else:
                # Fallback: uniform distribution
                normalized_priors = np.ones(len(scored)) / len(scored)
            
            # Assign normalized priors back to candidates
            for i, candidate in enumerate(scored):
                candidate.probability_prior = normalized_priors[i]
            
            # DEBUG: Log MTL final priors after softmax
            if team_making_change == 'MTL' and len(scored) > 0:
                top_prior = max(c.probability_prior for c in scored)
                avg_prior = np.mean([c.probability_prior for c in scored])
                logger.debug(f"MTL SOFTMAX NORMALIZED PRIORS:")
                logger.debug(f"  Top prior: {top_prior:.6f}")
                logger.debug(f"  Avg prior: {avg_prior:.6f}")
                logger.debug(f"  Sum of priors: {sum(c.probability_prior for c in scored):.6f}")
        
        return scored
    
    def get_top_combinations(self, n: int = 10) -> Dict[str, pd.DataFrame]:
        """Get top forward combinations and defense pairs"""
        
        # Top forward combinations
        fwd_data = []
        for combo, count in self.forward_combinations.most_common(n):
            players = combo.split('|')
            chemistry = sum(self.player_chemistry.get(tuple(sorted([players[i], players[j]])), 0)
                          for i in range(len(players)) 
                          for j in range(i + 1, len(players)))
            fwd_data.append({
                'combination': combo,
                'count': count,
                'chemistry': chemistry
            })
        
        # Top defense pairs
        def_data = []
        for pair, count in self.defense_pairs.most_common(n):
            players = pair.split('|')
            chemistry = self.player_chemistry.get(tuple(sorted(players)), 0) if len(players) >= 2 else 0
            def_data.append({
                'pair': pair,
                'count': count,
                'chemistry': chemistry
            })
        
        return {
            'forwards': pd.DataFrame(fwd_data),
            'defense': pd.DataFrame(def_data)
        }
    
    def _learn_rotation_sequences(self, data: pd.DataFrame):
        """
        Learn Markov rotation priors ρ_{k→j} from deployment sequences
        Tracks how often deployment k is followed by deployment j
        """
        
        logger.info("Learning Markov rotation sequences...")
        
        # Group by game to get sequential deployments
        if 'game_id' in data.columns:
            for game_id, game_data in data.groupby('game_id'):
                game_data = game_data.sort_values('period_time')
                
                prev_deployment = None
                for _, row in game_data.iterrows():
                    # Current deployment
                    opp_fwd = row.get('opp_forwards', '')
                    opp_def = row.get('opp_defense', '')
                    
                    if opp_fwd and opp_def:
                        curr_key = f"{opp_fwd}_{opp_def}"
                        
                        if prev_deployment is not None:
                            # Track transition
                            self.rotation_transitions[prev_deployment][curr_key] += 1
                            self.rotation_counts[prev_deployment] += 1
                        
                        prev_deployment = curr_key
        
        # Normalize to probabilities with Dirichlet smoothing
        for prev_key in self.rotation_transitions:
            total = self.rotation_counts[prev_key]
            n_transitions = len(self.rotation_transitions[prev_key])
            
            if total > 0 and n_transitions > 0:
                # Apply Dirichlet smoothing: add α to each count
                smoothed_total = total + (self.dirichlet_alpha * n_transitions)
                
                for next_key in self.rotation_transitions[prev_key]:
                    raw_count = self.rotation_transitions[prev_key][next_key]  # This is already the raw count
                    smoothed_count = raw_count + self.dirichlet_alpha
                    self.rotation_transitions[prev_key][next_key] = smoothed_count / smoothed_total
        
        logger.info(f"Learned {len(self.rotation_transitions)} rotation patterns")
        
        # LAST-CHANGE-AWARE: Learn tactical rotation patterns
        self._learn_last_change_rotation_sequences(data)
    
    def _learn_last_change_rotation_sequences(self, data: pd.DataFrame):
        """
        LAST-CHANGE-AWARE: Learn deployment patterns based on who has last change advantage
        
        This learns the 4 critical tactical scenarios:
        1. MTL has last change vs [Opponent] → MTL chooses optimal matchups  
        2. MTL doesn't have last change vs [Opponent] → MTL reacts/adapts
        3. [Opponent] has last change vs MTL → Opponent targets MTL weaknesses
        4. [Opponent] doesn't have last change vs MTL → Opponent reacts to MTL
        """
        
        logger.info("Learning last-change-aware rotation sequences...")
        
        # Required columns for last change analysis
        required_cols = ['home_team', 'away_team', 'last_change_team', 'opponent_team', 
                        'mtl_forwards', 'mtl_defense', 'opp_forwards', 'opp_defense']
        
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            logger.warning(f"Missing columns for last-change learning: {missing_cols}")
            return
        
        # Sort by game and time for sequence learning
        if 'game_id' in data.columns and 'game_seconds' in data.columns:
            data_sorted = data.sort_values(['game_id', 'game_seconds'])
        else:
            logger.warning("Cannot sort data for sequence learning - missing game_id/game_seconds")
            return
        
        sequence_count = 0
        
        # Process deployment sequences by game
        for game_id, game_data in data_sorted.groupby('game_id'):
            game_events = game_data.reset_index()
            
            # Learn sequences within this game
            for i in range(len(game_events) - 1):
                current_event = game_events.iloc[i]
                next_event = game_events.iloc[i + 1]
                
                # Extract deployment information
                current_mtl_deployment = self._create_deployment_key(
                    current_event.get('mtl_forwards', '').split('|'),
                    current_event.get('mtl_defense', '').split('|')
                )
                next_mtl_deployment = self._create_deployment_key(
                    next_event.get('mtl_forwards', '').split('|'),
                    next_event.get('mtl_defense', '').split('|')
                )
                
                current_opp_deployment = self._create_deployment_key(
                    current_event.get('opp_forwards', '').split('|'),
                    current_event.get('opp_defense', '').split('|')
                )
                next_opp_deployment = self._create_deployment_key(
                    next_event.get('opp_forwards', '').split('|'),
                    next_event.get('opp_defense', '').split('|')
                )
                
                # Determine teams and last change status
                opponent_team = current_event.get('opponent_team', 'UNK')
                last_change_team = current_event.get('last_change_team', 'UNK')
                
                # Scenario 1 & 2: MTL deployment patterns
                if current_mtl_deployment and next_mtl_deployment:
                    mtl_has_last_change = (last_change_team == 'MTL')
                    last_change_key = 'has_last_change' if mtl_has_last_change else 'no_last_change'
                    
                    # FLATTENED: Record MTL transition pattern with tuple key
                    count_key = ('MTL', opponent_team, last_change_key, current_mtl_deployment)
                    transition_key = ('MTL', opponent_team, last_change_key, current_mtl_deployment, next_mtl_deployment)
                    
                    self.last_change_rotation_counts[count_key] += 1
                    self.last_change_rotation_transitions[transition_key] += 1
                
                # Scenario 3 & 4: Opponent deployment patterns  
                if current_opp_deployment and next_opp_deployment and opponent_team != 'UNK':
                    opp_has_last_change = (last_change_team == opponent_team)
                    last_change_key = 'has_last_change' if opp_has_last_change else 'no_last_change'
                    
                    # FLATTENED: Record opponent transition pattern with tuple key
                    count_key = (opponent_team, 'MTL', last_change_key, current_opp_deployment)
                    transition_key = (opponent_team, 'MTL', last_change_key, current_opp_deployment, next_opp_deployment)
                    
                    self.last_change_rotation_counts[count_key] += 1
                    self.last_change_rotation_transitions[transition_key] += 1
                
                sequence_count += 1
        
        # Apply Dirichlet smoothing to last-change patterns
        self._smooth_last_change_transitions()
        
        logger.info(f"Learned {sequence_count} last-change-aware rotation sequences")
        logger.info(f"Last-change transition patterns learned: {len(self.last_change_rotation_transitions)}")
    
    def _create_deployment_key(self, forwards: List[str], defense: List[str]) -> Optional[str]:
        """Create a consistent key for deployment identification"""
        if not forwards or not defense or any(not p for p in forwards + defense):
            return None
        return f"{'|'.join(sorted([p for p in forwards if p]))}_{'|'.join(sorted([p for p in defense if p]))}"
    
    def _smooth_last_change_transitions(self):
        """Apply Dirichlet smoothing to last-change-aware transition probabilities with flattened structure"""
        
        # Group transitions by their context (team, opponent, last_change_status, prev_deployment)
        context_groups = defaultdict(list)
        
        # Organize transition keys by their context
        for transition_key in self.last_change_rotation_transitions:
            if len(transition_key) == 5:  # (team, opponent, last_change_status, prev_deployment, next_deployment)
                context_key = transition_key[:4]  # (team, opponent, last_change_status, prev_deployment)
                context_groups[context_key].append(transition_key)
        
        # Apply smoothing within each context group
        for context_key, transition_keys in context_groups.items():
            total_count = self.last_change_rotation_counts[context_key]
            
            if total_count > 0:
                # Calculate smoothed total
                num_transitions = len(transition_keys)
                smoothed_total = total_count + (num_transitions * self.dirichlet_alpha)
                
                # Convert raw counts to probabilities with smoothing
                for transition_key in transition_keys:
                    raw_count = self.last_change_rotation_transitions[transition_key]
                    smoothed_count = raw_count + self.dirichlet_alpha
                    self.last_change_rotation_transitions[transition_key] = smoothed_count / smoothed_total
    
    def apply_markov_rotation_prior(self, candidates: List[Candidate], 
                                   previous_deployment: Optional[str] = None,
                                   opponent_team: Optional[str] = None,
                                   last_change_team: Optional[str] = None,
                                   team_making_change: str = 'MTL') -> List[Candidate]:
        """
        LAST-CHANGE-AWARE: Apply rotation priors based on tactical situation
        
        Args:
            candidates: Deployment candidates to score
            previous_deployment: Previous deployment key
            opponent_team: Which opponent team we're facing
            last_change_team: Which team has last change advantage
            team_making_change: Which team is making the deployment ('MTL' or opponent)
        """
        
        if previous_deployment is None:
            return candidates
        
        # Determine last change status for the team making the change
        if last_change_team and opponent_team:
            has_last_change = (last_change_team == team_making_change)
            last_change_key = 'has_last_change' if has_last_change else 'no_last_change'
            
            # HARDENED FALLBACK: Use multi-level fallback policy
            context_key = (team_making_change, opponent_team, last_change_key, previous_deployment)
            
            # Try to get transition probabilities with comprehensive fallback
            transition_probs = self._get_fallback_transition_probs(
                context_key, previous_deployment, opponent_team
            )
            
            if not transition_probs:
                # Even the fallback policy couldn't find patterns - log and return
                logger.warning(
                    f"No rotation patterns available for {team_making_change} vs {opponent_team} "
                    f"({last_change_key}, prev: {previous_deployment})"
                )
                return candidates
        else:
            # No tactical info available - use general rotation patterns with logging
            if previous_deployment in self.rotation_transitions:
                transition_probs = self.rotation_transitions[previous_deployment]
                logger.debug(f"Using general rotation patterns (no tactical context) for {previous_deployment}")
            else:
                logger.warning(f"No rotation patterns available for {previous_deployment} (no tactical context)")
                return candidates
        
        # Apply rotation priors to candidates with detailed logging
        context_desc = f"{team_making_change} vs {opponent_team}" if opponent_team else "general"
        
        for candidate in candidates:
            cand_key = f"{'|'.join(sorted(candidate.forwards))}_{'|'.join(sorted(candidate.defense))}"
            
            if cand_key in transition_probs:
                # Boost probability based on rotation prior
                rotation_boost = transition_probs[cand_key]
                candidate.probability_prior *= (1 + rotation_boost)
                
                logger.debug(f"Applied rotation boost {rotation_boost:.3f} to {cand_key}")
        
        # Log comprehensive statistics about prior application
        self._log_prior_application_stats(candidates, transition_probs, context_desc)
        
        return candidates
    
    def _get_fallback_transition_probs(self, context_key: tuple, previous_deployment: str, 
                                     opponent_team: str = None) -> Dict[str, float]:
        """
        HARDENED FALLBACK POLICY: Multi-level fallback for missing rotation priors
        
        Fallback hierarchy:
        1. Exact tactical context (team, opponent, last_change, prev_deployment)
        2. Same opponent, different last_change status
        3. Same team, different opponent
        4. General rotation patterns (no tactical context)
        5. Uniform distribution (last resort)
        
        Args:
            context_key: (team, opponent, last_change_status, prev_deployment)
            previous_deployment: Previous deployment key
            opponent_team: Opponent team for logging
            
        Returns:
            Dict mapping next_deployment -> probability
        """
        team, opponent, last_change_status, prev_deploy = context_key
        fallback_used = None
        transition_probs = {}
        
        # LEVEL 1: Exact tactical context (already tried in caller)
        for transition_key, prob in self.last_change_rotation_transitions.items():
            if (len(transition_key) == 5 and transition_key[:4] == context_key):
                next_deployment = transition_key[4]
                transition_probs[next_deployment] = prob
        
        if transition_probs:
            logger.debug(f"Fallback Level 1: Exact tactical context for {team} vs {opponent}")
            return transition_probs
        
        # LEVEL 2: Same opponent, different last_change status
        alternate_last_change = 'no_last_change' if last_change_status == 'has_last_change' else 'has_last_change'
        alternate_context = (team, opponent, alternate_last_change, prev_deploy)
        
        for transition_key, prob in self.last_change_rotation_transitions.items():
            if (len(transition_key) == 5 and transition_key[:4] == alternate_context):
                next_deployment = transition_key[4]
                transition_probs[next_deployment] = prob * 0.7  # Reduced confidence
        
        if transition_probs:
            fallback_used = f"Level 2: Alternate last_change ({alternate_last_change}) vs {opponent}"
            logger.info(f"Fallback {fallback_used}")
            return transition_probs
        
        # LEVEL 3: Same team, different opponent (generalized team behavior)
        for transition_key, prob in self.last_change_rotation_transitions.items():
            if (len(transition_key) == 5 and 
                transition_key[0] == team and  # Same team
                transition_key[2] == last_change_status and  # Same last_change status
                transition_key[3] == prev_deploy):  # Same previous deployment
                next_deployment = transition_key[4]
                # Average across opponents, reduce confidence
                transition_probs[next_deployment] = transition_probs.get(next_deployment, 0) + prob * 0.5
        
        if transition_probs:
            # Normalize averaged probabilities
            total_prob = sum(transition_probs.values())
            if total_prob > 0:
                transition_probs = {k: v/total_prob for k, v in transition_probs.items()}
                fallback_used = f"Level 3: Generalized {team} behavior ({len(transition_probs)} patterns)"
                logger.info(f"Fallback {fallback_used}")
                return transition_probs
        
        # LEVEL 4: General rotation patterns (no tactical context)
        if previous_deployment in self.rotation_transitions:
            transition_probs = self.rotation_transitions[previous_deployment].copy()
            if transition_probs:
                fallback_used = f"Level 4: General rotation patterns"
                logger.info(f"Fallback {fallback_used}")
                return transition_probs
        
        # LEVEL 5: Uniform distribution (last resort)
        # This should rarely happen in production but ensures graceful degradation
        fallback_used = "Level 5: Uniform distribution (no patterns available)"
        logger.warning(f"Fallback {fallback_used} for {team} vs {opponent}")
        
        # Return empty dict - caller will handle this case
        return {}
    
    def _log_prior_application_stats(self, candidates: List[Candidate], transition_probs: Dict[str, float],
                                   context: str) -> None:
        """Log detailed statistics about prior application"""
        applied_count = 0
        total_boost = 0.0
        max_boost = 0.0
        
        for candidate in candidates:
            cand_key = f"{'|'.join(sorted(candidate.forwards))}_{'|'.join(sorted(candidate.defense))}"
            if cand_key in transition_probs:
                boost = transition_probs[cand_key]
                applied_count += 1
                total_boost += boost
                max_boost = max(max_boost, boost)
        
        if applied_count > 0:
            avg_boost = total_boost / applied_count
            coverage = applied_count / len(candidates)
            logger.debug(
                f"Prior stats {context}: {applied_count}/{len(candidates)} candidates "
                f"({coverage:.1%} coverage), avg_boost={avg_boost:.3f}, max_boost={max_boost:.3f}"
            )
        else:
            logger.warning(f"Prior stats {context}: No candidates matched available patterns")
    
    def stochastic_rare_line_sample(self, candidates: List[Candidate], 
                                   n_samples: int = 15,
                                   include_rare: bool = True) -> List[Candidate]:
        """
        Stochastic sampling with bias towards rare lines
        Ensures model sees diverse deployments during training
        """
        
        if len(candidates) <= n_samples:
            return candidates
        
        # Calculate sampling weights
        weights = []
        for candidate in candidates:
            cand_key = f"{'|'.join(sorted(candidate.forwards))}_{'|'.join(sorted(candidate.defense))}"
            frequency = self.line_frequencies.get(cand_key, 0)
            
            if include_rare and frequency < self.rare_threshold:
                # Boost weight for rare lines (inverse frequency with temperature)
                weight = 1.0 / (1.0 + frequency) ** (1.0 / self.sampling_temperature)
            else:
                # Standard weight for common lines
                weight = candidate.probability_prior
            
            weights.append(weight)
        
        # Normalize weights
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # Sample without replacement
        indices = np.random.choice(
            len(candidates), 
            size=min(n_samples, len(candidates)),
            replace=False,
            p=weights
        )
        
        sampled = [candidates[i] for i in indices]
        
        # Log sampling statistics
        n_rare = sum(1 for c in sampled 
                    if self.line_frequencies.get(f"{'|'.join(sorted(c.forwards))}_{'|'.join(sorted(c.defense))}", 0) < self.rare_threshold)
        logger.debug(f"Sampled {len(sampled)} candidates ({n_rare} rare lines)")
        
        return sampled
    
    def generate_special_teams_second_units(self, available_players: Dict,
                                           is_powerplay: bool = True) -> List[Candidate]:
        """
        Generate second unit candidates for special teams
        Important for realistic deployment patterns in PP/PK
        """
        
        candidates = []
        units_dict = self.pp_second_units if is_powerplay else self.pk_second_units
        
        # Get position requirements
        if is_powerplay:
            n_fwd, n_def = 4, 1  # Typical PP second unit
        else:
            n_fwd, n_def = 2, 2  # Typical PK second unit
        
        available_fwd = set(available_players.get('forwards', []))
        available_def = set(available_players.get('defense', []))
        
        # Generate from historical second units
        for unit_key, frequency in units_dict.most_common(5):
            if '|' in unit_key and '_' in unit_key:
                fwd_part, def_part = unit_key.split('_')
                fwd_players = fwd_part.split('|') if fwd_part else []
                def_players = def_part.split('|') if def_part else []
                
                # Check availability
                if (set(fwd_players).issubset(available_fwd) and 
                    set(def_players).issubset(available_def) and
                    len(fwd_players) == n_fwd and len(def_players) == n_def):
                    
                    candidate = Candidate(
                        forwards=fwd_players,
                        defense=def_players,
                        probability_prior=frequency / 100.0  # Normalize
                    )
                    candidates.append(candidate)
        
        # Generate variations if not enough historical data
        if len(candidates) < 3:
            # Create second units from less-used players
            fwd_list = list(available_fwd)
            def_list = list(available_def)
            
            # Sort by usage (assume less-used players for second unit)
            # This would need actual usage data in production
            np.random.shuffle(fwd_list)
            np.random.shuffle(def_list)
            
            if len(fwd_list) >= n_fwd and len(def_list) >= n_def:
                candidate = Candidate(
                    forwards=fwd_list[3:3+n_fwd] if n_fwd == 4 else fwd_list[3:3+n_fwd],
                    defense=def_list[2:2+n_def],
                    probability_prior=0.5
                )
                candidates.append(candidate)
        
        return candidates
    
    def save_patterns(self, filepath: Path):
        """Save learned patterns to disk"""
        
        import pickle
        
        patterns = {
            'forward_combinations': dict(self.forward_combinations),
            'defense_pairs': dict(self.defense_pairs),
            'full_deployments': dict(self.full_deployments),
            'powerplay_units': dict(self.powerplay_units),
            'penalty_kill_units': dict(self.penalty_kill_units),
            'player_chemistry': dict(self.player_chemistry),
            'coach_patterns': self.coach_patterns,
            'forwards_pool': list(self.forwards_pool),
            'defense_pool': list(self.defense_pool),
            # NEW: Save Markov and stochastic sampling data
            'rotation_transitions': dict(self.rotation_transitions),
            'rotation_counts': dict(self.rotation_counts),
            'line_frequencies': dict(self.line_frequencies),
            'pp_second_units': dict(self.pp_second_units),
            'pk_second_units': dict(self.pk_second_units),
            
            # LAST-CHANGE-AWARE: Save flattened tactical rotation patterns
            'last_change_rotation_transitions': dict(self.last_change_rotation_transitions),
            'last_change_rotation_counts': dict(self.last_change_rotation_counts),
            
            # METADATA: Store format version for backward compatibility
            'patterns_format_version': '2.0'  # Flattened tuple-key format
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(patterns, f)
        
        logger.info(f"Saved patterns to {filepath}")
    
    def _serialize_nested_dict(self, nested_dict):
        """Convert nested defaultdicts to regular dicts for serialization"""
        if isinstance(nested_dict, defaultdict):
            result = {}
            for key, value in nested_dict.items():
                result[key] = self._serialize_nested_dict(value)
            return result
        elif isinstance(nested_dict, dict):
            result = {}
            for key, value in nested_dict.items():
                result[key] = self._serialize_nested_dict(value)
            return result
        else:
            return nested_dict
    
    def _deserialize_nested_dict(self, regular_dict, default_value=None):
        """Convert regular dicts back to nested defaultdicts after loading"""
        if default_value is None:
            # For transition probabilities (float values)
            result = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
        elif default_value == 0:
            # For counts (int values)
            result = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        
        for key1, level1 in regular_dict.items():
            if isinstance(level1, dict):
                for key2, level2 in level1.items():
                    if isinstance(level2, dict):
                        for key3, level3 in level2.items():
                            if isinstance(level3, dict):
                                for key4, value in level3.items():
                                    result[key1][key2][key3][key4] = value
                            else:
                                result[key1][key2][key3] = level3
                    else:
                        result[key1][key2] = level2
            else:
                result[key1] = level1
        
        return result
    
    def load_patterns(self, filepath: Path):
        """Load learned patterns from disk"""
        
        import pickle
        
        with open(filepath, 'rb') as f:
            patterns = pickle.load(f)
        
        self.forward_combinations = Counter(patterns['forward_combinations'])
        self.defense_pairs = Counter(patterns['defense_pairs'])
        self.full_deployments = Counter(patterns['full_deployments'])
        self.powerplay_units = Counter(patterns['powerplay_units'])
        self.penalty_kill_units = Counter(patterns['penalty_kill_units'])
        self.player_chemistry = defaultdict(float, patterns['player_chemistry'])
        self.coach_patterns = patterns['coach_patterns']
        self.forwards_pool = set(patterns['forwards_pool'])
        self.defense_pool = set(patterns['defense_pool'])
        
        # Load enhanced pattern data if available
        if 'rotation_transitions' in patterns:
            self.rotation_transitions = defaultdict(lambda: defaultdict(float), patterns['rotation_transitions'])
        if 'rotation_counts' in patterns:
            self.rotation_counts = defaultdict(int, patterns['rotation_counts'])
        if 'line_frequencies' in patterns:
            self.line_frequencies = Counter(patterns['line_frequencies'])
        if 'pp_second_units' in patterns:
            self.pp_second_units = Counter(patterns['pp_second_units'])
        if 'pk_second_units' in patterns:
            self.pk_second_units = Counter(patterns['pk_second_units'])
        
        # LAST-CHANGE-AWARE: Load tactical rotation patterns with backward compatibility
        format_version = patterns.get('patterns_format_version', '1.0')
        
        if 'last_change_rotation_transitions' in patterns:
            if format_version == '2.0':
                # NEW FORMAT: Flattened tuple-key structure
                self.last_change_rotation_transitions = defaultdict(float, patterns['last_change_rotation_transitions'])
                logger.info("Loaded flattened last-change rotation patterns (v2.0)")
            else:
                # LEGACY FORMAT: Nested defaultdict structure
                self.last_change_rotation_transitions = self._deserialize_nested_dict(
                    patterns['last_change_rotation_transitions']
                )
                logger.info("Loaded legacy nested last-change rotation patterns (v1.0)")
                
        if 'last_change_rotation_counts' in patterns:
            if format_version == '2.0':
                # NEW FORMAT: Flattened tuple-key structure
                self.last_change_rotation_counts = defaultdict(int, patterns['last_change_rotation_counts'])
            else:
                # LEGACY FORMAT: Nested defaultdict structure
                self.last_change_rotation_counts = self._deserialize_nested_dict(
                    patterns['last_change_rotation_counts'], default_value=0
                )
        
        # PLAYER-VS-PLAYER: Load matchup patterns if available (v2.1 format)
        if 'player_matchup_patterns' in patterns:
            matchup_patterns = patterns['player_matchup_patterns']
            
            # Load global matchup counts
            if 'global_matchup_counts' in matchup_patterns:
                self.player_matchup_counts = defaultdict(float)
                for key_str, count in matchup_patterns['global_matchup_counts'].items():
                    parts = key_str.split('__vs__')
                    if len(parts) == 2:
                        key = (parts[0], parts[1])
                        self.player_matchup_counts[key] = float(count)
            
            # Load last-change-aware matchup counts
            if 'last_change_matchup_counts' in matchup_patterns:
                self.last_change_player_matchups = defaultdict(float)
                for key_str, count in matchup_patterns['last_change_matchup_counts'].items():
                    parts = key_str.split('__')
                    if len(parts) >= 6:
                        key = (parts[0], parts[2], parts[3][3:], parts[4][3:])
                        self.last_change_player_matchups[key] = float(count)
            
            # Load situation-specific matchup counts
            if 'situation_matchup_counts' in matchup_patterns:
                self.situation_player_matchups = defaultdict(lambda: defaultdict(float))
                for key_str, count in matchup_patterns['situation_matchup_counts'].items():
                    parts = key_str.split('__')
                    if len(parts) >= 4:
                        player_pair_key = (parts[0], parts[2])  # (mtl_player, opp_player)
                        situation = parts[3][4:]  # Remove sit_ prefix
                        self.situation_player_matchups[player_pair_key][situation] = float(count)
            
            # Load MTL last-change matrices if present
            if 'mtl_response_matrix' in matchup_patterns:
                temp_resp = defaultdict(lambda: defaultdict(float))
                for opp_lineup, inner in matchup_patterns['mtl_response_matrix'].items():
                    for mtl_resp, w in inner.items():
                        temp_resp[opp_lineup][mtl_resp] = float(w)
                self.mtl_response_matrix = temp_resp
            if 'mtl_vs_opp_forwards' in matchup_patterns:
                temp_mtl_vs_opp = defaultdict(lambda: defaultdict(float))
                for mtl_fwd, inner in matchup_patterns['mtl_vs_opp_forwards'].items():
                    for opp_fwd, w in inner.items():
                        temp_mtl_vs_opp[mtl_fwd][opp_fwd] = float(w)
                self.mtl_vs_opp_forwards = temp_mtl_vs_opp
            if 'mtl_defense_vs_opp_forwards' in matchup_patterns:
                temp_mtl_def_vs_opp = defaultdict(lambda: defaultdict(float))
                for mtl_def, inner in matchup_patterns['mtl_defense_vs_opp_forwards'].items():
                    for opp_fwd, w in inner.items():
                        temp_mtl_def_vs_opp[mtl_def][opp_fwd] = float(w)
                self.mtl_defense_vs_opp_forwards = temp_mtl_def_vs_opp
            
            logger.info(f"Loaded player-vs-player matchup patterns:")
            logger.info(f"  - {len(self.player_matchup_counts)} global matchups")
            logger.info(f"  - {len(self.last_change_player_matchups)} last-change matchups")
            logger.info(f"  - {len(self.situation_player_matchups)} situation-specific matchups")
        
        logger.info(f"Loaded patterns from {filepath}")
    
    def load_player_matchup_patterns_v21(self, dir_path: Path) -> bool:
        """Load player-vs-player matchup patterns from v2.1 JSON saved by DataProcessor."""
        try:
            import json
            v21_file = dir_path / 'player_matchup_patterns_v2.1.json'
            if not v21_file.exists():
                logger.warning(f"v2.1 matchup patterns not found at {v21_file}")
                return False
            with open(v21_file, 'r') as f:
                data = json.load(f)
            # Clear existing
            self.player_matchup_counts = defaultdict(float)
            self.last_change_player_matchups = defaultdict(float)
            self.situation_player_matchups = defaultdict(lambda: defaultdict(float))
            # Global counts
            for key_str, count in data.get('global_matchup_counts', {}).items():
                parts = key_str.split('__vs__')
                if len(parts) == 2:
                    self.player_matchup_counts[(parts[0], parts[1])] = float(count)
            # Last-change counts: key format mtl__opp__lc_<team>__role_<team>
            for key_str, count in data.get('last_change_matchup_counts', {}).items():
                parts = key_str.split('__')
                # Format: player1__vs__player2__lc_TEAM__tm_TEAM → length 5
                if len(parts) >= 5:
                    key = (parts[0], parts[2], parts[3][3:], parts[4][3:])
                    self.last_change_player_matchups[key] = float(count)
            # Situation counts
            for key_str, count in data.get('situation_matchup_counts', {}).items():
                parts = key_str.split('__')
                if len(parts) >= 4:
                    pair_key = (parts[0], parts[2])
                    situation = parts[3][4:]
                    self.situation_player_matchups[pair_key][situation] = float(count)
            # MTL-side matrices
            if 'mtl_response_matrix' in data:
                temp_resp = defaultdict(lambda: defaultdict(float))
                for opp_lineup, inner in data['mtl_response_matrix'].items():
                    for mtl_resp, w in inner.items():
                        temp_resp[opp_lineup][mtl_resp] = float(w)
                self.mtl_response_matrix = temp_resp
            if 'mtl_vs_opp_forwards' in data:
                temp_mtl_vs_opp = defaultdict(lambda: defaultdict(float))
                for mtl_fwd, inner in data['mtl_vs_opp_forwards'].items():
                    for opp_fwd, w in inner.items():
                        temp_mtl_vs_opp[mtl_fwd][opp_fwd] = float(w)
                self.mtl_vs_opp_forwards = temp_mtl_vs_opp
            if 'mtl_defense_vs_opp_forwards' in data:
                temp_mtl_def_vs_opp = defaultdict(lambda: defaultdict(float))
                for mtl_def, inner in data['mtl_defense_vs_opp_forwards'].items():
                    for opp_fwd, w in inner.items():
                        temp_mtl_def_vs_opp[mtl_def][opp_fwd] = float(w)
                self.mtl_defense_vs_opp_forwards = temp_mtl_def_vs_opp
            logger.info(
                f"Loaded v2.1 matchup patterns: globals={len(self.player_matchup_counts)}, "
                f"last_change={len(self.last_change_player_matchups)}, situations={len(self.situation_player_matchups)}"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to load v2.1 matchup patterns: {e}")
            return False
    
    def log_matchup_priors_to_metrics(self, candidates: List[Candidate], opponent_team: str, 
                                     strength: str, eval_metrics_helper):
        """Log probability priors (full combined priors) to evaluation metrics helper for analysis"""
        if not hasattr(eval_metrics_helper, 'update_matchup_prior'):
            return  # Skip if metrics helper doesn't support prior tracking
        
        for i, candidate in enumerate(candidates):
            # Use probability_prior (full softmax-normalized combined prior) instead of just matchup_prior
            probability_prior = getattr(candidate, 'probability_prior', 0.0)
            candidate_id = f"{'-'.join(candidate.forwards)}_{'-'.join(candidate.defense)}"
            
            eval_metrics_helper.update_matchup_prior(
                opponent_team=opponent_team,
                strength=strength,
                matchup_prior=probability_prior,  # Pass full prior (keeping param name for compatibility)
                candidate_id=candidate_id
            )
            
            # Log detailed info for top candidates
            if i < 5 and abs(probability_prior) > 0.001:  # Top 5 candidates with non-zero priors
                logger.debug(f"Probability prior {opponent_team} {strength}: {candidate_id} = {probability_prior:.4f}")
    
    def compute_matchup_prior(self, candidate_players: List[str], opponent_players: List[str], 
                             opponent_team: str = None, last_change_team: str = None, 
                             team_making_change: str = 'MTL', situation: str = '5v5') -> float:
        """
        Compute player-vs-player matchup prior for a candidate against opponent deployment
        
        This calculates how frequently the candidate's players have been matched up
        against the current opponent players in the past, giving higher weight to:
        1. Recent matchups (via EWMA weighting)
        2. Last-change-aware patterns (tactical situations)
        3. Situation-specific patterns (5v5, PP, PK, etc.)
        
        Args:
            candidate_players: List of MTL players in this candidate
            opponent_players: List of current opponent players on ice
            opponent_team: Opponent team name (for team-specific patterns)
            last_change_team: Which team has the last change advantage
            team_making_change: Which team is making the change ('MTL' or opponent)
            situation: Game situation ('5v5', '5v4', etc.)
            
        Returns:
            float: Matchup prior score (higher = more familiar matchup)
        """
        if not self.enable_matchup_priors or not candidate_players or not opponent_players:
            return 0.0
        
        total_matchup_score = 0.0
        total_possible_matchups = len(candidate_players) * len(opponent_players)
        
        # Compute matchup scores for each player pairing
        for mtl_player in candidate_players:
            for opp_player in opponent_players:
                matchup_score = 0.0
                
                # 1. GLOBAL: Overall matchup frequency (baseline)
                global_key = (mtl_player, opp_player)
                if global_key in self.player_matchup_counts:
                    global_count = self.player_matchup_counts[global_key]
                    if global_count >= self.min_matchup_threshold:
                        matchup_score += global_count * 0.3  # 30% weight for global patterns
                
                # 2. LAST-CHANGE-AWARE: Tactical matchup patterns (higher priority)
                if last_change_team and team_making_change:
                    lc_key = (mtl_player, opp_player, last_change_team, team_making_change)
                    if lc_key in self.last_change_player_matchups:
                        lc_count = self.last_change_player_matchups[lc_key]
                        if lc_count >= self.min_matchup_threshold:
                            matchup_score += lc_count * 0.5  # 50% weight for tactical patterns
                
                # 3. SITUATION-SPECIFIC: Game situation patterns
                situation_pair_key = (mtl_player, opp_player)
                if situation_pair_key in self.situation_player_matchups:
                    situation_count = self.situation_player_matchups[situation_pair_key].get(situation, 0.0)
                    if situation_count >= self.min_matchup_threshold:
                        matchup_score += situation_count * 0.2  # 20% weight for situation patterns
                
                # 4. OPTIONAL: MTL last-change priors when MTL is the decision-maker
                if last_change_team == 'MTL' and team_making_change == 'MTL':
                    # Forward vs forward bias
                    mtl_fwd_bias = self.mtl_vs_opp_forwards.get(mtl_player, {}).get(opp_player, 0.0)
                    if mtl_fwd_bias > 0:
                        matchup_score += 0.1 * mtl_fwd_bias
                    # Defense vs forward bias
                    mtl_def_bias = self.mtl_defense_vs_opp_forwards.get(mtl_player, {}).get(opp_player, 0.0)
                    if mtl_def_bias > 0:
                        matchup_score += 0.1 * mtl_def_bias
                
                # Add to total (normalized by frequency)
                total_matchup_score += matchup_score
        
        # Normalize by number of possible pairings and apply scaling
        if total_possible_matchups > 0:
            normalized_score = total_matchup_score / total_possible_matchups
            # Apply logarithmic scaling to prevent extreme values
            import math
            scaled_score = math.log(1 + normalized_score) * self.matchup_prior_weight
            return scaled_score
        
        return 0.0
    
    def get_matchup_prior_stats(self, candidate_players: List[str], opponent_players: List[str]) -> Dict[str, float]:
        """
        Get detailed matchup statistics for debugging and analysis
        
        Returns:
            Dict with matchup statistics and breakdown by pattern type
        """
        if not candidate_players or not opponent_players:
            return {'total_score': 0.0, 'global_matches': 0, 'tactical_matches': 0, 'situation_matches': 0}
        
        stats = {
            'total_score': 0.0,
            'global_matches': 0,
            'tactical_matches': 0, 
            'situation_matches': 0,
            'player_pair_details': []
        }
        
        for mtl_player in candidate_players:
            for opp_player in opponent_players:
                pair_stats = {'mtl_player': mtl_player, 'opp_player': opp_player}
                
                # Global matchup count
                global_key = (mtl_player, opp_player)
                global_count = self.player_matchup_counts.get(global_key, 0.0)
                if global_count >= self.min_matchup_threshold:
                    stats['global_matches'] += 1
                    pair_stats['global_count'] = global_count
                
                stats['player_pair_details'].append(pair_stats)
        
        # Compute overall matchup prior
        stats['total_score'] = self.compute_matchup_prior(candidate_players, opponent_players)
        
        return stats
