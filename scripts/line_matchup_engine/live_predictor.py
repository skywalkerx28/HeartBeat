"""
HeartBeat Live Line Matchup Predictor
Real-time prediction engine for opponent line deployments during live games
Professional-grade implementation with sub-10ms latency
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging
import time
from pathlib import Path
import pickle
import json
from datetime import datetime
from collections import deque

# Import our modules
from conditional_logit_model import PyTorchConditionalLogit
from candidate_generator import CandidateGenerator, Candidate
from feature_engineering import FeatureEngineer
from player_mapper import PlayerMapper, get_mapper

logger = logging.getLogger(__name__)

@dataclass
class GameState:
    """Current state of the live game"""
    game_id: str
    period: int = 1
    period_time: float = 0.0
    game_time: float = 0.0
    home_team: str = ""
    away_team: str = ""
    home_score: int = 0
    away_score: int = 0
    strength_state: str = "5v5"
    zone: str = "nz"
    last_stoppage: str = "faceoff"
    
    # On-ice players
    mtl_forwards_on_ice: List[str] = field(default_factory=list)
    mtl_defense_on_ice: List[str] = field(default_factory=list)
    mtl_goalie_on_ice: str = ""
    
    opp_forwards_on_ice: List[str] = field(default_factory=list)
    opp_defense_on_ice: List[str] = field(default_factory=list)
    opp_goalie_on_ice: str = ""
    
    # Available players (not on ice, not penalized)
    mtl_forwards_available: List[str] = field(default_factory=list)
    mtl_defense_available: List[str] = field(default_factory=list)
    opp_forwards_available: List[str] = field(default_factory=list)
    opp_defense_available: List[str] = field(default_factory=list)
    
    # ENHANCED FATIGUE SYSTEM: Comprehensive real-time rest and shift tracking
    # Basic rest tracking (legacy compatibility)
    player_rest_times: Dict[str, float] = field(default_factory=dict)          # Game-time rest
    player_shift_starts: Dict[str, float] = field(default_factory=dict)        # Current shift start times
    player_shift_lengths: Dict[str, float] = field(default_factory=dict)       # Last shift lengths
    
    # DUAL REST SIGNALS: Real-time comprehensive fatigue modeling  
    player_rest_real_times: Dict[str, float] = field(default_factory=dict)     # Real elapsed rest (includes stoppages)
    player_intermission_flags: Dict[str, int] = field(default_factory=dict)    # 1 if returned after intermission
    
    # SHIFT AND TOI TRACKING: Complete workload monitoring
    player_shift_counts_period: Dict[str, int] = field(default_factory=dict)   # Shifts this period
    player_shift_counts_game: Dict[str, int] = field(default_factory=dict)     # Total game shifts
    player_toi_past_20min: Dict[str, float] = field(default_factory=dict)      # TOI in rolling 20min window
    player_cumulative_toi_game: Dict[str, float] = field(default_factory=dict) # Total game TOI
    
    # EWMA PATTERN RECOGNITION: Exponentially weighted moving averages
    player_ewma_shift_lengths: Dict[str, float] = field(default_factory=dict)  # EWMA shift length patterns
    player_ewma_rest_lengths: Dict[str, float] = field(default_factory=dict)   # EWMA rest length patterns
    
    # STOPPAGE CONTEXT: Real-time stoppage and game situation tracking  
    last_stoppage_type: str = "faceoff"                                        # Type of last stoppage
    last_stoppage_duration: float = 0.0                                        # Duration of last stoppage
    last_stoppage_time: float = 0.0                                            # When stoppage occurred
    
    # SHIFT HISTORY: Complete shift sequences for EWMA calculations
    player_shift_history: Dict[str, List[Dict]] = field(default_factory=dict)  # Complete shift sequences per player
    
    # DECISION CONTEXT: Who has deployment advantage
    decision_role: int = 0  # 1 if MTL decides (has last change), 0 if opponent decides
    last_change_team: str = ""  # Which team made the last change
    
    # PHASE FLAGS: High-leverage situation detection
    is_period_late: bool = False  # True if period_time >= 17:00 (1020s)
    is_game_late: bool = False    # True if game_seconds >= 55:00 (3300s)
    is_late_pk: bool = False      # True if PK situation + late period
    is_late_pp: bool = False      # True if PP situation + late period
    is_close_and_late: bool = False  # True if close game (±1 goal) + late game
    
    # Recent history
    recent_deployments: deque = field(default_factory=lambda: deque(maxlen=10))
    
    @property
    def score_differential(self) -> int:
        """Score differential from MTL perspective"""
        mtl_score = self.home_score if 'MTL' in self.home_team else self.away_score
        opp_score = self.away_score if 'MTL' in self.home_team else self.home_score
        return mtl_score - opp_score
    
    @property
    def has_last_change(self) -> bool:
        """Whether MTL has last change advantage"""
        return 'MTL' in self.home_team
    
    @property
    def time_remaining(self) -> float:
        """Time remaining in period (seconds)"""
        return max(0, 1200 - self.period_time)


@dataclass
class PredictionResult:
    """Result of a line deployment prediction"""
    timestamp: datetime
    game_state: GameState
    candidates: List[Candidate]
    probabilities: np.ndarray
    top_predictions: List[Dict]
    explanations: List[str]
    inference_time_ms: float
    confidence_score: float


class LiveLinePredictor:
    """
    Real-time line matchup predictor for live NHL games
    Optimized for < 10ms inference latency
    """
    
    def __init__(self, 
                 model_path: Optional[Path] = None,
                 patterns_path: Optional[Path] = None,
                 features_path: Optional[Path] = None,
                 player_mapping_path: Optional[Path] = None):
        
        # Core components
        self.model = PyTorchConditionalLogit(n_context_features=20, embedding_dim=32)
        self.candidate_generator = CandidateGenerator()
        self.feature_engineer = FeatureEngineer()
        
        # Initialize player mapper
        if not player_mapping_path:
            # Try to find it relative to model path
            if model_path:
                player_mapping_path = model_path.parent.parent.parent / 'data' / 'processed' / 'dim' / 'player_ids.csv'
        self.player_mapper = get_mapper(player_mapping_path)
        logger.info(f"Initialized player mapper with {len(self.player_mapper.player_map)} players")
        
        # Load pre-trained models if provided
        if model_path and model_path.exists():
            self.model.load_model(model_path)
            logger.info(f"Loaded model from {model_path}")
        
        if patterns_path and patterns_path.exists():
            self.candidate_generator.load_patterns(patterns_path)
            logger.info(f"Loaded patterns from {patterns_path}")
        
        if features_path and features_path.exists():
            self.feature_engineer.load_features(features_path)
            logger.info(f"Loaded features from {features_path}")
        
        # Performance tracking
        self.prediction_history = []
        self.latency_tracker = deque(maxlen=100)
        
        # Cache for faster inference
        self.context_cache = {}
        self.candidate_cache = {}
        
        # Online learning components
        self.online_buffer = []
        self.online_update_frequency = 10  # Update every N predictions
        
        # Calibration temperature (learned during training)
        self.temperature = 1.0
        
        # NEW: Opponent trend priors and hazard-rate modeling
        self.opponent_trends = {}  # Loaded from predictive_patterns.pkl
        self.hazard_rate_models = {}  # Player-specific exponential models for return time
        self.opponent_recent_games = {}  # Track recent opponent performance trends
    
    def predict(self, 
                game_state: GameState,
                max_candidates: int = 12,
                top_k: int = 3,
                opponent_team: Optional[str] = None) -> PredictionResult:
        """
        Main prediction function for live games
        Returns top-k most likely opponent deployments with explanations
        
        Target latency: < 10ms total
        """
        
        start_time = time.perf_counter()
        
        # Step 1: Generate candidates with hazard-rate availability (target: 1-2ms)
        candidates = self._generate_candidates(game_state, max_candidates, opponent_team)
        
        # Step 2: Create context features (target: < 1ms)
        context = self._create_context_features(game_state)
        
        # Step 3: Compute probabilities (target: < 0.5ms)
        probabilities = self._compute_probabilities(
            candidates, context, game_state
        )
        
        # Step 4: Generate explanations (target: < 0.5ms)
        top_indices = np.argsort(probabilities)[-top_k:][::-1]
        top_predictions = []
        explanations = []
        
        for idx in top_indices:
            candidate = candidates[idx]
            prob = probabilities[idx]
            
            # Include both IDs and names in prediction
            prediction = {
                'forwards': candidate.forwards,
                'defense': candidate.defense,
                'forwards_names': self.player_mapper.ids_to_names(candidate.forwards),
                'defense_names': self.player_mapper.ids_to_names(candidate.defense),
                'formatted_line': self.player_mapper.format_line(candidate.forwards, ' - '),
                'formatted_defense': self.player_mapper.format_line(candidate.defense, ' - '),
                'probability': float(prob),
                'confidence': self._compute_confidence(prob, probabilities)
            }
            top_predictions.append(prediction)
            
            # Generate explanation
            explanation = self._generate_explanation(
                candidate, game_state, prob
            )
            explanations.append(explanation)
        
        # Calculate confidence score
        confidence = self._compute_overall_confidence(probabilities)
        
        # Measure latency
        inference_time_ms = (time.perf_counter() - start_time) * 1000
        self.latency_tracker.append(inference_time_ms)
        
        # Create result
        result = PredictionResult(
            timestamp=datetime.now(),
            game_state=game_state,
            candidates=candidates,
            probabilities=probabilities,
            top_predictions=top_predictions,
            explanations=explanations,
            inference_time_ms=inference_time_ms,
            confidence_score=confidence
        )
        
        # Store for online learning
        self.prediction_history.append(result)
        
        # Log performance
        if len(self.latency_tracker) % 10 == 0:
            avg_latency = np.mean(self.latency_tracker)
            logger.debug(f"Average latency (last 100): {avg_latency:.2f}ms")
        
        return result
    
    def predict_mtl_deployment(self, 
                              game_state: GameState,
                              max_candidates: int = 12,
                              opponent_team: Optional[str] = None) -> List[Candidate]:
        """
        Predict MTL deployment candidates with player-vs-player matchup awareness
        
        This method is used when MTL needs to make a deployment decision,
        taking into account the current opponent deployment for matchup priors.
        
        Args:
            game_state: Current game state including opponent on-ice players
            max_candidates: Maximum number of candidates to generate
            opponent_team: Opponent team name for matchup patterns
            
        Returns:
            List of Candidate objects ranked by likelihood with matchup priors
        """
        # Create game situation with current opponent deployment for matchup priors
        game_situation = {
            'zone': game_state.zone,
            'strength': game_state.strength_state,
            'score_diff': game_state.score_differential,
            'period': game_state.period,
            'time_remaining': game_state.time_remaining,
            # PLAYER-VS-PLAYER: Include current opponent deployment
            'current_opponent_players': game_state.opp_forwards_on_ice + game_state.opp_defense_on_ice
        }
        
        # Prepare MTL available players
        mtl_available = {
            'forwards': game_state.mtl_forwards_available if hasattr(game_state, 'mtl_forwards_available') else [],
            'defense': game_state.mtl_defense_available if hasattr(game_state, 'mtl_defense_available') else []
        }
        
        # Prepare rest times for MTL players
        mtl_rest_times = {}
        all_mtl_players = mtl_available['forwards'] + mtl_available['defense']
        for player in all_mtl_players:
            mtl_rest_times[player] = game_state.player_rest_times.get(player, 90.0) if hasattr(game_state, 'player_rest_times') else 90.0
        
        # Generate MTL candidates with matchup-aware priors
        candidates = self.candidate_generator.generate_candidates(
            game_situation,
            mtl_available,
            mtl_rest_times,
            max_candidates=max_candidates,
            opponent_team=opponent_team,
            last_change_team=getattr(game_state, 'last_change_team', None),
            team_making_change='MTL'  # MTL is making the deployment decision
        )
        
        # Log matchup prior influence for debugging
        if candidates and opponent_team:
            matchup_influenced = [c for c in candidates if getattr(c, 'matchup_prior', 0.0) > 0]
            if matchup_influenced:
                avg_matchup_prior = np.mean([c.matchup_prior for c in matchup_influenced])
                logger.debug(f"Player-vs-player matchups influenced {len(matchup_influenced)}/{len(candidates)} candidates, avg_prior={avg_matchup_prior:.3f}")
        
        return candidates
    
    def predict_deployment_for_team(self,
                                   game_state: GameState,
                                   team: str,
                                   opponent_team: str,
                                   max_candidates: int = 12) -> Dict[str, Any]:
        """
        BIDIRECTIONAL PREDICTION: Predict deployment for any team (MTL or opponent)
        
        This method correctly handles last-change context for both sides:
        - When team has last change: uses patterns where team had decision advantage
        - When team doesn't have last change: uses patterns where team reacted to opponent
        
        Args:
            game_state: Current game state
            team: Team to predict for ('MTL' or opponent abbreviation)
            opponent_team: The opposing team
            max_candidates: Number of candidates to generate
            
        Returns:
            Dict with candidates, tactical context, and prediction metadata
        """
        # Determine last change context
        home_team = game_state.home_team
        last_change_team = home_team  # Home team always has last change in NHL
        
        # Set up prediction context based on which team we're predicting for
        if team == 'MTL':
            # Predicting MTL deployment
            team_making_change = 'MTL'
            current_opponent = opponent_team
            
            # Get MTL available players
            available = {
                'forwards': getattr(game_state, 'mtl_forwards_available', []),
                'defense': getattr(game_state, 'mtl_defense_available', [])
            }
            
            # MTL rest times
            rest_times = {}
            all_players = available['forwards'] + available['defense']
            for player in all_players:
                rest_times[player] = game_state.player_rest_times.get(player, 90.0) if hasattr(game_state, 'player_rest_times') else 90.0
                
        else:
            # Predicting opponent deployment
            team_making_change = opponent_team
            current_opponent = 'MTL'
            
            # Get opponent available players
            available = {
                'forwards': getattr(game_state, 'opp_forwards_available', []),
                'defense': getattr(game_state, 'opp_defense_available', [])
            }
            
            # Opponent rest times
            rest_times = {}
            all_players = available['forwards'] + available['defense']
            for player in all_players:
                rest_times[player] = game_state.player_rest_times.get(player, 90.0) if hasattr(game_state, 'player_rest_times') else 90.0
        
        # Determine tactical context
        has_last_change = (last_change_team == team)  # Use the team we're predicting for, not team_making_change
        tactical_context = "has_last_change" if has_last_change else "no_last_change"
        
        # Build game situation with current opponent deployment for matchup priors
        game_situation = {
            'strength': game_state.strength_state,
            'zone': getattr(game_state, 'zone', 'nz'),
            'period': game_state.period,
            'period_time': game_state.period_time,
            'score_diff': game_state.home_score - game_state.away_score if team == home_team else game_state.away_score - game_state.home_score,
            'current_opponent_players': []  # Will be populated with current opponent on-ice players
        }
        
        # Add current opponent deployment for matchup priors
        if team == 'MTL':
            game_situation['current_opponent_players'] = (
                getattr(game_state, 'opp_forwards_on_ice', []) + 
                getattr(game_state, 'opp_defense_on_ice', [])
            )
        else:
            game_situation['current_opponent_players'] = (
                getattr(game_state, 'mtl_forwards_on_ice', []) + 
                getattr(game_state, 'mtl_defense_on_ice', [])
            )
        
        # Generate candidates with proper tactical context
        candidates = self.candidate_generator.generate_candidates(
            game_situation,
            available,
            rest_times,
            max_candidates=max_candidates,
            opponent_team=current_opponent,
            last_change_team=last_change_team,
            team_making_change=team_making_change
        )
        
        return {
            'candidates': candidates,
            'team': team,
            'opponent_team': current_opponent,
            'last_change_team': last_change_team,
            'has_last_change': has_last_change,
            'tactical_context': tactical_context,
            'explanation': f"{team} {'has' if has_last_change else 'does not have'} last change advantage vs {current_opponent}",
            'prediction_metadata': {
                'num_candidates': len(candidates),
                'available_forwards': len(available['forwards']),
                'available_defense': len(available['defense']),
                'opponent_on_ice': len(game_situation['current_opponent_players'])
            }
        }
    
    def predict_opponent_deployment(self,
                                   game_state: GameState,
                                   opponent_team: str,
                                   max_candidates: int = 12) -> List[Candidate]:
        """
        WRAPPER: Predict opponent deployment with correct parameter mapping
        """
        result = self.predict_deployment_for_team(
            game_state=game_state,
            team=opponent_team,
            opponent_team='MTL',
            max_candidates=max_candidates
        )
        return result['candidates']
    
    def predict_strategic_deployment(self, 
                                   game_state: GameState,
                                   scenario: str,
                                   opponent_team: str,
                                   max_candidates: int = 12) -> Dict[str, Any]:
        """
        STRATEGIC BIDIRECTIONAL PREDICTION for Montreal Canadiens
        
        This is the main method MTL uses during games to stay one step ahead.
        It predicts both sides and provides strategic recommendations.
        
        Scenarios:
        - 'mtl_has_last_change': MTL can react to opponent deployment
        - 'opponent_has_last_change': MTL must deploy first, predict opponent response
        - 'simultaneous_change': Both teams changing simultaneously
        
        Returns:
            Dict with MTL recommendations, opponent predictions, and strategic analysis
        """
        start_time = time.time()
        
        result = {
            'scenario': scenario,
            'timestamp': datetime.now().isoformat(),
            'game_state_snapshot': {
                'period': game_state.period,
                'time_remaining': game_state.time_remaining,
                'score_diff': game_state.score_differential,
                'strength': game_state.strength_state,
                'zone': game_state.zone
            }
        }
        
        if scenario == 'mtl_has_last_change':
            # MTL has the tactical advantage - can react to opponent
            result['strategic_advantage'] = 'MTL'
            
            # 1. Predict what opponent will deploy (they go first)
            opp_predictions = self.predict_deployment_for_team(game_state, opponent_team, 'MTL', max_candidates)
            result['opponent_predictions'] = {
                'top_deployments': [
                    {
                        'players': c.forwards + c.defense,
                        'probability': c.probability_prior,
                        'matchup_prior': getattr(c, 'matchup_prior', 0.0),
                        'chemistry_score': c.chemistry_score,
                        'fatigue_score': c.fatigue_score
                    }
                    for c in opp_predictions['candidates'][:3]
                ]
            }
            
            # 2. For each likely opponent deployment, find optimal MTL counter
            mtl_optimal_responses = []
            for opp_deployment in result['opponent_predictions']['top_deployments']:
                # Simulate game state with this opponent deployment on ice
                temp_game_state = GameState(
                    game_id=game_state.game_id,
                    period=game_state.period,
                    period_time=game_state.period_time,
                    home_team=game_state.home_team,
                    away_team=game_state.away_team,
                    home_score=game_state.home_score,
                    away_score=game_state.away_score,
                    strength_state=game_state.strength_state,
                    opp_forwards_on_ice=opp_deployment['players'][:3],
                    opp_defense_on_ice=opp_deployment['players'][3:5],
                    mtl_forwards_available=getattr(game_state, 'mtl_forwards_available', []),
                    mtl_defense_available=getattr(game_state, 'mtl_defense_available', []),
                    player_rest_times=getattr(game_state, 'player_rest_times', {})
                )
                
                # Get MTL candidates optimized against this specific opponent deployment
                mtl_response = self.predict_deployment_for_team(temp_game_state, 'MTL', opponent_team, max_candidates)
                
                if mtl_response['candidates']:
                    best_mtl = mtl_response['candidates'][0]
                    optimal_response = {
                        'against_opponent': opp_deployment['players'],
                        'opponent_probability': opp_deployment['probability'],
                        'mtl_optimal': {
                            'players': best_mtl.forwards + best_mtl.defense,
                            'probability_prior': best_mtl.probability_prior,
                            'matchup_prior': getattr(best_mtl, 'matchup_prior', 0.0),
                            'chemistry_score': best_mtl.chemistry_score,
                            'fatigue_score': best_mtl.fatigue_score
                        }
                    }
                    mtl_optimal_responses.append(optimal_response)
            
            result['mtl_optimal_responses'] = mtl_optimal_responses
            
            # 3. Strategic recommendation (highest expected value)
            if mtl_optimal_responses:
                best_response = max(mtl_optimal_responses, 
                                  key=lambda x: x['opponent_probability'] * x['mtl_optimal']['probability_prior'])
                result['strategic_recommendation'] = best_response
                
        elif scenario == 'opponent_has_last_change':
            # Opponent has tactical advantage - MTL must deploy first and predict response
            result['strategic_advantage'] = 'OPPONENT'
            
            # 1. Generate MTL deployment options
            mtl_prediction = self.predict_deployment_for_team(game_state, 'MTL', opponent_team, max_candidates)
            mtl_candidates = mtl_prediction['candidates']
            result['mtl_deployment_options'] = [
                {
                    'players': c.forwards + c.defense,
                    'probability_prior': c.probability_prior,
                    'matchup_prior': getattr(c, 'matchup_prior', 0.0),
                    'chemistry_score': c.chemistry_score,
                    'fatigue_score': c.fatigue_score
                }
                for c in mtl_candidates[:5]  # Top 5 options
            ]
            
            # 2. For each MTL option, predict opponent's best counter-response
            mtl_risk_analysis = []
            for mtl_candidate in mtl_candidates[:3]:  # Analyze top 3 MTL options
                # Simulate game state with this MTL deployment
                temp_game_state = game_state
                temp_game_state.mtl_forwards_on_ice = mtl_candidate.forwards
                temp_game_state.mtl_defense_on_ice = mtl_candidate.defense
                
                # Predict opponent's response to this MTL deployment
                opp_response = self.predict_deployment_for_team(temp_game_state, opponent_team, 'MTL', max_candidates)
                
                risk_analysis = {
                    'mtl_deployment': mtl_candidate.forwards + mtl_candidate.defense,
                    'mtl_probability': mtl_candidate.probability_prior,
                    'opponent_counter_responses': [
                        {
                            'players': c.forwards + c.defense,
                            'probability': c.probability_prior,
                            'matchup_prior': getattr(c, 'matchup_prior', 0.0),
                            'threat_level': self._assess_matchup_threat(
                                mtl_candidate.forwards + mtl_candidate.defense,
                                c.forwards + c.defense,
                                opponent_team
                            )
                        }
                        for c in opp_response['candidates'][:3]
                    ]
                }
                mtl_risk_analysis.append(risk_analysis)
            
            result['mtl_risk_analysis'] = mtl_risk_analysis
            
            # 3. Strategic recommendation (lowest risk, highest reward)
            if mtl_risk_analysis:
                best_option = min(mtl_risk_analysis, 
                                key=lambda x: sum(r['threat_level'] * r['probability'] 
                                                 for r in x['opponent_counter_responses']))
                result['strategic_recommendation'] = best_option
        
        else:  # simultaneous_change
            # Both teams changing - predict most likely scenarios
            result['strategic_advantage'] = 'NEUTRAL'
            
            mtl_candidates = self.predict_mtl_deployment(game_state, max_candidates, opponent_team)
            opp_predictions = self.predict(game_state, max_candidates, opponent_team)
            
            # Cross-analyze all combinations
            matchup_matrix = []
            for mtl_cand in mtl_candidates[:3]:
                for opp_pred in opp_predictions.top_predictions[:3]:
                    matchup_score = self._evaluate_matchup_quality(
                        mtl_cand.forwards + mtl_cand.defense,
                        opp_pred['forwards'] + opp_pred['defense'],
                        opponent_team
                    )
                    
                    matchup_matrix.append({
                        'mtl_deployment': mtl_cand.forwards + mtl_cand.defense,
                        'opp_deployment': opp_pred['forwards'] + opp_pred['defense'],
                        'combined_probability': mtl_cand.probability_prior * opp_pred['probability'],
                        'matchup_quality': matchup_score,
                        'expected_value': matchup_score * mtl_cand.probability_prior * opp_pred['probability']
                    })
            
            result['matchup_matrix'] = sorted(matchup_matrix, key=lambda x: x['expected_value'], reverse=True)
            result['strategic_recommendation'] = matchup_matrix[0] if matchup_matrix else None
        
        # Performance tracking
        inference_time = (time.time() - start_time) * 1000
        result['inference_time_ms'] = inference_time
        result['strategic_confidence'] = self._calculate_strategic_confidence(result)
        
        logger.info(f"Strategic prediction completed: {scenario}, {inference_time:.2f}ms")
        return result
    
    def _assess_matchup_threat(self, mtl_players: List[str], opp_players: List[str], opponent_team: str) -> float:
        """
        Assess threat level of opponent deployment against MTL deployment
        Higher values = more dangerous for MTL (opponent has advantage)
        """
        if hasattr(self.candidate_generator, 'compute_matchup_prior'):
            # Opponent's familiarity with MTL = higher threat to MTL
            # This measures how often the opponent has successfully deployed these players against MTL
            opp_familiarity_with_mtl = self.candidate_generator.compute_matchup_prior(
                candidate_players=opp_players,
                opponent_players=mtl_players,
                opponent_team='MTL',  # From opponent's perspective, MTL is the opponent
                situation='5v5'
            )
            
            # MTL's familiarity with opponent = lower threat (MTL has experience)
            mtl_familiarity_with_opp = self.candidate_generator.compute_matchup_prior(
                candidate_players=mtl_players,
                opponent_players=opp_players,
                opponent_team=opponent_team,
                situation='5v5'
            )
            
            # Threat = opponent's advantage - MTL's advantage
            threat_differential = opp_familiarity_with_mtl - mtl_familiarity_with_opp
            
            # Convert to 0-1 threat scale (0.5 = neutral, 1.0 = high threat, 0.0 = MTL advantage)
            threat_score = 0.5 + (threat_differential * 0.5)
            return max(0.0, min(1.0, threat_score))
            
        return 0.5  # Neutral threat if no data
    
    def _evaluate_matchup_quality(self, mtl_players: List[str], opp_players: List[str], opponent_team: str) -> float:
        """
        Evaluate overall matchup quality from MTL perspective
        Higher values = better matchup for MTL
        """
        if hasattr(self.candidate_generator, 'compute_matchup_prior'):
            # MTL's familiarity with this opponent deployment
            mtl_familiarity = self.candidate_generator.compute_matchup_prior(
                candidate_players=mtl_players,
                opponent_players=opp_players,
                opponent_team=opponent_team,
                situation='5v5'
            )
            
            # Opponent's familiarity with MTL deployment (threat to MTL)
            opp_familiarity = self.candidate_generator.compute_matchup_prior(
                candidate_players=opp_players,
                opponent_players=mtl_players,
                opponent_team='MTL',
                situation='5v5'
            )
            
            # Quality = MTL's advantage - opponent's advantage
            return mtl_familiarity - opp_familiarity
        return 0.0
    
    def _calculate_strategic_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence in strategic recommendation"""
        if 'strategic_recommendation' not in result or not result['strategic_recommendation']:
            return 0.0
        
        # Base confidence on probability spread and data quality
        if result['scenario'] == 'mtl_has_last_change':
            # High confidence when we have clear opponent predictions and good MTL responses
            opp_predictions = result.get('opponent_predictions', {}).get('top_deployments', [])
            if opp_predictions:
                top_prob = opp_predictions[0]['probability']
                prob_spread = top_prob - (opp_predictions[1]['probability'] if len(opp_predictions) > 1 else 0)
                return min(0.5 + prob_spread, 0.95)
        
        return 0.7  # Default moderate confidence
    
    def _generate_candidates(self, 
                            game_state: GameState,
                            max_candidates: int,
                            opponent_team: Optional[str] = None) -> List[Candidate]:
        """Generate deployment candidates with caching"""
        
        # Create cache key (include last-change and team role to avoid cross-context leakage)
        last_change_team = getattr(game_state, 'last_change_team', None)
        # Identify decision-maker team role from opponent_team vs MTL
        team_role = 'OPP' if opponent_team and opponent_team != 'MTL' else 'MTL'
        cache_key = f"{game_state.zone}_{game_state.strength_state}_{game_state.score_differential}_{last_change_team}_{team_role}"
        
        # Check cache
        if cache_key in self.candidate_cache:
            cached = self.candidate_cache[cache_key]
            # Filter by currently available players
            available = set(game_state.opp_forwards_available + game_state.opp_defense_available)
            valid_cached = []
            for candidate in cached:
                if all(p in available for p in candidate.forwards + candidate.defense):
                    valid_cached.append(candidate)
            
            if len(valid_cached) >= max_candidates // 2:
                # Use cached candidates plus some new ones
                new_candidates = self._generate_fresh_candidates(
                    game_state, max_candidates - len(valid_cached)
                )
                return valid_cached + new_candidates
        
        # Generate fresh candidates
        candidates = self._generate_fresh_candidates(game_state, max_candidates)
        
        # Update cache
        self.candidate_cache[cache_key] = candidates[:max_candidates//2]
        
        return candidates
    
    def _generate_fresh_candidates(self,
                                  game_state: GameState,
                                  n_candidates: int,
                                  opponent_team: Optional[str] = None) -> List[Candidate]:
        """Generate fresh candidates with hazard-rate availability and trend bias"""
        
        game_situation = {
            'zone': game_state.zone,
            'strength': game_state.strength_state,
            'score_diff': game_state.score_differential,
            'period': game_state.period,
            'time_remaining': game_state.time_remaining
        }
        
        # HAZARD-RATE ENHANCED availability filtering
        enhanced_rest_times = {}
        hazard_adjusted_available = {'forwards': [], 'defense': []}
        
        all_potential_players = game_state.opp_forwards_available + game_state.opp_defense_available
        
        for player_id in all_potential_players:
            current_rest = game_state.player_rest_times.get(player_id, 120.0)
            
            # Use hazard rate model to predict availability
            expected_additional, prob_available = self.predict_time_to_return(
                player_id, game_state.strength_state, current_rest
            )
            
            enhanced_rest_times[player_id] = current_rest
            
            # Include player if probability of availability > 70%
            if prob_available > 0.7:
                if player_id in game_state.opp_forwards_available:
                    hazard_adjusted_available['forwards'].append(player_id)
                elif player_id in game_state.opp_defense_available:
                    hazard_adjusted_available['defense'].append(player_id)
        
        # Generate base candidates
        candidates = self.candidate_generator.generate_candidates(
            game_situation,
            hazard_adjusted_available,
            enhanced_rest_times,
            max_candidates=n_candidates,
            # LAST-CHANGE-AWARE: Pass tactical information for live prediction
            opponent_team=opponent_team,
            last_change_team=game_state.last_change_team if hasattr(game_state, 'last_change_team') else None,
            team_making_change='MTL'  # Live predictor focuses on MTL deployment decisions
        )
        
        # Apply opponent trend bias if available
        if opponent_team:
            mtl_on_ice = game_state.mtl_forwards_on_ice + game_state.mtl_defense_on_ice
            candidates = self.apply_opponent_trend_bias(candidates, opponent_team, mtl_on_ice)
        
        return candidates
    
    def _create_context_features(self, game_state: GameState) -> np.ndarray:
        """Create context feature vector"""
        
        # Basic features
        features = []
        
        # Zone (one-hot)
        zone_features = [0, 0, 0]
        zone_map = {'oz': 0, 'nz': 1, 'dz': 2}
        zone_idx = zone_map.get(game_state.zone, 1)
        zone_features[zone_idx] = 1
        features.extend(zone_features)
        
        # Strength (one-hot)
        strength_features = [0] * 7
        strength_map = {
            '5v5': 0, 'evenStrength': 0,
            '5v4': 1, 'powerPlay': 1,
            '4v5': 2, 'penaltyKill': 2,
            '4v4': 3, '3v3': 4, '6v5': 5, '5v6': 6
        }
        strength_idx = strength_map.get(game_state.strength_state, 0)
        strength_features[strength_idx] = 1
        features.extend(strength_features)
        
        # Score differential (bucketized)
        score_features = [0] * 5
        diff = game_state.score_differential
        if diff <= -2:
            score_features[0] = 1
        elif diff == -1:
            score_features[1] = 1
        elif diff == 0:
            score_features[2] = 1
        elif diff == 1:
            score_features[3] = 1
        else:
            score_features[4] = 1
        features.extend(score_features)
        
        # Time features
        features.append(game_state.period / 3.0)  # Normalized period
        features.append(game_state.period_time / 1200.0)  # Normalized time
        features.append(1.0 if game_state.time_remaining < 120 else 0.0)  # Late game
        
        # Last change features (critical for model differentiation)
        features.append(1.0 if game_state.has_last_change else 0.0)  # MTL has last change
        features.append(1.0 if not game_state.has_last_change else 0.0)  # Opponent has last change
        
        return np.array(features)
    
    def _compute_probabilities(self,
                              candidates: List[Candidate],
                              context: np.ndarray,
                              game_state: GameState) -> np.ndarray:
        """Compute deployment probabilities using the model"""
        
        # Get MTL players on ice (opponents from model perspective)
        opponent_on_ice = game_state.mtl_forwards_on_ice + game_state.mtl_defense_on_ice
        
        # Get previous deployment if available
        previous_deployment = None
        if game_state.recent_deployments:
            previous_deployment = game_state.recent_deployments[-1]
        
        # Convert candidates to format expected by model
        candidate_dicts = [c.to_dict() for c in candidates]
        
        # ENHANCED MODEL PREDICTION: Use comprehensive fatigue data for live predictions
        probabilities = self.model.predict_probabilities(
            candidate_dicts,
            context,
            opponent_on_ice,
            game_state.player_rest_times,  # Legacy game-time rest
            previous_deployment,
            temperature=self.temperature,
            # COMPREHENSIVE FATIGUE INPUTS: Real-time tracking data
            shift_counts=game_state.player_shift_counts_period,        # Shifts this period
            toi_last_period=game_state.player_toi_past_20min,          # TOI rolling 20min
            rest_real_times=game_state.player_rest_real_times,         # Real elapsed rest (includes stoppages)
            intermission_flags=game_state.player_intermission_flags,   # Intermission indicators  
            shift_counts_game=game_state.player_shift_counts_game,     # Total game shifts
            cumulative_toi_game=game_state.player_cumulative_toi_game, # Total game TOI
            ewma_shift_lengths=game_state.player_ewma_shift_lengths,   # EWMA shift patterns
            ewma_rest_lengths=game_state.player_ewma_rest_lengths      # EWMA rest patterns
        )
        
        # Apply candidate priors as Bayesian update
        for i, candidate in enumerate(candidates):
            probabilities[i] *= (1 + 0.1 * candidate.probability_prior)
        
        # Renormalize
        probabilities /= probabilities.sum()
        
        return probabilities
    
    def _generate_explanation(self,
                            candidate: Candidate,
                            game_state: GameState,
                            probability: float) -> str:
        """Generate human-readable explanation for prediction"""
        
        explanations = []
        
        # Probability level
        if probability > 0.5:
            explanations.append("HIGH CONFIDENCE")
        elif probability > 0.3:
            explanations.append("MODERATE CONFIDENCE")
        else:
            explanations.append("LOW CONFIDENCE")
        
        # Zone context
        if game_state.zone == 'dz':
            explanations.append("DZ start - expect defensive lineup")
        elif game_state.zone == 'oz':
            explanations.append("OZ start - expect offensive lineup")
        
        # Strength state
        if 'powerPlay' in game_state.strength_state or '5v4' in game_state.strength_state:
            explanations.append("Power play unit likely")
        elif 'penaltyKill' in game_state.strength_state or '4v5' in game_state.strength_state:
            explanations.append("Penalty kill unit likely")
        
        # Chemistry
        if candidate.chemistry_score > 0.7:
            explanations.append("High chemistry trio")
        
        # Fatigue
        avg_rest = np.mean([game_state.player_rest_times.get(p, 120) 
                           for p in candidate.forwards + candidate.defense])
        if avg_rest < 45:
            explanations.append("Quick change (tired players)")
        elif avg_rest > 150:
            explanations.append("Fresh legs available")
        
        # Score state
        if game_state.score_differential <= -2 and game_state.time_remaining < 300:
            explanations.append("Trailing late - offensive push expected")
        elif game_state.score_differential >= 2 and game_state.time_remaining < 300:
            explanations.append("Protecting lead - defensive structure")
        
        # Matchup specific
        if game_state.has_last_change:
            explanations.append("Opponent has last change advantage")
        
        # MTL-side prior contributions (when MTL has last change)
        if hasattr(candidate, 'matchup_prior') and candidate.matchup_prior > 0:
            explanations.append(f"Familiar matchup (prior: {candidate.matchup_prior:.2f})")
            
            # Check if MTL-side priors contributed (when MTL has last change)
            if hasattr(game_state, 'last_change_team') and game_state.last_change_team == 'MTL':
                # Check if this candidate benefits from MTL-side historical patterns
                candidate_players = candidate.forwards + candidate.defense
                if hasattr(self.candidate_generator, 'mtl_vs_opp_forwards'):
                    mtl_contributions = []
                    for mtl_player in candidate_players:
                        total_mtl_bias = sum(self.candidate_generator.mtl_vs_opp_forwards.get(mtl_player, {}).values())
                        total_def_bias = sum(self.candidate_generator.mtl_defense_vs_opp_forwards.get(mtl_player, {}).values())
                        if total_mtl_bias > 0 or total_def_bias > 0:
                            mtl_contributions.append(mtl_player)
                    
                    if mtl_contributions:
                        explanations.append(f"MTL advantage: {len(mtl_contributions)} players with favorable history")
        
        return " | ".join(explanations)
    
    def _compute_confidence(self, prob: float, all_probs: np.ndarray) -> float:
        """Compute confidence score for a single prediction"""
        
        # Entropy-based confidence
        entropy = -np.sum(all_probs * np.log(all_probs + 1e-10))
        max_entropy = np.log(len(all_probs))
        
        # Normalized confidence (0 = uniform, 1 = certain)
        confidence = 1 - (entropy / max_entropy)
        
        # Weight by probability magnitude
        confidence *= prob
        
        return float(confidence)
    
    def _compute_overall_confidence(self, probabilities: np.ndarray) -> float:
        """Compute overall confidence in predictions"""
        
        # Multiple metrics
        max_prob = np.max(probabilities)
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
        top_2_sum = np.sum(np.sort(probabilities)[-2:])
        
        # Combine metrics
        confidence = 0.4 * max_prob + 0.3 * (1 - entropy/np.log(len(probabilities))) + 0.3 * top_2_sum
        
        return float(np.clip(confidence, 0, 1))
    
    def update_game_state(self,
                         game_state: GameState,
                         actual_deployment: Dict[str, List[str]],
                         current_real_time: Optional[float] = None,
                         stoppage_info: Optional[Dict[str, Any]] = None):
        """
        ENHANCED FATIGUE SYSTEM: Update comprehensive real-time player tracking
        
        Args:
            game_state: Current game state with enhanced fatigue tracking
            actual_deployment: Current deployment (forwards + defense)
            current_real_time: Real elapsed time (includes stoppages), optional
            stoppage_info: Dict with 'type', 'duration' for stoppage tracking
        """
        
        # Store actual outcome for online learning
        self.online_buffer.append({
            'game_state': game_state,
            'prediction': self.prediction_history[-1] if self.prediction_history else None,
            'actual': actual_deployment
        })
        
        # ENHANCED REAL-TIME FATIGUE TRACKING
        current_game_time = game_state.game_time
        current_period_time = game_state.period_time
        current_period = game_state.period
        current_real_time = current_real_time or (current_game_time * 1.2)  # Approximate if not provided
        
        # Track all players in game (on ice + available)
        all_players = set(
            game_state.mtl_forwards_on_ice + game_state.mtl_defense_on_ice +
            game_state.opp_forwards_on_ice + game_state.opp_defense_on_ice +
            game_state.opp_forwards_available + game_state.opp_defense_available
        )
        
        # Current deployment players
        on_ice = set(actual_deployment['forwards'] + actual_deployment['defense'])
        
        # COMPREHENSIVE PLAYER STATE UPDATES
        for player in all_players:
            # Initialize tracking if new player
            if player not in game_state.player_rest_times:
                self._initialize_player_tracking(game_state, player)
            
            if player in on_ice:
                # PLAYER IS ON ICE: Track shift start and update patterns
                if player not in game_state.player_shift_starts:
                    # New shift starting
                    self._start_player_shift(game_state, player, current_game_time, 
                                           current_period_time, current_real_time, current_period)
            else:
                # PLAYER IS OFF ICE: End shift and update comprehensive rest tracking
                if player in game_state.player_shift_starts:
                    # Shift ending - comprehensive tracking update
                    self._end_player_shift(game_state, player, current_game_time, 
                                         current_period_time, current_real_time, current_period)
                
                # Update dual rest signals
                self._update_player_rest(game_state, player, current_game_time, 
                                       current_period_time, current_real_time, current_period)
        
        # STOPPAGE TRACKING: Update stoppage context if provided
        if stoppage_info:
            game_state.last_stoppage_type = stoppage_info.get('type', 'unknown')
            game_state.last_stoppage_duration = stoppage_info.get('duration', 0.0)
            game_state.last_stoppage_time = current_real_time
        
        # Add to recent deployments history
        game_state.recent_deployments.append(
            actual_deployment['forwards'] + actual_deployment['defense']
        )
        
        # UPDATE DECISION CONTEXT AND PHASE FLAGS
        self._update_decision_context(game_state)
        self._update_phase_flags(game_state)
        
        # Trigger online update if buffer is full
        if len(self.online_buffer) >= self.online_update_frequency:
            self._perform_online_update()
    
    def _initialize_player_tracking(self, game_state: GameState, player_id: str):
        """Initialize comprehensive tracking for a new player"""
        
        # Basic tracking
        game_state.player_rest_times[player_id] = 90.0  # Default game-time rest
        game_state.player_shift_lengths[player_id] = 45.0  # Default shift length
        
        # Enhanced fatigue tracking
        game_state.player_rest_real_times[player_id] = 110.0  # Default real-time rest
        game_state.player_intermission_flags[player_id] = 0   # No intermission initially
        
        # Shift and TOI tracking
        game_state.player_shift_counts_period[player_id] = 0   # No shifts this period yet
        game_state.player_shift_counts_game[player_id] = 0     # No game shifts yet
        game_state.player_toi_past_20min[player_id] = 0.0      # No recent TOI
        game_state.player_cumulative_toi_game[player_id] = 0.0 # No cumulative TOI
        
        # EWMA patterns (use realistic defaults from shift priors)
        game_state.player_ewma_shift_lengths[player_id] = 45.0  # Average NHL shift
        game_state.player_ewma_rest_lengths[player_id] = 90.0   # Average NHL rest
        
        # Initialize shift history
        game_state.player_shift_history[player_id] = []
    
    def _start_player_shift(self, game_state: GameState, player_id: str,
                           current_game_time: float, current_period_time: float,
                           current_real_time: float, current_period: int):
        """Track when a player starts a new shift"""
        
        # Record shift start times
        game_state.player_shift_starts[player_id] = current_game_time
        
        # Check for intermission boundary
        player_history = game_state.player_shift_history.get(player_id, [])
        if player_history:
            last_shift = player_history[-1]
            if last_shift.get('period', current_period) != current_period:
                # Player returned after intermission
                game_state.player_intermission_flags[player_id] = 1
                
                # Reset period tracking for new period
                game_state.player_shift_counts_period[player_id] = 0
            else:
                game_state.player_intermission_flags[player_id] = 0
        
        logger.debug(f"Player {player_id} started shift at game_time={current_game_time:.1f}s")
    
    def _end_player_shift(self, game_state: GameState, player_id: str,
                         current_game_time: float, current_period_time: float, 
                         current_real_time: float, current_period: int):
        """Comprehensive tracking when player ends shift"""
        
        if player_id not in game_state.player_shift_starts:
            return  # Player wasn't tracked as starting a shift
            
        # Calculate shift length
        shift_start_game_time = game_state.player_shift_starts[player_id]
        shift_length = current_game_time - shift_start_game_time
        
        # Validate realistic shift bounds
        if 15.0 <= shift_length <= 180.0:  # 15s to 3 minutes
            # Update basic tracking
            game_state.player_shift_lengths[player_id] = shift_length
            
            # SHIFT COUNTING: Increment shift counters
            game_state.player_shift_counts_period[player_id] += 1
            game_state.player_shift_counts_game[player_id] += 1
            
            # TOI ACCUMULATION: Add to time-on-ice tracking
            game_state.player_cumulative_toi_game[player_id] += shift_length
            
            # Update rolling 20-minute TOI window
            toi_20min_cutoff = current_game_time - 1200.0  # 20 minutes ago
            player_history = game_state.player_shift_history.get(player_id, [])
            recent_toi = sum(
                shift.get('shift_length', 0) for shift in player_history
                if shift.get('end_game_time', 0) > toi_20min_cutoff
            ) + shift_length  # Include current shift
            game_state.player_toi_past_20min[player_id] = recent_toi
            
            # SHIFT HISTORY: Record complete shift for EWMA calculations
            shift_record = {
                'start_game_time': shift_start_game_time,
                'end_game_time': current_game_time,
                'start_period_time': game_state.player_shift_starts.get(f"{player_id}_period_start", current_period_time - shift_length),
                'end_period_time': current_period_time,
                'shift_length': shift_length,
                'period': current_period,
                'strength_state': game_state.strength_state,
                'zone': game_state.zone,
                'score_diff': game_state.score_differential
            }
            
            # Initialize or append to shift history
            if player_id not in game_state.player_shift_history:
                game_state.player_shift_history[player_id] = []
            game_state.player_shift_history[player_id].append(shift_record)
            
            # EWMA PATTERN UPDATES: Calculate exponentially weighted moving averages
            self._update_ewma_patterns(game_state, player_id)
            
            logger.debug(f"Player {player_id} ended shift: {shift_length:.1f}s, "
                        f"total_shifts={game_state.player_shift_counts_game[player_id]}, "
                        f"period_shifts={game_state.player_shift_counts_period[player_id]}")
        
        # Remove from shift tracking
        del game_state.player_shift_starts[player_id]
        if f"{player_id}_period_start" in game_state.player_shift_starts:
            del game_state.player_shift_starts[f"{player_id}_period_start"]
    
    def _update_player_rest(self, game_state: GameState, player_id: str,
                           current_game_time: float, current_period_time: float,
                           current_real_time: float, current_period: int):
        """Update dual rest signals for off-ice player"""
        
        # Get last shift info for rest calculation
        player_history = game_state.player_shift_history.get(player_id, [])
        
        if player_history:
            last_shift = player_history[-1]
            last_shift_end_game_time = last_shift.get('end_game_time', current_game_time)
            last_shift_end_period_time = last_shift.get('end_period_time', current_period_time) 
            last_shift_period = last_shift.get('period', current_period)
            
            # DUAL REST CALCULATION: Game-time vs real-time
            if last_shift_period == current_period:
                # Within same period
                rest_game_time = current_game_time - last_shift_end_game_time
                rest_real_time = current_real_time - last_shift_end_game_time  # Approximation
                game_state.player_intermission_flags[player_id] = 0
            else:
                # Across periods - intermission occurred
                rest_game_time = current_period_time  # New period game time
                rest_real_time = 1080.0  # Standard 18-minute intermission
                game_state.player_intermission_flags[player_id] = 1
            
            # Update rest times
            game_state.player_rest_times[player_id] = max(15.0, rest_game_time)
            game_state.player_rest_real_times[player_id] = max(15.0, rest_real_time)
        else:
            # No shift history - use defaults
            game_state.player_rest_times[player_id] = 90.0
            game_state.player_rest_real_times[player_id] = 110.0
            game_state.player_intermission_flags[player_id] = 0
    
    def _update_ewma_patterns(self, game_state: GameState, player_id: str, decay_factor: float = 0.3):
        """Update EWMA patterns for shift and rest lengths"""
        
        player_history = game_state.player_shift_history.get(player_id, [])
        if len(player_history) < 2:
            return  # Need at least 2 shifts for patterns
        
        # Extract recent shift lengths (last 5 shifts)
        recent_shifts = player_history[-5:]
        shift_lengths = [shift.get('shift_length', 45.0) for shift in recent_shifts]
        
        # Calculate EWMA for shift lengths
        if shift_lengths:
            weights = np.array([decay_factor ** i for i in range(len(shift_lengths))])
            weights = weights / weights.sum() if weights.sum() > 0 else weights
            ewma_shift = np.average(shift_lengths, weights=weights)
            game_state.player_ewma_shift_lengths[player_id] = float(ewma_shift)
        
        # Calculate rest intervals between shifts (within same period)
        rest_intervals = []
        for i in range(1, len(player_history)):
            prev_shift = player_history[i-1]
            curr_shift = player_history[i]
            
            # Only calculate rest within same period
            if prev_shift.get('period') == curr_shift.get('period'):
                rest_interval = curr_shift.get('start_game_time', 0) - prev_shift.get('end_game_time', 0)
                if 0 < rest_interval < 600:  # Valid rest (up to 10 minutes)
                    rest_intervals.append(rest_interval)
        
        # Calculate EWMA for rest lengths
        if rest_intervals:
            recent_rests = rest_intervals[-5:]  # Last 5 rest intervals
            weights = np.array([decay_factor ** i for i in range(len(recent_rests))])
            weights = weights / weights.sum() if weights.sum() > 0 else weights
            ewma_rest = np.average(recent_rests, weights=weights)
            game_state.player_ewma_rest_lengths[player_id] = float(ewma_rest)
    
    def _perform_online_update(self):
        """Perform online model update with recent predictions"""
        
        if not self.online_buffer:
            return
        
        # Prepare mini-batch
        correct_predictions = 0
        total_predictions = 0
        
        for record in self.online_buffer:
            if record['prediction']:
                # Check if we predicted correctly
                actual_set = set(record['actual']['forwards'] + record['actual']['defense'])
                
                for pred in record['prediction'].top_predictions:
                    pred_set = set(pred['forwards'] + pred['defense'])
                    if actual_set == pred_set:
                        correct_predictions += 1
                        break
                
                total_predictions += 1
        
        # Calculate accuracy
        if total_predictions > 0:
            accuracy = correct_predictions / total_predictions
            logger.info(f"Online accuracy (last {total_predictions}): {accuracy:.2%}")
        
        # Update model parameters (simplified - in production use proper gradients)
        if accuracy < 0.5 and len(self.online_buffer) > 5:
            # Adjust temperature for better calibration
            self.temperature *= 1.05
            logger.info(f"Adjusted temperature to {self.temperature:.3f}")
        
        # Clear buffer
        self.online_buffer = []
    
    def load_opponent_trends(self, patterns_path: Path, opponent_team: str):
        """Load opponent-specific historical patterns for trend-based priors"""
        
        try:
            with open(patterns_path, 'rb') as f:
                patterns = pickle.load(f)
            
            # Extract opponent-specific matchup data
            if 'opponent_aggregated_matchups' in patterns and opponent_team in patterns['opponent_aggregated_matchups']:
                self.opponent_trends[opponent_team] = patterns['opponent_aggregated_matchups'][opponent_team]
                logger.info(f"✓ Loaded trends for {opponent_team}: {len(self.opponent_trends[opponent_team])} MTL players tracked")
            
            # Extract player-specific rest patterns for hazard modeling
            if 'player_specific_rest' in patterns:
                self._build_hazard_rate_models(patterns['player_specific_rest'])
            
            # LAST-CHANGE-AWARE: Load tactical rotation patterns for live prediction
            if hasattr(self.candidate_generator, 'last_change_rotation_transitions'):
                if 'last_change_rotation_transitions' in patterns:
                    # Update candidate generator with opponent-specific patterns
                    for team, team_patterns in patterns['last_change_rotation_transitions'].items():
                        if opponent_team in team_patterns or team == opponent_team:
                            # Load patterns involving this opponent
                            self.candidate_generator.last_change_rotation_transitions.update(
                                self.candidate_generator._deserialize_nested_dict(patterns['last_change_rotation_transitions'])
                            )
                            logger.info(f"✓ Loaded last-change rotation patterns for {opponent_team}")
                            break
            
        except Exception as e:
            logger.warning(f"Could not load opponent trends: {e}")
    
    def _build_hazard_rate_models(self, rest_patterns: Dict):
        """Build exponential hazard rate models for player return times"""
        
        for player_id, situations in rest_patterns.items():
            player_hazard_models = {}
            
            for situation, rest_data in situations.items():
                if rest_data.get('samples', 0) >= 5:  # Need minimum samples
                    # Extract return time distribution parameters
                    mean_rest = rest_data.get('mean', 90.0)
                    std_rest = rest_data.get('std', 15.0)
                    
                    # Fit exponential distribution: λ = 1/mean
                    lambda_rate = 1.0 / max(mean_rest, 30.0)  # Prevent division by zero
                    
                    # Hazard function: h(t) = λ (constant for exponential)
                    player_hazard_models[situation] = {
                        'lambda': lambda_rate,
                        'mean': mean_rest,
                        'std': std_rest,
                        'samples': rest_data.get('samples', 0)
                    }
            
            if player_hazard_models:
                self.hazard_rate_models[player_id] = player_hazard_models
        
        logger.info(f"✓ Built hazard rate models for {len(self.hazard_rate_models)} players")
    
    def predict_time_to_return(self, player_id: str, situation: str, 
                              current_rest_time: float) -> Tuple[float, float]:
        """
        Predict time until player returns using hazard rate modeling
        
        Args:
            player_id: Player to predict
            situation: Current game situation
            current_rest_time: How long they've been resting
        
        Returns:
            Tuple of (expected_additional_rest, probability_available_now)
        """
        
        if player_id not in self.hazard_rate_models:
            # Use global default
            default_mean = 90.0
            lambda_rate = 1.0 / default_mean
        else:
            models = self.hazard_rate_models[player_id]
            if situation in models:
                lambda_rate = models[situation]['lambda']
                mean_rest = models[situation]['mean']
            else:
                # Use 5v5 as fallback
                fallback_situation = '5v5' if '5v5' in models else list(models.keys())[0]
                lambda_rate = models[fallback_situation]['lambda']
                mean_rest = models[fallback_situation]['mean']
        
        # Exponential survival function: S(t) = exp(-λt)
        # Probability still resting after current_rest_time
        prob_still_resting = np.exp(-lambda_rate * current_rest_time)
        
        # Probability available now
        prob_available = 1.0 - prob_still_resting
        
        # Expected additional rest time (conditional on not yet returned)
        # E[T - t | T > t] = 1/λ (memoryless property of exponential)
        expected_additional = 1.0 / lambda_rate
        
        return float(expected_additional), float(prob_available)
    
    def apply_opponent_trend_bias(self, candidates: List[Candidate], 
                                 opponent_team: str, mtl_on_ice: List[str]) -> List[Candidate]:
        """Apply opponent-specific trend bias to candidate probabilities"""
        
        if opponent_team not in self.opponent_trends:
            return candidates  # No trend data available
        
        trend_data = self.opponent_trends[opponent_team]
        
        for candidate in candidates:
            trend_bias = 0.0
            
            # Calculate trend bias based on historical opponent preferences
            for opp_player in candidate.forwards + candidate.defense:
                for mtl_player in mtl_on_ice:
                    if mtl_player in trend_data and opp_player in trend_data[mtl_player]:
                        # Historical percentage of time opponent used opp_player vs mtl_player
                        historical_pct = trend_data[mtl_player][opp_player]
                        
                        # Convert percentage to logit bias
                        # ψ_trend = log(p_trend / (1 - p_trend))
                        p_trend = max(0.01, min(0.99, historical_pct / 100.0))
                        logit_bias = np.log(p_trend / (1 - p_trend))
                        trend_bias += logit_bias * 0.1  # Scale factor
            
            # Apply trend bias to probability prior
            candidate.probability_prior *= np.exp(trend_bias)
        
        return candidates
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for monitoring"""
        
        stats = {
            'total_predictions': len(self.prediction_history),
            'avg_latency_ms': np.mean(self.latency_tracker) if self.latency_tracker else 0,
            'p95_latency_ms': np.percentile(self.latency_tracker, 95) if self.latency_tracker else 0,
            'max_latency_ms': np.max(self.latency_tracker) if self.latency_tracker else 0,
            'cache_size': len(self.candidate_cache),
            'temperature': self.temperature
        }
        
        # Calculate recent accuracy if available
        if self.prediction_history:
            recent = self.prediction_history[-100:]
            confidences = [r.confidence_score for r in recent]
            stats['avg_confidence'] = np.mean(confidences)
            stats['recent_predictions'] = len(recent)
        
        return stats
    
    def export_predictions(self, output_path: Path):
        """Export recent predictions for analysis"""
        
        if not self.prediction_history:
            logger.warning("No predictions to export")
            return
        
        export_data = []
        for result in self.prediction_history[-1000:]:  # Last 1000 predictions
            export_data.append({
                'timestamp': result.timestamp.isoformat(),
                'game_id': result.game_state.game_id,
                'period': result.game_state.period,
                'time': result.game_state.period_time,
                'zone': result.game_state.zone,
                'strength': result.game_state.strength_state,
                'score_diff': result.game_state.score_differential,
                'top_prediction': result.top_predictions[0] if result.top_predictions else None,
                'confidence': result.confidence_score,
                'latency_ms': result.inference_time_ms,
                'explanation': result.explanations[0] if result.explanations else ""
            })
        
        # Save as JSON
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(export_data)} predictions to {output_path}")

    def handle_period_transition(self, game_state: GameState, new_period: int):
        """Handle period transitions and intermission resets"""
        
        logger.info(f"Period transition: {game_state.period} → {new_period}")
        
        # Update game state for new period
        old_period = game_state.period
        game_state.period = new_period
        game_state.period_time = 0.0  # Reset period time
        
        # Reset period-specific tracking for all players
        for player_id in game_state.player_shift_counts_period:
            game_state.player_shift_counts_period[player_id] = 0
        
        # Mark all players as having intermission (for those who return)
        # This will be updated appropriately when they actually return
        logger.info(f"✓ Reset period tracking for {len(game_state.player_shift_counts_period)} players")
    
    def handle_stoppage_event(self, game_state: GameState, stoppage_type: str, 
                             current_real_time: float):
        """Handle whistles, penalties, icing, timeouts, etc."""
        
        # Calculate stoppage duration if resuming from previous stoppage
        if game_state.last_stoppage_time > 0:
            stoppage_duration = current_real_time - game_state.last_stoppage_time
            game_state.last_stoppage_duration = max(0.0, min(stoppage_duration, 300.0))  # Cap at 5 minutes
        else:
            game_state.last_stoppage_duration = 0.0
        
        # Update stoppage tracking
        game_state.last_stoppage_type = stoppage_type
        game_state.last_stoppage_time = current_real_time
        
        logger.debug(f"Stoppage: {stoppage_type}, duration: {game_state.last_stoppage_duration:.1f}s")
    
    def get_player_fatigue_summary(self, game_state: GameState, player_id: str) -> Dict[str, Any]:
        """Get comprehensive fatigue summary for a specific player"""
        
        if player_id not in game_state.player_rest_times:
            return {"error": "Player not found in game state"}
        
        return {
            # Dual rest signals
            "rest_game_time": game_state.player_rest_times.get(player_id, 90.0),
            "rest_real_time": game_state.player_rest_real_times.get(player_id, 110.0),
            "intermission_flag": bool(game_state.player_intermission_flags.get(player_id, 0)),
            
            # Workload tracking
            "shifts_this_period": game_state.player_shift_counts_period.get(player_id, 0),
            "shifts_total_game": game_state.player_shift_counts_game.get(player_id, 0),
            "toi_past_20min": game_state.player_toi_past_20min.get(player_id, 0.0),
            "toi_cumulative_game": game_state.player_cumulative_toi_game.get(player_id, 0.0),
            
            # Pattern recognition
            "ewma_shift_length": game_state.player_ewma_shift_lengths.get(player_id, 45.0),
            "ewma_rest_length": game_state.player_ewma_rest_lengths.get(player_id, 90.0),
            
            # Derived metrics
            "toi_past_20min_minutes": game_state.player_toi_past_20min.get(player_id, 0.0) / 60.0,
            "toi_cumulative_minutes": game_state.player_cumulative_toi_game.get(player_id, 0.0) / 60.0,
            "avg_shift_length": game_state.player_ewma_shift_lengths.get(player_id, 45.0),
            "total_shifts": len(game_state.player_shift_history.get(player_id, [])),
            
            # Readiness assessment
            "is_well_rested": game_state.player_rest_real_times.get(player_id, 110.0) > 90.0,
            "is_overused": game_state.player_shift_counts_period.get(player_id, 0) > 15,
            "is_heavy_toi": game_state.player_cumulative_toi_game.get(player_id, 0.0) > 1200.0  # >20 minutes
        }
    
    def _update_decision_context(self, game_state: GameState):
        """Update decision role based on last change team"""
        game_state.decision_role = 1 if game_state.last_change_team == 'MTL' else 0
    
    def _update_phase_flags(self, game_state: GameState):
        """Update phase flags based on current game timing and score"""
        # Calculate game seconds
        game_seconds = (game_state.period - 1) * 1200.0 + game_state.period_time
        
        # Late timing flags
        game_state.is_period_late = game_state.period_time >= 1020.0  # >= 17:00 in period
        game_state.is_game_late = game_seconds >= 3300.0  # >= 55:00 total game time
        
        # Strength state checks
        is_pk_situation = game_state.strength_state in ['4v5', 'penaltyKill']
        is_pp_situation = game_state.strength_state in ['5v4', 'powerPlay']
        
        # High-leverage situation flags
        game_state.is_late_pk = is_pk_situation and game_state.is_period_late
        game_state.is_late_pp = is_pp_situation and game_state.is_period_late
        
        # Close and late game flag
        is_close_game = abs(game_state.score_differential) <= 1
        game_state.is_close_and_late = is_close_game and game_state.is_game_late
    
    def log_fatigue_state(self, game_state: GameState, top_players: Optional[List[str]] = None):
        """Log current fatigue state for debugging/monitoring"""
        
        if not top_players:
            # Use all tracked players
            all_players = set(game_state.player_rest_times.keys())
            top_players = list(all_players)[:10]  # First 10 for brevity
        
        logger.info("LIVE FATIGUE STATE:")
        for player_id in top_players[:5]:  # Limit output
            summary = self.get_player_fatigue_summary(game_state, player_id)
            if "error" not in summary:
                logger.info(f"  {player_id}: "
                           f"Rest={summary['rest_real_time']:.0f}s, "
                           f"Shifts={summary['shifts_this_period']}/{summary['shifts_total_game']}, "
                           f"TOI={summary['toi_cumulative_minutes']:.1f}min, "
                           f"EWMA_shift={summary['ewma_shift_length']:.1f}s")


def run_live_simulation():
    """Simulate live prediction for testing"""
    
    # Initialize predictor
    predictor = LiveLinePredictor()
    
    # Create mock game state
    game_state = GameState(
        game_id="test_001",
        period=2,
        period_time=600.0,
        home_team="MTL",
        away_team="TOR",
        home_score=2,
        away_score=1,
        strength_state="5v5",
        zone="dz",
        mtl_forwards_on_ice=["8480018", "8481540", "8483515"],
        mtl_defense_on_ice=["8476875", "8482087"],
        opp_forwards_available=["8479318", "8478483", "8482720", "8475166", "8480801"],
        opp_defense_available=["8475690", "8476853", "8475883", "8476792"]
    )
    
    # Initialize rest times
    all_players = (game_state.mtl_forwards_on_ice + game_state.mtl_defense_on_ice +
                  game_state.opp_forwards_available + game_state.opp_defense_available)
    game_state.player_rest_times = {p: np.random.uniform(30, 180) for p in all_players}
    
    # Run predictions
    logger.info("Starting live simulation...")
    
    for i in range(10):
        # Make prediction
        result = predictor.predict(game_state)
        
        # Display results
        print(f"\n{'='*60}")
        print(f"Prediction {i+1} - {result.game_state.zone.upper()} Zone Start")
        print(f"Score: MTL {game_state.home_score} - {game_state.away_score} TOR")
        print(f"Time: P{game_state.period} {int(game_state.period_time//60)}:{int(game_state.period_time%60):02d}")
        print(f"Inference Time: {result.inference_time_ms:.2f}ms")
        print(f"\nTop Predictions:")
        
        for j, (pred, exp) in enumerate(zip(result.top_predictions, result.explanations), 1):
            print(f"{j}. Probability: {pred['probability']:.2%}")
            print(f"   Forwards: {pred.get('formatted_line', pred['forwards'])}")
            print(f"   Defense: {pred.get('formatted_defense', pred['defense'])}")
            print(f"   {exp}")
        
        print(f"\nOverall Confidence: {result.confidence_score:.2%}")
        
        # Simulate game progression
        game_state.period_time += np.random.uniform(30, 90)
        game_state.zone = np.random.choice(['oz', 'nz', 'dz'])
        
        # Simulate actual deployment
        actual = {
            'forwards': result.top_predictions[0]['forwards'],
            'defense': result.top_predictions[0]['defense']
        }
        predictor.update_game_state(game_state, actual)
    
    # Display performance stats
    stats = predictor.get_performance_stats()
    print(f"\n{'='*60}")
    print("Performance Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def run_strategic_bidirectional_example():
    """
    COMPREHENSIVE BIDIRECTIONAL EXAMPLE for Montreal Canadiens
    Demonstrates how MTL coaches use the strategic deployment system
    """
    predictor = LiveLinePredictor()
    
    # Create realistic game state (MTL vs TOR, late 2nd period, tied game)
    game_state = GameState(
        game_id="20231201_MTL_TOR",
        period=2,
        period_time=1134.5,
        home_team="MTL",
        away_team="TOR", 
        home_score=2,
        away_score=2,
        strength_state="5v5",
        zone="nz",
        
        # Current on-ice players
        mtl_forwards_on_ice=["8480018", "8481540", "8483515"],
        mtl_defense_on_ice=["8476875", "8482087"],
        opp_forwards_on_ice=["8479318", "8478483", "8482720"],
        opp_defense_on_ice=["8475690", "8476853"],
        
        # Available players for changes
        mtl_forwards_available=["8477949", "8478401", "8480893"],
        mtl_defense_available=["8476792", "8477500"],
        opp_forwards_available=["8475166", "8480801", "8481528"],
        opp_defense_available=["8475883", "8476792"],
        
        last_change_team="TOR"
    )
    
    print("="*80)
    print("HEARTBEAT BIDIRECTIONAL STRATEGIC SYSTEM - MTL CANADIENS")
    print("="*80)
    print(f"Game: {game_state.home_team} vs {game_state.away_team} (Tied 2-2)")
    print(f"Situation: Period {game_state.period}, {game_state.strength_state}")
    print(f"Last Change Advantage: {game_state.last_change_team}")
    print()
    
    # STRATEGIC DEPLOYMENT SCENARIOS
    print("SCENARIO: OPPONENT HAS LAST CHANGE - MTL MUST DEPLOY FIRST")
    print("-" * 60)
    
    try:
        strategic_result = predictor.predict_strategic_deployment(
            game_state, 
            scenario='opponent_has_last_change',
            opponent_team='TOR'
        )
        
        print(f"Strategic Analysis Complete ({strategic_result['inference_time_ms']:.1f}ms)")
        print(f"Confidence: {strategic_result['strategic_confidence']:.1%}")
        print()
        print("MTL can now predict both sides and make optimal decisions!")
        
    except Exception as e:
        print(f"Strategic analysis in development: {e}")
    
    print()
    print("="*80)
    print("BIDIRECTIONAL SYSTEM: LEARNING BOTH SIDES FOR TACTICAL ADVANTAGE")
    print("="*80)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Run the strategic bidirectional example
    print("Running Strategic Bidirectional Example...")
    run_strategic_bidirectional_example()
    
    print("\n" + "="*60 + "\n")
    
    # Run the original live simulation
    print("Running Original Live Simulation...")
    run_live_simulation()
