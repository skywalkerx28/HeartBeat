"""
HeartBeat PyTorch Conditional Logit Model for Line Matchup Prediction
Deep neural network with automatic differentiation for gradient optimization
Professional-grade for NHL analytics with high granularity
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
import logging
from dataclasses import dataclass
from pathlib import Path
import pickle
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Set device for GPU acceleration if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")


class PlayerEmbeddingLayer(nn.Module):
    """
    Learnable player embeddings with position-specific constraints
    Handles unseen players gracefully with position-based defaults
    """
    
    def __init__(self, n_players: int = 1000, embedding_dim: int = 32, 
                 n_positions: int = 2):  # F/D
        super().__init__()
        
        # Primary player embeddings
        self.player_embeddings = nn.Embedding(
            n_players, embedding_dim, padding_idx=0
        )
        
        # Position-specific embeddings as fallback
        self.position_embeddings = nn.Embedding(n_positions, embedding_dim)
        
        # Initialize with small random values
        nn.init.normal_(self.player_embeddings.weight, mean=0, std=0.1)
        nn.init.normal_(self.position_embeddings.weight, mean=0, std=0.05)
        
        self.embedding_dim = embedding_dim
        self.player_to_idx = {}  # Maps player_id to embedding index
        self.position_to_idx = {'F': 0, 'D': 1}
        self.next_idx = 1  # 0 is padding
        
    def register_player(self, player_id: str, position: str = 'F') -> int:
        """Register a new player and return their embedding index"""
        if player_id not in self.player_to_idx:
            if self.next_idx >= self.player_embeddings.num_embeddings:
                # Expand embedding matrix if needed
                self._expand_embeddings()
            self.player_to_idx[player_id] = self.next_idx
            self.next_idx += 1
        return self.player_to_idx[player_id]
    
    def _expand_embeddings(self):
        """Dynamically expand embedding matrix when needed"""
        old_embeddings = self.player_embeddings.weight.data
        new_size = old_embeddings.size(0) * 2
        
        self.player_embeddings = nn.Embedding(
            new_size, self.embedding_dim, padding_idx=0
        )
        self.player_embeddings.weight.data[:old_embeddings.size(0)] = old_embeddings
        nn.init.normal_(
            self.player_embeddings.weight.data[old_embeddings.size(0):], 
            mean=0, std=0.1
        )
        
    def forward(self, player_ids: List[str], positions: Optional[List[str]] = None):
        """Get embeddings for a list of players"""
        indices = []
        for i, pid in enumerate(player_ids):
            if pid in self.player_to_idx:
                indices.append(self.player_to_idx[pid])
            else:
                # Use position embedding for unknown players
                pos = positions[i] if positions else 'F'
                indices.append(0)  # Will be replaced with position embedding
        
        indices_tensor = torch.tensor(indices, dtype=torch.long, device=device)
        embeddings = self.player_embeddings(indices_tensor)
        
        # Replace unknown player embeddings with position defaults
        if positions:
            for i, idx in enumerate(indices):
                if idx == 0:
                    pos_idx = self.position_to_idx.get(positions[i], 0)
                    pos_emb = self.position_embeddings(
                        torch.tensor([pos_idx], device=device)
                    )
                    embeddings[i] = pos_emb.squeeze()
        
        return embeddings


class ChemistryNetwork(nn.Module):
    """
    Neural network for learning pairwise chemistry between players
    Uses embeddings to generalize to unseen combinations
    """
    
    def __init__(self, embedding_dim: int = 32):
        super().__init__()
        
        # Chemistry computation network
        self.chemistry_net = nn.Sequential(
            nn.Linear(embedding_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Tanh()  # Chemistry score in [-1, 1]
        )
        
    def forward(self, player1_emb: torch.Tensor, player2_emb: torch.Tensor):
        """Compute chemistry score between two players"""
        # Concatenate embeddings
        combined = torch.cat([player1_emb, player2_emb], dim=-1)
        chemistry = self.chemistry_net(combined)
        return chemistry.squeeze()


class MatchupInteractionNetwork(nn.Module):
    """
    Deep network for learning complex matchup interactions
    Models how opponent players match up against MTL players
    """
    
    def __init__(self, embedding_dim: int = 32):
        super().__init__()
        
        # Matchup interaction network with attention mechanism
        self.matchup_net = nn.Sequential(
            nn.Linear(embedding_dim * 2, 128),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # Attention weights for importance of matchups
        self.attention = nn.Sequential(
            nn.Linear(embedding_dim * 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, opp_embeddings: torch.Tensor, mtl_embeddings: torch.Tensor):
        """
        Compute matchup interaction scores with vectorized batched attention
        opp_embeddings: [n_opp, embedding_dim]
        mtl_embeddings: [n_mtl, embedding_dim]
        """
        n_opp, n_mtl = opp_embeddings.size(0), mtl_embeddings.size(0)
        
        # Guard against empty embeddings
        if n_opp == 0 or n_mtl == 0:
            return torch.tensor(0.0, device=opp_embeddings.device)
        
        # VECTORIZED: Compute all pairwise interactions efficiently
        # Expand dimensions for broadcasting: [n_opp, 1, embedding_dim] and [1, n_mtl, embedding_dim]
        opp_expanded = opp_embeddings.unsqueeze(1)  # [n_opp, 1, embedding_dim]
        mtl_expanded = mtl_embeddings.unsqueeze(0)  # [1, n_mtl, embedding_dim]
        
        # Broadcast and concatenate: [n_opp, n_mtl, embedding_dim * 2]
        opp_broadcast = opp_expanded.expand(n_opp, n_mtl, -1)  # [n_opp, n_mtl, embedding_dim]
        mtl_broadcast = mtl_expanded.expand(n_opp, n_mtl, -1)  # [n_opp, n_mtl, embedding_dim]
        combined = torch.cat([opp_broadcast, mtl_broadcast], dim=-1)  # [n_opp, n_mtl, embedding_dim * 2]
        
        # Reshape for batch processing: [n_opp * n_mtl, embedding_dim * 2]
        combined_flat = combined.view(-1, combined.size(-1))
        
        # BATCHED COMPUTATION: Process all pairs at once
        interactions_flat = self.matchup_net(combined_flat)  # [n_opp * n_mtl, 1]
        attentions_flat = self.attention(combined_flat)      # [n_opp * n_mtl, 1]
        
        # Reshape back to interaction matrix: [n_opp, n_mtl, 1]
        interactions = interactions_flat.view(n_opp, n_mtl, 1)
        attentions = attentions_flat.view(n_opp, n_mtl, 1)
        
        # Apply attention weighting: [n_opp, n_mtl, 1]
        weighted_interactions = interactions * attentions
        
        return weighted_interactions.sum()


class FatigueRotationModule(nn.Module):
    """
    Neural module for fatigue and rotation modeling
    Learns complex patterns of player rest and rotation sequences
    """
    
    def __init__(self, input_dim: int = 18):  # Expanded from 10 to 18 features
        super().__init__()
        
        # ENHANCED fatigue impact network for comprehensive fatigue modeling
        self.fatigue_net = nn.Sequential(
            nn.Linear(input_dim, 64),      # Increased capacity for more features
            nn.LayerNorm(64),              # Better normalization
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Tanh()  # Bounded output for stability
        )
        
        # Rotation pattern network (Markov-like transitions)
        self.rotation_net = nn.Sequential(
            nn.Linear(64, 32),  # Previous + current line embeddings
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()  # Rotation probability
        )
        
        # Learnable fatigue parameters
        self.alpha_rest = nn.Parameter(torch.tensor(0.01))
        self.alpha_shifts = nn.Parameter(torch.tensor(-0.005))
        self.alpha_toi = nn.Parameter(torch.tensor(-0.01))
        
        # TEAM-AWARE: Learnable team-specific fatigue modulation parameters
        # These will be learned during training to capture team-specific fatigue patterns
        self.team_fatigue_scales = nn.ParameterDict()
        self._initialize_team_fatigue_scales()
        
    def compute_fatigue(self, 
                        rest_times: Dict[str, float], 
                        shift_counts: Dict[str, int],
                        toi_last_period: Dict[str, float],
                        players: List[str],
                        # ENHANCED FATIGUE INPUTS: New comprehensive fatigue signals
                        rest_real_times: Optional[Dict[str, float]] = None,
                        intermission_flags: Optional[Dict[str, int]] = None, 
                        shift_counts_game: Optional[Dict[str, int]] = None,
                        cumulative_toi_game: Optional[Dict[str, float]] = None,
                        ewma_shift_lengths: Optional[Dict[str, float]] = None,
                        ewma_rest_lengths: Optional[Dict[str, float]] = None,
                        # TEAM-AWARE: Optional opponent team for team-specific fatigue modeling
                        opponent_team: Optional[str] = None) -> torch.Tensor:
        """
        ENHANCED Compute fatigue penalty with dual rest signals and comprehensive metrics
        
        Args:
            rest_times: Game-clock rest times (seconds)
            shift_counts: Shifts this period
            toi_last_period: TOI in past 20 minutes
            players: List of player IDs
            rest_real_times: Real elapsed rest times (includes stoppages)
            intermission_flags: 1 if player returned after intermission, 0 if within-period
            shift_counts_game: Total shifts in game
            cumulative_toi_game: Total TOI in game
            ewma_shift_lengths: EWMA of recent shift lengths
            ewma_rest_lengths: EWMA of recent rest lengths
            
        Returns:
            Fatigue penalty tensor (higher = more fatigued)
        """
        
        # Initialize optional inputs with defaults
        rest_real_times = rest_real_times or {}
        intermission_flags = intermission_flags or {}
        shift_counts_game = shift_counts_game or {}
        cumulative_toi_game = cumulative_toi_game or {}
        ewma_shift_lengths = ewma_shift_lengths or {}
        ewma_rest_lengths = ewma_rest_lengths or {}
        
        fatigue_features = []
        
        for player in players:
            # DUAL REST SIGNALS
            rest_game = rest_times.get(player, 90.0)        # Game-clock rest (default 90s)
            rest_real = rest_real_times.get(player, 110.0)   # Real-time rest (default 110s)
            intermission = intermission_flags.get(player, 0) # Intermission flag (default 0)
            
            # SHIFT AND TOI METRICS
            shifts_period = shift_counts.get(player, 0)                    # Shifts this period
            shifts_game = shift_counts_game.get(player, 0)                 # Total game shifts
            toi_20min = toi_last_period.get(player, 0.0)                   # TOI past 20 min
            toi_game = cumulative_toi_game.get(player, 0.0)                # Total game TOI
            
            # EWMA PATTERNS
            ewma_shift = ewma_shift_lengths.get(player, 45.0)              # EWMA shift length
            ewma_rest = ewma_rest_lengths.get(player, 90.0)                # EWMA rest length
            
            # NORMALIZED FEATURES (0-1 scale for network stability)
            rest_game_norm = min(rest_game / 300.0, 1.0)      # 0-1 (300s = 5min fully rested)
            rest_real_norm = min(rest_real / 360.0, 1.0)      # 0-1 (360s = 6min fully rested)
            shifts_period_norm = min(shifts_period / 15.0, 1.0) # 0-1 (15 shifts = heavy period)
            shifts_game_norm = min(shifts_game / 30.0, 1.0)   # 0-1 (30 shifts = heavy game)
            toi_20min_norm = min(toi_20min / 1200.0, 1.0)     # 0-1 (20min = max window)
            toi_game_norm = min(toi_game / 1800.0, 1.0)       # 0-1 (30min = heavy game)
            ewma_shift_norm = min(ewma_shift / 90.0, 1.0)     # 0-1 (90s = long shifts)
            ewma_rest_norm = min(ewma_rest / 180.0, 1.0)      # 0-1 (180s = long rests)
            
            # BINARY INDICATORS
            is_very_tired = 1.0 if rest_game < 20 else 0.0    # Extremely short rest
            is_overused = 1.0 if shifts_period > 18 else 0.0  # Many shifts this period
            is_heavy_load = 1.0 if toi_game > 1200 else 0.0   # >20min total TOI
            
            # INTERACTION FEATURES (capture complex fatigue patterns)
            rest_shift_interaction = rest_game_norm * shifts_period_norm
            rest_toi_interaction = rest_game_norm * toi_game_norm
            shift_toi_interaction = shifts_period_norm * toi_20min_norm
            
            # REST QUALITY METRICS
            rest_quality = np.exp(-rest_game / 120.0)         # Exponential decay (2min half-life)
            rest_real_advantage = max(0.0, rest_real - rest_game) / 60.0  # Stoppage rest bonus
            
            # COMPREHENSIVE 18-FEATURE VECTOR
            player_features = [
                # Core rest signals (4 features)
                rest_game_norm, rest_real_norm, float(intermission), rest_quality,
                
                # Shift and TOI load (4 features)  
                shifts_period_norm, shifts_game_norm, toi_20min_norm, toi_game_norm,
                
                # Pattern recognition (2 features)
                ewma_shift_norm, ewma_rest_norm,
                
                # Binary fatigue flags (3 features)
                is_very_tired, is_overused, is_heavy_load,
                
                # Interaction terms (3 features)
                rest_shift_interaction, rest_toi_interaction, shift_toi_interaction,
                
                # Advanced features (2 features)
                rest_real_advantage, (rest_game / 120.0) ** 2  # Quadratic rest effect
            ]
            
            fatigue_features.append(player_features)
        
        # Average fatigue across all players in deployment
        fatigue_tensor = torch.tensor(
            np.mean(fatigue_features, axis=0), 
            dtype=torch.float32, 
            device=device
        )
        
        # TEAM-AWARE: Apply opponent-specific fatigue modulation
        if opponent_team:
            team_fatigue_modulation = self._get_team_fatigue_modulation(opponent_team, device)
            fatigue_tensor = fatigue_tensor * team_fatigue_modulation
        
        # Compute fatigue score through network
        fatigue_score = self.fatigue_net(fatigue_tensor)
        
        # ENHANCED parametric components using dual rest signals
        avg_rest_game = np.mean([rest_times.get(p, 90) for p in players])
        avg_rest_real = np.mean([rest_real_times.get(p, 110) for p in players])
        avg_shifts_period = np.mean([shift_counts.get(p, 0) for p in players])
        avg_shifts_game = np.mean([shift_counts_game.get(p, 0) for p in players])
        avg_toi_20min = np.mean([toi_last_period.get(p, 0) for p in players])
        avg_toi_game = np.mean([cumulative_toi_game.get(p, 0) for p in players])
        
        # Enhanced parametric fatigue model
        parametric_score = (
            self.alpha_rest * avg_rest_game +                     # Game-clock rest effect
            self.alpha_shifts * avg_shifts_period +               # Period shift load
            self.alpha_toi * avg_toi_20min +                      # Rolling TOI fatigue
            0.001 * (avg_rest_real - avg_rest_game) +             # Stoppage rest bonus
            -0.002 * avg_shifts_game +                            # Cumulative shift penalty
            -0.0005 * avg_toi_game                                # Cumulative TOI penalty
        )
        
        return fatigue_score + parametric_score
    
    def _initialize_team_fatigue_scales(self):
        """TEAM-AWARE: Initialize team-specific fatigue scaling parameters"""
        nhl_teams = [
            'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL',
            'DET', 'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR',
            'OTT', 'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
            'WPG', 'WSH', 'UNK'  # Include UNK for unknown teams
        ]
        
        for team in nhl_teams:
            # Initialize with slight variations around 1.0 (neutral scaling)
            # These will be learned during training
            random_noise = torch.randn(18) * 0.05  # Use torch.randn for proper dtype
            self.team_fatigue_scales[team] = nn.Parameter(torch.ones(18, dtype=torch.float32) + random_noise)
    
    def _get_team_fatigue_modulation(self, opponent_team: str, device) -> torch.Tensor:
        """TEAM-AWARE: Get team-specific fatigue modulation factors"""
        if opponent_team in self.team_fatigue_scales:
            return self.team_fatigue_scales[opponent_team].to(device)
        else:
            # Default to UNK team scaling if opponent team not found
            return self.team_fatigue_scales['UNK'].to(device)


class PyTorchConditionalLogit(nn.Module):
    """
    Main PyTorch model for line matchup prediction
    Combines all components with automatic differentiation
    """
    
    def __init__(self, 
                 n_context_features: int = 36,  # Expanded from 30 to 36 for score situation features
                 embedding_dim: int = 32,
                 n_players: int = 1000,
                 shift_priors_path: Optional[str] = None,
                 fatigue_input_dim: int = 18,  # ENHANCED: Configurable fatigue dimensions
                 enable_team_embeddings: bool = True,  # TEAM-AWARE: Enable opponent team embeddings
                 team_embedding_dim: int = 16,  # TEAM-AWARE: Team embedding dimension
                 n_teams: int = 32):  # TEAM-AWARE: Max number of NHL teams
        super().__init__()
        
        self.n_context_features = n_context_features
        self.embedding_dim = embedding_dim
        self.n_shift_features = 8  # Shift priors dimensions
        self.fatigue_input_dim = fatigue_input_dim  # Store for FatigueRotationModule
        
        # TEAM-AWARE: Store team embedding configuration
        self.enable_team_embeddings = enable_team_embeddings
        self.team_embedding_dim = team_embedding_dim
        self.n_teams = n_teams
        
        # Load shift priors
        self.shift_priors = {}
        if shift_priors_path:
            self._load_shift_priors(shift_priors_path)
        
        # Core modules
        self.player_embeddings = PlayerEmbeddingLayer(n_players, embedding_dim)
        self.chemistry_net = ChemistryNetwork(embedding_dim)
        self.matchup_net = MatchupInteractionNetwork(embedding_dim)
        self.fatigue_rotation = FatigueRotationModule(input_dim=fatigue_input_dim)  # Configurable dimensions
        
        # BIDIRECTIONAL TEAM-AWARE: Team embedding layer for MTL + opponent interactions
        if self.enable_team_embeddings:
            self.team_embeddings = nn.Embedding(n_teams, team_embedding_dim)
            # BIDIRECTIONAL: Small MLP head for team utility (32D -> 16D -> 8D -> 1D)
            self.team_utility_head = nn.Sequential(
                nn.Linear(team_embedding_dim * 2, embedding_dim // 2),  # 32D -> 16D
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(embedding_dim // 2, embedding_dim // 4),      # 16D -> 8D
                nn.ReLU(),
                nn.Linear(embedding_dim // 4, 1)                       # 8D -> 1D
            )
            logger.info(f"Bidirectional team embeddings: {n_teams} teams, {team_embedding_dim}D each, 32D interaction")
        else:
            self.team_embeddings = None
            self.team_utility_head = None
            
        # TEAM-AWARE: Create team name to index mapping
        self.team_to_idx = self._create_team_mapping() if self.enable_team_embeddings else {}
        
        # Context processing
        self.context_net = nn.Sequential(
            nn.Linear(n_context_features, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
        
        # Player-context interaction network
        self.player_context_net = nn.Sequential(
            nn.Linear(embedding_dim + 16, 48),  # Player emb + context
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(48, 24),
            nn.ReLU(),
            nn.Linear(24, 1)
        )
        
        # Global deployment scoring
        # TEAM-AWARE: Dynamic feature count based on team embedding configuration
        # PLAYER-VS-PLAYER: Add matchup prior dimension
        # Base features: 7 scalar utilities + embedding_dim + 16 (processed context) + 8 (shift priors) + 1 (matchup prior)
        base_features = 7 + embedding_dim + 16 + self.n_shift_features + 1  # 7 + 32 + 16 + 8 + 1 = 64
        # Team features are dynamically added per forward pass, so max size is base + 1
        max_features = base_features + (1 if self.enable_team_embeddings else 0)  # 64 or 65
        expected_features = max_features
        
        self.deployment_scorer = nn.Sequential(
            nn.Linear(expected_features, 64),  # All features combined
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)  # Single deployment score
        )
        
        logger.info(f"Deployment scorer initialized: {expected_features} input features (team_aware={self.enable_team_embeddings})")
        
        # Learned parameters
        self.theta_base = nn.ParameterDict()  # Base deployment propensities
        self.special_teams_boost = nn.Parameter(torch.tensor(0.0))
        
        # Markov rotation priors
        self.rotation_memory = {}  # Stores recent deployments
        self.rotation_priors = defaultdict(lambda: defaultdict(float))
        
        # NEW: Temperature calibration parameter (learned during validation)
        self.calibration_temperature = nn.Parameter(torch.tensor(1.0))
        
        # Batch processing optimization
        self.max_batch_size = 32  # Process candidates in batches for efficiency
    
    def _load_shift_priors(self, shift_priors_path: str):
        """Load shift priors from parquet/csv file"""
        try:
            import pandas as pd
            from pathlib import Path
            
            path = Path(shift_priors_path)
            if path.suffix == '.parquet':
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            
            # Create dictionary mapping player_id to shift statistics
            for _, row in df.iterrows():
                player_id = str(int(row['player_id']))
                
                # Extract key shift metrics as 8-dimensional vector
                priors = np.array([
                    row.get('EV_shift_mean', 45.0),       # Average EV shift length
                    row.get('EV_shift_std', 15.0),        # EV shift variability
                    row.get('PP_shift_mean', 50.0),       # Average PP shift length
                    row.get('PK_shift_mean', 50.0),       # Average PK shift length
                    row.get('avg_shifts_per_game', 18.0), # Shifts per game
                    row.get('avg_toi_per_game', 900.0),   # TOI per game (seconds)
                    row.get('overall_shift_mean', 45.0),  # Overall avg shift
                    row.get('overall_shift_std', 15.0)    # Overall variability
                ])
                
                self.shift_priors[player_id] = torch.tensor(priors, dtype=torch.float32, device=device)
            
            logger.info(f"Loaded shift priors for {len(self.shift_priors)} players into PyTorch model")
            
        except Exception as e:
            logger.warning(f"Failed to load shift priors into PyTorch model: {e}")
    
    def _create_team_mapping(self) -> Dict[str, int]:
        """TEAM-AWARE: Create mapping from team names to embedding indices"""
        nhl_teams = [
            'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL',
            'DET', 'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR',
            'OTT', 'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
            'WPG', 'WSH'
        ]
        
        team_mapping = {}
        for i, team in enumerate(nhl_teams):
            team_mapping[team] = i
            
        # Add unknown team mapping
        team_mapping['UNK'] = len(nhl_teams)
        
        logger.info(f"Created team mapping for {len(team_mapping)} teams")
        return team_mapping
    
    def _normalize_shift_priors(self, shift_priors: torch.Tensor) -> torch.Tensor:
        """
        Normalize shift priors to prevent extreme values while preserving hockey meaning
        
        Expected shift_priors format (8D):
        [avg_shift_s, shift_count_period, rest_s, rest_s, shifts_game, toi_s, shift_s, rest_s]
        """
        if len(shift_priors) != 8:
            return shift_priors  # Return as-is if unexpected format
        
        # Normalize each component to reasonable ranges for neural network
        normalized = torch.zeros_like(shift_priors)
        
        # Shift lengths (indices 0, 6): normalize to ~45s baseline
        normalized[0] = torch.clamp(shift_priors[0] / 45.0, 0.1, 3.0)  # 0.1-3.0× normal
        normalized[6] = torch.clamp(shift_priors[6] / 45.0, 0.1, 3.0)
        
        # Shift counts (indices 1, 4): normalize to ~15-20 shifts
        normalized[1] = torch.clamp(shift_priors[1] / 15.0, 0.1, 2.0)   # Period shifts
        normalized[4] = torch.clamp(shift_priors[4] / 20.0, 0.1, 2.0)   # Game shifts
        
        # Rest times (indices 2, 3, 7): normalize to ~60-120s baseline
        normalized[2] = torch.clamp(shift_priors[2] / 90.0, 0.1, 5.0)
        normalized[3] = torch.clamp(shift_priors[3] / 90.0, 0.1, 5.0)
        normalized[7] = torch.clamp(shift_priors[7] / 90.0, 0.1, 5.0)
        
        # TOI (index 5): normalize to ~900s (15min) baseline
        normalized[5] = torch.clamp(shift_priors[5] / 900.0, 0.1, 2.0)
        
        return normalized
    
    def __init_ood_counters(self):
        """Initialize OOD detection counters"""
        if not hasattr(self, 'ood_counters'):
            self.ood_counters = {
                'dimension_mismatches': 0,
                'nan_sanitizations': 0,
                'inf_sanitizations': 0,
                'extreme_values': 0,
                'by_opponent': defaultdict(lambda: {
                    'nan_count': 0, 'inf_count': 0, 'extreme_count': 0
                })
            }
    
    def _validate_and_log_feature_vector(self, feature_vector: torch.Tensor, opponent_team: str = None):
        """
        OOD DETECTION: Validate feature vector and log anomalies
        
        Detects:
        1. Dimension mismatches
        2. NaN/Inf values  
        3. Extreme values outside expected ranges
        4. Per-opponent anomaly patterns
        """
        self.__init_ood_counters()
        
        # Check for extreme values (beyond expected hockey statistics)
        # Reduced threshold during training as some extreme values are normal in early epochs
        extreme_mask = torch.abs(feature_vector) > 15.0  # Increased threshold from 10.0 to 15.0
        extreme_count = extreme_mask.sum().item()
        
        # Only warn if significant portion of features are extreme
        if extreme_count > len(feature_vector) * 0.2:  # More than 20% of features extreme
            self.ood_counters['extreme_values'] += 1
            if opponent_team:
                self.ood_counters['by_opponent'][opponent_team]['extreme_count'] += 1
            
            logger.warning(
                f"OOD: {extreme_count}/{len(feature_vector)} extreme values detected (>15.0) vs {opponent_team or 'Unknown'}"
            )
        
        # Check for suspicious patterns in specific feature ranges
        if len(feature_vector) >= 10:  # Only if we have enough features
            # Base utilities should be reasonable (first 7 features)
            base_utilities = feature_vector[:7]
            if torch.any(torch.abs(base_utilities) > 7.0):
                logger.warning(f"OOD: Base utilities outside expected range vs {opponent_team or 'Unknown'}")
            
            # Player embeddings should be normalized (features 7-39 typically)
            if len(feature_vector) > 39:
                player_emb = feature_vector[7:39]
                if torch.std(player_emb) > 3.0:
                    logger.warning(f"OOD: Player embeddings highly variable vs {opponent_team or 'Unknown'}")
    
    def _log_sanitization_event(self, nan_count: int, inf_count: int, opponent_team: str = None):
        """Log feature vector sanitization events"""
        self.__init_ood_counters()
        
        if nan_count > 0:
            self.ood_counters['nan_sanitizations'] += 1
            if opponent_team:
                self.ood_counters['by_opponent'][opponent_team]['nan_count'] += 1
        
        if inf_count > 0:
            self.ood_counters['inf_sanitizations'] += 1
            if opponent_team:
                self.ood_counters['by_opponent'][opponent_team]['inf_count'] += 1
        
        logger.warning(
            f"Feature sanitization: {nan_count} NaNs, {inf_count} Infs replaced vs {opponent_team or 'Unknown'}"
        )
    
    def get_ood_statistics(self) -> Dict:
        """Return OOD detection statistics for monitoring"""
        if not hasattr(self, 'ood_counters'):
            return {}
        
        return {
            'total_dimension_mismatches': self.ood_counters['dimension_mismatches'],
            'total_nan_sanitizations': self.ood_counters['nan_sanitizations'], 
            'total_inf_sanitizations': self.ood_counters['inf_sanitizations'],
            'total_extreme_values': self.ood_counters['extreme_values'],
            'by_opponent_summary': {
                team: {
                    'total_anomalies': stats['nan_count'] + stats['inf_count'] + stats['extreme_count'],
                    'breakdown': stats
                }
                for team, stats in self.ood_counters['by_opponent'].items()
                if stats['nan_count'] + stats['inf_count'] + stats['extreme_count'] > 0
            }
        }
        
    def register_players(self, players: List[str], positions: Optional[Dict[str, str]] = None):
        """Register all players in the dataset"""
        for player in players:
            pos = positions.get(player, 'F') if positions else 'F'
            idx = self.player_embeddings.register_player(player, pos)
            
            # Initialize base propensity parameter
            if player not in self.theta_base:
                self.theta_base[player] = nn.Parameter(torch.tensor(0.0))
    
    def compute_deployment_utility(self,
                                  candidate: Dict,
                                  context: torch.Tensor,
                                  opponent_on_ice: List[str],
                                  rest_times: Dict[str, float],
                                  shift_counts: Dict[str, int],
                                  toi_last_period: Dict[str, float],
                                  previous_deployment: Optional[List[str]] = None,
                                  # ENHANCED FATIGUE INPUTS: New comprehensive signals
                                  rest_real_times: Optional[Dict[str, float]] = None,
                                  intermission_flags: Optional[Dict[str, int]] = None,
                                  shift_counts_game: Optional[Dict[str, int]] = None,
                                  cumulative_toi_game: Optional[Dict[str, float]] = None,
                                 ewma_shift_lengths: Optional[Dict[str, float]] = None,
                                 ewma_rest_lengths: Optional[Dict[str, float]] = None,
                                 opponent_team: Optional[str] = None,
                                 matchup_prior: Optional[float] = None,  # PLAYER-VS-PLAYER: Player-level matchup score
                                 probability_prior: Optional[float] = None) -> torch.Tensor:  # FULL PRIOR: Combined softmax-normalized prior
        """
        Compute utility for a single deployment candidate with team-aware features, player-vs-player matchups, and full priors
        Fully differentiable for gradient optimization
        """
        
        # Extract players from candidate
        forwards = candidate.get('forwards', [])
        defense = candidate.get('defense', [])
        all_players = forwards + defense
        
        # 1. Get player embeddings with self-attention pooling
        player_embs = self.player_embeddings(all_players)
        
        # Self-attention pooling (instead of simple mean)
        if len(all_players) > 1:
            # Compute attention weights
            attn_scores = torch.matmul(player_embs, player_embs.transpose(0, 1))
            attn_weights = F.softmax(attn_scores.mean(dim=1), dim=0)
            
            # Weighted pooling preserves ordering-invariant but context-aware info
            pooled_player_emb = torch.matmul(attn_weights.unsqueeze(0), player_embs).squeeze(0)
        else:
            # Single player case
            pooled_player_emb = player_embs[0] if len(player_embs) > 0 else torch.zeros(self.embedding_dim, device=device)
        # Sanitize pooled embedding to prevent NaNs from propagating
        pooled_player_emb = torch.nan_to_num(pooled_player_emb, nan=0.0, posinf=5.0, neginf=-5.0)
        
        # 2. Process context through network (sanitize first to avoid NaNs in LayerNorm)
        context = torch.nan_to_num(context, nan=0.0, posinf=5.0, neginf=-5.0)
        context_processed = self.context_net(context.unsqueeze(0)).squeeze()
        context_processed = torch.nan_to_num(context_processed, nan=0.0, posinf=5.0, neginf=-5.0)
        
        # 3. Base deployment propensities (θ) - normalize by number of players
        if len(all_players) > 0:
            base_utility = torch.stack([
                self.theta_base.get(p, torch.tensor(0.0, device=device)) 
                for p in all_players
            ]).mean()
        else:
            base_utility = torch.tensor(0.0, device=device)
        # Bound to safe range to avoid OOD base-utility warnings (widened to -6.0/6.0 for cleaner data)
        base_utility = torch.clamp(base_utility, min=-6.0, max=6.0)
        
        # 4. Player-context interactions (φ)
        player_context_utils = []
        for i, player in enumerate(all_players):
            combined = torch.cat([player_embs[i], context_processed])
            util = self.player_context_net(combined)
            player_context_utils.append(util)
        
        # Normalize by number of players to keep scale consistent across candidates
        player_context_utility = (
            torch.stack(player_context_utils).mean()
            if player_context_utils else torch.tensor(0.0, device=device)
        )
        player_context_utility = torch.clamp(player_context_utility, min=-6.0, max=6.0)
        
        # 5. Chemistry scores (η) - pairwise within forwards
        chemistry_utility = torch.tensor(0.0, device=device)
        for i in range(len(forwards)):
            for j in range(i + 1, len(forwards)):
                emb_i = self.player_embeddings([forwards[i]])[0]
                emb_j = self.player_embeddings([forwards[j]])[0]
                chemistry = self.chemistry_net(emb_i, emb_j)
                chemistry_utility += chemistry
        
        # 6. Matchup interactions (ψ)
        if opponent_on_ice:
            opp_embs = self.player_embeddings(opponent_on_ice)
            mtl_embs = self.player_embeddings(forwards)  # Focus on forward matchups
            matchup_utility = self.matchup_net(opp_embs, mtl_embs)
            # Normalize by the number of opponent-vs-MTL forward pairs to prevent scale blow-up
            n_pairs = len(opponent_on_ice) * len(forwards)
            if n_pairs > 0:
                matchup_utility = matchup_utility / float(n_pairs)
        else:
            matchup_utility = torch.tensor(0.0, device=device)
        matchup_utility = torch.clamp(matchup_utility, min=-6.0, max=6.0)
        
        # 7. ENHANCED Fatigue penalty with dual rest signals and comprehensive metrics
        fatigue_penalty = self.fatigue_rotation.compute_fatigue(
            rest_times=rest_times, 
            shift_counts=shift_counts, 
            toi_last_period=toi_last_period, 
            players=all_players,
            rest_real_times=rest_real_times,
            intermission_flags=intermission_flags,
            shift_counts_game=shift_counts_game,
            cumulative_toi_game=cumulative_toi_game,
            ewma_shift_lengths=ewma_shift_lengths,
            ewma_rest_lengths=ewma_rest_lengths,
            # TEAM-AWARE: Pass opponent team for team-specific fatigue patterns
            opponent_team=opponent_team
        )
        fatigue_penalty = torch.clamp(fatigue_penalty, min=-6.0, max=6.0)
        
        # 8. Rotation bonus (Markov prior)
        rotation_bonus = torch.tensor(0.0, device=device)
        if previous_deployment:
            prev_key = tuple(sorted(previous_deployment))
            curr_key = tuple(sorted(all_players))
            if prev_key in self.rotation_priors:
                rotation_bonus = torch.tensor(
                    self.rotation_priors[prev_key].get(curr_key, 0.0),
                    device=device
                )
        rotation_bonus = torch.clamp(rotation_bonus, min=-3.0, max=3.0)
        
        # 9. Special teams adjustment
        is_special_teams = (context[5] != 0 or context[6] != 0)  # PP/PK indicators
        special_adjustment = self.special_teams_boost if is_special_teams else torch.tensor(0.0, device=device)
        if isinstance(special_adjustment, torch.Tensor):
            special_adjustment = torch.clamp(special_adjustment, min=-2.0, max=2.0)
        
        # 10. Shift priors (averaged across players in deployment)
        shift_priors_avg = torch.zeros(self.n_shift_features, device=device)
        if self.shift_priors:
            valid_priors = []
            for player in all_players:
                if player in self.shift_priors:
                    valid_priors.append(self.shift_priors[player])
            
            if valid_priors:
                shift_priors_avg = torch.stack(valid_priors).mean(dim=0)
            else:
                # Default shift priors if no players found (realistic NHL values)
                # Values: [avg_shift_s, shift_count_period, rest_s, rest_s, shifts_game, toi_s, shift_s, rest_s]
                shift_priors_avg = torch.tensor([45.0, 15.0, 50.0, 50.0, 18.0, 900.0, 45.0, 15.0], 
                                               device=device, dtype=torch.float32)
        
        # 11. BIDIRECTIONAL TEAM LEARNING: Complete MTL + Opponent behavioral modeling
        team_utility = torch.tensor(0.0, device=device)
        if self.enable_team_embeddings and opponent_team:
            # OPPONENT IDENTITY: How the opponent team typically behaves
            # - Their line combinations preferences
            # - Their coaching tendencies  
            # - Their player deployment patterns
            opp_team_idx = self.team_to_idx.get(opponent_team, self.team_to_idx.get('UNK', 0))
            opp_team_emb = self.team_embeddings(torch.tensor(opp_team_idx, device=device))
            
            # MTL IDENTITY: How Montreal Canadiens typically behave
            # - Our line combinations preferences
            # - Our coaching tendencies
            # - Our player deployment patterns
            mtl_team_idx = self.team_to_idx.get('MTL', 0)
            mtl_team_emb = self.team_embeddings(torch.tensor(mtl_team_idx, device=device))
            
            # BIDIRECTIONAL INTERACTION: MTL vs Opponent matchup dynamics
            # This learns: "How does MTL adapt vs TOR" AND "How does TOR adapt vs MTL"
            # Critical for live prediction: model knows both sides' tendencies
            team_interaction = torch.cat([mtl_team_emb, opp_team_emb], dim=0)  # 32D: MTL+Opponent
            
            # Team-specific utility contribution via small MLP head (32D -> 16D -> 8D -> 1D)
            team_utility = self.team_utility_head(team_interaction).squeeze()  # Output is scalar
            team_utility = torch.nan_to_num(team_utility, nan=0.0, posinf=5.0, neginf=-5.0)
        
        # 12. PLAYER-VS-PLAYER MATCHUP PRIOR: Historical familiarity between specific players
        # This captures how often these exact MTL players have faced these exact opponent players
        matchup_prior_tensor = torch.tensor(0.0, device=device)
        if matchup_prior is not None:
            matchup_prior_tensor = torch.tensor(matchup_prior, device=device, dtype=torch.float32)
            matchup_prior_tensor = torch.nan_to_num(matchup_prior_tensor, nan=0.0, posinf=5.0, neginf=-5.0)
        
        # Combine all utilities - ensure all are 1D tensors
        def ensure_1d_tensor(tensor):
            """Ensure tensor is 1D for concatenation"""
            if tensor.dim() == 0:
                return tensor.unsqueeze(0)
            elif tensor.dim() > 1:
                return tensor.squeeze()
            else:
                return tensor
        
        # Convert all components to 1D tensors
        components = [
            ensure_1d_tensor(base_utility),
            ensure_1d_tensor(player_context_utility),
            ensure_1d_tensor(chemistry_utility),
            ensure_1d_tensor(matchup_utility),
            ensure_1d_tensor(fatigue_penalty),
            ensure_1d_tensor(rotation_bonus),
            ensure_1d_tensor(special_adjustment if isinstance(special_adjustment, torch.Tensor) else torch.tensor([special_adjustment], device=device)),
            ensure_1d_tensor(pooled_player_emb),
            ensure_1d_tensor(context_processed),
            ensure_1d_tensor(self._normalize_shift_priors(shift_priors_avg)),  # Add NORMALIZED shift priors
            ensure_1d_tensor(matchup_prior_tensor)  # PLAYER-VS-PLAYER: Add matchup prior
        ]
        
        # TEAM-AWARE: Add team embedding contribution (with zero padding when team info missing)
        if self.enable_team_embeddings:
            if opponent_team:
                components.insert(-3, ensure_1d_tensor(team_utility))  # Insert before pooled_player_emb
            else:
                # Pad with zero when no team info provided but embeddings are enabled
                zero_team_utility = torch.tensor(0.0, device=device).unsqueeze(0)
                components.insert(-3, zero_team_utility)
        
        feature_vector = torch.cat(components)

        # OOD DETECTION: Comprehensive feature vector validation and logging
        self._validate_and_log_feature_vector(feature_vector, opponent_team)
        
        # Sanitize features to prevent propagation of invalid values
        original_nans = torch.isnan(feature_vector).sum().item()
        original_infs = torch.isinf(feature_vector).sum().item()
        
        feature_vector = torch.nan_to_num(feature_vector, nan=0.0, posinf=5.0, neginf=-5.0)
        feature_vector = torch.clamp(feature_vector, min=-5.0, max=5.0)
        
        # Log sanitization events
        if original_nans > 0 or original_infs > 0:
            self._log_sanitization_event(original_nans, original_infs, opponent_team)
        
        # Assert correct dimension with enhanced error reporting
        team_dim = 1 if self.enable_team_embeddings else 0
        matchup_dim = 1  # Always include matchup prior dimension (0.0 when not available)
        expected_dim = 7 + self.embedding_dim + 16 + self.n_shift_features + team_dim + matchup_dim
        
        if feature_vector.size(0) != expected_dim:
            error_msg = (
                f"CRITICAL: Feature vector dimension mismatch!\n"
                f"  Received: {feature_vector.size(0)} dimensions\n"
                f"  Expected: {expected_dim} dimensions\n"
                f"  Breakdown: 7 (base) + {self.embedding_dim} (embedding) + 16 (context) + "
                f"{self.n_shift_features} (shift) + {team_dim} (team) + {matchup_dim} (matchup)\n"
                f"  Opponent: {opponent_team}\n"
                f"  Team embeddings enabled: {self.enable_team_embeddings}"
            )
            logger.error(error_msg)
            raise AssertionError(error_msg)
        
        # Final deployment score through deep network
        total_utility = self.deployment_scorer(feature_vector)
        
        # PRIOR BOOST: Incorporate candidate generator's sophisticated prior (if available)
        # The probability_prior is already softmax-normalized across candidates by the generator
        # Convert to log-space and add as a bias to the utility (will be re-softmaxed in forward())
        if probability_prior is not None and probability_prior > 0:
            # Prior is in probability space [0,1], convert to log-odds for utility addition
            prior_boost = torch.log(torch.tensor(probability_prior + 1e-8, device=device, dtype=torch.float32))
            prior_boost = torch.clamp(prior_boost, min=-10.0, max=0.0)  # Clamp to prevent extreme values
            total_utility = total_utility + prior_boost
        
        return total_utility.squeeze()
    
    def forward(self, candidates: List[Dict], 
                context: torch.Tensor,
                opponent_on_ice: List[str],
                rest_times: Dict[str, float],
                shift_counts: Dict[str, int],
                toi_last_period: Dict[str, float],
                previous_deployment: Optional[List[str]] = None,
                # ENHANCED FATIGUE INPUTS: New comprehensive signals
                rest_real_times: Optional[Dict[str, float]] = None,
                intermission_flags: Optional[Dict[str, int]] = None,
                shift_counts_game: Optional[Dict[str, int]] = None,
                cumulative_toi_game: Optional[Dict[str, float]] = None,
                ewma_shift_lengths: Optional[Dict[str, float]] = None,
                ewma_rest_lengths: Optional[Dict[str, float]] = None,
                opponent_team: Optional[str] = None) -> torch.Tensor:  # TEAM-AWARE: Add opponent team
        """
        BATCHED forward pass: compute probabilities for all candidates efficiently
        Returns calibrated log-probabilities for numerical stability
        """
        
        n_candidates = len(candidates)
        
        if n_candidates <= self.max_batch_size:
            # Process all candidates at once
            utilities = self._compute_batched_utilities(
                candidates, context, opponent_on_ice,
                rest_times, shift_counts, toi_last_period, previous_deployment,
                rest_real_times, intermission_flags, shift_counts_game, 
                cumulative_toi_game, ewma_shift_lengths, ewma_rest_lengths,
                opponent_team  # TEAM-AWARE: Pass opponent team
            )
        else:
            # Process in batches
            utilities = []
            for i in range(0, n_candidates, self.max_batch_size):
                batch_end = min(i + self.max_batch_size, n_candidates)
                batch_candidates = candidates[i:batch_end]
                
                batch_utilities = self._compute_batched_utilities(
                    batch_candidates, context, opponent_on_ice,
                    rest_times, shift_counts, toi_last_period, previous_deployment,
                    rest_real_times, intermission_flags, shift_counts_game, 
                    cumulative_toi_game, ewma_shift_lengths, ewma_rest_lengths,
                    opponent_team  # TEAM-AWARE: Pass opponent team
                )
                utilities.append(batch_utilities)
            
            utilities = torch.cat(utilities, dim=0)
        
        # Replace any NaN/Inf utilities with safe finite values and report
        nonfinite_mask = ~torch.isfinite(utilities)
        replaced_count = int(nonfinite_mask.sum().item())
        if replaced_count > 0:
            try:
                logger.warning(f"Utilities contained {replaced_count}/{utilities.numel()} non-finite values; sanitizing")
            except Exception:
                pass
        utilities = torch.nan_to_num(utilities, nan=0.0, posinf=10.0, neginf=-10.0)

        # Apply temperature calibration with numerical stability
        denom = torch.clamp(self.calibration_temperature, min=1e-8)
        scaled_utilities = utilities / denom

        # Ensure scaled utilities are finite before softmax
        scaled_utilities = torch.nan_to_num(scaled_utilities, nan=0.0, posinf=10.0, neginf=-10.0)

        # Clamp utilities to prevent extreme values that cause softmax overflow
        scaled_utilities = torch.clamp(scaled_utilities, min=-10.0, max=10.0)
        
        # Compute calibrated log-probabilities with numerical stability
        log_probs = F.log_softmax(scaled_utilities, dim=0)
        
        return log_probs
    
    def predict_probabilities(self,
                             candidates: List[Dict],
                             context: np.ndarray,
                             opponent_on_ice: List[str],
                             rest_times: Dict[str, float],
                             previous_deployment: Optional[List[str]] = None,
                             temperature: float = 1.0,
                             # ENHANCED FATIGUE INPUTS: Support for comprehensive fatigue tracking
                             shift_counts: Optional[Dict[str, int]] = None,
                             toi_last_period: Optional[Dict[str, float]] = None,
                             rest_real_times: Optional[Dict[str, float]] = None,
                             intermission_flags: Optional[Dict[str, int]] = None,
                             shift_counts_game: Optional[Dict[str, int]] = None,
                             cumulative_toi_game: Optional[Dict[str, float]] = None,
                             ewma_shift_lengths: Optional[Dict[str, float]] = None,
                             ewma_rest_lengths: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Convenience method for live prediction with comprehensive fatigue tracking
        Returns probabilities (not log-probabilities) for easy consumption
        """
        # Convert context to tensor
        context_tensor = torch.tensor(context, dtype=torch.float32, device=device)
        
        # Initialize optional inputs with defaults
        shift_counts = shift_counts or {}
        toi_last_period = toi_last_period or {}
        rest_real_times = rest_real_times or {}
        intermission_flags = intermission_flags or {}
        shift_counts_game = shift_counts_game or {}
        cumulative_toi_game = cumulative_toi_game or {}
        ewma_shift_lengths = ewma_shift_lengths or {}
        ewma_rest_lengths = ewma_rest_lengths or {}
        
        # Call enhanced forward method with comprehensive fatigue inputs
        with torch.no_grad():
            log_probs = self.forward(
                candidates, context_tensor, opponent_on_ice,
                rest_times, shift_counts, toi_last_period, previous_deployment,
                rest_real_times=rest_real_times,
                intermission_flags=intermission_flags,
                shift_counts_game=shift_counts_game,
                cumulative_toi_game=cumulative_toi_game,
                ewma_shift_lengths=ewma_shift_lengths,
                ewma_rest_lengths=ewma_rest_lengths
            )
            
            # Apply temperature scaling
            scaled_log_probs = log_probs / temperature
            
            # Convert to probabilities
            probabilities = torch.exp(scaled_log_probs)
            
        return probabilities.cpu().numpy()
    
    def _compute_batched_utilities(self, candidates: List[Dict],
                                  context: torch.Tensor,
                                  opponent_on_ice: List[str],
                                  rest_times: Dict[str, float],
                                  shift_counts: Dict[str, int],
                                  toi_last_period: Dict[str, float],
                                  previous_deployment: Optional[List[str]] = None,
                                  # ENHANCED FATIGUE INPUTS: New comprehensive signals
                                  rest_real_times: Optional[Dict[str, float]] = None,
                                  intermission_flags: Optional[Dict[str, int]] = None,
                                  shift_counts_game: Optional[Dict[str, int]] = None,
                                  cumulative_toi_game: Optional[Dict[str, float]] = None,
                                  ewma_shift_lengths: Optional[Dict[str, float]] = None,
                                  ewma_rest_lengths: Optional[Dict[str, float]] = None,
                                  opponent_team: Optional[str] = None) -> torch.Tensor:  # TEAM-AWARE: Add opponent team
        """Compute utilities for a batch of candidates efficiently"""
        
        batch_utilities = []
        
        # Process candidates in vectorized manner where possible
        for candidate in candidates:
            # PRIOR INCORPORATION: Extract both matchup prior and full probability prior
            matchup_prior = candidate.get('matchup_prior', None)
            probability_prior = candidate.get('probability_prior', None)  # Softmax-normalized combined prior
            
            utility = self.compute_deployment_utility(
                candidate, context, opponent_on_ice,
                rest_times, shift_counts, toi_last_period, previous_deployment,
                rest_real_times, intermission_flags, shift_counts_game, 
                cumulative_toi_game, ewma_shift_lengths, ewma_rest_lengths,
                opponent_team,  # TEAM-AWARE: Pass opponent team to utility computation
                matchup_prior,   # PLAYER-VS-PLAYER: Pass matchup prior from candidate
                probability_prior  # FULL PRIOR: Pass combined softmax-normalized prior
            )
            batch_utilities.append(utility)
        
        return torch.stack(batch_utilities)
    
    def update_rotation_priors(self, deployment_sequence: List[List[str]], 
                               learning_rate: float = 0.1):
        """
        Update Markov rotation priors from observed sequences
        Uses exponential smoothing for online learning
        """
        
        for i in range(len(deployment_sequence) - 1):
            prev = tuple(sorted(deployment_sequence[i]))
            curr = tuple(sorted(deployment_sequence[i + 1]))
            
            # Exponential smoothing update
            old_value = self.rotation_priors[prev].get(curr, 0.0)
            self.rotation_priors[prev][curr] = (
                (1 - learning_rate) * old_value + learning_rate * 1.0
            )
            
            # Decay other transitions
            for other_key in self.rotation_priors[prev]:
                if other_key != curr:
                    self.rotation_priors[prev][other_key] *= (1 - learning_rate * 0.1)
    
    def predict_deployment_chain(self, current_state: Dict, 
                                 rest_patterns: Dict,
                                 n_future: int = 3) -> List[Dict]:
        """
        Predict chain of future deployments based on current state
        Uses learned rest patterns and rotation priors
        """
        
        predictions = []
        current_deployment = current_state.get('current_deployment')
        player_last_shift_end = current_state.get('player_last_shift_end', {})
        game_clock = current_state.get('game_clock', 0)
        
        for i in range(n_future):
            # Estimate when current shift will end
            expected_shift_end = game_clock + self._estimate_shift_length(current_state)
            
            # Calculate player availability at shift end
            available_players = self._get_available_players(
                expected_shift_end, 
                player_last_shift_end,
                rest_patterns
            )
            
            # Generate candidates
            candidates = self._generate_future_candidates(
                available_players,
                current_deployment,
                self.rotation_priors
            )
            
            # Predict most likely deployment
            if candidates:
                # Create context for future prediction
                future_context = self._project_context(current_state, i)
                
                # Get probabilities
                with torch.no_grad():
                    log_probs = self.forward(
                        candidates,
                        future_context,
                        current_state.get('opponent_on_ice', []),
                        {},  # Rest times will be calculated
                        {},  # Shift counts
                        {},  # TOI last period
                        current_deployment
                    )
                
                probs = torch.exp(log_probs)
                best_idx = torch.argmax(probs).item()
                
                prediction = {
                    'time_offset': expected_shift_end - game_clock,
                    'deployment': candidates[best_idx],
                    'probability': probs[best_idx].item(),
                    'confidence': self._calculate_confidence(probs),
                    'top_3_alternatives': self._get_top_alternatives(candidates, probs, 3)
                }
                
                predictions.append(prediction)
                
                # Update state for next prediction
                current_deployment = candidates[best_idx]
                game_clock = expected_shift_end
                
                # Update player rest tracking
                for player in candidates[best_idx].get('forwards', []) + candidates[best_idx].get('defense', []):
                    player_last_shift_end[player] = expected_shift_end
        
        return predictions
    
    def _estimate_shift_length(self, state: Dict) -> float:
        """
        Estimate shift length using fatigue module for consistency
        Delegates to fatigue module's context-aware calculation
        """
        
        # Extract players and context for fatigue module
        current_deployment = state.get('current_deployment', [])
        if not current_deployment:
            # Fallback to simple calculation if no deployment provided
            return self._simple_shift_estimate(state)
        
        # Create fatigue context
        rest_times = {p: 60.0 for p in current_deployment}  # Assume moderate rest
        shift_counts = {p: 10 for p in current_deployment}  # Assume moderate usage
        toi_last_period = {p: 300.0 for p in current_deployment}  # Assume moderate TOI
        
        # Use fatigue module to compute context-aware shift length
        # Note: opponent_team not available in this context, will use default behavior
        fatigue_penalty = self.fatigue_rotation.compute_fatigue(
            rest_times, shift_counts, toi_last_period, current_deployment,
            opponent_team=None  # TEAM-AWARE: No opponent team in shift length prediction
        )
        
        # Base length with fatigue adjustment
        base_length = 45.0
        
        # Special teams adjustments
        strength = state.get('strength', '5v5')
        if 'powerPlay' in strength or '5v4' in strength:
            base_length *= 1.35
        elif 'penaltyKill' in strength or '4v5' in strength:
            base_length *= 1.25
        elif '3v3' in strength:
            base_length *= 1.5
        
        # Apply fatigue penalty (negative penalty = longer shifts if well-rested)
        fatigue_adjusted_length = base_length * (1.0 - fatigue_penalty.item() * 0.3)
        
        return max(25.0, min(90.0, fatigue_adjusted_length))  # Bounded [25s, 90s]
    
    def _simple_shift_estimate(self, state: Dict) -> float:
        """Simple fallback shift estimation when fatigue module unavailable"""
        
        base_length = 45.0
        
        # Adjust for special teams
        if 'powerPlay' in state.get('strength', ''):
            base_length *= 1.35
        elif 'penaltyKill' in state.get('strength', ''):
            base_length *= 1.25
        elif '3v3' in state.get('strength', ''):
            base_length *= 1.5
        
        # Adjust for period and score
        period = state.get('period', 1)
        score_diff = state.get('score_diff', 0)
        
        if period == 3:
            if score_diff < 0:  # Trailing
                base_length *= 0.85  # Shorter shifts when desperate
            elif score_diff > 1:  # Comfortable lead
                base_length *= 1.1  # Can afford longer shifts
        
        return base_length
    
    def _get_available_players(self, time: float, 
                              last_shift_end: Dict,
                              rest_patterns: Dict) -> Dict:
        """Determine which players are available based on rest patterns"""
        
        available = {'forwards': [], 'defense': []}
        
        for player, last_end in last_shift_end.items():
            time_rested = time - last_end
            
            # Get player's typical rest requirement
            if player in rest_patterns:
                required_rest = rest_patterns[player].get('mean', 90)
            else:
                required_rest = 90  # Default
            
            if time_rested >= required_rest * 0.8:  # 80% of typical rest
                # Determine position (simplified)
                if player in self.player_embeddings.player_to_idx:
                    # Would check actual position data
                    available['forwards'].append(player)  # Simplified
        
        return available
    
    def _calculate_confidence(self, probs: torch.Tensor) -> float:
        """Calculate confidence score from probability distribution"""
        
        # Higher entropy = lower confidence
        entropy = -(probs * torch.log(probs + 1e-10)).sum().item()
        max_entropy = np.log(len(probs))
        
        # Normalize to 0-1 where 1 is most confident
        confidence = 1.0 - (entropy / max_entropy)
        
        return confidence
    
    def _generate_future_candidates(self, available_players: Dict,
                                   current_deployment: Optional[List[str]],
                                   rotation_priors: Dict) -> List[Dict]:
        """Generate candidate deployments for future prediction"""
        
        candidates = []
        
        # If we have rotation priors, use them
        if current_deployment and tuple(sorted(current_deployment)) in rotation_priors:
            curr_key = tuple(sorted(current_deployment))
            likely_next = rotation_priors[curr_key]
            
            # Sort by probability
            sorted_next = sorted(likely_next.items(), key=lambda x: x[1], reverse=True)
            
            for deployment_key, prob in sorted_next[:10]:  # Top 10 most likely
                # Parse deployment key
                if '_' in deployment_key:
                    fwd_part, def_part = deployment_key.split('_')
                    forwards = fwd_part.split('|') if fwd_part else []
                    defense = def_part.split('|') if def_part else []
                    
                    candidates.append({
                        'forwards': forwards,
                        'defense': defense,
                        'rotation_probability': prob
                    })
        
        # Add some available player combinations if not enough from priors
        if len(candidates) < 5 and available_players:
            # Simple combination (would be more sophisticated in production)
            if len(available_players.get('forwards', [])) >= 3:
                candidates.append({
                    'forwards': available_players['forwards'][:3],
                    'defense': available_players.get('defense', [])[:2],
                    'rotation_probability': 0.1
                })
        
        return candidates if candidates else [{'forwards': [], 'defense': []}]
    
    def _project_context(self, current_state: Dict, steps_ahead: int) -> torch.Tensor:
        """Project game context into the future"""
        
        context = torch.zeros(36, dtype=torch.float32)  # Updated for score situation features
        
        # Copy current context
        if 'context' in current_state:
            context = current_state['context'].clone()
        
        # Adjust time features
        period = current_state.get('period', 1)
        period_time = current_state.get('period_time', 0)
        
        # Project time forward (approximate)
        future_time = period_time + (45 * steps_ahead)  # 45 sec per shift
        
        if future_time > 1200:  # Next period
            period = min(period + 1, 3)
            future_time = future_time % 1200
        
        context[3] = period / 3.0
        context[4] = future_time / 1200.0
        
        # Decay momentum features slightly
        context[16] *= (0.9 ** steps_ahead)
        context[17] *= (0.9 ** steps_ahead)
        
        return context
    
    def _get_top_alternatives(self, candidates: List[Dict], 
                            probs: torch.Tensor, n: int = 3) -> List[Dict]:
        """Get top N alternative deployments with probabilities"""
        
        top_indices = torch.topk(probs, min(n, len(probs))).indices
        
        alternatives = []
        for idx in top_indices:
            alternatives.append({
                'deployment': candidates[idx.item()],
                'probability': probs[idx].item()
            })
        
        return alternatives
    
    def train_step(self, batch_data: Dict, optimizer: optim.Optimizer, 
                   l1_reg: float = 1e-4, l2_reg: float = 1e-4) -> float:
        """
        HARDENED: Single training step with configurable L1/L2 regularization
        
        Args:
            batch_data: Training batch
            optimizer: PyTorch optimizer
            l1_reg: L1 regularization strength
            l2_reg: L2 regularization strength
        """
        
        optimizer.zero_grad()
        
        # Extract batch data
        candidates = batch_data['candidates']
        context = batch_data['context']
        true_deployment = batch_data['true_deployment']
        opponent_on_ice = batch_data['opponent_on_ice']
        rest_times = batch_data['rest_times']
        shift_counts = batch_data['shift_counts']
        toi_last_period = batch_data['toi_last_period']
        previous = batch_data.get('previous_deployment')
        season_weight = batch_data.get('season_weight', 1.0)  # Get season weight
        
        # TEAM-AWARE: Extract opponent team for team-specific learning
        opponent_team = batch_data.get('opponent_team', None)
        
        # ENHANCED FATIGUE: Extract comprehensive fatigue inputs
        rest_real_times = batch_data.get('rest_real_times', {})
        intermission_flags = batch_data.get('intermission_flags', {})
        shift_counts_game = batch_data.get('shift_counts_game', {})
        cumulative_toi_game = batch_data.get('cumulative_toi_game', {})
        ewma_shift_lengths = batch_data.get('ewma_shift_lengths', {})
        ewma_rest_lengths = batch_data.get('ewma_rest_lengths', {})
        
        # Basic sanity checks before forward
        if len(candidates) < 2:
            return 0.0
        if context is None or not torch.isfinite(context).all():
            return 0.0
        
        # COMPREHENSIVE Forward pass with all team-aware and fatigue inputs
        log_probs = self.forward(
            candidates, context, opponent_on_ice,
            rest_times, shift_counts, toi_last_period, previous,
            # ENHANCED FATIGUE: Comprehensive fatigue signals
            rest_real_times, intermission_flags, shift_counts_game,
            cumulative_toi_game, ewma_shift_lengths, ewma_rest_lengths,
            # TEAM-AWARE: Opponent team for team-specific patterns
            opponent_team
        )
        
        # Find index of true deployment
        true_idx = None
        for i, cand in enumerate(candidates):
            cand_players = set(cand.get('forwards', []) + cand.get('defense', []))
            true_players = set(true_deployment.get('forwards', []) + 
                             true_deployment.get('defense', []))
            if cand_players == true_players:
                true_idx = i
                break
        
        if true_idx is None:
            # True deployment not in candidates - skip
            return 0.0
        
        # Negative log-likelihood loss with numerical stability
        log_prob_true = log_probs[true_idx]
        
        # Guard against -inf log probabilities
        if torch.isinf(log_prob_true) or torch.isnan(log_prob_true):
            return 0.0  # Skip batch with invalid probabilities
            
        loss = -log_prob_true
        
        # Apply season weight to the loss
        weighted_loss = loss * season_weight
        
        # HARDENED: Add configurable L1 + L2 regularization 
        l1_penalty = torch.tensor(0.0, device=device)
        l2_penalty = torch.tensor(0.0, device=device)
        
        for param in self.parameters():
            if param is None:
                continue
            if not torch.isfinite(param).all():
                # sanitize parameter copy for regularization
                safe_param = torch.nan_to_num(param, nan=0.0, posinf=0.0, neginf=0.0)
                l1_penalty = l1_penalty + torch.norm(safe_param, 1)  # L1 norm
                l2_penalty = l2_penalty + torch.norm(safe_param, 2)  # L2 norm
            else:
                l1_penalty = l1_penalty + torch.norm(param, 1)  # L1 norm
                l2_penalty = l2_penalty + torch.norm(param, 2)  # L2 norm
        
        # Total loss with configurable regularization
        total_loss = weighted_loss + l1_reg * l1_penalty + l2_reg * l2_penalty
        if not torch.isfinite(total_loss):
            return 0.0
        
        # Backward pass
        total_loss.backward()
        
        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(self.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        return total_loss.item()
    
    def calibrate_temperature(self, validation_data: List[Dict], 
                             max_iter: int = 100, lr: float = 0.01):
        """
        Calibrate temperature parameter using held-out validation data
        Implements Platt scaling for proper probability calibration
        """
        
        logger.info("Calibrating temperature parameter...")
        
        # Collect validation predictions
        raw_logits = []
        true_labels = []
        
        self.eval()
        with torch.no_grad():
            for batch in validation_data:
                candidates = batch['candidates']
                true_deployment = batch['true_deployment']
                
                # Get raw utilities (before temperature scaling)
                utilities = self._compute_batched_utilities(
                    candidates, batch['context'], batch['opponent_on_ice'],
                    batch['rest_times'], batch['shift_counts'], batch['toi_last_period'],
                    batch.get('previous_deployment')
                )
                
                # Find true label index
                true_idx = self._find_true_deployment_index(true_deployment, candidates)
                if true_idx is not None:
                    raw_logits.append(utilities)
                    true_labels.append(true_idx)
        
        if len(raw_logits) < 10:
            logger.warning("Insufficient validation data for temperature calibration")
            return
        
        # Optimize temperature using cross-entropy loss
        temp_optimizer = optim.LBFGS([self.calibration_temperature], lr=lr, max_iter=max_iter)
        
        def closure():
            temp_optimizer.zero_grad()
            total_loss = torch.tensor(0.0, device=device, requires_grad=True)
            
            # Process each batch separately to handle variable sizes
            for logits, true_idx in zip(raw_logits, true_labels):
                # Apply temperature scaling
                denom = torch.clamp(self.calibration_temperature, min=1e-8)
                scaled_logits = logits / denom
                # Sanitize and clamp for stability
                scaled_logits = torch.nan_to_num(scaled_logits, nan=0.0, posinf=10.0, neginf=-10.0)
                scaled_logits = torch.clamp(scaled_logits, min=-10.0, max=10.0)
                log_probs = F.log_softmax(scaled_logits, dim=-1)
                
                # Cross-entropy loss for this batch
                true_idx_tensor = torch.tensor(true_idx, dtype=torch.long, device=device)
                loss = F.nll_loss(log_probs.unsqueeze(0), true_idx_tensor.unsqueeze(0))
                total_loss = total_loss + loss
            
            # Average loss over all batches
            avg_loss = total_loss / len(raw_logits)
            avg_loss.backward()
            
            return avg_loss
        
        temp_optimizer.step(closure)
        
        logger.info(f"✓ Temperature calibrated to: {self.calibration_temperature.item():.4f}")
    
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
    
    def save_model(self, path: str):
        """Save model state and parameters"""
        torch.save({
            'model_state_dict': self.state_dict(),
            'player_mappings': self.player_embeddings.player_to_idx,
            'rotation_priors': dict(self.rotation_priors),
            'embedding_dim': self.embedding_dim,
            'n_context_features': self.n_context_features
        }, path)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model state and parameters"""
        checkpoint = torch.load(path, map_location=device)
        self.load_state_dict(checkpoint['model_state_dict'])
        self.player_embeddings.player_to_idx = checkpoint['player_mappings']
        self.rotation_priors = defaultdict(
            lambda: defaultdict(float), 
            checkpoint['rotation_priors']
        )
        
        logger.info(f"Model loaded from {path}")


# Stochastic Rare-Line Sampler
class StochasticRareLineSampler:
    """
    Implements stochastic sampling for rare line combinations
    Ensures model learns from infrequent but critical deployments
    """
    
    def __init__(self, temperature: float = 1.5, rare_threshold: int = 5):
        self.temperature = temperature
        self.rare_threshold = rare_threshold
        self.line_frequencies = defaultdict(int)
        
    def update_frequencies(self, deployment_data: pd.DataFrame):
        """Track line combination frequencies"""
        for _, row in deployment_data.iterrows():
            forwards = tuple(sorted(row.get('forwards', [])))
            defense = tuple(sorted(row.get('defense', [])))
            line_key = (forwards, defense)
            self.line_frequencies[line_key] += 1
    
    def sample_candidates(self, all_candidates: List[Dict], 
                         n_samples: int = 12) -> List[Dict]:
        """
        Sample candidates with bias towards rare combinations
        Uses inverse frequency weighting with temperature control
        """
        
        if len(all_candidates) <= n_samples:
            return all_candidates
        
        # Calculate sampling weights
        weights = []
        for candidate in all_candidates:
            forwards = tuple(sorted(candidate.get('forwards', [])))
            defense = tuple(sorted(candidate.get('defense', [])))
            line_key = (forwards, defense)
            
            frequency = self.line_frequencies.get(line_key, 0)
            
            if frequency <= self.rare_threshold:
                # Boost rare lines
                weight = 1.0 / (1.0 + frequency) ** (1.0 / self.temperature)
            else:
                # Normal weight for common lines
                weight = 1.0 / (1.0 + np.log(frequency + 1))
            
            weights.append(weight)
        
        # Normalize weights
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # Sample without replacement
        indices = np.random.choice(
            len(all_candidates), 
            size=min(n_samples, len(all_candidates)),
            replace=False,
            p=weights
        )
        
        return [all_candidates[i] for i in indices]


if __name__ == "__main__":
    """Test PyTorch model initialization and basic forward pass"""
    
    # Initialize model
    model = PyTorchConditionalLogit(n_context_features=36, embedding_dim=32)  # Updated for score situation features
    model.to(device)
    
    # Register some test players
    test_players = [f"player_{i}" for i in range(50)]
    model.register_players(test_players)
    
    # Create test candidates
    candidates = [
        {
            'forwards': ['player_1', 'player_2', 'player_3'],
            'defense': ['player_4', 'player_5']
        },
        {
            'forwards': ['player_6', 'player_7', 'player_8'],
            'defense': ['player_9', 'player_10']
        }
    ]
    
    # Test context
    context = torch.randn(36, device=device)  # Updated for score situation features
    
    # Test forward pass
    log_probs = model.forward(
        candidates,
        context,
        opponent_on_ice=['player_11', 'player_12'],
        rest_times={'player_1': 60, 'player_2': 45},
        shift_counts={'player_1': 10, 'player_2': 12},
        toi_last_period={'player_1': 300, 'player_2': 350},
        previous_deployment=['player_15', 'player_16']
    )
    
    print(f"Model initialized successfully on {device}")
    print(f"Log probabilities shape: {log_probs.shape}")
    print(f"Probabilities sum to: {torch.exp(log_probs).sum().item():.4f}")
    
    # Initialize optimizer for training
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    print(f"Optimizer initialized with {sum(p.numel() for p in model.parameters())} parameters")
