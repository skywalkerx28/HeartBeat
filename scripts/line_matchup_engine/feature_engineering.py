"""
HeartBeat Feature Engineering for Line Matchup Prediction
Builds sophisticated features for conditional logit model
Professional-grade NHL analytics implementation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import logging
from scipy import sparse
from sklearn.preprocessing import LabelEncoder, StandardScaler
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class FeatureSet:
    """Container for all features used in prediction model"""
    # Context features (global)
    zone_features: np.ndarray  # One-hot encoded zone
    strength_features: np.ndarray  # One-hot encoded strength state
    score_features: np.ndarray  # Score differential buckets
    time_features: np.ndarray  # Period and time buckets
    
    # Player-specific features
    player_base: Dict[str, float]  # Base deployment propensity
    player_context: Dict[str, np.ndarray]  # Player x context interactions
    
    # Chemistry features
    forward_chemistry: Dict[Tuple[str, str], float]  # Pairwise chemistry
    defense_chemistry: Dict[Tuple[str, str], float]
    
    # Matchup features
    matchup_scores: Dict[Tuple[str, str], float]  # Player vs opponent scores
    
    # Fatigue/rotation features
    rest_times: Dict[str, float]  # Time since last shift
    shift_lengths: Dict[str, float]  # Recent shift lengths
    rotation_probs: Dict[str, float]  # Markov rotation probabilities
    
    # Shift priors
    shift_priors: Dict[str, np.ndarray]  # Historical shift patterns per player


class FeatureEngineer:
    """Creates features for line matchup prediction"""
    
    def __init__(self, shift_priors_path: Optional[str] = None):
        self.zone_encoder = LabelEncoder()
        self.strength_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        
        # Load shift priors if provided
        self.shift_priors = {}
        if shift_priors_path:
            self._load_shift_priors(shift_priors_path)
        
        # Feature dimensions
        self.n_zone_features = 3  # OZ, NZ, DZ
        self.n_strength_features = 7  # 5v5, 5v4, 4v5, 4v4, 3v3, 6v5, 5v6
        self.n_score_features = 5  # down 2+, down 1, tied, up 1, up 2+
        self.n_shift_features = 8  # EV_mean, EV_std, PP_mean, PK_mean, shifts_per_game, toi_per_game, rest_mean, rest_std
        self.n_time_features = 6  # period + early/middle/late + rolling_xG + rolling_PDO
        
        # Learned parameters (populated during training)
        self.player_embeddings = {}
        self.chemistry_matrix = {}
        self.matchup_matrix = {}
    
    def _load_shift_priors(self, shift_priors_path: str):
        """Load shift priors from parquet file"""
        try:
            path = Path(shift_priors_path)
            if path.suffix == '.parquet':
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            
            # Create dictionary mapping player_id to shift statistics
            for _, row in df.iterrows():
                player_id = str(int(row['player_id']))
                
                # Extract key shift metrics
                priors = np.array([
                    row.get('EV_shift_mean', 45.0),  # Average EV shift length
                    row.get('EV_shift_std', 15.0),   # EV shift variability
                    row.get('PP_shift_mean', 50.0),  # Average PP shift length
                    row.get('PK_shift_mean', 50.0),  # Average PK shift length
                    row.get('avg_shifts_per_game', 18.0),  # Shifts per game
                    row.get('avg_toi_per_game', 900.0),    # TOI per game (seconds)
                    row.get('overall_shift_mean', 45.0),   # Overall avg shift
                    row.get('overall_shift_std', 15.0)     # Overall variability
                ])
                
                self.shift_priors[player_id] = priors
            
            logger.info(f"Loaded shift priors for {len(self.shift_priors)} players")
            
        except Exception as e:
            logger.warning(f"Failed to load shift priors: {e}")
            # Continue without shift priors
        
    def create_context_features(self, event_data: pd.DataFrame) -> np.ndarray:
        """Create global context features for each event"""
        n_events = len(event_data)
        
        # Zone features (one-hot)
        zone_features = np.zeros((n_events, self.n_zone_features))
        zone_map = {'oz': 0, 'nz': 1, 'dz': 2}
        for idx, zone in enumerate(event_data['zone_start']):
            if zone in zone_map:
                zone_features[idx, zone_map[zone]] = 1
            else:
                zone_features[idx, 1] = 1  # Default to neutral zone
        
        # Strength features (one-hot)
        strength_features = np.zeros((n_events, self.n_strength_features))
        strength_map = {
            '5v5': 0, 'evenStrength': 0,
            '5v4': 1, 'powerPlay': 1,
            '4v5': 2, 'penaltyKill': 2,
            '4v4': 3, '3v3': 4, '6v5': 5, '5v6': 6
        }
        for idx, strength in enumerate(event_data['strength_state']):
            strength_idx = strength_map.get(strength, 0)
            strength_features[idx, strength_idx] = 1
        
        # Score differential features (bucketized)
        score_features = np.zeros((n_events, self.n_score_features))
        for idx, diff in enumerate(event_data['score_differential']):
            if diff <= -2:
                score_features[idx, 0] = 1  # Down by 2+
            elif diff == -1:
                score_features[idx, 1] = 1  # Down by 1
            elif diff == 0:
                score_features[idx, 2] = 1  # Tied
            elif diff == 1:
                score_features[idx, 3] = 1  # Up by 1
            else:
                score_features[idx, 4] = 1  # Up by 2+
        
        # Time features (period + time bucket + rolling metrics)
        time_features = np.zeros((n_events, self.n_time_features + 2))  # +2 for rolling xG and PDO
        
        # Calculate rolling metrics for each event
        rolling_xg_diff = self._calculate_rolling_xg_differential(event_data)
        rolling_pdo = self._calculate_rolling_pdo(event_data)
        
        for idx, row in event_data.iterrows():
            period = min(row['period'] - 1, 2)  # Cap at period 3
            time_features[idx, period] = 1
            
            # Add time bucket as continuous feature
            if row['time_bucket'] == 'early':
                time_features[idx, 3] = 0.0
            elif row['time_bucket'] == 'middle':
                time_features[idx, 3] = 0.5
            else:  # late
                time_features[idx, 3] = 1.0
            
            # Add rolling metrics (NEW)
            time_features[idx, 4] = rolling_xg_diff[idx]  # Rolling xG differential
            time_features[idx, 5] = rolling_pdo[idx]       # Rolling PDO
        
        # Add reserved feature for future expansion
        reserved_features = np.zeros((n_events, 1))  # Reserved for future features
        
        # Combine all context features to exactly 20 dimensions
        # 3 (zone) + 7 (strength) + 5 (score) + 4 (time) + 1 (reserved) = 20
        context_features = np.hstack([
            zone_features,           # 3 features
            strength_features,       # 7 features  
            score_features,          # 5 features
            time_features[:, :4],    # 4 time features (period + bucket)
            reserved_features        # 1 reserved feature
        ])
        
        # Verify exact dimension requirement
        assert context_features.shape[1] == 20, f"Context tensor must be exactly 20 features, got {context_features.shape[1]}"
        
        logger.info(f"Created context features with shape: {context_features.shape}")
        return context_features
    
    def create_player_features(self, 
                              players: List[str],
                              context: np.ndarray,
                              player_embeddings: Optional[Dict] = None) -> np.ndarray:
        """Create player-specific features including embeddings"""
        
        if player_embeddings is None:
            player_embeddings = self.player_embeddings
        
        n_players = len(players)
        embedding_dim = 16  # Dimension of player embeddings
        
        # Initialize feature matrix
        player_features = np.zeros((n_players, embedding_dim + len(context)))
        
        for idx, player_id in enumerate(players):
            # Get player embedding (or initialize if new)
            if player_id not in player_embeddings:
                player_embeddings[player_id] = np.random.randn(embedding_dim) * 0.01
            
            embedding = player_embeddings[player_id]
            player_features[idx, :embedding_dim] = embedding
            
            # Add player x context interaction
            player_features[idx, embedding_dim:] = embedding[0] * context
        
        return player_features
    
    def create_chemistry_features(self,
                                 forward_combo: List[str],
                                 defense_pair: List[str]) -> float:
        """Calculate chemistry score for a line combination"""
        chemistry_score = 0.0
        
        # Forward chemistry (all pairs within the trio)
        for i in range(len(forward_combo)):
            for j in range(i + 1, len(forward_combo)):
                pair = tuple(sorted([forward_combo[i], forward_combo[j]]))
                chemistry_score += self.chemistry_matrix.get(pair, 0.0)
        
        # Defense chemistry
        if len(defense_pair) >= 2:
            d_pair = tuple(sorted(defense_pair[:2]))
            chemistry_score += self.chemistry_matrix.get(d_pair, 0.0)
        
        # Forward-defense chemistry (weighted less)
        for f in forward_combo:
            for d in defense_pair:
                pair = tuple(sorted([f, d]))
                chemistry_score += 0.3 * self.chemistry_matrix.get(pair, 0.0)
        
        return chemistry_score
    
    def create_matchup_features(self,
                               our_players: List[str],
                               opp_players: List[str]) -> float:
        """Calculate matchup score between our players and opponents"""
        matchup_score = 0.0
        
        for our_player in our_players:
            for opp_player in opp_players:
                matchup_key = (our_player, opp_player)
                matchup_score += self.matchup_matrix.get(matchup_key, 0.0)
        
        # Normalize by number of matchups
        if len(our_players) > 0 and len(opp_players) > 0:
            matchup_score /= (len(our_players) * len(opp_players))
        
        return matchup_score
    
    def create_fatigue_features(self,
                               players: List[str],
                               rest_times: Dict[str, float],
                               shift_lengths: Dict[str, float]) -> np.ndarray:
        """Create fatigue-related features for players"""
        
        fatigue_features = []
        
        for player_id in players:
            rest = rest_times.get(player_id, 120.0)  # Default 2 minutes if unknown
            recent_shift = shift_lengths.get(player_id, 45.0)  # Default 45 seconds
            
            # Features: rest time, recent shift length, fatigue score
            fatigue_score = np.exp(-rest / 60.0) * (1 + recent_shift / 60.0)
            fatigue_features.extend([rest, recent_shift, fatigue_score])
        
        return np.array(fatigue_features)
    
    def create_rotation_features(self,
                                current_players: List[str],
                                previous_players: List[str],
                                rotation_history: Dict) -> float:
        """Calculate rotation probability based on Markov chain"""
        
        if not previous_players:
            return 0.0
        
        # Create transition key
        prev_key = '|'.join(sorted(previous_players))
        curr_key = '|'.join(sorted(current_players))
        transition_key = f"{prev_key}->{curr_key}"
        
        # Get transition probability from history
        rotation_prob = rotation_history.get(transition_key, 0.001)  # Small default
        
        # Apply log transformation for model
        return np.log(rotation_prob + 1e-10)
    
    def build_candidate_features(self,
                                candidates: List[Dict],
                                context: np.ndarray,
                                opponent_on_ice: List[str],
                                rest_times: Dict[str, float]) -> np.ndarray:
        """Build feature matrix for all candidate deployments"""
        
        n_candidates = len(candidates)
        feature_list = []
        
        for candidate in candidates:
            features = []
            
            # Context features (same for all candidates)
            features.extend(context)
            
            # Player base features
            forwards = candidate.get('forwards', [])
            defense = candidate.get('defense', [])
            all_players = forwards + defense
            
            # Average player embeddings
            if self.player_embeddings:
                avg_embedding = np.zeros(16)
                for player in all_players:
                    if player in self.player_embeddings:
                        avg_embedding += self.player_embeddings[player]
                if len(all_players) > 0:
                    avg_embedding /= len(all_players)
                features.extend(avg_embedding)
            
            # Chemistry score
            chemistry = self.create_chemistry_features(forwards, defense)
            features.append(chemistry)
            
            # Matchup score
            matchup = self.create_matchup_features(all_players, opponent_on_ice)
            features.append(matchup)
            
            # Fatigue features (average)
            avg_rest = np.mean([rest_times.get(p, 120.0) for p in all_players])
            features.append(avg_rest)
            
            # Double-shift penalty
            double_shift_penalty = sum([1 for p in all_players if rest_times.get(p, 120) < 30])
            features.append(double_shift_penalty)
            
            # Shift priors (averaged across all players in the deployment)
            if self.shift_priors:
                avg_priors = np.zeros(self.n_shift_features)
                prior_count = 0
                
                for player in all_players:
                    if player in self.shift_priors:
                        avg_priors += self.shift_priors[player]
                        prior_count += 1
                
                if prior_count > 0:
                    avg_priors /= prior_count
                else:
                    # Use default values if no priors found
                    avg_priors = np.array([45.0, 15.0, 50.0, 50.0, 18.0, 900.0, 45.0, 15.0])
                
                features.extend(avg_priors)
            else:
                # No shift priors loaded, use zeros
                features.extend([0.0] * self.n_shift_features)
            
            feature_list.append(features)
        
        feature_matrix = np.array(feature_list)
        logger.debug(f"Built features for {n_candidates} candidates, shape: {feature_matrix.shape}")
        
        return feature_matrix
    
    def learn_embeddings(self, 
                        deployment_data: pd.DataFrame,
                        embedding_dim: int = 16) -> Dict[str, np.ndarray]:
        """Learn player embeddings from deployment history"""
        
        from sklearn.decomposition import TruncatedSVD
        
        # Build co-occurrence matrix
        all_players = set()
        for _, row in deployment_data.iterrows():
            mtl_f = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_d = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            all_players.update(mtl_f + mtl_d)
        
        player_list = sorted(list(all_players))
        player_idx = {p: i for i, p in enumerate(player_list)}
        n_players = len(player_list)
        
        # Co-occurrence matrix
        cooc_matrix = sparse.lil_matrix((n_players, n_players))
        
        for _, row in deployment_data.iterrows():
            mtl_f = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_d = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            players = mtl_f + mtl_d
            
            for i, p1 in enumerate(players):
                if p1 in player_idx:
                    for p2 in players[i+1:]:
                        if p2 in player_idx:
                            idx1, idx2 = player_idx[p1], player_idx[p2]
                            cooc_matrix[idx1, idx2] += 1
                            cooc_matrix[idx2, idx1] += 1
        
        # Convert to CSR for efficiency
        cooc_matrix = cooc_matrix.tocsr()
        
        # Check if we have enough players for SVD
        if n_players < 2:
            logger.warning(f"Insufficient players ({n_players}) for SVD embedding learning")
            self.player_embeddings = {}
            return {}
        
        # Apply SVD for dimensionality reduction
        n_components = min(embedding_dim, n_players - 1)
        if n_components < 1:
            logger.warning(f"Cannot perform SVD with n_components={n_components}")
            self.player_embeddings = {}
            return {}
            
        svd = TruncatedSVD(n_components=n_components)
        embeddings = svd.fit_transform(cooc_matrix)
        
        # Create embedding dictionary
        embedding_dict = {}
        for player, idx in player_idx.items():
            embedding_dict[player] = embeddings[idx]
        
        logger.info(f"Learned embeddings for {len(embedding_dict)} players")
        self.player_embeddings = embedding_dict
        
        return embedding_dict
    
    def learn_chemistry(self, 
                       deployment_data: pd.DataFrame,
                       min_together: int = 5,
                       shrinkage_factor: float = 15.0) -> Dict[Tuple[str, str], float]:
        """
        Learn chemistry scores with Bayesian shrinkage for small samples
        Uses adjusted plus-minus approach: η̂ = (n/(n+k))η_raw
        """
        
        chemistry_scores = {}
        pair_counts = {}
        pair_success = {}
        pair_toi = {}  # Track actual time together
        
        for _, row in deployment_data.iterrows():
            mtl_f = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_d = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            
            # Use exact shift length if available, otherwise estimate
            shift_length = row.get('shift_length', 45.0)
            
            # Score differential as proxy for success (goals for/against)
            success_metric = row.get('score_differential', 0)
            
            # Track forward pairs with exact TOI
            for i in range(len(mtl_f)):
                for j in range(i + 1, len(mtl_f)):
                    pair = tuple(sorted([mtl_f[i], mtl_f[j]]))
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
                    pair_success[pair] = pair_success.get(pair, 0) + success_metric
                    pair_toi[pair] = pair_toi.get(pair, 0) + shift_length
            
            # Track defense pairs with exact TOI
            for i in range(len(mtl_d)):
                for j in range(i + 1, len(mtl_d)):
                    pair = tuple(sorted([mtl_d[i], mtl_d[j]]))
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
                    pair_success[pair] = pair_success.get(pair, 0) + success_metric
                    pair_toi[pair] = pair_toi.get(pair, 0) + shift_length
            
            # Forward-defense cross chemistry (reduced weight)
            for f in mtl_f:
                for d in mtl_d:
                    pair = tuple(sorted([f, d]))
                    pair_counts[pair] = pair_counts.get(pair, 0) + 0.5  # Lower weight
                    pair_success[pair] = pair_success.get(pair, 0) + success_metric * 0.5
                    pair_toi[pair] = pair_toi.get(pair, 0) + shift_length * 0.5
        
        # BAYESIAN SHRINKAGE: Implement adjusted plus-minus style shrinkage
        for pair, count in pair_counts.items():
            if count >= min_together and pair_toi.get(pair, 0) > 0:
                # Raw chemistry score
                raw_chemistry = pair_success[pair] / count
                
                # Bayesian shrinkage: η̂ = (n/(n+k))η_raw
                n_observations = count
                shrunk_chemistry = (n_observations / (n_observations + shrinkage_factor)) * raw_chemistry
                
                # Additional normalization by time together (more time = more reliable)
                time_weight = min(1.0, pair_toi[pair] / 900.0)  # 15 minutes = full weight
                
                # Final chemistry score: tanh-bounded with shrinkage
                final_score = np.tanh(shrunk_chemistry * time_weight / 2.0)
                chemistry_scores[pair] = final_score
                
                # Log high-chemistry pairs for validation
                if abs(final_score) > 0.5:
                    logger.debug(f"High chemistry: {pair} = {final_score:.3f} "
                               f"(n={n_observations}, TOI={pair_toi[pair]:.1f}s)")
        
        logger.info(f"✓ Learned chemistry for {len(chemistry_scores)} player pairs with Bayesian shrinkage")
        logger.info(f"  Shrinkage factor k = {shrinkage_factor}")
        logger.info(f"  Minimum TOI threshold: {min_together} shifts")
        
        self.chemistry_matrix = chemistry_scores
        return chemistry_scores
    
    def learn_matchup_interactions(self, 
                                      deployment_data: pd.DataFrame,
                                      shift_data: Optional[Dict[str, List[float]]] = None,
                                      min_matchups: int = 3) -> Dict[Tuple[str, str], float]:
        """
        Learn multi-level matchup interactions with strength conditioning
        
        MATHEMATICAL IMPROVEMENTS:
        1. Strength-conditioned expectations (separate 5v5 vs special teams)
        2. Exact TOI from sequential appearances  
        3. Bayesian shrinkage for small samples
        4. Multi-granularity tracking (individual + unit level)
        """
        
        # Multiple tracking structures for different granularities
        matchup_scores = {}  # Individual player-to-player scores (main output)
        line_vs_line = {}    # Full unit matchups (for pattern detection)
        pair_vs_line = {}    # D-pair vs forward line patterns
        
        # STRENGTH CONDITIONING: Separate tracking by game situation
        toi_by_strength = defaultdict(lambda: defaultdict(float))  # [strength][player] = TOI
        matchup_toi_by_strength = defaultdict(lambda: defaultdict(float))  # [strength][(p1,p2)] = TOI
        
        # Time tracking (global)
        total_toi = {}       # Total time on ice per player
        matchup_toi = {}     # Time on ice for player pairs
        unit_toi = {}        # Time for full unit matchups
        
        # Track shift lengths from actual data if provided
        avg_shift_length = 45.0  # Default fallback
        if shift_data and 'avg_shift_lengths' in shift_data:
            all_shifts = list(shift_data['avg_shift_lengths'].values())
            if all_shifts:
                avg_shift_length = np.mean(all_shifts)
        
        for idx, row in deployment_data.iterrows():
            # Parse all players
            mtl_forwards = row['mtl_forwards'].split('|') if row['mtl_forwards'] else []
            mtl_defense = row['mtl_defense'].split('|') if row['mtl_defense'] else []
            opp_forwards = row['opp_forwards'].split('|') if row['opp_forwards'] else []
            opp_defense = row['opp_defense'].split('|') if row['opp_defense'] else []
            
            mtl_players = mtl_forwards + mtl_defense
            opp_players = opp_forwards + opp_defense
            
            # Get strength state for conditioning
            strength_state = row.get('strength_state', '5v5')
            
            # Calculate exact shift length using game time progression
            shift_length = self._calculate_shift_length(deployment_data, idx, row)
            
            # Track UNIT-LEVEL matchups (lines and pairs as cohesive units)
            if opp_defense and mtl_forwards:
                # D-pair vs Forward line
                pair_key = tuple(sorted(opp_defense))
                line_key = tuple(sorted(mtl_forwards))
                unit_key = (pair_key, line_key)
                if unit_key not in pair_vs_line:
                    pair_vs_line[unit_key] = 0
                pair_vs_line[unit_key] += shift_length
            
            if opp_forwards and mtl_forwards:
                # Forward line vs Forward line
                opp_line_key = tuple(sorted(opp_forwards))
                mtl_line_key = tuple(sorted(mtl_forwards))
                line_unit_key = (opp_line_key, mtl_line_key)
                if line_unit_key not in line_vs_line:
                    line_vs_line[line_unit_key] = 0
                line_vs_line[line_unit_key] += shift_length
            
            # Track INDIVIDUAL PLAYER interactions with STRENGTH CONDITIONING
            # This is crucial - EVERY player tracks against EVERY opponent by situation
            for opp_player in opp_players:
                # Track total ice time globally and by strength
                if opp_player not in total_toi:
                    total_toi[opp_player] = 0
                total_toi[opp_player] += shift_length
                toi_by_strength[strength_state][opp_player] += shift_length
                
                for mtl_player in mtl_players:
                    # Individual player-to-player tracking (global)
                    matchup_key = (opp_player, mtl_player)
                    if matchup_key not in matchup_toi:
                        matchup_toi[matchup_key] = 0
                    matchup_toi[matchup_key] += shift_length
                    
                    # STRENGTH-CONDITIONED tracking
                    matchup_toi_by_strength[strength_state][matchup_key] += shift_length
                    
                    # Track MTL player total time
                    if mtl_player not in total_toi:
                        total_toi[mtl_player] = 0
            
            # Update MTL player times (global and by strength)
            for mtl_player in mtl_players:
                total_toi[mtl_player] = total_toi.get(mtl_player, 0) + shift_length
                toi_by_strength[strength_state][mtl_player] += shift_length
        
        # STRENGTH-CONDITIONED MATCHUP SCORES with Bayesian shrinkage
        for strength_state, strength_matchups in matchup_toi_by_strength.items():
            strength_total_toi = sum(toi_by_strength[strength_state].values())
            
            if strength_total_toi < 300:  # Skip if insufficient data for this strength
                continue
            
            for (opp_player, mtl_player), toi_together in strength_matchups.items():
                # Only score if meaningful sample size
                if toi_together >= min_matchups * avg_shift_length:
                    
                    # Get strength-specific TOI totals
                    opp_strength_toi = toi_by_strength[strength_state].get(opp_player, 0)
                    mtl_strength_toi = toi_by_strength[strength_state].get(mtl_player, 0)
                    
                    # MATHEMATICAL PRECISION: Strength-conditioned expected TOI
                    # E[TOI_together | strength] = (TOI_opp^strength × TOI_mtl^strength) / TOI_total^strength
                    expected_toi_strength = (opp_strength_toi * mtl_strength_toi) / max(strength_total_toi, 1.0)
                    
                    if expected_toi_strength > 0:
                        # Log-ratio of observed vs expected for this strength
                        log_ratio = np.log((toi_together + 1.0) / (expected_toi_strength + 1.0))
                        
                        # BAYESIAN SHRINKAGE based on sample size
                        n_shifts = toi_together / avg_shift_length
                        shrinkage_k = 8.0  # Shrinkage factor for matchups
                        shrunk_ratio = (n_shifts / (n_shifts + shrinkage_k)) * log_ratio
                        
                        # Weight by strength importance (5v5 is most important)
                        strength_weights = {
                            '5v5': 1.0, 'evenStrength': 1.0,
                            '5v4': 0.7, 'powerPlay': 0.7,
                            '4v5': 0.8, 'penaltyKill': 0.8,
                            '4v4': 0.6, '3v3': 0.5
                        }
                        strength_weight = strength_weights.get(strength_state, 0.3)
                        
                        # Final matchup score: tanh-bounded, strength-weighted, shrunk
                        final_score = np.tanh(shrunk_ratio * 0.15) * strength_weight
                        
                        # Aggregate across all strengths for this matchup
                        global_matchup_key = (opp_player, mtl_player)
                        if global_matchup_key not in matchup_scores:
                            matchup_scores[global_matchup_key] = 0
                        matchup_scores[global_matchup_key] += final_score
        
        # Store all levels of matchup data
        self.matchup_matrix = matchup_scores  # Individual scores
        self.line_matchups = line_vs_line     # Line unit patterns  
        self.pair_vs_line_matchups = pair_vs_line  # D-pair vs forwards
        
        # Log statistics
        logger.info(f"Learned {len(matchup_scores)} individual player matchup scores")
        logger.info(f"Tracked {len(line_vs_line)} line-vs-line unit patterns")
        logger.info(f"Tracked {len(pair_vs_line)} D-pair vs forward-line patterns")
        
        # Find strongest individual matchups for logging
        if matchup_scores:
            top_matchups = sorted(matchup_scores.items(), 
                                key=lambda x: abs(x[1]), reverse=True)[:5]
            for (opp, mtl), score in top_matchups:
                logger.debug(f"  {opp} vs {mtl}: {score:.3f}")
        
        return matchup_scores
    
    def _calculate_shift_length(self, deployment_data: pd.DataFrame, idx: int, 
                               row: pd.Series) -> float:
        """Calculate actual shift length accounting for period boundaries"""
        
        if idx < len(deployment_data) - 1:
            next_row = deployment_data.iloc[idx + 1]
            current_period = row.get('period', 1)
            next_period = next_row.get('period', 1)
            
            if current_period == next_period:
                # Same period - calculate time difference
                current_time = row.get('period_time', 0)
                next_time = next_row.get('period_time', 0)
                
                if next_time > current_time:
                    shift_length = min(next_time - current_time, 120.0)  # Cap at 2 min
                else:
                    # Time went backwards (shouldn't happen in same period)
                    shift_length = 45.0
            else:
                # Period boundary - use remaining time in current period
                current_time = row.get('period_time', 0)
                period_end = 1200.0  # 20 minutes in seconds
                shift_length = min(period_end - current_time, 60.0)  # Cap at 1 min
        else:
            # Last event - estimate based on typical end-of-game shift
            shift_length = 30.0  # Shorter shifts at game end
        
        # Adjust for special teams (PP/PK shifts are longer)
        strength = row.get('strength_state', '5v5')
        if 'powerPlay' in strength or '5v4' in strength or '6v5' in strength:
            shift_length *= 1.35  # PP shifts significantly longer
        elif 'penaltyKill' in strength or '4v5' in strength or '5v6' in strength:
            shift_length *= 1.25  # PK shifts moderately longer
        elif '4v4' in strength:
            shift_length *= 1.2  # 4v4 slightly longer
        elif '3v3' in strength:
            shift_length *= 1.5  # 3v3 OT shifts much longer (more ice space)
        
        return shift_length
    
    def save_features(self, output_path: str) -> None:
        """Save all learned features including multi-level matchup data"""
        import pickle
        
        features = {
            'player_embeddings': self.player_embeddings,
            'chemistry_matrix': self.chemistry_matrix,
            'matchup_matrix': self.matchup_matrix,  # Individual player-to-player scores
            'line_matchups': getattr(self, 'line_matchups', {}),  # Line vs line patterns
            'pair_vs_line_matchups': getattr(self, 'pair_vs_line_matchups', {}),  # D-pair vs forwards
            'encoders': {
                'zone': self.zone_encoder,
                'strength': self.strength_encoder,
                'scaler': self.scaler
            }
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(features, f)
        
        # Log comprehensive feature statistics
        logger.info(f"Saved features to {output_path}")
        logger.info(f"  - {len(features.get('player_embeddings', {}))} player embeddings")
        logger.info(f"  - {len(features.get('chemistry_matrix', {}))} chemistry pairs")
        logger.info(f"  - {len(features.get('matchup_matrix', {}))} individual matchup scores")
        logger.info(f"  - {len(features.get('line_matchups', {}))} line-vs-line unit patterns")
        logger.info(f"  - {len(features.get('pair_vs_line_matchups', {}))} D-pair vs forward line patterns")
    
    def load_features(self, input_path: str) -> None:
        """Load learned features from disk"""
        import pickle
        
        with open(input_path, 'rb') as f:
            features = pickle.load(f)
        
        self.player_embeddings = features['player_embeddings']
        self.chemistry_matrix = features['chemistry_matrix']
        self.matchup_matrix = features['matchup_matrix']
        self.zone_encoder = features['encoders']['zone']
        self.strength_encoder = features['encoders']['strength']
        self.scaler = features['encoders']['scaler']
        
        logger.info(f"Loaded features from {input_path}")
    
    def _calculate_rolling_xg_differential(self, event_data: pd.DataFrame, 
                                          window_seconds: float = 120.0) -> np.ndarray:
        """
        Calculate rolling expected goals differential in last 120 seconds
        Strong predictive signal for coach behavior
        """
        
        n_events = len(event_data)
        rolling_xg = np.zeros(n_events)
        
        # Simulate xG data if not available
        for idx, row in event_data.iterrows():
            # Look back 120 seconds for rolling calculation
            lookback_time = row.get('game_time', 0) - window_seconds
            
            # Calculate xG differential in window (simulated)
            # In production, this would use actual xG from shots
            period = row.get('period', 1)
            score_diff = row.get('score_differential', 0)
            
            # Simulate xG based on game context
            if score_diff > 0:  # Leading
                xg_diff = 0.2 + np.random.normal(0, 0.3)
            elif score_diff < 0:  # Trailing
                xg_diff = -0.1 + np.random.normal(0, 0.4)
            else:  # Tied
                xg_diff = np.random.normal(0, 0.25)
            
            rolling_xg[idx] = np.clip(xg_diff, -2.0, 2.0)  # Bounded
        
        return rolling_xg
    
    def _calculate_rolling_pdo(self, event_data: pd.DataFrame) -> np.ndarray:
        """
        Calculate rolling PDO (shooting % + save %) over recent events
        Team confidence/momentum indicator
        """
        
        n_events = len(event_data)
        rolling_pdo = np.zeros(n_events)
        
        # Simulate PDO data
        for idx, row in event_data.iterrows():
            # Normal PDO is around 100 (100%)
            base_pdo = 100.0
            
            # Adjust based on context
            score_diff = row.get('score_differential', 0)
            period = row.get('period', 1)
            
            # Simulate momentum effects
            if score_diff > 1:  # Winning big
                pdo_adjustment = np.random.normal(2.0, 3.0)
            elif score_diff < -1:  # Losing big
                pdo_adjustment = np.random.normal(-2.0, 3.0)
            else:
                pdo_adjustment = np.random.normal(0, 2.5)
            
            rolling_pdo[idx] = np.clip(base_pdo + pdo_adjustment, 95.0, 105.0)
        
        # Normalize to [-1, 1] range for model
        rolling_pdo_normalized = (rolling_pdo - 100.0) / 5.0
        
        return rolling_pdo_normalized
