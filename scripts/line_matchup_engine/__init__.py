"""
HeartBeat Line Matchup Engine
Professional-grade NHL line deployment prediction system for Montreal Canadiens
"""

from .data_processor import PlayByPlayProcessor, DeploymentEvent
from .feature_engineering import FeatureEngineer, FeatureSet
from .conditional_logit_model import ConditionalLogitModel, ModelParameters
from .candidate_generator import CandidateGenerator, Candidate
from .live_predictor import LiveLinePredictor, GameState, PredictionResult
from .train_engine import LineMatchupTrainer
from .player_mapper import PlayerMapper, get_mapper

__version__ = "1.0.0"
__author__ = "HeartBeat Analytics"

__all__ = [
    'PlayByPlayProcessor',
    'DeploymentEvent',
    'FeatureEngineer',
    'FeatureSet',
    'ConditionalLogitModel',
    'ModelParameters',
    'CandidateGenerator',
    'Candidate',
    'LiveLinePredictor',
    'GameState',
    'PredictionResult',
    'LineMatchupTrainer',
    'PlayerMapper',
    'get_mapper'
]
