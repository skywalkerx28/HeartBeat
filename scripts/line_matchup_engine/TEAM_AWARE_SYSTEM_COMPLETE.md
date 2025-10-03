# HeartBeat Line Matchup Engine - Team-Aware System Implementation

## 🎯 **OVERVIEW**

The HeartBeat Line Matchup Engine has been enhanced with comprehensive **team-aware** and **last-change-aware** functionality, transforming it into a sophisticated bidirectional hockey analytics system that learns both MTL and opponent behaviors with tactical precision.

## 📊 **SYSTEM ARCHITECTURE**

### **Bidirectional Learning Framework**
The system now learns four distinct tactical scenarios:

1. **MTL has last change vs [Opponent]** → MTL chooses optimal matchups (offensive advantage)
2. **MTL doesn't have last change vs [Opponent]** → MTL reacts/adapts (defensive positioning)  
3. **[Opponent] has last change vs MTL** → Opponent targets MTL weaknesses
4. **[Opponent] doesn't have last change vs MTL** → Opponent reacts to MTL deployment

### **Core Components Enhanced**

#### **1. Neural Network Architecture** (`conditional_logit_model.py`)
- **Bidirectional Team Embeddings**: 32 NHL teams (including UTA, excluding ARI) with 16D embeddings
- **MTL + Opponent Interaction**: Concatenated 32D team features (16D MTL + 16D opponent)
- **Team-Aware Utility Computation**: Dynamic team-specific deployment utilities
- **Team-Aware Fatigue Modulation**: Opponent-specific fatigue scaling parameters

#### **2. Data Processing** (`data_processor.py`)
- **Comprehensive Rest Pattern Collection**:
  - `MTL_vs_TOR`: How MTL players rest when facing Toronto
  - `MTL_vs_BOS`: How MTL players rest when facing Boston
  - `TOR_players`: How Toronto players typically rest
  - `TOR_vs_MTL`: How Toronto players rest specifically against MTL
- **Bidirectional Pattern Storage**: Both MTL and opponent behaviors captured
- **Team-Aware Event Threading**: `opponent_team` field in all deployment events

#### **3. Candidate Generation** (`candidate_generator.py`)
- **Last-Change-Aware Rotation Priors**: 
  ```
  [team][opponent][last_change_status][prev_deployment][next_deployment] = probability
  ```
- **Tactical Pattern Learning**: Four distinct deployment scenarios
- **Team-Conditioned Candidate Selection**: Opponent-aware candidate generation
- **Pattern Serialization**: Save/load last-change-aware rotation patterns

#### **4. Training Engine** (`train_engine.py`)
- **Game-Level Data Splitting**: Prevents within-game leakage
- **Per-Opponent Evaluation Metrics**: Accuracy breakdown by opponent team
- **RMSE Evaluation**: Shift length and rest time prediction accuracy
- **NONE_OF_THE_ABOVE Validation**: Realistic validation when true deployment not in candidates
- **Team-Aware Batch Creation**: All batches include opponent team information

#### **5. Live Prediction** (`live_predictor.py`)
- **Team-Aware Real-Time Prediction**: Uses opponent team for tactical decisions
- **Last-Change-Aware Pattern Loading**: Applies tactical rotation patterns
- **Opponent-Specific Hazard Modeling**: Team-aware player availability prediction
- **Bidirectional Strategic Deployment**: Predicts both MTL and opponent deployment scenarios

#### **6. Player-vs-Player Matchup Intelligence** (`data_processor.py`, `candidate_generator.py`)
- **Granular Interaction Tracking**: Records every MTL player vs opponent player pairing
- **Matchup Frequency Analysis**: EWMA-weighted counts for recency bias
- **Last-Change-Aware Player Patterns**: Tactical matchup preferences by decision advantage
- **Situation-Specific Interactions**: Player matchups by game strength (5v5, PP, PK)
- **Performance Optimization**: Top-N pruning keeps most meaningful matchups per player
- **Matchup Prior Integration**: Player familiarity influences candidate probabilities

## 🎯 **PLAYER-VS-PLAYER MATCHUP SYSTEM**

### **Architecture Overview**
The player-vs-player matchup layer adds granular interaction intelligence to the team-aware system, tracking individual player familiarity and tactical preferences at the most detailed level.

### **Data Extraction & Storage**
```
Every deployment event captures:
MTL_Player_1 ↔ Opponent_Player_A  (frequency: 2.5, last_change: MTL, situation: 5v5)
MTL_Player_1 ↔ Opponent_Player_B  (frequency: 1.8, last_change: TOR, situation: 5v4)
MTL_Player_2 ↔ Opponent_Player_A  (frequency: 3.2, last_change: MTL, situation: 5v5)
```

#### **Three-Layer Pattern Storage**
1. **Global Matchup Counts**: `(mtl_player, opponent_player) → weighted_frequency`
2. **Last-Change-Aware Patterns**: `(mtl_player, opponent_player, last_change_team, team_making_change) → weighted_frequency`
3. **Situation-Specific Patterns**: `(mtl_player, opponent_player, game_situation) → weighted_frequency`

### **EWMA Recency Weighting**
- **Alpha = 0.2**: Recent matchups weighted more heavily than historical ones
- **Memory Management**: Automatic pruning of low-frequency pairs (< 3 occurrences)
- **Top-N Optimization**: Keep only 25 most frequent matchups per player for performance

### **Matchup Prior Computation**
```python
def compute_matchup_prior(candidate_players, opponent_players, opponent_team, last_change_team, situation):
    """
    Calculate player-vs-player familiarity score for a candidate deployment
    
    Returns: Scalar matchup prior (0.0 to 1.0+)
    - 0.0: No previous interactions
    - 0.5: Moderate familiarity 
    - 1.0+: High familiarity/tactical advantage
    """
```

### **Integration with Candidate Generation**
1. **Prior Computation**: Each candidate gets matchup_prior based on player interactions
2. **Log-Space Blending**: `candidate.probability_prior *= exp(matchup_prior * weight)`
3. **Model Feature**: Matchup prior becomes input feature to neural network
4. **Dynamic Weighting**: Configurable influence via `matchup_prior_weight` parameter

### **Performance Analytics**
- **Matchup Prior Metrics**: Track utilization rate, average prior by opponent/strength
- **Memory Optimization**: Automatic pruning prevents memory bloat during training
- **CSV Export**: Detailed analysis of matchup influence patterns

## 🔄 **DATA FLOW**

### **Training Phase**
1. **Data Processing**: Extract events with `opponent_team` and `last_change_team`
2. **Player-vs-Player Tracking**: Record all individual player interactions with EWMA weighting
3. **Pattern Learning**: Build team-aware rest patterns and rotation priors
4. **Matchup Prior Computation**: Calculate player familiarity scores for candidates
5. **Feature Engineering**: Fit on training data only (no leakage)
6. **Model Training**: Bidirectional team embeddings + player matchup priors
7. **Validation**: Per-opponent metrics with realistic candidate generation

### **Live Prediction Phase**
1. **Pattern Loading**: Load team-aware rotation priors, rest patterns, and player matchup data
2. **Opponent Detection**: Identify opponent team and current deployment from game state  
3. **Tactical Context**: Determine last change advantage
4. **Player Matchup Analysis**: Compute familiarity priors for candidate vs current opponent lineup
5. **Team-Aware Prediction**: Generate candidates using opponent-specific patterns + matchup priors
6. **Deployment Recommendation**: Optimal MTL deployment vs specific opponent with player-level intelligence

## 📈 **EVALUATION METRICS**

### **Per-Opponent Accuracy**
- **Top-1 Accuracy**: Exact deployment prediction by opponent
- **Top-3 Accuracy**: Deployment in top-3 candidates by opponent
- **Loss**: Cross-entropy loss by opponent team

### **RMSE Evaluation**
- **Shift Length RMSE**: Prediction accuracy by opponent and game strength
- **Rest Time RMSE**: Rest pattern prediction accuracy by opponent and game strength

### **Player-vs-Player Matchup Metrics**
- **Matchup Prior Utilization**: Percentage of candidates with non-zero matchup priors
- **Average Prior by Opponent**: Mean matchup familiarity score by opponent team
- **Matchup Coverage**: Percentage of player pairs with historical interaction data
- **Top-N Pruning Efficiency**: Memory reduction achieved through matchup optimization

### **Health Monitoring**
- **Validation Skip Rate**: Ensures realistic validation difficulty
- **Per-Opponent Sample Count**: Balanced evaluation across opponents
- **Health Warnings**: Automatic detection of training issues

## 🧪 **TESTING FRAMEWORK**

### **Comprehensive Test Suite**
- `test_team_embeddings.py`: Team embedding shapes and forward pass
- `test_team_aware_fatigue.py`: Team-specific fatigue modulation
- `test_team_rest_patterns.py`: Team-aware rest pattern collection
- `test_bidirectional_team_learning.py`: MTL + opponent interaction
- `test_last_change_rotations.py`: Tactical rotation pattern learning
- `test_per_opponent_metrics.py`: Per-opponent evaluation metrics
- `test_rmse_evaluation.py`: Shift/rest prediction accuracy
- `test_validation_none_counting.py`: NONE_OF_THE_ABOVE validation logic
- `test_player_vs_player_matchups.py`: Player-vs-player interaction tracking and analysis
- `test_live_predictor_matchup_integration.py`: End-to-end matchup prior integration
- `test_matchup_prior_logging.py`: Matchup metrics and analytics validation
- `test_matchup_pruning.py`: Performance optimization and memory management

## 🚀 **TRAINING COMMAND**

Launch comprehensive team-aware training:

```bash
cd scripts/line_matchup_engine
python3 train_engine.py \
  --data_path /path/to/mtl_play_by_play \
  --split_strategy game_level \
  --val_fraction 0.15 \
  --holdout_fraction 0.10 \
  --enable_team_embeddings \
  --team_embedding_dim 16 \
  --l1_reg 1e-4 \
  --l2_reg 1e-5 \
  --epochs 50 \
  --random_seed 42
```

## 📊 **EXPECTED TRAINING METRICS**

### **Healthy First-Epoch Validation**
- **ValLoss**: 2.0-2.5 (realistic for multi-thousand-class problem)
- **ValAcc**: 5-15% (challenging but learnable)
- **ValTop3**: 20-40% (reasonable top-3 performance)
- **Per-Opponent Variation**: Different accuracy by opponent team

### **RMSE Targets**
- **Shift Length RMSE**: 10-20 seconds (reasonable prediction accuracy)
- **Rest Time RMSE**: 30-60 seconds (accounts for coaching variability)

## 🎯 **LIVE DEPLOYMENT**

### **Real-Time Usage**
```python
from live_predictor import LiveLinePredictor

predictor = LiveLinePredictor(
    model_path="models/line_matchup/pytorch_model.pth",
    patterns_path="models/line_matchup/predictive_patterns.pkl"
)

# Get team-aware prediction
deployment = predictor.predict_optimal_deployment(
    game_state=current_game_state,
    opponent_team="TOR",  # Team-aware prediction
    last_change_team="MTL"  # Tactical advantage context
)
```

## 🏆 **SYSTEM CAPABILITIES**

The enhanced HeartBeat Line Matchup Engine now provides:

1. **Tactical Intelligence**: Learns last change advantage patterns
2. **Bidirectional Learning**: Both MTL and opponent behavior modeling
3. **Team-Specific Adaptation**: Different strategies vs different opponents
4. **Player-vs-Player Intelligence**: Granular matchup familiarity and interaction patterns
5. **Performance Optimization**: Memory-efficient top-N matchup pruning for scalability
6. **Professional Rigor**: Comprehensive validation and health monitoring
7. **Real-Time Deployment**: Live game prediction with tactical context and player-level intelligence

### **Advanced Matchup Intelligence**
- **Individual Player Familiarity**: Tracks every MTL vs opponent player interaction
- **Tactical Matchup Preferences**: Last-change-aware player deployment patterns
- **Situation-Specific Intelligence**: Player interactions by game strength and context
- **Dynamic Recency Weighting**: Recent interactions weighted more heavily than historical ones
- **Scalable Performance**: Automatic pruning maintains focus on most meaningful matchups

**The system is now ready for professional NHL coaching staff deployment with comprehensive team-aware and player-level tactical intelligence that operates at the granular level of individual player interactions.**