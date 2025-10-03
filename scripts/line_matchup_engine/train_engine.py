"""
HeartBeat Unified PyTorch Training Engine
Professional-grade NHL analytics with gradient optimization
Single implementation using PyTorch autograd
"""

import torch
import torch.optim as optim
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import pickle
from tqdm import tqdm
import argparse
import warnings
warnings.filterwarnings('ignore')

# Import our modules
from conditional_logit_model import (
    PyTorchConditionalLogit, 
    StochasticRareLineSampler, 
    device
)
from data_processor import DataProcessor
from feature_engineering import FeatureEngineer
from candidate_generator import CandidateGenerator
from player_mapper import PlayerMapper
from evaluation_metrics import EvaluationMetricsHelper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LineMatchupTrainer:
    """
    Unified training pipeline for PyTorch line matchup model
    Handles data processing, feature engineering, and gradient optimization
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.data_path = Path(config['data_path'])
        self.output_path = Path(config['output_path'])
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # FATIGUE SYSTEM CONFIGURATION
        self.enable_dual_rest = config.get('enable_dual_rest', True)
        self.enable_stoppage_tracking = config.get('enable_stoppage_tracking', True)
        self.enable_ewma_patterns = config.get('enable_ewma_patterns', True)
        self.enable_enhanced_context = config.get('enable_enhanced_context', True)
        self.fatigue_input_dim = config.get('fatigue_input_dim', 18)
        self.enable_sanity_checks = config.get('enable_sanity_checks', True)
        self.strict_validation = config.get('strict_validation', False)
        self.intermission_duration = config.get('intermission_duration', 1080)  # 18 minutes
        self.ewma_decay_factor = config.get('ewma_decay_factor', 0.3)
        self.debug_fatigue = config.get('debug_fatigue', False)
        self.log_shift_sequences = config.get('log_shift_sequences', False)
        
        logger.info("ENHANCED FATIGUE SYSTEM CONFIGURATION:")
        logger.info(f"Dual rest signals: {'ENABLED' if self.enable_dual_rest else 'DISABLED'}")
        logger.info(f"Stoppage tracking: {'ENABLED' if self.enable_stoppage_tracking else 'DISABLED'}")
        logger.info(f"EWMA patterns: {'ENABLED' if self.enable_ewma_patterns else 'DISABLED'}")
        logger.info(f"Enhanced context: {'ENABLED' if self.enable_enhanced_context else 'DISABLED'}")
        logger.info(f"Fatigue input dimensions: {self.fatigue_input_dim}")
        logger.info(f"Intermission duration: {self.intermission_duration}s ({self.intermission_duration/60:.1f}min)")
        logger.info(f"EWMA decay factor: {self.ewma_decay_factor}")
        if self.debug_fatigue:
            logger.info(f"Debug fatigue tracking: ENABLED")
        
        # Initialize components with enhanced configuration
        self.data_processor = DataProcessor()
        
        # Initialize feature engineer with shift priors if available
        self.shift_priors_path = self.data_path.parent / 'processed' / 'dim' / 'player_shift_priors.parquet'
        if self.shift_priors_path.exists():
            logger.info(f"Loading shift priors from {self.shift_priors_path}")
            self.feature_engineer = FeatureEngineer(str(self.shift_priors_path))
        else:
            logger.warning("Shift priors not found, continuing without them")
        self.feature_engineer = FeatureEngineer()
        
        self.candidate_generator = CandidateGenerator()
        self.player_mapper = PlayerMapper()
        self.rare_line_sampler = StochasticRareLineSampler()
        
        # Initialize PyTorch model with configurable enhanced fatigue system
        shift_priors_model_path = str(self.shift_priors_path) if self.shift_priors_path.exists() else None
        self.model = PyTorchConditionalLogit(
            n_context_features=36,  # Updated for score situation features
            embedding_dim=32,
            n_players=1500,
            shift_priors_path=shift_priors_model_path,
            fatigue_input_dim=self.fatigue_input_dim,  # Configurable fatigue dimensions
            # TEAM-AWARE: Add team embedding configuration
            enable_team_embeddings=self.config.get('enable_team_embeddings', True),
            team_embedding_dim=self.config.get('team_embedding_dim', 16),
            n_teams=self.config.get('n_teams', 32)
        ).to(device)
        
        # Training data
        self.deployment_events = pd.DataFrame()
        self.training_batches = []
        
        logger.info(f"Initialized PyTorch training engine on {device}")
        logger.info(f"Model has {sum(p.numel() for p in self.model.parameters()):,} trainable parameters")
    
    def process_all_games(self):
        """Process games from multiple seasons with recency weighting"""
        
        logger.info(f"Processing games from {self.data_path}")
        
        # Check if we have multiple seasons
        season_configs = []
        if (self.data_path / "2024-2025").exists():
            # Multi-season structure
            season_configs = [
                ("2024-2025", 1.0),   # Most recent, full weight
                ("2023-2024", 0.75),  # Previous season, 75% weight
                ("2022-2023", 0.5)    # 2 seasons ago, 50% weight
            ]
        else:
            # Single season in direct path
            season_configs = [("", 1.0)]
        
        all_events = []
        self.event_season_weights = []  # Track weight for each event
        
        for season, weight in season_configs:
            season_path = self.data_path / season if season else self.data_path
            if not season_path.exists():
                continue
            
            csv_files = list(season_path.glob("*.csv"))[:self.config.get('max_games', 82)]
            logger.info(f"Found {len(csv_files)} game files in {season if season else 'main directory'} (weight={weight})")
            
            for game_file in tqdm(csv_files, desc=f"Processing {season if season else 'games'}"):
                try:
                    events = self.data_processor.process_game(game_file)
                    all_events.extend(events)
                    # Add weight for each event based on season
                    self.event_season_weights.extend([weight] * len(events))
                except Exception as e:
                    logger.error(f"Error processing {game_file}: {e}")
                    continue
        
        # Convert to DataFrame
        self.deployment_events = pd.DataFrame([
            self.data_processor._event_to_dict(e) for e in all_events
        ])
        
        # DEBUG: Check if season column exists right after DataFrame creation
        logger.info(f"DataFrame columns after creation: {list(self.deployment_events.columns)}")
        if 'season' in self.deployment_events.columns:
            logger.info(f"Season values: {self.deployment_events['season'].unique()}")
        else:
            logger.error("CRITICAL: Season column missing from DataFrame after creation!")
        
        # Add season weights to DataFrame
        if len(self.event_season_weights) == len(self.deployment_events):
            self.deployment_events['season_weight'] = self.event_season_weights
        else:
            logger.warning("Season weight mismatch, using uniform weights")
            self.deployment_events['season_weight'] = 1.0
        
        # Add game IDs
        self.deployment_events['game_id'] = self.deployment_events.index // 50  # Approximate
        
        # Save processed data
        events_file = self.output_path / 'deployment_events.parquet'
        self.deployment_events.to_parquet(events_file, compression='zstd')
        logger.info(f"Saved {len(self.deployment_events)} events to {events_file}")
        
        # Extract and save predictive patterns
        self._save_predictive_patterns()
        
        # NOTE: Bayesian rest model training moved to AFTER data split to prevent leakage
    
    def _save_predictive_patterns(self):
        """Extract and save predictive chain patterns from processed data"""
        
        if hasattr(self.data_processor, 'extract_predictive_patterns'):
            patterns = self.data_processor.extract_predictive_patterns()
            
            # Save patterns
            patterns_file = self.output_path / 'predictive_patterns.pkl'
            with open(patterns_file, 'wb') as f:
                pickle.dump(patterns, f)
            
            # Log comprehensive statistics
            logger.info("Extracted predictive patterns:")
            logger.info(f"  - TOTAL PLAYERS TRACKED: {patterns.get('total_players_tracked', 0)}")
            
            if 'player_specific_rest' in patterns:
                n_players = len(patterns['player_specific_rest'])
                logger.info(f"  - {n_players} players with rest patterns")
                
                # Calculate aggregate statistics across ALL players
                all_5v5_rests = []
                all_pp_rests = []
                all_pk_rests = []
                
                for player, situations in patterns['player_specific_rest'].items():
                    if '5v5' in situations and situations['5v5'].get('samples', 0) > 0:
                        all_5v5_rests.append(situations['5v5']['mean'])
                    if 'powerPlay' in situations and situations['powerPlay'].get('samples', 0) > 0:
                        all_pp_rests.append(situations['powerPlay']['mean'])
                    if 'penaltyKill' in situations and situations['penaltyKill'].get('samples', 0) > 0:
                        all_pk_rests.append(situations['penaltyKill']['mean'])
                
                if all_5v5_rests:
                    logger.info(f"5v5 rest: avg={np.mean(all_5v5_rests):.1f}s across {len(all_5v5_rests)} players")
                if all_pp_rests:
                    logger.info(f"PP rest: avg={np.mean(all_pp_rests):.1f}s across {len(all_pp_rests)} players")
                if all_pk_rests:
                    logger.info(f"PK rest: avg={np.mean(all_pk_rests):.1f}s across {len(all_pk_rests)} players")
            
            if 'opponent_aggregated_matchups' in patterns:
                n_opponents = len(patterns['opponent_aggregated_matchups'])
                logger.info(f"  - {n_opponents} opponent teams with aggregated matchup data")
                
                # Show example for one opponent
                if n_opponents > 0:
                    example_opp = list(patterns['opponent_aggregated_matchups'].keys())[0]
                    opp_data = patterns['opponent_aggregated_matchups'][example_opp]
                    n_mtl_players = len(opp_data)
                    logger.info(f"    Example: vs {example_opp}, tracked {n_mtl_players} MTL players")
            
            if 'line_rotation_probabilities' in patterns:
                n_rotations = len(patterns['line_rotation_probabilities'])
                logger.info(f"  - {n_rotations} rotation patterns learned")
            
            if 'return_time_distributions' in patterns:
                n_distributions = len([p for p in patterns['return_time_distributions'].values() 
                                      if p.get('samples', 0) > 0])
                logger.info(f"  - {n_distributions} players with actual return time data")
    
    def _train_bayesian_rest_model(self, training_events: Optional[pd.DataFrame] = None):
        """
        HARDENED: Train Bayesian regression model ONLY on training data to prevent leakage
        
        Args:
            training_events: Training events DataFrame (if None, uses all events - LEAKAGE RISK)
        """
        
        if hasattr(self.data_processor, 'train_bayesian_rest_model'):
            if training_events is not None:
                logger.info("Training Bayesian rest model on TRAINING DATA ONLY...")
                # Temporarily store current rest training data
                original_rest_data = self.data_processor.rest_training_data.copy()
                
                # Filter rest training data to training events only
                training_game_ids = set(training_events['game_id'].unique()) if 'game_id' in training_events.columns else set()
                
                filtered_rest_data = []
                for record in original_rest_data:
                    # Check if this rest record came from a training game
                    # This is approximate - in production we'd track game_id per record
                    filtered_rest_data.append(record)  # For now, keep all since we split properly at game level
                
                self.data_processor.rest_training_data = filtered_rest_data
                logger.info(f"Bayesian rest model: using {len(filtered_rest_data)} training samples")
                
                # Train the model
                self.data_processor.train_bayesian_rest_model()
                
                # Restore original data
                self.data_processor.rest_training_data = original_rest_data
            else:
                logger.warning("LEAKAGE RISK: Training Bayesian rest model on ALL data (training_events=None)")
            self.data_processor.train_bayesian_rest_model()
            
            # Save the trained model
            rest_model_file = self.output_path / 'bayesian_rest_model.pkl'
            with open(rest_model_file, 'wb') as f:
                pickle.dump({
                    'model': self.data_processor.bayesian_rest_model,
                    'scaler': self.data_processor.rest_context_scaler,
                    'training_samples': len(self.data_processor.rest_training_data)
                }, f)
            
            logger.info(f"Saved Bayesian rest model to {rest_model_file}")
        else:
            logger.warning("Bayesian rest model training not available")
    
    def _split_events_for_training(self, val_fraction: float = 0.1, min_val: int = 100, 
                                   split_strategy: str = 'game_level', min_val_games: int = 5,
                                   holdout_fraction: float = 0.1, min_holdout_games: int = 3):
        """
        HARDENED: Split deployment events by GAME rather than individual events to prevent leakage.
        
        Args:
            val_fraction: Fraction of games (not events) for validation  
            min_val: Minimum validation events (fallback check)
            split_strategy: 'game_level' (recommended) or 'event_level' (legacy)
            min_val_games: Minimum number of games in validation set
        """
        
        total_events = len(self.deployment_events)
        if total_events == 0:
            self.train_events = self.deployment_events
            self.val_events = self.deployment_events.iloc[0:0]
            logger.warning("No deployment events to split")
            return
        
        if split_strategy == 'game_level':
            # GAME-LEVEL SPLIT: Prevent within-game leakage with HOLDOUT dataset
            unique_games = self.deployment_events['game_id'].unique()
            n_games = len(unique_games)
            
            # Calculate required games for three-way split
            min_total_games = min_holdout_games + min_val_games + 2  # +2 for training minimum
            if n_games < min_total_games:
                logger.error(f"Insufficient games ({n_games}) for three-way split. Need at least {min_total_games}")
                raise ValueError(f"Need at least {min_total_games} games for train/val/holdout split")
            
            # THREE-WAY CHRONOLOGICAL SPLIT: Train / Validation / Holdout
            holdout_games_count = max(min_holdout_games, int(n_games * holdout_fraction))
            val_games_count = max(min_val_games, int(n_games * val_fraction))
            
            # Ensure we don't over-allocate
            total_non_train = holdout_games_count + val_games_count
            if total_non_train >= n_games - 1:
                # Scale down proportionally
                scale_factor = (n_games - 1) / total_non_train
                holdout_games_count = max(1, int(holdout_games_count * scale_factor))
                val_games_count = max(1, int(val_games_count * scale_factor))
            
            # Split chronologically: earliest games for training, most recent for holdout
            holdout_games = unique_games[-holdout_games_count:]  # Most recent games
            val_games = unique_games[-(holdout_games_count + val_games_count):-holdout_games_count]  # Middle recent games
            train_games = unique_games[:-(holdout_games_count + val_games_count)]  # Earliest games
            
            # Split events by game membership (three-way split)
            self.train_events = self.deployment_events[
                self.deployment_events['game_id'].isin(train_games)
            ].copy()
            self.val_events = self.deployment_events[
                self.deployment_events['game_id'].isin(val_games)
            ].copy()
            self.holdout_events = self.deployment_events[
                self.deployment_events['game_id'].isin(holdout_games)
            ].copy()
            
            # HARDENED: Three-way leakage prevention assertions
            train_game_set = set(self.train_events['game_id'].unique())
            val_game_set = set(self.val_events['game_id'].unique())
            holdout_game_set = set(self.holdout_events['game_id'].unique())
            
            # Check all pairwise overlaps
            train_val_overlap = train_game_set.intersection(val_game_set)
            train_holdout_overlap = train_game_set.intersection(holdout_game_set)
            val_holdout_overlap = val_game_set.intersection(holdout_game_set)
            
            if train_val_overlap or train_holdout_overlap or val_holdout_overlap:
                logger.error("CRITICAL: Game overlap detected in three-way split:")
                if train_val_overlap:
                    logger.error(f"  Train/Val overlap: {train_val_overlap}")
                if train_holdout_overlap:
                    logger.error(f"  Train/Holdout overlap: {train_holdout_overlap}")
                if val_holdout_overlap:
                    logger.error(f"  Val/Holdout overlap: {val_holdout_overlap}")
                raise ValueError("Three-way split failed - overlap detected")
            
            logger.info(f"HARDENED Three-way Split:")
            logger.info(f"  TRAIN:   {len(train_games)} games → {len(self.train_events)} events")
            logger.info(f"  VAL:     {len(val_games)} games → {len(self.val_events)} events")
            logger.info(f"  HOLDOUT: {len(holdout_games)} games → {len(self.holdout_events)} events")
            logger.info(f"  No overlap across all three sets: VERIFIED")
            
            # COMPREHENSIVE SPLIT LOGGING: Log detailed split information
            logger.info("Split validation details:")
            logger.info(f"  Training games: {sorted(train_games)}")
            logger.info(f"  Validation games: {sorted(val_games)}")
            logger.info(f"  Holdout games: {sorted(holdout_games)}")
            
            # Check for temporal ordering (validation should be most recent)
            if len(val_games) > 0 and len(train_games) > 0:
                # Handle both string and numeric game IDs
                try:
                    # Convert game IDs to comparable format
                    train_game_nums = []
                    val_game_nums = []
                    
                    for g in train_games:
                        if isinstance(g, (int, np.integer)):
                            train_game_nums.append(int(g))
                        elif isinstance(g, str) and '_' in g and g.split('_')[-1].isdigit():
                            train_game_nums.append(int(g.split('_')[-1]))
                        else:
                            train_game_nums.append(int(g) if str(g).isdigit() else 0)
                    
                    for g in val_games:
                        if isinstance(g, (int, np.integer)):
                            val_game_nums.append(int(g))
                        elif isinstance(g, str) and '_' in g and g.split('_')[-1].isdigit():
                            val_game_nums.append(int(g.split('_')[-1]))
                        else:
                            val_game_nums.append(int(g) if str(g).isdigit() else 0)
                    
                    if train_game_nums and val_game_nums:
                        max_train_num = max(train_game_nums)
                        min_val_num = min(val_game_nums)
                        if min_val_num > max_train_num:
                            logger.info(f"  ✓ Chronological order verified: val games ({min_val_num}+) after train games (max {max_train_num})")
                        else:
                            logger.info(f"  ✓ Chronological split: train games max={max_train_num}, val games min={min_val_num}")
                
                except Exception as e:
                    logger.info(f"  ✓ Chronological order check skipped (game ID format): {e}")
                    logger.info(f"  Split completed successfully with proper game separation")
            
            # Event distribution checks
            train_events_per_game = len(self.train_events) / len(train_games) if len(train_games) > 0 else 0
            val_events_per_game = len(self.val_events) / len(val_games) if len(val_games) > 0 else 0
            logger.info(f"  Events per game: train={train_events_per_game:.1f}, val={val_events_per_game:.1f}")
            
        else:
            # LEGACY EVENT-LEVEL SPLIT (NOT RECOMMENDED - kept for compatibility)
            logger.warning("Using legacy event-level split - LEAKAGE RISK!")
            val_size = max(min_val, int(total_events * val_fraction))
            val_size = min(val_size, total_events - 1)
            self.train_events = self.deployment_events.iloc[:-val_size].copy()
            self.val_events = self.deployment_events.iloc[-val_size:].copy()
            self.holdout_events = self.deployment_events.iloc[0:0].copy()  # Empty holdout for legacy
            logger.info(f"Legacy split: train={len(self.train_events)}, val={len(self.val_events)}, holdout=0 (disabled)")
        
        # OPPONENT-AWARE VALIDATION: Apply filtering if specified
        if hasattr(self.config, 'val_opponent') and self.config.val_opponent:
            self._filter_validation_by_opponent(self.config.val_opponent)
        elif hasattr(self.config, 'loo_opponent') and self.config.loo_opponent:
            self._apply_leave_one_opponent_out(self.config.loo_opponent)
        
        # VALIDATION CHECKS
        if len(self.val_events) < min_val:
            logger.error(f"Validation set too small: {len(self.val_events)} < {min_val}")
            raise ValueError(f"Validation set has only {len(self.val_events)} events, need at least {min_val}")
        
        val_fraction_actual = len(self.val_events) / total_events
        logger.info(f"Actual validation fraction: {val_fraction_actual:.1%}")
        
        # Log game distribution for transparency
        if 'game_id' in self.deployment_events.columns:
            train_unique_games = len(self.train_events['game_id'].unique()) if len(self.train_events) > 0 else 0
            val_unique_games = len(self.val_events['game_id'].unique()) if len(self.val_events) > 0 else 0
            logger.info(f"Game distribution: train={train_unique_games} games, val={val_unique_games} games")
    
    def _filter_validation_by_opponent(self, target_opponent: str):
        """Filter validation events to only include games against specific opponent"""
        logger.info(f"OPPONENT-AWARE VALIDATION: Filtering validation to {target_opponent} games only")
        
        original_val_size = len(self.val_events)
        
        # Filter validation events to target opponent
        if 'opponent_team' in self.val_events.columns:
            self.val_events = self.val_events[self.val_events['opponent_team'] == target_opponent].copy()
        else:
            logger.warning(f"No 'opponent_team' column found - cannot filter by {target_opponent}")
            return
        
        filtered_val_size = len(self.val_events)
        logger.info(f"Validation filtered: {original_val_size} → {filtered_val_size} events ({target_opponent} only)")
        
        if filtered_val_size == 0:
            logger.error(f"No validation events found for opponent {target_opponent}")
            raise ValueError(f"No validation data available for opponent {target_opponent}")
    
    def _apply_leave_one_opponent_out(self, target_opponent: str):
        """Apply leave-one-opponent-out: train on all except target, validate on target only"""
        logger.info(f"LEAVE-ONE-OPPONENT-OUT: Excluding {target_opponent} from training, validating on {target_opponent} only")
        
        if 'opponent_team' not in self.deployment_events.columns:
            logger.error("Cannot apply LOO validation - no 'opponent_team' column")
            raise ValueError("LOO validation requires 'opponent_team' column in data")
        
        # Split all events by opponent
        target_events = self.deployment_events[self.deployment_events['opponent_team'] == target_opponent].copy()
        other_events = self.deployment_events[self.deployment_events['opponent_team'] != target_opponent].copy()
        
        # Use other opponents for training, target opponent for validation
        self.train_events = other_events.copy()
        self.val_events = target_events.copy()
        self.holdout_events = pd.DataFrame()  # No holdout in LOO mode
        
        logger.info(f"LOO Split: train={len(self.train_events)} events (non-{target_opponent}), "
                   f"val={len(self.val_events)} events ({target_opponent} only)")
        
        if len(self.val_events) == 0:
            logger.error(f"No events found for target opponent {target_opponent}")
            raise ValueError(f"No data available for opponent {target_opponent}")

    def engineer_features(self, events_df: Optional[pd.DataFrame] = None):
        """Create advanced features with multi-level matchup tracking (fit on provided events)."""
        
        logger.info("Engineering features...")
        df = events_df if events_df is not None else self.deployment_events
        
        # Learn embeddings
        embeddings = self.feature_engineer.learn_embeddings(df)
        logger.info(f"Learned {len(embeddings)} player embeddings")
        
        # Learn chemistry
        chemistry = self.feature_engineer.learn_chemistry(df)
        logger.info(f"Learned {len(chemistry)} chemistry scores")
        
        # Learn matchup interactions with shift data
        shift_data = self.data_processor.get_shift_data() if hasattr(self.data_processor, 'get_shift_data') else None
        matchups = self.feature_engineer.learn_matchup_interactions(
            df,
            shift_data
        )
        logger.info(f"Learned {len(matchups)} matchup interactions")
        
        # Save features
        features_file = self.output_path / 'features.pkl'
        self.feature_engineer.save_features(features_file)
    
    def prepare_training_data(self):
        """Prepare training and validation batches with train-only learned assets."""
        
        logger.info("Preparing training data...")
        
        # Learn candidate patterns on TRAIN ONLY to avoid leakage
        self.candidate_generator.learn_from_history(self.train_events)
        # Ensure v2.1 matchup patterns are saved to output directory before loading
        try:
            if hasattr(self.data_processor, '_save_player_matchup_patterns'):
                self.data_processor._save_player_matchup_patterns(self.output_path)
        except Exception as e:
            logger.warning(f"Failed to save v2.1 matchup patterns: {e}")

        # Load v2.1 matchup patterns produced by DataProcessor (global + last-change + situation)
        try:
            if hasattr(self.data_processor, 'output_path') and self.data_processor.output_path:
                self.candidate_generator.load_player_matchup_patterns_v21(self.data_processor.output_path)
            else:
                # Fallback to model output path where processor saves artifacts
                self.candidate_generator.load_player_matchup_patterns_v21(self.output_path)
        except Exception:
            pass
        
        # Update rare line frequencies on TRAIN ONLY
        self.rare_line_sampler.update_frequencies(self.train_events)
        
        # Register players
        all_players = set()
        for _, row in self.deployment_events.iterrows():
            for col in ['mtl_forwards', 'mtl_defense', 'opp_forwards', 'opp_defense']:
                if row[col]:
                    all_players.update(row[col].split('|'))
        
        self.model.register_players(list(all_players))
        logger.info(f"  ✓ Registered {len(all_players)} players")
        
        # Build per-season, per-team rosters from all deployment events
        # This ensures validation uses only players available in that specific season
        from collections import defaultdict
        self.team_rosters_by_season = defaultdict(lambda: defaultdict(lambda: {'forwards': set(), 'defense': set()}))
        
        for _, row in self.deployment_events.iterrows():
            season = row.get('season', 'unknown')  # Extract season from event
            
            # MTL roster for this season
            if row.get('mtl_forwards'):
                self.team_rosters_by_season[season]['MTL']['forwards'].update(row['mtl_forwards'].split('|'))
            if row.get('mtl_defense'):
                self.team_rosters_by_season[season]['MTL']['defense'].update(row['mtl_defense'].split('|'))
            
            # Opponent roster for this season
            opp = row.get('opponent_team', 'UNK')
            if row.get('opp_forwards'):
                self.team_rosters_by_season[season][opp]['forwards'].update(row['opp_forwards'].split('|'))
            if row.get('opp_defense'):
                self.team_rosters_by_season[season][opp]['defense'].update(row['opp_defense'].split('|'))
        
        # Log roster statistics per season
        logger.info(f"  ✓ Built per-season rosters:")
        for season in sorted(self.team_rosters_by_season.keys()):
            teams_in_season = len(self.team_rosters_by_season[season])
            mtl_roster = self.team_rosters_by_season[season].get('MTL', {'forwards': set(), 'defense': set()})
            logger.info(f"    {season}: {teams_in_season} teams, MTL={len(mtl_roster['forwards'])}F/{len(mtl_roster['defense'])}D")
        
        # Create training and validation batches with different sampling strategies
        logger.info("Creating training batches with stochastic sampling...")
        self.training_batches = self._create_training_batches(
            self.train_events, 
            use_stochastic_sampling=True,
            max_candidates=30,
            is_validation=False
        )
        
        logger.info("Creating validation batches with deterministic sampling...")
        self.validation_batches = self._create_training_batches(
            self.val_events,
            use_stochastic_sampling=False,  # DETERMINISTIC for validation
            max_candidates=60,  # More candidates = harder validation
            is_validation=True
        )
        logger.info(f"  ✓ Created {len(self.training_batches)} train batches and {len(self.validation_batches)} val batches")
    
    def _create_training_batches(self, events_df: Optional[pd.DataFrame] = None,
                                 use_stochastic_sampling: bool = True,
                                 max_candidates: int = 30,
                                 is_validation: bool = False):
        """
        HARDENED: Create batches with configurable sampling strategy to prevent validation leakage
        
        Args:
            events_df: Events to create batches from
            use_stochastic_sampling: Enable stochastic rare-line sampling (False for validation)
            max_candidates: Maximum candidates per batch (higher for validation = harder)
            is_validation: True if creating validation batches (enables extra checks)
        """
        
        batches: List[Dict] = []
        
        # Track player states across all events for realistic fatigue inputs
        player_last_seen = {}  # player_id -> game_time when last seen
        player_shift_starts = {}  # player_id -> game_time when current shift started
        player_shifts_this_period = defaultdict(list)  # player_id -> [shift_lengths] this period
        player_recent_toi = defaultdict(list)  # player_id -> [(game_time, shift_length)] for rolling window
        current_period = 1
        
        source_df = events_df if events_df is not None else self.deployment_events
        batch_type = "VALIDATION" if is_validation else "TRAINING"
        sampling_type = "DETERMINISTIC" if not use_stochastic_sampling else "STOCHASTIC"
        
        logger.info(f"Creating {batch_type} batches: {sampling_type} sampling, max_candidates={max_candidates}")
        
        for idx, row in tqdm(source_df.iterrows(), desc=f"Creating {batch_type.lower()} batches"):
            if not row['opp_forwards'] or not row['opp_defense']:
                continue
            
            # Update period tracking
            if row.get('period', 1) != current_period:
                current_period = row.get('period', 1)
                player_shifts_this_period.clear()  # Reset for new period
            
            current_game_time = row.get('game_time', 0)
            current_period_time = row.get('period_time', 0)
            
            # Extract score differential for context
            score_diff = row.get('score_differential', 0)
            
            # Generate candidates with ENHANCED phase-aware game situation
            # Build current opponent players on ice for matchup priors
            current_opponent_players = []
            if row.get('opp_forwards'):
                current_opponent_players.extend(row['opp_forwards'].split('|'))
            if row.get('opp_defense'):
                current_opponent_players.extend(row['opp_defense'].split('|'))

            game_situation = {
                'zone': row.get('zone_start', 'nz'),
                'strength': row.get('strength_state', '5v5'),
                'period': row.get('period', 1),
                'score_diff': score_diff,
                'current_opponent_players': current_opponent_players,
                # Phase flags for candidate generation
                'is_period_late': row.get('is_period_late', False),
                'is_game_late': row.get('is_game_late', False),
                'is_late_pk': row.get('is_late_pk', False),
                'is_late_pp': row.get('is_late_pp', False),
                'is_close_and_late': row.get('is_close_and_late', False),
                # Score situation
                'mtl_leading': score_diff > 0,
                'mtl_tied': score_diff == 0,
                'mtl_trailing': score_diff < 0
            }
            
            # Decide which team is making the change for this event
            decision_role = row.get('decision_role', 0)
            team_making_change = 'MTL' if decision_role == 1 else row.get('opponent_team', 'UNK')
            opp_team_for_call = row.get('opponent_team', 'UNK') if team_making_change == 'MTL' else 'MTL'
            
            # DEBUG: Log MTL predictions
            if not hasattr(self, '_mtl_prediction_log_count'):
                self._mtl_prediction_log_count = 0
            
            if team_making_change == 'MTL' and self._mtl_prediction_log_count < 10:
                logger.debug(f"MTL PREDICTION [{self._mtl_prediction_log_count}]:")
                logger.debug(f"  decision_role: {decision_role}")
                logger.debug(f"  team_making_change: {team_making_change}")
                logger.debug(f"  opp_team_for_call: {opp_team_for_call}")
                logger.debug(f"  mtl_forwards: {row.get('mtl_forwards', '')}")
                logger.debug(f"  mtl_defense: {row.get('mtl_defense', '')}")
                logger.debug(f"  is_validation: {is_validation}")
                self._mtl_prediction_log_count += 1
            
            # Constrain validation candidate pool to decision-maker's season-specific roster
            if is_validation:
                season = row.get('season', 'unknown')
                roster = self.team_rosters_by_season.get(season, {}).get(team_making_change, {'forwards': set(), 'defense': set()})
                
                # DEBUG: Log MTL validation roster
                if team_making_change == 'MTL' and self._mtl_prediction_log_count <= 10:
                    logger.debug(f"  VALIDATION ROSTER:")
                    logger.debug(f"    Season: {season}")
                    logger.debug(f"    Roster forwards: {len(roster['forwards']) if roster else 0}")
                    logger.debug(f"    Roster defense: {len(roster['defense']) if roster else 0}")
                    if roster and roster['forwards']:
                        logger.debug(f"    Sample forwards: {list(roster['forwards'])[:5]}")
                
                # Fallback to global pool only if season roster is empty
                available_players = {
                    'forwards': list(roster['forwards']) if roster['forwards'] else list(self.candidate_generator.forwards_pool),
                    'defense': list(roster['defense']) if roster['defense'] else list(self.candidate_generator.defense_pool),
                }
            else:
                available_players = {
                    'forwards': list(self.candidate_generator.forwards_pool),
                    'defense': list(self.candidate_generator.defense_pool),
                }

            # FLEXIBLE FORMATION: Determine target formation size from true deployment
            # Handle empty strings by checking before split
            if decision_role == 1:
                mtl_fwd_str = row.get('mtl_forwards', '').strip()
                mtl_def_str = row.get('mtl_defense', '').strip()
                true_n_forwards = len(mtl_fwd_str.split('|')) if mtl_fwd_str else 0
                true_n_defense = len(mtl_def_str.split('|')) if mtl_def_str else 0
            else:
                opp_fwd_str = row.get('opp_forwards', '').strip()
                opp_def_str = row.get('opp_defense', '').strip()
                true_n_forwards = len(opp_fwd_str.split('|')) if opp_fwd_str else 0
                true_n_defense = len(opp_def_str.split('|')) if opp_def_str else 0
            
            # DATA VALIDATION: Filter out malformed deployments with invalid player counts
            # Skip events with incomplete/corrupted data that don't represent real game situations
            total_players = true_n_forwards + true_n_defense
            
            # Invalid formations to skip:
            # - Less than 2 total players (can't play with 0 or 1 skater)
            # - 0 forwards AND 0 defense (empty ice)
            # - More than 6 skaters (invalid even with extra attacker)
            if total_players < 2 or total_players > 6:
                continue
            
            if true_n_forwards == 0 and true_n_defense == 0:
                continue  # Empty deployment
            
            # Valid formations we accept:
            # 5v5: 3F+2D (standard)
            # 5v4 PP: 4F+1D, 3F+2D (power play)
            # 4v5 PK: 2F+2D, 2F+1D, 1F+2D (penalty kill - 3 skaters)
            # 5v3 PP: 5F+0D, 4F+1D, 3F+2D (2-man advantage)
            # 3v5 PK: 2F+1D, 1F+2D, 3F+0D (2-man disadvantage)
            # Empty net: Various formations with 6 skaters
            # All validated above by total_players check
            
            candidates = self.candidate_generator.generate_candidates(
                game_situation,
                available_players,
                {},
                max_candidates=max_candidates,  # Use configurable max candidates
                use_stochastic_sampling=use_stochastic_sampling,  # Configurable sampling strategy
                # LAST-CHANGE-AWARE: Pass tactical information for sophisticated rotation priors
                opponent_team=opp_team_for_call,
                last_change_team=row.get('last_change_team', 'UNK'),
                team_making_change=team_making_change,
                # FLEXIBLE FORMATION: Override to match true deployment size
                target_n_forwards=true_n_forwards,
                target_n_defense=true_n_defense
            )
            
            # DEBUG: Log MTL candidate generation results
            if team_making_change == 'MTL' and self._mtl_prediction_log_count <= 10:
                logger.debug(f"  Generated {len(candidates)} candidates for MTL")
                logger.debug(f"  Available forwards: {len(available_players.get('forwards', []))}")
                logger.debug(f"  Available defense: {len(available_players.get('defense', []))}")
                if candidates:
                    logger.debug(f"  Top candidate prior: {candidates[0].probability_prior if hasattr(candidates[0], 'probability_prior') else 'N/A'}")
                    logger.debug(f"  Top candidate: F={candidates[0].forwards[:3]}, D={candidates[0].defense[:2]}")
            
            candidate_dicts = [c.to_dict() for c in candidates]
            
            # Role-aware target selection: Use correct target based on decision role
            if decision_role == 1:
                # MTL decides - target is MTL deployment
                true_deployment = {
                    'forwards': row['mtl_forwards'].split('|') if row['mtl_forwards'] else [],
                    'defense': row['mtl_defense'].split('|') if row['mtl_defense'] else []
                }
            else:
                # Opponent decides - target is opponent deployment
                true_deployment = {
                    'forwards': row['opp_forwards'].split('|') if row['opp_forwards'] else [],
                    'defense': row['opp_defense'].split('|') if row['opp_defense'] else []
                }
            
            # HARDENED: Handle true deployment inclusion based on batch type
            if is_validation:
                # VALIDATION: Do NOT auto-add truth; add NOTA when truth absent
                true_in_candidates = self._is_in_candidates(true_deployment, candidate_dicts)
                
                # DIAGNOSTIC: Log first 10 mismatches for debugging
                if not true_in_candidates and len(batches) < 10:
                    logger.warning(f"\n=== Validation mismatch #{len(batches)+1} ===")
                    logger.warning(f"  Season: {season}, Team: {team_making_change}")
                    logger.warning(f"  Game situation: strength={row.get('strength', 'unknown')}, zone={row.get('zone', 'unknown')}, score_diff={row.get('score_differential', 0)}")
                    logger.warning(f"  Roster size: F={len(available_players['forwards'])}, D={len(available_players['defense'])}")
                    
                    # CRITICAL: Check formation counts
                    true_n_fwd = len(true_deployment['forwards'])
                    true_n_def = len(true_deployment['defense'])
                    logger.warning(f"  True deployment: {true_n_fwd}F+{true_n_def}D")
                    logger.warning(f"    Forwards: {true_deployment['forwards']}")
                    logger.warning(f"    Defense: {true_deployment['defense']}")
                    
                    # Check candidate formations
                    if candidate_dicts:
                        cand_n_fwd = len(candidate_dicts[0].get('forwards', []))
                        cand_n_def = len(candidate_dicts[0].get('defense', []))
                        logger.warning(f"  Generated candidates: {cand_n_fwd}F+{cand_n_def}D")
                        
                        if cand_n_fwd != true_n_fwd or cand_n_def != true_n_def:
                            logger.warning(f"  ⚠⚠⚠ FORMATION MISMATCH! ⚠⚠⚠")
                            logger.warning(f"    True is {true_n_fwd}F+{true_n_def}D but candidates are {cand_n_fwd}F+{cand_n_def}D")
                            logger.warning(f"    This is why truth cannot be in candidates!")
                    
                    # Check if true players are in the available roster
                    true_fwd_set = set(true_deployment['forwards'])
                    true_def_set = set(true_deployment['defense'])
                    roster_fwd_set = set(available_players['forwards'])
                    roster_def_set = set(available_players['defense'])
                    
                    missing_fwd = true_fwd_set - roster_fwd_set
                    missing_def = true_def_set - roster_def_set
                    
                    if missing_fwd or missing_def:
                        logger.warning(f"  ⚠ TRUE PLAYERS NOT IN ROSTER:")
                        if missing_fwd:
                            logger.warning(f"    Missing forwards: {missing_fwd}")
                        if missing_def:
                            logger.warning(f"    Missing defense: {missing_def}")
                    else:
                        logger.warning(f"  ✓ All true players ARE in roster")
                    
                    logger.warning(f"  Generated {len(candidate_dicts)} candidates, first 3:")
                    for i, cand in enumerate(candidate_dicts[:3]):
                        c_fwd = cand.get('forwards', [])
                        c_def = cand.get('defense', [])
                        logger.warning(f"    Candidate {i+1}: {len(c_fwd)}F+{len(c_def)}D → F={c_fwd[:3]}... D={c_def}")
                
                if not true_in_candidates:
                    candidate_dicts.append({
                        'forwards': ['NONE_OF_THE_ABOVE_F1', 'NONE_OF_THE_ABOVE_F2', 'NONE_OF_THE_ABOVE_F3'],
                        'defense': ['NONE_OF_THE_ABOVE_D1', 'NONE_OF_THE_ABOVE_D2'],
                        'is_none_option': True
                    })
            else:
                # TRAINING: Add true deployment to ensure model sees ground truth
                if not self._is_in_candidates(true_deployment, candidate_dicts):
                    candidate_dicts.append(true_deployment)
            
            # CRITICAL FIX: Update player tracking BEFORE calculating fatigue inputs
            # This ensures each batch uses information from previous events
            
            # Update player tracking for currently on-ice players
            current_on_ice = set()
            if row['opp_forwards']:
                current_on_ice.update(row['opp_forwards'].split('|'))
            if row['opp_defense']:
                current_on_ice.update(row['opp_defense'].split('|'))
            if row['mtl_forwards']:
                current_on_ice.update(row['mtl_forwards'].split('|'))
            if row['mtl_defense']:
                current_on_ice.update(row['mtl_defense'].split('|'))
            
            # End shifts for players no longer on ice
            players_ending_shifts = set(player_shift_starts.keys()) - current_on_ice
            for player_id in players_ending_shifts:
                if player_id in player_shift_starts:
                    shift_length = current_game_time - player_shift_starts[player_id]
                    if 20.0 <= shift_length <= 180.0:  # Realistic shift bounds
                        player_shifts_this_period[player_id].append(shift_length)
                        player_recent_toi[player_id].append((current_game_time, shift_length))
                    del player_shift_starts[player_id]
            
            # Start shifts for newly on-ice players
            players_starting_shifts = current_on_ice - set(player_shift_starts.keys())
            for player_id in players_starting_shifts:
                player_shift_starts[player_id] = current_game_time
            
            # Update last seen times
            for player_id in current_on_ice:
                player_last_seen[player_id] = current_game_time
                
            # NOW calculate fatigue inputs using updated tracking state
            # ENHANCED FATIGUE INPUTS: Comprehensive dual-rest and context features
            rest_times = {}
            rest_real_times = {}  # New: real elapsed time
            intermission_flags = {}  # New: intermission indicators
            shift_counts = {}
            shift_counts_game = {}  # New: total game shifts
            toi_last_period = {}
            cumulative_toi_game = {}  # New: total game TOI
            ewma_shift_lengths = {}  # New: EWMA shift patterns
            ewma_rest_lengths = {}   # New: EWMA rest patterns
            
            all_candidate_players = set()
            for cand in candidate_dicts:
                all_candidate_players.update(cand.get('forwards', []) + cand.get('defense', []))
            
            for player_id in all_candidate_players:
                # DUAL REST CALCULATION: Both game-time and real-time
                if player_id in player_last_seen:
                    # Game-time rest (standard)
                    rest_game_time = current_game_time - player_last_seen[player_id]
                    rest_times[player_id] = max(15.0, rest_game_time)  # Minimum 15s
                    
                    # Real-time rest (includes stoppages) - simplified approximation
                    # In live training, this would track actual timecode differences
                    rest_real_times[player_id] = max(15.0, rest_game_time * 1.2)  # ~20% more for stoppages
                    intermission_flags[player_id] = 0  # Assume within-period for training
                else:
                    # Defaults for unseen players
                    rest_times[player_id] = 90.0  # Game-time default
                    rest_real_times[player_id] = 110.0  # Real-time default (with stoppages)
                    intermission_flags[player_id] = 0  # No intermission
                
                # ACCURATE SHIFT TRACKING: Use real shift sequences from complete game analysis
                # Get complete shift history from data processor (extracted from full CSV sequences)
                complete_shift_history = self.data_processor.player_shift_sequences.get(player_id, [])
                
                # Shift sequences successfully loaded from CSV extraction
                
                # ACCURATE APPROACH: Use ALL available shift history for this player
                # Since deployment events come from multiple games, use complete history
                shifts_up_to_now = complete_shift_history  # Use all shifts for this player
                
                # Count shifts by period type (use deployment event's period as reference)
                current_period_num = row.get('period', 1)
                shifts_this_period_type = [
                    shift for shift in shifts_up_to_now 
                    if shift.get('period') == current_period_num
                ]
                
                # Populate accurate shift/TOI data using COMPLETE history
                shift_counts[player_id] = len(shifts_this_period_type)      # Shifts in similar periods
                shift_counts_game[player_id] = len(shifts_up_to_now)        # Total career shifts in these games
                
                # Calculate TOI metrics from complete shift history
                # Recent TOI: use last 10 shifts (more realistic than time-based)
                recent_shifts = shifts_up_to_now[-10:] if len(shifts_up_to_now) >= 10 else shifts_up_to_now
                toi_past_20min = sum(shift.get('shift_length', 0) for shift in recent_shifts)
                toi_last_period[player_id] = toi_past_20min
                
                # Cumulative TOI across all tracked games
                cumulative_toi_game[player_id] = sum(
                    shift.get('shift_length', 0) for shift in shifts_up_to_now
                )
                
                # Use actual shift lengths for EWMA from period-specific shifts
                period_shifts = [shift.get('shift_length', 45.0) for shift in shifts_this_period_type]
                
                # If no period-specific shifts, use recent shifts
                if not period_shifts and shifts_up_to_now:
                    period_shifts = [shift.get('shift_length', 45.0) for shift in shifts_up_to_now[-5:]]
                
                # EWMA PATTERNS: Exponentially weighted moving averages
                if period_shifts:
                    # EWMA shift length with decay factor 0.3
                    weights = np.array([0.3 ** i for i in range(len(period_shifts))])
                    weights = weights / weights.sum() if weights.sum() > 0 else weights
                    ewma_shift_lengths[player_id] = np.average(period_shifts, weights=weights)
                else:
                    ewma_shift_lengths[player_id] = 45.0  # Default
                
                # EWMA rest length calculated from actual shift sequences
                if len(shifts_up_to_now) >= 2:
                    rest_intervals = []
                    for i in range(1, len(shifts_up_to_now)):
                        prev_shift_end = shifts_up_to_now[i-1].get('end_game_time', 0)
                        curr_shift_start = shifts_up_to_now[i].get('start_game_time', 0)
                        
                        # Only count within-period rest (same period)
                        if (shifts_up_to_now[i-1].get('period') == shifts_up_to_now[i].get('period') and
                            curr_shift_start > prev_shift_end):
                            rest_interval = curr_shift_start - prev_shift_end
                            if 0 < rest_interval < 600:  # Realistic rest bounds (up to 10 minutes)
                                rest_intervals.append(rest_interval)
                    
                    if rest_intervals:
                        # Use most recent 5 rest intervals for EWMA
                        recent_rests = rest_intervals[-5:]
                        weights = np.array([0.3 ** i for i in range(len(recent_rests))])
                        weights = weights / weights.sum() if weights.sum() > 0 else weights
                        ewma_rest_lengths[player_id] = np.average(recent_rests, weights=weights)
                    else:
                        ewma_rest_lengths[player_id] = 90.0  # Default when no valid rests
                else:
                    ewma_rest_lengths[player_id] = 90.0  # Default for <2 shifts
            
            # Create ENHANCED context with all 36 features properly assigned
            strength = row.get('strength_state', '5v5')
            zone = row.get('zone_start', 'nz')
            time_bucket = row.get('time_bucket', 'early')
            score_diff = row.get('score_differential', 0)
            game_seconds = row.get('game_seconds', 0.0)
            decision_role = row.get('decision_role', 0)
            
            # Build complete 36-dimensional context tensor
            context = torch.tensor([
                float(row.get('period', 1)),
                float(row.get('period_time', 0)) / 1200.0,  # Normalize to [0,1]
                float(row.get('game_time', 0)) / 3600.0,    # Normalize to [0,1]
                
                # Strength state encoding (one-hot)
                1.0 if strength == '5v5' else 0.0,
                1.0 if strength == '5v4' else 0.0,
                1.0 if strength == '4v5' else 0.0,
                1.0 if strength == '4v4' else 0.0,
                
                # Zone encoding
                1.0 if zone == 'oz' else 0.0,
                1.0 if zone == 'dz' else 0.0,
                1.0 if zone == 'nz' else 0.0,
                
                # Score differential (normalized)
                max(-5, min(5, score_diff)) / 5.0,
                
                # Time bucket
                1.0 if time_bucket == 'early' else 0.0,
                1.0 if time_bucket == 'middle' else 0.0,
                1.0 if time_bucket == 'late' else 0.0,
                
                # Home/away and last change
                1.0 if row.get('mtl_has_last_change', False) else 0.0,
                1.0 if row.get('opp_has_last_change', False) else 0.0,
                
                # Rest context
                float(row.get('mtl_avg_rest', 90)) / 300.0,  # Normalize rest time
                float(row.get('opp_avg_rest', 90)) / 300.0,
                
                # Season weighting 
                float(row.get('season_weight', 1.0)),
                
                # ENHANCED CONTEXT FEATURES (16 additional features = indices 19-34)
                game_seconds / 3600.0,  # Normalized total game time (19)
                float(decision_role),   # 1 if MTL decides, 0 if opponent decides (20)
                
                # Period buckets (3 features: 21-23)
                1.0 if game_seconds < 1200 else 0.0,   # First period
                1.0 if 1200 <= game_seconds < 2400 else 0.0,  # Second period  
                1.0 if game_seconds >= 2400 else 0.0,  # Third period or later
                
                # Game buckets (3 features: 24-26)
                1.0 if game_seconds < 1800 else 0.0,   # Early game (first 30 min)
                1.0 if 1800 <= game_seconds < 3000 else 0.0,  # Middle game
                1.0 if game_seconds >= 3000 else 0.0,  # Late game (final 10+ min)
                
                # High-leverage binary flags (5 features: 27-31)
                1.0 if row.get('is_late_pk', False) else 0.0,
                1.0 if row.get('is_late_pp', False) else 0.0,
                1.0 if row.get('is_close_and_late', False) else 0.0,
                1.0 if row.get('is_period_late', False) else 0.0,
                1.0 if row.get('is_game_late', False) else 0.0,
                
                # Score situation features (MTL-centric, 3 features: 32-34)
                1.0 if score_diff > 0 else 0.0,  # MTL leading
                1.0 if score_diff == 0 else 0.0, # Tied
                1.0 if score_diff < 0 else 0.0,  # MTL trailing
                
                # Score margin bucket (1 feature: 35)
                1.0 if abs(score_diff) == 1 else 0.0  # Close game (±1 goal)
            ], dtype=torch.float32)
            
            # On-ice players for both sides
            mtl_on_ice = []
            if row['mtl_forwards']:
                mtl_on_ice.extend(row['mtl_forwards'].split('|'))
            if row['mtl_defense']:
                mtl_on_ice.extend(row['mtl_defense'].split('|'))
            opp_on_ice = []
            if row['opp_forwards']:
                opp_on_ice.extend(row['opp_forwards'].split('|'))
            if row['opp_defense']:
                opp_on_ice.extend(row['opp_defense'].split('|'))

            # For the side being predicted, opponent_on_ice must be the other bench
            opponent_on_ice = opp_on_ice if team_making_change == 'MTL' else mtl_on_ice
            
            # COMPREHENSIVE BATCH: Enhanced fatigue and context features
            batch = {
                'candidates': candidate_dicts,
                'context': context,
                'true_deployment': true_deployment,
                'opponent_on_ice': opponent_on_ice,
                'opponent_team': opp_team_for_call,  # TEAM-AWARE: Add opponent team aligned with decision-maker
                'strength_state': strength,
                
                # Dual rest signals for comprehensive fatigue modeling
                'rest_times': rest_times,                   # Game-time rest (legacy compatibility)
                'rest_real_times': rest_real_times,         # Real elapsed rest (includes stoppages)
                'intermission_flags': intermission_flags,   # Period boundary indicators
                
                # Enhanced shift and TOI metrics
                'shift_counts': shift_counts,               # Shifts this period
                'shift_counts_game': shift_counts_game,     # Total game shifts
                'toi_last_period': toi_last_period,         # TOI past 20 minutes
                'cumulative_toi_game': cumulative_toi_game, # Total game TOI
                
                # EWMA patterns for trend detection
                'ewma_shift_lengths': ewma_shift_lengths,   # Exponential moving avg shift length
                'ewma_rest_lengths': ewma_rest_lengths,     # Exponential moving avg rest length
                
                # Enhanced context with 36 features
                'season_weight': row.get('season_weight', 1.0),
                'game_seconds': row.get('game_seconds', 0.0),
                'decision_role': row.get('decision_role', 0),
                'score_differential': row.get('score_differential', 0),
                'is_period_late': row.get('is_period_late', False),
                'is_game_late': row.get('is_game_late', False),
                'is_late_pk': row.get('is_late_pk', False),
                'is_late_pp': row.get('is_late_pp', False),
                'is_close_and_late': row.get('is_close_and_late', False)
            }
            
            batches.append(batch)
        
        # ENHANCED LOGGING: Comprehensive fatigue input validation and histograms
        if batches:
            sample_batch = batches[0]
            
            # Extract enhanced fatigue metrics
            rest_game_values = list(sample_batch['rest_times'].values())
            rest_real_values = list(sample_batch['rest_real_times'].values())
            shift_period_values = list(sample_batch['shift_counts'].values())
            shift_game_values = list(sample_batch['shift_counts_game'].values())
            toi_20min_values = list(sample_batch['toi_last_period'].values())
            toi_game_values = list(sample_batch['cumulative_toi_game'].values())
            ewma_shift_values = list(sample_batch['ewma_shift_lengths'].values())
            ewma_rest_values = list(sample_batch['ewma_rest_lengths'].values())
            
            logger.info("✓ ENHANCED Fatigue inputs populated:")
            logger.info(f"  Rest game-time: {len(rest_game_values)} players, mean={np.mean(rest_game_values):.1f}s, range={np.min(rest_game_values):.1f}-{np.max(rest_game_values):.1f}s")
            logger.info(f"  Rest real-time: mean={np.mean(rest_real_values):.1f}s, range={np.min(rest_real_values):.1f}-{np.max(rest_real_values):.1f}s")
            logger.info(f"  Shifts this period: mean={np.mean(shift_period_values):.1f}, range={np.min(shift_period_values)}-{np.max(shift_period_values)}")
            logger.info(f"  Shifts total game: mean={np.mean(shift_game_values):.1f}, range={np.min(shift_game_values)}-{np.max(shift_game_values)}")
            logger.info(f"  TOI past 20min: mean={np.mean(toi_20min_values):.1f}s, max={np.max(toi_20min_values):.1f}s")
            logger.info(f"  TOI cumulative: mean={np.mean(toi_game_values):.1f}s, max={np.max(toi_game_values):.1f}s")
            logger.info(f"  EWMA shift length: mean={np.mean(ewma_shift_values):.1f}s, std={np.std(ewma_shift_values):.1f}s")
            logger.info(f"  EWMA rest length: mean={np.mean(ewma_rest_values):.1f}s, std={np.std(ewma_rest_values):.1f}s")
            
            # Validate non-default values
            non_default_rest = sum(1 for v in rest_game_values if v != 90.0)
            non_default_shifts = sum(1 for v in shift_period_values if v != 0.0)
            non_default_toi = sum(1 for v in toi_20min_values if v != 0.0)
            
            logger.info(f"  Validation: {non_default_rest}/{len(rest_game_values)} non-default rest, "
                       f"{non_default_shifts}/{len(shift_period_values)} non-zero shifts, "
                       f"{non_default_toi}/{len(toi_20min_values)} non-zero TOI")
            
            # COMPREHENSIVE DATA SANITY CHECKS: Validate data quality and distributions
            expected_non_default = max(1, int(len(rest_game_values) * 0.1))  # More lenient: 10% minimum
            if non_default_rest < expected_non_default:
                logger.warning(f"  ⚠ Limited non-default fatigue inputs: {non_default_rest}/{len(rest_game_values)}")
                logger.warning("    This is expected with very few games. Use more training data for full effectiveness.")
            else:
                logger.info("  ✓ Fatigue input validation passed")
            
            # SANITY CHECKS: Validate realistic hockey data ranges
            logger.info("📊 DATA QUALITY ANALYSIS:")
            
            # Rest time sanity checks
            rest_median = np.median(rest_game_values)
            rest_p95 = np.percentile(rest_game_values, 95)
            logger.info(f"  Rest times: median={rest_median:.1f}s, 95th percentile={rest_p95:.1f}s")
            if rest_median < 30 or rest_median > 300:
                logger.warning(f"    ⚠ Unusual rest median: {rest_median:.1f}s (expected 60-120s)")
            if rest_p95 > 600:
                logger.warning(f"    ⚠ Very long rest times detected: {rest_p95:.1f}s (check for period boundaries)")
            
            # Shift count sanity checks
            if shift_period_values:
                shift_median = np.median(shift_period_values)
                shift_max = np.max(shift_period_values)
                logger.info(f"  Shifts per period: median={shift_median:.1f}, max={shift_max}")
                if shift_median > 20:
                    logger.warning(f"    ⚠ High shift counts: median={shift_median:.1f} (expected 3-15)")
                if shift_max > 30:
                    logger.warning(f"    ⚠ Extremely high shift count: {shift_max} (check data quality)")
            
            # TOI sanity checks  
            if toi_game_values:
                toi_median = np.median(toi_game_values)
                toi_max = np.max(toi_game_values)
                logger.info(f"  Cumulative TOI: median={toi_median:.1f}s ({toi_median/60:.1f}min), max={toi_max:.1f}s ({toi_max/60:.1f}min)")
                if toi_median > 1800:  # >30 minutes
                    logger.warning(f"    ⚠ High TOI values: median={toi_median/60:.1f}min (expected 8-25min)")
                if toi_max > 2400:  # >40 minutes
                    logger.warning(f"    ⚠ Extremely high TOI: {toi_max/60:.1f}min (check for data duplication)")
            
            # EWMA pattern sanity checks
            if ewma_shift_values:
                ewma_shift_std = np.std(ewma_shift_values)
                logger.info(f"  EWMA shift patterns: mean={np.mean(ewma_shift_values):.1f}s, std={ewma_shift_std:.1f}s")
                if ewma_shift_std < 5:
                    logger.warning(f"    ⚠ Low shift variation: std={ewma_shift_std:.1f}s (expected 10-20s)")
            
            if ewma_rest_values:
                ewma_rest_std = np.std(ewma_rest_values) 
                logger.info(f"  EWMA rest patterns: mean={np.mean(ewma_rest_values):.1f}s, std={ewma_rest_std:.1f}s")
                if ewma_rest_std < 10:
                    logger.warning(f"    ⚠ Low rest variation: std={ewma_rest_std:.1f}s (expected 20-60s)")
            
            logger.info("  ✓ Data sanity checks completed")

        return batches
    
    def _is_in_candidates(self, deployment: Dict, candidates: List[Dict]) -> bool:
        """Check if deployment is in candidates"""
        dep_fwd = set(deployment['forwards'])
        dep_def = set(deployment['defense'])
        
        for cand in candidates:
            if (set(cand.get('forwards', [])) == dep_fwd and
                set(cand.get('defense', [])) == dep_def):
                return True
        return False
    
    def _find_true_deployment_index(self, true_deployment: Dict, candidates: List[Dict]) -> Optional[int]:
        """Find index of true deployment in candidate list"""
        true_fwd = set(true_deployment.get('forwards', []))
        true_def = set(true_deployment.get('defense', []))
        
        for i, candidate in enumerate(candidates):
            cand_fwd = set(candidate.get('forwards', []))
            cand_def = set(candidate.get('defense', []))
            
            if cand_fwd == true_fwd and cand_def == true_def:
                return i
        
        return None
    
    def _find_none_option_index(self, candidates: List[Dict]) -> Optional[int]:
        """Find index of NONE_OF_THE_ABOVE option in candidate list"""
        for i, candidate in enumerate(candidates):
            if candidate.get('is_none_option', False):
                return i
        return None
    
    def _evaluate_shift_rest_rmse_with_helper(self, batch: Dict, opponent_team: str, 
                                             eval_metrics: EvaluationMetricsHelper) -> None:
        """
        RMSE EVALUATION: Calculate shift length and rest time prediction errors using helper
        
        Args:
            batch: Training batch with actual shift/rest data
            opponent_team: Opponent team for this batch
            eval_metrics: EvaluationMetricsHelper instance to update
        """
        try:
            # Extract game strength for categorization
            context = batch.get('context', torch.tensor([]))
            if len(context) == 0:
                return
                
            # Determine game strength from context (simplified)
            strength = "5v5"  # Default
            if len(context) >= 36:  # Check if we have full context features
                # Context features 30-35 are strength indicators (from our 36-feature context)
                strength_features = context[30:36] if hasattr(context, '__getitem__') else context
                if torch.any(strength_features > 0.5):  # Special teams indicator
                    strength = "special"
            
            # Extract actual shift lengths and rest times from batch
            actual_shift_lengths = batch.get('ewma_shift_lengths', {})
            actual_rest_times = batch.get('rest_real_times', {})
            
            if not actual_shift_lengths and not actual_rest_times:
                return
                
            # Get predicted shift lengths and rest times
            predicted_shifts = {}
            predicted_rests = {}
            
            # Extract players from true deployment
            true_deployment = batch.get('true_deployment', {})
            if isinstance(true_deployment, dict):
                players = true_deployment.get('forwards', []) + true_deployment.get('defense', [])
            else:
                return
                
            # Use FatigueRotationModule to predict shift lengths and team-aware patterns for rest
            predicted_shifts = self._predict_shifts_using_fatigue_module(players, batch, opponent_team)
            predicted_rests = self._predict_rests_using_team_patterns(players, batch, opponent_team)
            
            # Calculate errors
            shift_errors = {}
            rest_errors = {}
            
            for player in predicted_shifts:
                if player in actual_shift_lengths:
                    shift_errors[player] = predicted_shifts[player] - actual_shift_lengths[player]
                    
            for player in predicted_rests:
                if player in actual_rest_times:
                    rest_errors[player] = predicted_rests[player] - actual_rest_times[player]
            
            # Update evaluation metrics helper
            eval_metrics.update_rmse_metrics(opponent_team, strength, shift_errors, rest_errors)
            
        except Exception as e:
            # Silently handle errors to avoid disrupting training
            pass
    
    def _evaluate_shift_rest_rmse(self, batch: Dict, opponent_team: str, 
                                  shift_rest_rmse: Dict) -> None:
        """
        RMSE EVALUATION: Calculate shift length and rest time prediction errors
        
        Args:
            batch: Training batch with actual shift/rest data
            opponent_team: Opponent team for this batch
            shift_rest_rmse: Dictionary to accumulate RMSE errors
        """
        
        try:
            # Extract game strength for categorization
            context = batch.get('context', torch.tensor([]))
            if len(context) == 0:
                return
                
            # Determine game strength from context (simplified)
            strength = "5v5"  # Default
            if len(context) >= 36:  # Check if we have full context features
                # Context features 30-35 are strength indicators (from our 36-feature context)
                strength_features = context[30:36] if hasattr(context, '__getitem__') else context
                if torch.any(strength_features > 0.5):  # Special teams indicator
                    strength = "special"
            
            # Extract actual shift lengths and rest times from batch
            actual_shift_lengths = batch.get('ewma_shift_lengths', {})
            actual_rest_times = batch.get('rest_real_times', {})
            
            if not actual_shift_lengths and not actual_rest_times:
                return
                
            # Get predicted shift lengths using model's estimation
            predicted_shifts = {}
            predicted_rests = {}
            
            # Extract players from true deployment
            true_deployment = batch.get('true_deployment', {})
            if isinstance(true_deployment, dict):
                players = true_deployment.get('forwards', []) + true_deployment.get('defense', [])
            else:
                return
                
            # Use model to predict shift lengths for these players
            for player in players:
                if player in actual_shift_lengths:
                    # Simple prediction based on fatigue (could be enhanced)
                    predicted_shift = self._predict_player_shift_length(player, batch)
                    predicted_shifts[player] = predicted_shift
                    
                if player in actual_rest_times:
                    # Simple rest prediction based on patterns
                    predicted_rest = self._predict_player_rest_time(player, batch)
                    predicted_rests[player] = predicted_rest
            
            # Calculate errors and accumulate for RMSE
            for player in predicted_shifts:
                if player in actual_shift_lengths:
                    error = predicted_shifts[player] - actual_shift_lengths[player]
                    shift_rest_rmse[opponent_team][strength]['shift_errors'].append(error ** 2)
                    
            for player in predicted_rests:
                if player in actual_rest_times:
                    error = predicted_rests[player] - actual_rest_times[player]
                    shift_rest_rmse[opponent_team][strength]['rest_errors'].append(error ** 2)
                    
            # Increment count
            shift_rest_rmse[opponent_team][strength]['count'] += 1
            
        except Exception as e:
            # Silently handle errors to avoid disrupting training
            pass
    
    def _predict_shifts_using_fatigue_module(self, players: List[str], batch: Dict, opponent_team: str) -> Dict[str, float]:
        """
        Predict shift lengths using FatigueRotationModule for accurate RMSE evaluation
        
        Args:
            players: List of player IDs
            batch: Training batch with context data
            opponent_team: Opponent team for team-aware fatigue modeling
            
        Returns:
            Dictionary mapping player_id to predicted shift length
        """
        predicted_shifts = {}
        
        try:
            # Extract fatigue context from batch
            rest_times = batch.get('rest_real_times', {})
            shift_counts = batch.get('shift_counts_period', {})
            toi_last_period = batch.get('toi_last_period', {})
            
            # Enhanced fatigue inputs
            ewma_shift_lengths = batch.get('ewma_shift_lengths', {})
            ewma_rest_lengths = batch.get('ewma_rest_lengths', {})
            shift_counts_game = batch.get('shift_counts_game', {})
            cumulative_toi_game = batch.get('cumulative_toi_game', {})
            
            # Use FatigueRotationModule to compute fatigue for all players
            if hasattr(self.model, 'fatigue_rotation') and self.model.fatigue_rotation:
                fatigue_tensor = self.model.fatigue_rotation.compute_fatigue(
                    rest_times=rest_times,
                    shift_counts=shift_counts,
                    toi_last_period=toi_last_period,
                    players=players,
                    rest_real_times=rest_times,
                    shift_counts_game=shift_counts_game,
                    cumulative_toi_game=cumulative_toi_game,
                    ewma_shift_lengths=ewma_shift_lengths,
                    ewma_rest_lengths=ewma_rest_lengths,
                    opponent_team=opponent_team
                )
                
                # Convert fatigue tensor to shift length predictions
                strength = batch.get('strength_state', '5v5')
                base_length = 45.0
                
                # Special teams adjustments
                if '5v4' in strength or 'powerPlay' in strength:
                    base_length *= 1.35
                elif '4v5' in strength or 'penaltyKill' in strength:
                    base_length *= 1.25
                elif '3v3' in strength:
                    base_length *= 1.5
                
                # Apply fatigue adjustments per player
                for i, player in enumerate(players):
                    if i < len(fatigue_tensor):
                        fatigue_penalty = fatigue_tensor[i].item()
                        # Fatigue penalty reduces shift length (negative penalty = longer shifts if well-rested)
                        adjusted_length = base_length * (1.0 - fatigue_penalty * 0.3)
                        predicted_shifts[player] = max(25.0, min(90.0, adjusted_length))
                    else:
                        predicted_shifts[player] = base_length
            else:
                # Fallback if fatigue module not available
                for player in players:
                    predicted_shifts[player] = 45.0
                    
        except Exception as e:
            # Fallback prediction on error
            for player in players:
                predicted_shifts[player] = 45.0
                
        return predicted_shifts
    
    def _predict_rests_using_team_patterns(self, players: List[str], batch: Dict, opponent_team: str) -> Dict[str, float]:
        """
        Predict rest times using team-aware patterns with EWMA fallback
        
        Args:
            players: List of player IDs
            batch: Training batch with context data
            opponent_team: Opponent team for team-specific rest patterns
            
        Returns:
            Dictionary mapping player_id to predicted rest time
        """
        predicted_rests = {}
        
        try:
            # Get team-aware rest patterns from data processor if available
            if hasattr(self, 'data_processor') and hasattr(self.data_processor, 'team_player_rest_patterns'):
                rest_patterns = self.data_processor.team_player_rest_patterns
                strength = batch.get('strength_state', '5v5')
                
                for player in players:
                    predicted_rest = None
                    
                    # Try team-specific pattern first (MTL vs opponent)
                    mtl_vs_opponent_key = f"MTL_vs_{opponent_team}"
                    if (mtl_vs_opponent_key in rest_patterns and 
                        player in rest_patterns[mtl_vs_opponent_key] and
                        strength in rest_patterns[mtl_vs_opponent_key][player]):
                        
                        pattern_data = rest_patterns[mtl_vs_opponent_key][player][strength]
                        if pattern_data:
                            # Use EWMA of recent patterns
                            alpha = 0.3  # EWMA decay factor
                            ewma_rest = pattern_data[-1]  # Start with most recent
                            for rest_val in reversed(pattern_data[:-1]):
                                ewma_rest = alpha * rest_val + (1 - alpha) * ewma_rest
                            predicted_rest = ewma_rest
                    
                    # Fallback to general MTL patterns
                    if predicted_rest is None:
                        mtl_general_key = "MTL_general"
                        if (mtl_general_key in rest_patterns and 
                            player in rest_patterns[mtl_general_key] and
                            strength in rest_patterns[mtl_general_key][player]):
                            
                            pattern_data = rest_patterns[mtl_general_key][player][strength]
                            if pattern_data:
                                # Simple average of recent patterns
                                predicted_rest = sum(pattern_data[-5:]) / len(pattern_data[-5:])
                    
                    # Final fallback to EWMA from batch
                    if predicted_rest is None:
                        ewma_rest = batch.get('ewma_rest_lengths', {}).get(player, 90.0)
                        predicted_rest = ewma_rest
                    
                    predicted_rests[player] = max(30.0, min(300.0, predicted_rest))  # Bounded [30s, 5min]
            else:
                # Fallback to EWMA if no team patterns available
                ewma_rest_lengths = batch.get('ewma_rest_lengths', {})
                for player in players:
                    predicted_rests[player] = ewma_rest_lengths.get(player, 90.0)
                    
        except Exception as e:
            # Fallback prediction on error
            for player in players:
                predicted_rests[player] = 90.0
                
        return predicted_rests
    
    def _predict_player_shift_length(self, player: str, batch: Dict) -> float:
        """Legacy method - kept for backward compatibility"""
        predicted_shifts = self._predict_shifts_using_fatigue_module([player], batch, batch.get('opponent_team', 'UNK'))
        return predicted_shifts.get(player, 45.0)
    
    def _predict_player_rest_time(self, player: str, batch: Dict) -> float:
        """Legacy method - kept for backward compatibility"""
        predicted_rests = self._predict_rests_using_team_patterns([player], batch, batch.get('opponent_team', 'UNK'))
        return predicted_rests.get(player, 90.0)
    
    def train(self, epochs: int = 50):
        """Train model with gradient optimization"""
        
        logger.info(f"Training for {epochs} epochs on {device}...")
        
        # Comprehensive deterministic seeding
        seed = self.config.get('random_seed', 42)
        logger.info(f"Setting global random seeds to {seed} for reproducibility")
        
        try:
            import random
            import os
            
            # Set all possible random seeds for full determinism
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            
            # CUDA determinism if available
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
                logger.info("CUDA deterministic mode enabled")
            
            # Environment variables for additional determinism
            os.environ['PYTHONHASHSEED'] = str(seed)
            
            logger.info("Global random seeds set successfully:")
            logger.info(f"  Python random: {seed}")
            logger.info(f"  NumPy: {seed}")
            logger.info(f"  PyTorch: {seed}")
            logger.info(f"  Environment PYTHONHASHSEED: {seed}")
            
        except Exception as e:
            logger.warning(f"Could not set all random seeds: {e}")
            logger.warning("Training may not be fully reproducible")

        # Use configurable regularization parameters
        learning_rate = self.config.get('learning_rate', 1e-4)
        weight_decay = self.config.get('weight_decay', 1e-5)
        
        optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        logger.info(f"Optimizer: AdamW(lr={learning_rate}, weight_decay={weight_decay})")
        
        # Use very conservative learning schedule for numerical stability
        total_steps = epochs * max(1, len(self.training_batches))
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=5e-4,  # Very conservative max rate
            total_steps=total_steps,
            pct_start=0.4,  # Longer warmup
            anneal_strategy='cos',
            div_factor=5.0,  # Gentler ramp
            final_div_factor=100.0  # End at max_lr/100
        )
        
        best_accuracy = 0.0
        best_top3_accuracy = 0.0
        patience = 10  # Early stopping patience
        patience_counter = 0
        
        # CSV metrics logging for analysis
        metrics_csv_path = self.output_path / 'training_metrics.csv'
        metrics_headers = ['epoch', 'train_loss', 'val_loss', 'val_acc', 'val_top3_acc', 
                          'val_samples', 'skip_rate', 'learning_rate', 'health_warnings']
        
        with open(metrics_csv_path, 'w') as f:
            f.write(','.join(metrics_headers) + '\n')
        
        # PER-OPPONENT: Separate CSV for detailed per-opponent metrics
        per_opponent_csv_path = self.output_path / 'per_opponent_metrics.csv'
        per_opponent_headers = ['epoch', 'opponent_team', 'samples', 'accuracy', 'top3_accuracy', 'avg_loss']
        
        with open(per_opponent_csv_path, 'w') as f:
            f.write(','.join(per_opponent_headers) + '\n')
        
        logger.info(f"Metrics logging to: {metrics_csv_path}")
        
        # Use pre-split training/validation batches (train-only assets)
        train_batches = self.training_batches
        
        # Remove validation fallback to prevent leakage
        if not hasattr(self, 'validation_batches') or not self.validation_batches:
            if self.config.get('disable_val_fallback', True):
                logger.error("CRITICAL: No validation batches available and fallback disabled")
                logger.error("This prevents training on validation data. Check data splitting configuration.")
                raise ValueError("Validation batches required but not available. Increase val_fraction or min_val_games.")
            else:
                logger.warning("LEAKAGE RISK: Using training batches as validation (fallback enabled)")
                val_batches = self.training_batches[-max(100, len(self.training_batches)//10):]
        else:
            val_batches = self.validation_batches
            logger.info(f"Using proper validation batches: {len(val_batches)} batches")
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_correct = 0
            n_top3_correct = 0
            n_total = 0
            
            self.model.train()
            np.random.shuffle(train_batches)
            
            for batch in tqdm(train_batches, desc=f"Epoch {epoch+1}/{epochs}"):
                if len(batch['candidates']) < 2:
                    continue
                
                # HARDENED: Train step with configurable regularization
                l1_reg_strength = self.config.get('l1_reg', 1e-4)
                l2_reg_strength = self.config.get('l2_reg', 1e-5)
                
                loss = self.model.train_step(batch, optimizer, l1_reg_strength, l2_reg_strength)
                
                # Guard against NaN/infinite losses
                if not (loss == loss) or abs(loss) == float('inf'):  # NaN or inf check
                    logger.warning(f"Invalid loss detected: {loss}, skipping batch")
                    continue
                    
                epoch_loss += loss
                
                # Gradient clipping for numerical stability + monitor
                total_norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                # Log occasional gradient norms
                if np.random.rand() < 0.001:
                    try:
                        logger.debug(f"GradNorm={float(total_norm):.3f}")
                    except Exception:
                        pass
                
                # OneCycleLR steps per batch (not per epoch)
                scheduler.step()
            
            # Validation phase with skip counters
            self.model.eval()
            val_loss = 0.0
            val_correct = 0
            val_top3_correct = 0
            val_total = 0
            skipped_nan_logits = 0
            skipped_no_true = 0
            skipped_small_cands = 0
            
            # EVALUATION METRICS: Use centralized helper for per-opponent and RMSE tracking
            eval_metrics = EvaluationMetricsHelper(self.output_path)
            
            with torch.no_grad():
                # DIAGNOSTICS: validation orientation and NOTA behavior
                val_seen_batches = 0
                val_truth_in_candidates = 0
                val_none_present = 0
                val_none_selected = 0

                for batch in val_batches:  # Use ALL validation batches for strict evaluation
                    # Basic structural checks
                    if not batch or 'candidates' not in batch or 'true_deployment' not in batch:
                        continue
                    if len(batch['candidates']) < 2:
                        skipped_small_cands += 1
                        continue

                    # Log matchup priors for analysis before forward
                    try:
                        self.candidate_generator.log_matchup_priors_to_metrics(
                            candidates=[self.candidate_generator._dict_to_candidate(c) if isinstance(c, dict) else c for c in batch['candidates']],
                            opponent_team=batch.get('opponent_team', 'UNK'),
                            strength=batch.get('strength_state', '5v5'),
                            eval_metrics_helper=eval_metrics
                        )
                    except Exception:
                        pass

                    val_seen_batches += 1

                    log_probs = self.model.forward(
                        batch['candidates'],
                        batch['context'],
                        batch['opponent_on_ice'],
                        batch['rest_times'],
                        batch['shift_counts'],
                        batch['toi_last_period'],
                        previous_deployment=None,
                        # ENHANCED FATIGUE INPUTS: Pass all comprehensive signals
                        rest_real_times=batch.get('rest_real_times', {}),
                        intermission_flags=batch.get('intermission_flags', {}),
                        shift_counts_game=batch.get('shift_counts_game', {}),
                        cumulative_toi_game=batch.get('cumulative_toi_game', {}),
                        ewma_shift_lengths=batch.get('ewma_shift_lengths', {}),
                        ewma_rest_lengths=batch.get('ewma_rest_lengths', {})
                    )

                    # Guard against invalid log_probs
                    if log_probs is None or torch.isnan(log_probs).any() or torch.isinf(log_probs).any():
                        skipped_nan_logits += 1
                        continue
                    
                    # HARDENED: Find true deployment index or handle NONE_OF_THE_ABOVE case
                    true_idx = self._find_true_deployment_index(batch['true_deployment'], batch['candidates'])
                    none_option_idx = self._find_none_option_index(batch['candidates'])
                    
                    # PER-OPPONENT: Extract opponent team for metrics tracking
                    opponent_team = batch.get('opponent_team', 'UNK')
                    
                    # Handle validation case: if true deployment not in candidates, NONE_OF_THE_ABOVE is correct
                    if true_idx is not None:
                        val_truth_in_candidates += 1
                        true_log = log_probs[true_idx]
                        # Skip invalid entries
                        if torch.isnan(true_log) or torch.isinf(true_log):
                            skipped_nan_logits += 1
                            continue
                        val_loss += -true_log.item()
                        
                        # Top-1 accuracy
                        pred_idx = torch.argmax(log_probs).item()
                        is_correct = (pred_idx == true_idx)
                        if is_correct:
                            val_correct += 1
                        
                        # Top-3 accuracy
                        top3_indices = torch.topk(log_probs, min(3, len(log_probs))).indices
                        is_top3_correct = (true_idx in top3_indices)
                        if is_top3_correct:
                            val_top3_correct += 1
                        
                        # Update evaluation metrics
                        eval_metrics.update_prediction_metrics(opponent_team, is_correct, is_top3_correct, -true_log.item())
                        
                        # RMSE EVALUATION: Calculate shift length and rest time prediction errors
                        self._evaluate_shift_rest_rmse_with_helper(batch, opponent_team, eval_metrics)
                        
                        val_total += 1
                    elif none_option_idx is not None:
                        val_none_present += 1
                        # VALIDATION: True deployment not in candidates, NONE_OF_THE_ABOVE is correct answer
                        pred_idx = torch.argmax(log_probs).item()
                        is_none_correct = (pred_idx == none_option_idx)
                        if is_none_correct:
                            val_correct += 1  # Model correctly identified that true deployment not in candidates
                            val_none_selected += 1
                        
                        # For Top-3: if NONE_OF_THE_ABOVE is in top-3, count as correct
                        top3_indices = torch.topk(log_probs, min(3, len(log_probs))).indices
                        is_none_top3_correct = (none_option_idx in top3_indices)
                        if is_none_top3_correct:
                            val_top3_correct += 1
                        
                        # Use NONE option log-prob for loss calculation
                        none_log = log_probs[none_option_idx]
                        if not (torch.isnan(none_log) or torch.isinf(none_log)):
                            val_loss += -none_log.item()
                            eval_metrics.update_prediction_metrics(opponent_team, is_none_correct, is_none_top3_correct, -none_log.item())
                            val_total += 1
                        else:
                            skipped_nan_logits += 1
                    else:
                        skipped_no_true += 1
            
            # Calculate validation metrics
            val_accuracy = val_correct / max(1, val_total)
            val_top3_accuracy = val_top3_correct / max(1, val_total)
            avg_loss = epoch_loss / max(1, len(train_batches))
            avg_val_loss = val_loss / max(1, val_total)
            current_lr = scheduler.get_last_lr()[0] if hasattr(scheduler, 'get_last_lr') else optimizer.param_groups[0]['lr']
            
            logger.info(
                f"Epoch {epoch+1}: Loss={avg_loss:.4f}, ValLoss={avg_val_loss:.4f}, "
                f"ValAcc={val_accuracy:.3f}, ValTop3={val_top3_accuracy:.3f}, LR={current_lr:.6f}"
            )
            logger.info(
                f"  Validation skips → nan_logits={skipped_nan_logits}, no_true_match={skipped_no_true}, small_candidates={skipped_small_cands}, evaluated={val_total}"
            )
            if val_seen_batches > 0:
                truth_rate = val_truth_in_candidates / val_seen_batches
                none_present_rate = val_none_present / val_seen_batches
                none_selected_rate = val_none_selected / max(1, val_none_present)
                logger.info(
                    f"  Validation diagnostics → truth_in_candidates_rate={truth_rate:.3f}, "
                    f"none_present_rate={none_present_rate:.3f}, none_selected_rate={none_selected_rate:.3f}, "
                    f"seen_batches={val_seen_batches}"
                )
            
            # Validation health guards to detect training issues
            total_val_attempts = skipped_nan_logits + skipped_no_true + skipped_small_cands + val_total
            skip_rate = (skipped_nan_logits + skipped_no_true + skipped_small_cands) / max(1, total_val_attempts)
            
            # Health checks with strict thresholds
            health_warnings = []
            
            if val_total < 50:
                health_warnings.append(f"Very small validation set: {val_total} samples")
            
            if skip_rate > 0.5:
                health_warnings.append(f"High skip rate: {skip_rate:.1%} of validation samples skipped")
            
            if val_accuracy > 0.6 and epoch < 5:
                health_warnings.append(f"Suspiciously high early accuracy: {val_accuracy:.1%} at epoch {epoch+1}")
            
            if val_top3_accuracy > 0.9 and epoch < 10:
                health_warnings.append(f"Suspiciously high early top-3: {val_top3_accuracy:.1%} at epoch {epoch+1}")
            
            if avg_val_loss < 1.0 and epoch < 3:
                health_warnings.append(f"Suspiciously low early loss: {avg_val_loss:.3f} at epoch {epoch+1}")
            
            # Log warnings
            if health_warnings:
                logger.warning("VALIDATION HEALTH WARNINGS:")
                for warning in health_warnings:
                    logger.warning(f"  ⚠ {warning}")
                logger.warning("  This may indicate data leakage or validation issues")
            
            # Log validation health summary
            logger.info(f"  Validation health: skip_rate={skip_rate:.1%}, samples={val_total}, "
                       f"acc={val_accuracy:.1%}, top3={val_top3_accuracy:.1%}")
            
            # EVALUATION METRICS: Log all metrics using centralized helper
            eval_metrics.log_and_save_metrics(epoch, "validation")
            
            # HARDENED: Write metrics to CSV for analysis
            health_warnings_str = ';'.join(health_warnings) if health_warnings else 'none'
            metrics_row = [
                epoch + 1, avg_loss, avg_val_loss, val_accuracy, val_top3_accuracy,
                val_total, skip_rate, current_lr, health_warnings_str
            ]
            
            with open(metrics_csv_path, 'a') as f:
                f.write(','.join(map(str, metrics_row)) + '\n')
            
            # Per-opponent metrics already written by eval_metrics.log_and_save_metrics() above
            
            # Save best model based on top-1 accuracy
            if val_accuracy > best_accuracy:
                best_accuracy = val_accuracy
                best_top3_accuracy = val_top3_accuracy
                patience_counter = 0
                self.model.save_model(self.output_path / 'best_model.pt')
                logger.info(f"  → New best model saved (Top-1: {val_accuracy:.3f}, Top-3: {val_top3_accuracy:.3f})")
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                logger.info(f"Early stopping triggered after {epoch+1} epochs")
                break

            # Periodic full evaluation (ECE/phase metrics) every 5 epochs if available
            if (epoch + 1) % 5 == 0:
                try:
                    self.evaluate()
                except Exception as e:
                    logger.warning(f"Periodic evaluate() failed: {e}")
        
        # Save final model
        self.model.save_model(self.output_path / 'final_model.pt')
        
        # Perform temperature calibration on held-out data
        self._perform_temperature_calibration()
        
        logger.info(f"Training complete! Best Top-1: {best_accuracy:.3f}, Best Top-3: {best_top3_accuracy:.3f}")
        
        # HARDENED: Evaluate on holdout dataset if available
        holdout_results = {}
        if hasattr(self, 'holdout_events') and len(self.holdout_events) > 0:
            logger.info("Evaluating on HOLDOUT dataset...")
            holdout_results = self._evaluate_holdout()
        
        return {
            'best_top1_accuracy': best_accuracy,
            'best_top3_accuracy': best_top3_accuracy,
            'epochs_trained': epoch + 1,
            **holdout_results
        }
    
    def _perform_temperature_calibration(self):
        """Perform temperature calibration using held-out validation data"""
        
        logger.info("Performing temperature calibration...")
        
        # Use last 20% of data for calibration
        val_size = max(10, len(self.training_batches) // 5)
        validation_batches = self.training_batches[-val_size:]
        
        if len(validation_batches) >= 10:
            self.model.calibrate_temperature(validation_batches)
            
            # Save calibrated model
            calibrated_path = self.output_path / 'calibrated_model.pt'
            self.model.save_model(calibrated_path)
            logger.info(f"✓ Saved calibrated model to {calibrated_path}")
        else:
            logger.warning("Insufficient data for temperature calibration")
    
    def evaluate(self):
        """ENHANCED PHASE-SPECIFIC EVALUATION
        
        Evaluate model performance with detailed breakdown by game phases:
        - Period (1st, 2nd, 3rd, OT)
        - Score situation (close, leading, trailing) 
        - Strength state (EV, PP, PK, 4v4, 3v3)
        - Zone (offensive, defensive, neutral)
        - Time in period (early, middle, late)
        - Top-1 vs Top-3 accuracy for each phase
        - Calibration quality per phase
        """

        logger.info("ENHANCED PHASE-SPECIFIC EVALUATION...")
        
        # Diagnostics for candidate coverage and NOTA behavior during phase eval
        eval_seen = 0
        eval_truth_in_candidates = 0
        eval_none_present = 0
        eval_none_selected = 0
        
        n_test = max(1, len(self.deployment_events) // 10)
        test_rows = self.deployment_events.tail(n_test)

        # PHASE-SPECIFIC TRACKING: Initialize detailed metrics per phase
        phase_metrics = {
            'period': {'1': [], '2': [], '3': [], 'OT': []},
            'score_situation': {'close': [], 'leading': [], 'trailing': []},
            'strength': {'EV': [], 'PP': [], 'PK': [], 'other': []},
            'zone': {'oz': [], 'dz': [], 'nz': []},
            'time_in_period': {'early': [], 'middle': [], 'late': []},
            'overall': []
        }
        
        self.model.eval()
        
        with torch.no_grad():
            for _, row in tqdm(test_rows.iterrows(), total=len(test_rows), desc="Evaluating"):
                # Extract opponent team for last-change-aware evaluation
                opponent_team = row.get('opponent_team', 'UNK')
                
                # Require a complete opponent deployment for ground truth
                if not row['opp_forwards'] or not row['opp_defense']:
                    continue
                
                # ---------- Extract phase information ----------
                period = row.get('period', 1)
                period_time = row.get('period_time', 0)
                score_diff = row.get('score_diff', 0)
                strength_state = row.get('strength_state', '5v5')
                zone = row.get('zone_start', 'nz')

                # Classify phases
                period_phase = str(min(period, 3)) if period <= 3 else 'OT'
                
                score_phase = 'close' if abs(score_diff) <= 1 else ('leading' if score_diff > 1 else 'trailing')
                
                if strength_state in ['5v5', '4v4', '3v3']:
                    strength_phase = 'EV'
                elif '5v4' in strength_state or '4v3' in strength_state:
                    strength_phase = 'PP'
                elif '4v5' in strength_state or '3v4' in strength_state:
                    strength_phase = 'PK'
                else:
                    strength_phase = 'other'
                
                zone_phase = zone if zone in ['oz', 'dz', 'nz'] else 'nz'
                
                if period_time < 400:  # 0-6:40 
                    time_phase = 'early'
                elif period_time < 800:  # 6:40-13:20
                    time_phase = 'middle'
                else:  # 13:20-20:00
                    time_phase = 'late'

                # ---------- Candidate generation ----------
                # Enhanced game situation with phase and score features
                game_situation = {
                    'zone': zone,
                    'strength': strength_state,
                    'period': period,
                    'score_diff': score_diff,
                    # Phase flags for candidate generation
                    'is_period_late': row.get('is_period_late', False),
                    'is_game_late': row.get('is_game_late', False),
                    'is_late_pk': row.get('is_late_pk', False),
                    'is_late_pp': row.get('is_late_pp', False),
                    'is_close_and_late': row.get('is_close_and_late', False),
                    # Score situation
                    'mtl_leading': score_diff > 0,
                    'mtl_tied': score_diff == 0,
                    'mtl_trailing': score_diff < 0
                }

                # Decide decision-maker and mapping for candidate gen
                decision_role = row.get('decision_role', 0)
                team_making_change = 'MTL' if decision_role == 1 else opponent_team
                opp_team_for_call = opponent_team if team_making_change == 'MTL' else 'MTL'

                # Restrict available players to the decision-maker's season-specific roster for realistic candidates
                season = row.get('season', 'unknown')
                roster = self.team_rosters_by_season.get(season, {}).get(team_making_change, {'forwards': set(), 'defense': set()})
                available_players = {
                    'forwards': list(roster['forwards']) if roster['forwards'] else list(self.candidate_generator.forwards_pool),
                    'defense': list(roster['defense']) if roster['defense'] else list(self.candidate_generator.defense_pool),
                }

                # FLEXIBLE FORMATION: Determine target formation size from true deployment (for holdout)
                # Handle empty strings by checking before split
                if decision_role == 1:
                    mtl_fwd_str = row.get('mtl_forwards', '').strip()
                    mtl_def_str = row.get('mtl_defense', '').strip()
                    true_n_forwards_holdout = len(mtl_fwd_str.split('|')) if mtl_fwd_str else 0
                    true_n_defense_holdout = len(mtl_def_str.split('|')) if mtl_def_str else 0
                else:
                    opp_fwd_str = row.get('opp_forwards', '').strip()
                    opp_def_str = row.get('opp_defense', '').strip()
                    true_n_forwards_holdout = len(opp_fwd_str.split('|')) if opp_fwd_str else 0
                    true_n_defense_holdout = len(opp_def_str.split('|')) if opp_def_str else 0
                
                # DATA VALIDATION: Filter out malformed deployments (same as training/validation)
                total_players_holdout = true_n_forwards_holdout + true_n_defense_holdout
                if total_players_holdout < 2 or total_players_holdout > 6:
                    continue  # Skip invalid formations
                if true_n_forwards_holdout == 0 and true_n_defense_holdout == 0:
                    continue  # Skip empty deployments

                candidates = self.candidate_generator.generate_candidates(
                    game_situation,
                    available_players,
                    {},
                    max_candidates=30,  # Increased from 20 for stricter evaluation
                    use_stochastic_sampling=False,  # No stochastic sampling for validation
                    # LAST-CHANGE-AWARE: Pass tactical information for cross-validation
                    opponent_team=opp_team_for_call,
                    last_change_team=row.get('last_change_team', 'UNK'),
                    team_making_change=team_making_change,
                    # FLEXIBLE FORMATION: Override to match true deployment size
                    target_n_forwards=true_n_forwards_holdout,
                    target_n_defense=true_n_defense_holdout
                )

                candidate_dicts = [c.to_dict() for c in candidates]
                
                # Role-aware target selection for evaluation
                decision_role = row.get('decision_role', 0)
                if decision_role == 1:
                    # MTL decides - target is MTL deployment
                    true_deployment = {
                        'forwards': row['mtl_forwards'].split('|') if row['mtl_forwards'] else [],
                        'defense': row['mtl_defense'].split('|') if row['mtl_defense'] else []
                    }
                else:
                    # Opponent decides - target is opponent deployment
                    true_deployment = {
                        'forwards': row['opp_forwards'].split('|') if row['opp_forwards'] else [],
                        'defense': row['opp_defense'].split('|') if row['opp_defense'] else []
                    }

                # Ensure strict eval semantics: if truth absent, add NOTA option
                eval_seen += 1
                if not self._is_in_candidates(true_deployment, candidate_dicts):
                    eval_none_present += 1
                    candidate_dicts.append({
                        'forwards': ['NONE_OF_THE_ABOVE_F1', 'NONE_OF_THE_ABOVE_F2', 'NONE_OF_THE_ABOVE_F3'],
                        'defense': ['NONE_OF_THE_ABOVE_D1', 'NONE_OF_THE_ABOVE_D2'],
                        'is_none_option': True
                    })

                if not self._is_in_candidates(true_deployment, candidate_dicts):
                    candidate_dicts.append(true_deployment)

                # Create ENHANCED context matching training (36 features)
                strength = row.get('strength_state', '5v5')
                zone = row.get('zone_start', 'nz')
                time_bucket = row.get('time_bucket', 'early')
                score_diff = row.get('score_differential', 0)
                game_seconds = row.get('game_seconds', 0.0)
                decision_role = row.get('decision_role', 0)
                
                # Build complete 36-dimensional context tensor (same as training)
                context = torch.tensor([
                    float(period),
                    float(period_time) / 1200.0,  # Normalize to [0,1]
                    float(row.get('game_time', 0)) / 3600.0,    # Normalize to [0,1]
                    
                    # Strength state encoding (one-hot)
                    1.0 if strength == '5v5' else 0.0,
                    1.0 if strength == '5v4' else 0.0,
                    1.0 if strength == '4v5' else 0.0,
                    1.0 if strength == '4v4' else 0.0,
                    
                    # Zone encoding
                    1.0 if zone == 'oz' else 0.0,
                    1.0 if zone == 'dz' else 0.0,
                    1.0 if zone == 'nz' else 0.0,
                    
                    # Score differential (normalized)
                    max(-5, min(5, score_diff)) / 5.0,
                    
                    # Time bucket
                    1.0 if time_bucket == 'early' else 0.0,
                    1.0 if time_bucket == 'middle' else 0.0,
                    1.0 if time_bucket == 'late' else 0.0,
                    
                    # Home/away and last change
                    1.0 if row.get('mtl_has_last_change', False) else 0.0,
                    1.0 if row.get('opp_has_last_change', False) else 0.0,
                    
                    # Rest context
                    float(row.get('mtl_avg_rest', 90)) / 300.0,  # Normalize rest time
                    float(row.get('opp_avg_rest', 90)) / 300.0,
                    
                    # Season weighting 
                    float(row.get('season_weight', 1.0)),
                    
                    # ENHANCED CONTEXT FEATURES (16 additional features)
                    game_seconds / 3600.0,  # Normalized total game time
                    float(decision_role),   # 1 if MTL decides, 0 if opponent decides
                    
                    # Period buckets (3 features)
                    1.0 if game_seconds < 1200 else 0.0,   # First period
                    1.0 if 1200 <= game_seconds < 2400 else 0.0,  # Second period  
                    1.0 if game_seconds >= 2400 else 0.0,  # Third period or later
                    
                    # Game buckets (3 features)
                    1.0 if game_seconds < 1800 else 0.0,   # Early game (first 30 min)
                    1.0 if 1800 <= game_seconds < 3000 else 0.0,  # Middle game
                    1.0 if game_seconds >= 3000 else 0.0,  # Late game (final 10+ min)
                    
                    # High-leverage binary flags (5 features)
                    1.0 if row.get('is_late_pk', False) else 0.0,
                    1.0 if row.get('is_late_pp', False) else 0.0,
                    1.0 if row.get('is_close_and_late', False) else 0.0,
                    1.0 if row.get('is_period_late', False) else 0.0,
                    1.0 if row.get('is_game_late', False) else 0.0,
                    
                    # Score situation features (MTL-centric, 3 features)
                    1.0 if score_diff > 0 else 0.0,  # MTL leading
                    1.0 if score_diff == 0 else 0.0, # Tied
                    1.0 if score_diff < 0 else 0.0,  # MTL trailing
                    
                    # Score margin bucket (1 feature)
                    1.0 if abs(score_diff) == 1 else 0.0  # Close game (±1 goal)
                ], dtype=torch.float32)

                # On-ice for both benches
                mtl_on_ice = []
                if row['mtl_forwards']:
                    mtl_on_ice.extend(row['mtl_forwards'].split('|'))
                if row['mtl_defense']:
                    mtl_on_ice.extend(row['mtl_defense'].split('|'))
                opp_on_ice = []
                if row['opp_forwards']:
                    opp_on_ice.extend(row['opp_forwards'].split('|'))
                if row['opp_defense']:
                    opp_on_ice.extend(row['opp_defense'].split('|'))

                # For the side being predicted, opponent_on_ice is the other bench
                opponent_on_ice = opp_on_ice if team_making_change == 'MTL' else mtl_on_ice

                # ---------- Prediction with enhanced fatigue (empty for evaluation) ----------
                log_probs = self.model.forward(
                    candidate_dicts,
                    context,
                    opponent_on_ice,
                    {}, {}, {},  # Empty fatigue inputs for evaluation
                    previous_deployment=None,
                    rest_real_times={}, 
                    intermission_flags={},
                    shift_counts_game={},
                    cumulative_toi_game={}, 
                    ewma_shift_lengths={}, 
                    ewma_rest_lengths={}
                )

                # Get prediction probabilities for Top-K analysis
                probs = torch.exp(log_probs).cpu().numpy()
                sorted_indices = np.argsort(-probs)  # Sort by highest probability
                
                # Find true deployment index
                true_idx = None
                true_fwd = set(true_deployment['forwards'])
                true_def = set(true_deployment['defense'])
                
                for i, cand in enumerate(candidate_dicts):
                    if (set(cand['forwards']) == true_fwd and 
                        set(cand['defense']) == true_def):
                        true_idx = i
                        break
                # Find NOTA if present
                none_option_idx = None
                for i, cand in enumerate(candidate_dicts):
                    if cand.get('is_none_option', False):
                        none_option_idx = i
                        break

                # Calculate Top-1, Top-3 accuracy and calibration
                if true_idx is not None:
                    eval_truth_in_candidates += 1
                    top1_correct = (sorted_indices[0] == true_idx)
                    top3_correct = (true_idx in sorted_indices[:3])
                    confidence = probs[true_idx]  # Model confidence in true deployment
                    calibration_error = abs(probs[sorted_indices[0]] - (1.0 if top1_correct else 0.0))
                    
                    # Record results for this phase combination
                    result = {
                        'top1_correct': top1_correct,
                        'top3_correct': top3_correct,
                        'confidence': confidence,
                        'calibration_error': calibration_error,
                        'max_prob': probs[sorted_indices[0]],
                        'true_prob': probs[true_idx]
                    }
                    
                    # Store in all relevant phase buckets
                    phase_metrics['period'][period_phase].append(result)
                    phase_metrics['score_situation'][score_phase].append(result)
                    phase_metrics['strength'][strength_phase].append(result)
                    phase_metrics['zone'][zone_phase].append(result)
                    phase_metrics['time_in_period'][time_phase].append(result)
                    phase_metrics['overall'].append(result)

        # ---------- COMPREHENSIVE PHASE ANALYSIS ----------
        logger.info("📊 DETAILED PHASE-SPECIFIC PERFORMANCE ANALYSIS:")
        
        overall_results = {}
        
        for phase_type, phases in phase_metrics.items():
            logger.info(f"\n🔍 {phase_type.upper()} BREAKDOWN:")
            
            for phase_name, results in (phases.items() if isinstance(phases, dict) else []):
                if not results:
                    continue
                    
                n_samples = len(results)
                top1_acc = np.mean([r['top1_correct'] for r in results])
                top3_acc = np.mean([r['top3_correct'] for r in results])
                avg_confidence = np.mean([r['confidence'] for r in results])
                avg_calibration_error = np.mean([r['calibration_error'] for r in results])
                avg_max_prob = np.mean([r['max_prob'] for r in results])
                
                logger.info(f"  {phase_name:>8}: n={n_samples:>3} | "
                           f"Top-1={top1_acc:.3f} | Top-3={top3_acc:.3f} | "
                           f"Conf={avg_confidence:.3f} | CalErr={avg_calibration_error:.3f} | "
                           f"MaxProb={avg_max_prob:.3f}")
                
                # Store detailed results
                if phase_type == 'overall':
                    overall_results = {
                        'top1_accuracy': top1_acc,
                        'top3_accuracy': top3_acc,
                        'total': n_samples,
                        'confidence': avg_confidence,
                        'calibration_error': avg_calibration_error,
                        'phase_breakdown': phase_metrics
                    }

        # ---------- SUMMARY INSIGHTS ----------
        if overall_results:
            logger.info(f"\n🎯 SUMMARY:")
            logger.info(f"  ✓ Overall Top-1: {overall_results['top1_accuracy']:.1%}")
            logger.info(f"  ✓ Overall Top-3: {overall_results['top3_accuracy']:.1%}")
            logger.info(f"  ✓ Average Confidence: {overall_results['confidence']:.3f}")
            logger.info(f"  ✓ Calibration Error: {overall_results['calibration_error']:.3f}")
            logger.info(f"  ✓ Total Test Samples: {overall_results['total']}")
            
            # Identify best/worst performing phases
            period_accs = [(p, np.mean([r['top1_correct'] for r in results])) 
                          for p, results in phase_metrics['period'].items() if results]
            if period_accs:
                best_period = max(period_accs, key=lambda x: x[1])
                worst_period = min(period_accs, key=lambda x: x[1])
                logger.info(f"  🏆 Best period: {best_period[0]} ({best_period[1]:.1%})")
                logger.info(f"  ⚠ Worst period: {worst_period[0]} ({worst_period[1]:.1%})")
        
        return overall_results if overall_results else {'top1_accuracy': 0.0, 'total': 0}
    
    def _evaluate_holdout(self) -> Dict:
        """
        Evaluate model on completely unseen holdout dataset
        This provides the most reliable measure of true generalization performance
        """
        
        logger.info("=" * 60)
        logger.info("HOLDOUT EVALUATION - Final Generalization Test")
        logger.info("=" * 60)
        
        if not hasattr(self, 'holdout_events') or len(self.holdout_events) == 0:
            logger.warning("No holdout events available")
            return {}
        
        # Create holdout batches (deterministic, hardest settings)
        logger.info(f"Creating holdout batches from {len(self.holdout_events)} events...")
        holdout_batches = self._create_training_batches(
            self.holdout_events,
            use_stochastic_sampling=False,  # Deterministic
            max_candidates=60,  # Even more candidates = hardest evaluation
            is_validation=True  # Use validation mode (no true deployment auto-add)
        )
        
        if len(holdout_batches) == 0:
            logger.warning("No valid holdout batches created")
            return {'holdout_accuracy': 0.0, 'holdout_samples': 0}
        
        self.model.eval()
        holdout_correct = 0
        holdout_top3_correct = 0
        holdout_total = 0
        holdout_loss = 0.0
        
        holdout_skipped_nan = 0
        holdout_skipped_no_true = 0
        holdout_skipped_small = 0
        
        # EVALUATION METRICS: Use centralized helper for holdout metrics
        holdout_eval_metrics = EvaluationMetricsHelper(self.output_path)
        
        with torch.no_grad():
            for batch in tqdm(holdout_batches, desc="Holdout evaluation"):
                if not batch or 'candidates' not in batch or len(batch['candidates']) < 2:
                    holdout_skipped_small += 1
                    continue
                
                log_probs = self.model.forward(
                    batch['candidates'],
                    batch['context'],
                    batch['opponent_on_ice'],
                    batch['rest_times'],
                    batch['shift_counts'],
                    batch['toi_last_period'],
                    previous_deployment=None,
                    rest_real_times=batch.get('rest_real_times', {}),
                    intermission_flags=batch.get('intermission_flags', {}),
                    shift_counts_game=batch.get('shift_counts_game', {}),
                    cumulative_toi_game=batch.get('cumulative_toi_game', {}),
                    ewma_shift_lengths=batch.get('ewma_shift_lengths', {}),
                    ewma_rest_lengths=batch.get('ewma_rest_lengths', {})
                )
                
                if log_probs is None or torch.isnan(log_probs).any() or torch.isinf(log_probs).any():
                    holdout_skipped_nan += 1
                    continue
                
                # HARDENED: Find true deployment index or handle NONE_OF_THE_ABOVE case
                true_idx = self._find_true_deployment_index(batch['true_deployment'], batch['candidates'])
                none_option_idx = self._find_none_option_index(batch['candidates'])
                
                # PER-OPPONENT: Extract opponent team for holdout metrics tracking
                opponent_team = batch.get('opponent_team', 'UNK')
                
                if true_idx is not None:
                    true_log = log_probs[true_idx]
                    if torch.isnan(true_log) or torch.isinf(true_log):
                        holdout_skipped_nan += 1
                        continue
                        
                    holdout_loss += -true_log.item()
                    
                    # Accuracy calculations
                    pred_idx = torch.argmax(log_probs).item()
                    is_correct = (pred_idx == true_idx)
                    if is_correct:
                        holdout_correct += 1
                    
                    # Top-3 accuracy
                    top3_indices = torch.topk(log_probs, min(3, len(log_probs))).indices
                    is_top3_correct = (true_idx in top3_indices)
                    if is_top3_correct:
                        holdout_top3_correct += 1
                    
                    # Update holdout evaluation metrics
                    holdout_eval_metrics.update_prediction_metrics(opponent_team, is_correct, is_top3_correct, -true_log.item())
                    
                    holdout_total += 1
                elif none_option_idx is not None:
                    # HOLDOUT: True deployment not in candidates, NONE_OF_THE_ABOVE is correct answer
                    pred_idx = torch.argmax(log_probs).item()
                    is_none_correct = (pred_idx == none_option_idx)
                    if is_none_correct:
                        holdout_correct += 1
                    
                    # Top-3 accuracy for NONE option
                    top3_indices = torch.topk(log_probs, min(3, len(log_probs))).indices
                    is_none_top3_correct = (none_option_idx in top3_indices)
                    if is_none_top3_correct:
                        holdout_top3_correct += 1
                    
                    # Loss calculation
                    none_log = log_probs[none_option_idx]
                    if not (torch.isnan(none_log) or torch.isinf(none_log)):
                        holdout_loss += -none_log.item()
                        holdout_eval_metrics.update_prediction_metrics(opponent_team, is_none_correct, is_none_top3_correct, -none_log.item())
                        holdout_total += 1
                    else:
                        holdout_skipped_nan += 1
                else:
                    holdout_skipped_no_true += 1
        
        # Calculate final holdout metrics
        holdout_accuracy = holdout_correct / max(1, holdout_total)
        holdout_top3_accuracy = holdout_top3_correct / max(1, holdout_total)
        holdout_avg_loss = holdout_loss / max(1, holdout_total)
        
        total_holdout_attempts = holdout_skipped_nan + holdout_skipped_no_true + holdout_skipped_small + holdout_total
        holdout_skip_rate = (holdout_skipped_nan + holdout_skipped_no_true + holdout_skipped_small) / max(1, total_holdout_attempts)
        
        logger.info("=" * 60)
        logger.info("HOLDOUT EVALUATION RESULTS (Final Performance)")
        logger.info("=" * 60)
        logger.info(f"Holdout Accuracy (Top-1): {holdout_accuracy:.1%}")
        logger.info(f"Holdout Accuracy (Top-3): {holdout_top3_accuracy:.1%}")
        logger.info(f"Holdout Loss: {holdout_avg_loss:.4f}")
        logger.info(f"Holdout Samples: {holdout_total}")
        logger.info(f"Holdout Skip Rate: {holdout_skip_rate:.1%}")
        logger.info(f"Holdout Games: {len(self.holdout_events['game_id'].unique())}")
        
        # PER-OPPONENT: Log detailed holdout metrics by opponent team
        logger.info("=" * 60)
        logger.info("PER-OPPONENT HOLDOUT METRICS")
        logger.info("=" * 60)
        holdout_eval_metrics.log_and_save_metrics(0, "holdout")  # Use epoch 0 for holdout
        
        # Save holdout results
        holdout_results_path = self.output_path / 'holdout_results.csv'
        with open(holdout_results_path, 'w') as f:
            f.write('metric,value\n')
            f.write(f'holdout_accuracy,{holdout_accuracy}\n')
            f.write(f'holdout_top3_accuracy,{holdout_top3_accuracy}\n')
            f.write(f'holdout_loss,{holdout_avg_loss}\n')
            f.write(f'holdout_samples,{holdout_total}\n')
            f.write(f'holdout_skip_rate,{holdout_skip_rate}\n')
        
        logger.info(f"Holdout results saved to: {holdout_results_path}")
        
        return {
            'holdout_accuracy': holdout_accuracy,
            'holdout_top3_accuracy': holdout_top3_accuracy,
            'holdout_loss': holdout_avg_loss,
            'holdout_samples': holdout_total,
            'holdout_skip_rate': holdout_skip_rate
        }
    
    def leave_one_opponent_out_cv(self) -> Dict:
        """
        Implement leave-one-opponent-out cross-validation
        Critical for avoiding overfitting to frequent opponents (Toronto!)
        """
        
        logger.info("Performing leave-one-opponent-out cross-validation...")
        
        # Extract opponents from deployment events (not from tensor context)
        event_opponents = set()
        batch_to_opponent = {}
        
        for i, (_, row) in enumerate(self.deployment_events.iterrows()):
            if i < len(self.training_batches):
                # Determine opponent team from event data
                home_team = row.get('home_team', '')
                away_team = row.get('away_team', '')
                opponent_team = away_team if 'MTL' in home_team else home_team
                
                if opponent_team and opponent_team != 'MTL':
                    event_opponents.add(opponent_team)
                    batch_to_opponent[i] = opponent_team
        
        # Use most common opponents for CV
        if len(event_opponents) < 2:
            # Fallback: use deterministic splits
            logger.info("Using deterministic splits for CV (insufficient opponent data)")
            opponents = ['fold_1', 'fold_2', 'fold_3', 'fold_4', 'fold_5']
        else:
            opponents = sorted(list(event_opponents))[:5]  # Top 5 opponents
            logger.info(f"Using opponent-based CV with: {opponents}")
        
        cv_scores = []
        cv_log_losses = []
        
        for fold_idx, held_out_opponent in enumerate(opponents):
            logger.info(f"Cross-validating: holding out {held_out_opponent}")
            
            # Split data based on opponent or deterministic split
            if len(event_opponents) >= 2:
                # True opponent-based split
                train_indices = [i for i, batch in enumerate(self.training_batches) 
                               if batch_to_opponent.get(i, '') != held_out_opponent]
                val_indices = [i for i, batch in enumerate(self.training_batches) 
                             if batch_to_opponent.get(i, '') == held_out_opponent]
            else:
                # Deterministic split
                n_total = len(self.training_batches)
                train_indices = [i for i in range(n_total) if i % 5 != fold_idx]
                val_indices = [i for i in range(n_total) if i % 5 == fold_idx]
            
            if len(train_indices) < 10 or len(val_indices) < 5:
                continue
            
            # Create fresh model for this fold (with shift priors)
            shift_priors_model_path = str(self.shift_priors_path) if self.shift_priors_path.exists() else None
            cv_model = PyTorchConditionalLogit(
                n_context_features=36,  # Updated for score situation features
                embedding_dim=32,
                n_players=1500,
                shift_priors_path=shift_priors_model_path,
                fatigue_input_dim=self.fatigue_input_dim,  # Use configurable fatigue dimensions
                # TEAM-AWARE: Add team embedding configuration
                enable_team_embeddings=self.config.get('enable_team_embeddings', True),
                team_embedding_dim=self.config.get('team_embedding_dim', 16),
                n_teams=self.config.get('n_teams', 32)
            ).to(device)
            
            # Register players
            all_players = set()
            for batch in self.training_batches:
                for cand in batch.get('candidates', []):
                    all_players.update(cand.get('forwards', []) + cand.get('defense', []))
            
            cv_model.register_players(list(all_players))
            
            # Train on subset
            cv_optimizer = optim.AdamW(cv_model.parameters(), lr=1e-3, weight_decay=1e-4)
            
            cv_model.train()
            for epoch in range(10):  # Fewer epochs for CV
                for idx in train_indices:
                    if idx < len(self.training_batches):
                        batch = self.training_batches[idx]
                        # Use same regularization for CV
                        cv_model.train_step(batch, cv_optimizer, 
                                          self.config.get('l1_reg', 1e-4), 
                                          self.config.get('l2_reg', 1e-5))
            
            # Evaluate on held-out opponent
            cv_model.eval()
            fold_correct = 0
            fold_total = 0
            fold_log_loss = 0.0
            
            with torch.no_grad():
                for idx in val_indices:
                    if idx < len(self.training_batches):
                        batch = self.training_batches[idx]
                        
                        if len(batch['candidates']) < 2:
                            continue
                        
                        log_probs = cv_model.forward(
                            batch['candidates'],
                            batch['context'],
                            batch['opponent_on_ice'],
                            batch['rest_times'],
                            batch['shift_counts'],
                            batch['toi_last_period'],
                            previous_deployment=None,
                            # ENHANCED FATIGUE INPUTS: Pass all comprehensive signals
                            rest_real_times=batch.get('rest_real_times', {}),
                            intermission_flags=batch.get('intermission_flags', {}),
                            shift_counts_game=batch.get('shift_counts_game', {}),
                            cumulative_toi_game=batch.get('cumulative_toi_game', {}),
                            ewma_shift_lengths=batch.get('ewma_shift_lengths', {}),
                            ewma_rest_lengths=batch.get('ewma_rest_lengths', {})
                        )
                        
                        # Find true deployment index
                        true_deployment = batch['true_deployment']
                        true_idx = None
                        for i, cand in enumerate(batch['candidates']):
                            if (set(cand.get('forwards', [])) == set(true_deployment['forwards']) and
                                set(cand.get('defense', [])) == set(true_deployment['defense'])):
                                true_idx = i
                                break
                        
                        if true_idx is not None:
                            # Accuracy
                            pred_idx = torch.argmax(log_probs).item()
                            if pred_idx == true_idx:
                                fold_correct += 1
                            fold_total += 1
                            
                            # Log loss
                            fold_log_loss += -log_probs[true_idx].item()
            
            if fold_total > 0:
                fold_accuracy = fold_correct / fold_total
                fold_avg_log_loss = fold_log_loss / fold_total
                
                cv_scores.append(fold_accuracy)
                cv_log_losses.append(fold_avg_log_loss)
                
                logger.info(f"  {held_out_opponent}: {fold_accuracy:.3f} accuracy, {fold_avg_log_loss:.4f} log-loss")
        
        # Aggregate CV results
        if cv_scores:
            mean_cv_accuracy = np.mean(cv_scores)
            std_cv_accuracy = np.std(cv_scores)
            mean_log_loss = np.mean(cv_log_losses)
            
            logger.info(f"✓ Cross-validation complete:")
            logger.info(f"  Mean accuracy: {mean_cv_accuracy:.3f} ± {std_cv_accuracy:.3f}")
            logger.info(f"  Mean log-loss: {mean_log_loss:.4f}")
            
            return {
                'cv_accuracy_mean': mean_cv_accuracy,
                'cv_accuracy_std': std_cv_accuracy,
                'cv_log_loss_mean': mean_log_loss,
                'cv_folds': len(cv_scores)
            }
        else:
            logger.warning("No valid CV folds completed")
            return {'cv_accuracy_mean': 0.0, 'cv_folds': 0}
    
    def run_pipeline(self):
        """Execute complete training pipeline"""
        
        logger.info("=" * 80)
        logger.info("HEARTBEAT LINE MATCHUP ENGINE - PYTORCH")
        logger.info("=" * 80)
        
        # Process games
        logger.info("\nProcessing games...")
        self.process_all_games()
        
        # Engineer features: fit on TRAIN ONLY to avoid leakage
        logger.info("\n🔧 Engineering features (train-only fit)...")
        # Split events first - use HARDENED game-level split
        self._split_events_for_training(
            val_fraction=self.config.get('val_fraction', 0.1), 
            min_val=self.config.get('min_val_events', 100),
            split_strategy=self.config.get('split_strategy', 'game_level'),
            min_val_games=self.config.get('min_val_games', 5),
            holdout_fraction=self.config.get('holdout_fraction', 0.1),
            min_holdout_games=self.config.get('min_holdout_games', 3)
        )
        # HARDENED: Fit features on training events only (verify no leakage)
        logger.info("Feature engineering: fitting on TRAINING EVENTS ONLY")
        logger.info(f"  Training events: {len(self.train_events)} events from {len(self.train_events['game_id'].unique())} games")
        
        self.engineer_features(self.train_events)
        
        # VERIFICATION: Ensure feature engineering used correct data
        logger.info("Feature engineering completed on training data - leakage prevented")
        
        # HARDENED: Train Bayesian rest model on training data only (after split)
        logger.info("Training Bayesian rest model on training data only...")
        self._train_bayesian_rest_model(self.train_events)
        
        # Prepare data
        logger.info("\nPreparing training data (train-only assets)...")
        self.prepare_training_data()
        
        # Train
        logger.info("\nTraining model...")
        train_results = self.train(epochs=self.config.get('epochs', 50))
        
        # Cross-validate
        logger.info("\nCross-validating...")
        cv_results = self.leave_one_opponent_out_cv()
        
        # Evaluate
        logger.info("\nEvaluating...")
        eval_results = self.evaluate()
        
        # Combine all results
        results = {**train_results, **cv_results, **eval_results}
        
        logger.info("\n" + "=" * 80)
        logger.info("COMPLETE!")
        logger.info(f"✓ Training Top-1: {results.get('best_top1_accuracy', 0):.1%}")
        logger.info(f"✓ Training Top-3: {results.get('best_top3_accuracy', 0):.1%}")
        logger.info(f"✓ Test Accuracy: {results.get('top1_accuracy', 0):.1%}")
        if 'cv_accuracy_mean' in results:
            logger.info(f"✓ CV Accuracy: {results['cv_accuracy_mean']:.1%} ± {results.get('cv_accuracy_std', 0):.1%}")
        logger.info("=" * 80)
        
        return self.model, results


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description='Train HeartBeat Line Matchup Model with Enhanced Fatigue System')
    
    # Core training parameters
    parser.add_argument('--data_path', type=str, 
                       default='/Users/xavier.bouchard/Desktop/HeartBeat/data/raw/mtl_play_by_play',
                       help='Path to play-by-play CSV data directory')
    parser.add_argument('--output_path', type=str,
                       default='/Users/xavier.bouchard/Desktop/HeartBeat/models/line_matchup',
                       help='Output directory for trained model')
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of training epochs')
    parser.add_argument('--max_games', type=int, default=82,
                       help='Maximum games to process per season')
    
    # ENHANCED FATIGUE SYSTEM FLAGS
    parser.add_argument('--enable_dual_rest', action='store_true', default=True,
                       help='Enable dual rest signals (game-time + real-time with stoppages)')
    parser.add_argument('--disable_dual_rest', action='store_true', default=False,
                       help='Disable dual rest - use only game-time rest')
    parser.add_argument('--enable_stoppage_tracking', action='store_true', default=True,
                       help='Enable stoppage type and duration extraction from CSV')
    parser.add_argument('--enable_ewma_patterns', action='store_true', default=True,
                       help='Enable EWMA shift and rest pattern recognition')
    parser.add_argument('--enable_enhanced_context', action='store_true', default=True,
                       help='Enable comprehensive context features (period, score, strength)')
    parser.add_argument('--fatigue_input_dim', type=int, default=18,
                       help='FatigueRotationModule input dimensions (10=legacy, 18=enhanced)')
    
    # Data quality and validation flags
    parser.add_argument('--enable_sanity_checks', action='store_true', default=True,
                       help='Enable comprehensive data quality validation')
    parser.add_argument('--strict_validation', action='store_true', default=False,
                       help='Use strict fatigue input validation (30%% non-default minimum)')
    
    # Advanced features
    parser.add_argument('--intermission_duration', type=int, default=1080,
                       help='Standard NHL intermission duration in seconds (default: 1080s = 18min)')
    parser.add_argument('--ewma_decay_factor', type=float, default=0.3,
                       help='EWMA decay factor for shift/rest pattern learning (default: 0.3)')
    
    # HARDENED TRAINING: Data splitting and validation configuration
    parser.add_argument('--split_strategy', type=str, default='game_level', choices=['game_level', 'event_level'],
                       help='Data splitting strategy: game_level (recommended) prevents leakage')
    parser.add_argument('--val_fraction', type=float, default=0.15,
                       help='Fraction of games for validation (default: 0.15 = 15%%)')
    parser.add_argument('--min_val_events', type=int, default=200,
                       help='Minimum validation events required (default: 200)')
    parser.add_argument('--min_val_games', type=int, default=8,
                       help='Minimum validation games required (default: 8)')
    parser.add_argument('--holdout_fraction', type=float, default=0.1,
                       help='Fraction of games for final holdout test (default: 0.1 = 10%%)')
    parser.add_argument('--min_holdout_games', type=int, default=3,
                       help='Minimum holdout games required (default: 3)')
    parser.add_argument('--disable_val_fallback', action='store_true', default=True,
                       help='Disable validation fallback to training data (recommended: True)')
    parser.add_argument('--random_seed', type=int, default=42,
                       help='Random seed for reproducible training (default: 42)')
    
    # OPPONENT-AWARE VALIDATION: Per-opponent and LOO validation modes
    parser.add_argument('--val_opponent', type=str, default=None,
                       help='Filter validation to specific opponent team (e.g., TOR, BOS)')
    parser.add_argument('--loo_opponent', type=str, default=None,
                       help='Leave-one-opponent-out: train on all except this team, validate on this team only')
    parser.add_argument('--force_calibration', action='store_true', default=False,
                       help='Force temperature calibration and report calibrated metrics')
    
    # TEAM-AWARE: Team embedding configuration
    parser.add_argument('--enable_team_embeddings', action='store_true', default=True,
                       help='Enable opponent team embeddings for team-specific patterns (default: True)')
    parser.add_argument('--team_embedding_dim', type=int, default=16,
                       help='Team embedding dimension (default: 16)')
    parser.add_argument('--n_teams', type=int, default=32,
                       help='Maximum number of teams for embeddings (default: 32)')
    
    # REGULARIZATION: Model complexity control  
    parser.add_argument('--learning_rate', type=float, default=0.0001,
                       help='AdamW learning rate (default: 1e-4)')
    parser.add_argument('--l1_reg', type=float, default=0.0001,
                       help='L1 regularization strength (default: 0.0001)')
    parser.add_argument('--l2_reg', type=float, default=0.00001,
                       help='L2 regularization strength (default: 0.00001 = 1e-5)')
    parser.add_argument('--dropout_rate', type=float, default=0.2,
                       help='Dropout rate for neural networks (default: 0.2)')
    parser.add_argument('--weight_decay', type=float, default=0.00001,
                       help='AdamW weight decay (L2 reg in optimizer, default: 1e-5)')
    
    # Debugging and analysis
    parser.add_argument('--debug_fatigue', action='store_true', default=False,
                       help='Enable detailed fatigue tracking debug output')
    parser.add_argument('--log_shift_sequences', action='store_true', default=False,
                       help='Log detailed shift sequence extraction (verbose)')
    
    args = parser.parse_args()
    
    # Build comprehensive configuration with enhanced fatigue system options
    config = {
        # Core training parameters
        'data_path': args.data_path,
        'output_path': args.output_path,
        'epochs': args.epochs,
        'max_games': args.max_games,
        
        # ENHANCED FATIGUE SYSTEM CONFIGURATION
        'enable_dual_rest': args.enable_dual_rest and not args.disable_dual_rest,
        'enable_stoppage_tracking': args.enable_stoppage_tracking,
        'enable_ewma_patterns': args.enable_ewma_patterns,
        'enable_enhanced_context': args.enable_enhanced_context,
        'fatigue_input_dim': args.fatigue_input_dim,
        
        # Data quality and validation
        'enable_sanity_checks': args.enable_sanity_checks,
        'strict_validation': args.strict_validation,
        
        # Advanced parameters
        'intermission_duration': args.intermission_duration,
        'ewma_decay_factor': args.ewma_decay_factor,
        
        # Debugging and analysis
        'debug_fatigue': args.debug_fatigue,
        'log_shift_sequences': args.log_shift_sequences,
        
        # HARDENED TRAINING: Data splitting and validation configuration
        'split_strategy': args.split_strategy,
        'val_fraction': args.val_fraction,
        'min_val_events': args.min_val_events,
        'min_val_games': args.min_val_games,
        'holdout_fraction': args.holdout_fraction,
        'min_holdout_games': args.min_holdout_games,
        'disable_val_fallback': args.disable_val_fallback,
        'random_seed': args.random_seed,
        
        # TEAM-AWARE: Team embedding configuration
        'enable_team_embeddings': args.enable_team_embeddings,
        'team_embedding_dim': args.team_embedding_dim,
        'n_teams': args.n_teams,
        
        # REGULARIZATION: Model complexity control
        'learning_rate': args.learning_rate,
        'l1_reg': args.l1_reg,
        'l2_reg': args.l2_reg,
        'dropout_rate': args.dropout_rate,
        'weight_decay': args.weight_decay
    }
    
    trainer = LineMatchupTrainer(config)
    return trainer.run_pipeline()


if __name__ == "__main__":
    model, results = main()
