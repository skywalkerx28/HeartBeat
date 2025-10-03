"""
HeartBeat Evaluation Metrics Helper
Centralized handling of per-opponent and RMSE evaluation metrics
Professional-grade implementation for NHL analytics
"""

import logging
from typing import Dict, Any, DefaultDict
from collections import defaultdict
from pathlib import Path
import math

logger = logging.getLogger(__name__)


class MatchupPriorMetrics:
    """
    Tracks probability prior (full combined prior from candidate generator)
    Previously tracked only matchup_prior (player-vs-player component)
    Now tracks probability_prior (softmax-normalized combined prior including all factors)
    Analyzes impact across opponents and game strengths
    """
    
    def __init__(self):
        # Track probability prior statistics by opponent and strength
        # Note: Internal storage still uses 'matchup_stats' name for backward compatibility
        self.matchup_stats = defaultdict(lambda: defaultdict(lambda: {
            'count': 0, 'total_prior': 0.0, 'min_prior': float('inf'), 
            'max_prior': float('-inf'), 'non_zero_count': 0
        }))
        
        # Track candidate-level prior influence
        self.candidate_matchup_influence = []
    
    def update_matchup_prior(self, opponent_team: str, strength: str, matchup_prior: float, 
                           candidate_id: str = None):
        """
        Update probability prior statistics
        Note: 'matchup_prior' parameter name kept for compatibility, 
        but now receives full probability_prior (combined softmax-normalized prior)
        """
        stats = self.matchup_stats[opponent_team][strength]
        stats['count'] += 1
        stats['total_prior'] += matchup_prior
        stats['min_prior'] = min(stats['min_prior'], matchup_prior)
        stats['max_prior'] = max(stats['max_prior'], matchup_prior)
        
        if abs(matchup_prior) > 0.001:  # Consider non-zero if > 0.001
            stats['non_zero_count'] += 1
        
        # Track individual candidate influence
        if candidate_id:
            self.candidate_matchup_influence.append({
                'opponent': opponent_team,
                'strength': strength,
                'prior': matchup_prior,
                'candidate': candidate_id
            })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive matchup prior analysis"""
        summary = {
            'by_opponent': {},
            'by_strength': defaultdict(lambda: {
                'count': 0, 'avg_prior': 0.0, 'utilization_rate': 0.0
            }),
            'overall': {
                'total_evaluations': 0,
                'non_zero_rate': 0.0,
                'avg_prior_when_used': 0.0
            }
        }
        
        total_evaluations = 0
        total_non_zero = 0
        total_prior_sum = 0.0
        
        for opponent, strength_stats in self.matchup_stats.items():
            opponent_summary = {
                'total_count': 0,
                'avg_prior': 0.0,
                'utilization_rate': 0.0,
                'by_strength': {}
            }
            
            opp_total = 0
            opp_prior_sum = 0.0
            opp_non_zero = 0
            
            for strength, stats in strength_stats.items():
                if stats['count'] > 0:
                    avg_prior = stats['total_prior'] / stats['count']
                    utilization_rate = stats['non_zero_count'] / stats['count']
                    
                    opponent_summary['by_strength'][strength] = {
                        'count': stats['count'],
                        'avg_prior': avg_prior,
                        'min_prior': stats['min_prior'],
                        'max_prior': stats['max_prior'],
                        'utilization_rate': utilization_rate
                    }
                    
                    # Aggregate by strength across all opponents
                    summary['by_strength'][strength]['count'] += stats['count']
                    summary['by_strength'][strength]['avg_prior'] += stats['total_prior']
                    
                    # Ensure non_zero_count is tracked for strength aggregation
                    if 'non_zero_count' not in summary['by_strength'][strength]:
                        summary['by_strength'][strength]['non_zero_count'] = 0
                    summary['by_strength'][strength]['non_zero_count'] += stats['non_zero_count']
                    
                    # Opponent totals
                    opp_total += stats['count']
                    opp_prior_sum += stats['total_prior']
                    opp_non_zero += stats['non_zero_count']
                    
                    # Overall totals
                    total_evaluations += stats['count']
                    total_non_zero += stats['non_zero_count']
                    total_prior_sum += stats['total_prior']
            
            if opp_total > 0:
                opponent_summary['total_count'] = opp_total
                opponent_summary['avg_prior'] = opp_prior_sum / opp_total
                opponent_summary['utilization_rate'] = opp_non_zero / opp_total
            
            summary['by_opponent'][opponent] = opponent_summary
        
        # Finalize strength aggregates
        for strength in summary['by_strength']:
            if summary['by_strength'][strength]['count'] > 0:
                summary['by_strength'][strength]['avg_prior'] /= summary['by_strength'][strength]['count']
                non_zero_count = summary['by_strength'][strength].get('non_zero_count', 0)
                summary['by_strength'][strength]['utilization_rate'] = non_zero_count / summary['by_strength'][strength]['count']
        
        # Overall summary
        if total_evaluations > 0:
            summary['overall'] = {
                'total_evaluations': total_evaluations,
                'non_zero_rate': total_non_zero / total_evaluations,
                'avg_prior_overall': total_prior_sum / total_evaluations,
                'avg_prior_when_used': (total_prior_sum / total_non_zero) if total_non_zero > 0 else 0.0
            }
        
        return summary
    
    def log_detailed_analysis(self, phase: str = "validation"):
        """Log comprehensive matchup prior analysis"""
        summary = self.get_summary()
        
        logger.info(f"MATCHUP PRIOR ANALYSIS - {phase.upper()}")
        logger.info("=" * 60)
        
        # Overall statistics
        overall = summary.get('overall', {})
        total_evals = overall.get('total_evaluations', 0)
        non_zero_rate = overall.get('non_zero_rate', 0.0)
        avg_prior_overall = overall.get('avg_prior_overall', 0.0)
        avg_prior_when_used = overall.get('avg_prior_when_used', 0.0)
        logger.info(f"Total evaluations: {total_evals}")
        logger.info(f"Non-zero prior rate: {non_zero_rate:.1%}")
        logger.info(f"Average prior (overall): {avg_prior_overall:.4f}")
        logger.info(f"Average prior (when used): {avg_prior_when_used:.4f}")
        logger.info("")
        
        # By opponent analysis
        logger.info("BY OPPONENT:")
        for opponent, stats in sorted(summary['by_opponent'].items()):
            logger.info(f"  {opponent}: {stats['total_count']} evals, "
                       f"avg_prior={stats['avg_prior']:.4f}, "
                       f"utilization={stats['utilization_rate']:.1%}")
            
            # Show strength breakdown for this opponent
            for strength, strength_stats in stats['by_strength'].items():
                logger.info(f"    {strength}: {strength_stats['count']} evals, "
                           f"avg={strength_stats['avg_prior']:.4f}, "
                           f"range=[{strength_stats['min_prior']:.4f}, {strength_stats['max_prior']:.4f}]")
        
        logger.info("")
        
        # By strength analysis
        logger.info("BY STRENGTH:")
        for strength, stats in sorted(summary['by_strength'].items()):
            if stats['count'] > 0:
                logger.info(f"  {strength}: {stats['count']} evals, "
                           f"avg_prior={stats['avg_prior']:.4f}")
    
    def save_detailed_csv(self, output_path: Path, phase: str = "validation"):
        """Save detailed matchup prior data to CSV"""
        import pandas as pd
        
        if not self.candidate_matchup_influence:
            logger.warning("No matchup influence data to save")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(self.candidate_matchup_influence)
        
        # Add computed columns
        df['abs_prior'] = df['prior'].abs()
        df['has_prior'] = df['abs_prior'] > 0.001
        df['phase'] = phase
        
        # Save to CSV
        csv_path = output_path / f"matchup_prior_analysis_{phase}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved matchup prior analysis to {csv_path}")
        
        # Save summary statistics
        summary = self.get_summary()
        overall = summary.get('overall', {})
        summary_df = pd.DataFrame([
            {'metric': 'total_evaluations', 'value': overall.get('total_evaluations', 0)},
            {'metric': 'non_zero_rate', 'value': overall.get('non_zero_rate', 0.0)},
            {'metric': 'avg_prior_overall', 'value': overall.get('avg_prior_overall', 0.0)},
            {'metric': 'avg_prior_when_used', 'value': overall.get('avg_prior_when_used', 0.0)}
        ])
        
        summary_path = output_path / f"matchup_prior_summary_{phase}.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Saved matchup prior summary to {summary_path}")


class PerOpponentMetrics:
    """
    Tracks and manages per-opponent validation metrics
    Handles accuracy, top-3 accuracy, and loss by opponent team
    """
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'correct': 0, 'top3_correct': 0, 'total': 0, 'loss': 0.0
        })
    
    def update_correct(self, opponent_team: str, is_correct: bool, is_top3_correct: bool, loss: float):
        """Update metrics for a correct prediction"""
        if is_correct:
            self.metrics[opponent_team]['correct'] += 1
        if is_top3_correct:
            self.metrics[opponent_team]['top3_correct'] += 1
        self.metrics[opponent_team]['total'] += 1
        self.metrics[opponent_team]['loss'] += loss
    
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get computed accuracy and loss metrics by team"""
        summary = {}
        for team, metrics in self.metrics.items():
            if metrics['total'] > 0:
                summary[team] = {
                    'accuracy': metrics['correct'] / metrics['total'],
                    'top3_accuracy': metrics['top3_correct'] / metrics['total'],
                    'avg_loss': metrics['loss'] / metrics['total'],
                    'samples': metrics['total']
                }
        return summary
    
    def log_summary(self, phase: str = "validation"):
        """Log detailed per-opponent metrics"""
        logger.info(f"Per-opponent {phase} metrics:")
        summary = self.get_summary()
        for team, metrics in sorted(summary.items()):
            logger.info(f"  {team}: {metrics['samples']:3d} samples, "
                       f"acc={metrics['accuracy']:.3f}, "
                       f"top3={metrics['top3_accuracy']:.3f}, "
                       f"loss={metrics['avg_loss']:.3f}")
    
    def write_csv(self, csv_path: Path, epoch: int):
        """Write metrics to CSV file"""
        summary = self.get_summary()
        with open(csv_path, 'a') as f:
            for team, metrics in sorted(summary.items()):
                f.write(f"{epoch},{team},{metrics['samples']},"
                       f"{metrics['accuracy']:.4f},{metrics['top3_accuracy']:.4f},"
                       f"{metrics['avg_loss']:.4f}\n")


class ShiftRestRMSE:
    """
    Tracks and computes RMSE for shift length and rest time predictions
    Organized by opponent team and strength situation
    """
    
    def __init__(self):
        self.rmse_data = defaultdict(lambda: defaultdict(lambda: {
            'shift_errors': [], 'rest_errors': [], 'count': 0
        }))
    
    def add_errors(self, opponent_team: str, strength: str, 
                   shift_errors: Dict[str, float], rest_errors: Dict[str, float]):
        """Add shift and rest prediction errors for a batch"""
        for player, error in shift_errors.items():
            self.rmse_data[opponent_team][strength]['shift_errors'].append(error ** 2)
        
        for player, error in rest_errors.items():
            self.rmse_data[opponent_team][strength]['rest_errors'].append(error ** 2)
        
        if shift_errors or rest_errors:  # Only increment if we had predictions
            self.rmse_data[opponent_team][strength]['count'] += 1
    
    def compute_rmse(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Compute RMSE values by team and strength"""
        rmse_summary = {}
        for team, strength_data in self.rmse_data.items():
            rmse_summary[team] = {}
            for strength, metrics in strength_data.items():
                if metrics['count'] > 0:
                    shift_rmse = 0.0
                    rest_rmse = 0.0
                    
                    if metrics['shift_errors']:
                        shift_rmse = math.sqrt(sum(metrics['shift_errors']) / len(metrics['shift_errors']))
                    
                    if metrics['rest_errors']:
                        rest_rmse = math.sqrt(sum(metrics['rest_errors']) / len(metrics['rest_errors']))
                    
                    rmse_summary[team][strength] = {
                        'shift_rmse': shift_rmse,
                        'rest_rmse': rest_rmse,
                        'count': metrics['count'],
                        'shift_predictions': len(metrics['shift_errors']),
                        'rest_predictions': len(metrics['rest_errors'])
                    }
        return rmse_summary
    
    def log_summary(self, phase: str = "validation"):
        """Log RMSE evaluation results"""
        logger.info(f"RMSE Evaluation by Opponent and Strength ({phase}):")
        rmse_summary = self.compute_rmse()
        
        for team, strength_data in rmse_summary.items():
            for strength, metrics in strength_data.items():
                logger.info(f"  {team} {strength}: {metrics['count']} batches, "
                           f"shift_RMSE={metrics['shift_rmse']:.2f}s, "
                           f"rest_RMSE={metrics['rest_rmse']:.2f}s "
                           f"({metrics['shift_predictions']} shift, "
                           f"{metrics['rest_predictions']} rest predictions)")


class EvaluationMetricsHelper:
    """
    Centralized helper for managing all evaluation metrics
    Combines per-opponent and RMSE tracking with unified logging
    """
    
    def __init__(self, output_path: Path):
        self.per_opponent = PerOpponentMetrics()
        self.rmse = ShiftRestRMSE()
        self.matchup_metrics = MatchupPriorMetrics()
        self.output_path = output_path
        
        # Initialize CSV file with headers
        self.per_opponent_csv = output_path / 'per_opponent_metrics.csv'
        self._init_csv_headers()
    
    def _init_csv_headers(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not self.per_opponent_csv.exists():
            headers = ['epoch', 'opponent_team', 'samples', 'accuracy', 'top3_accuracy', 'avg_loss']
            with open(self.per_opponent_csv, 'w') as f:
                f.write(','.join(headers) + '\n')
    
    def update_prediction_metrics(self, opponent_team: str, is_correct: bool, 
                                is_top3_correct: bool, loss: float):
        """Update per-opponent prediction metrics"""
        self.per_opponent.update_correct(opponent_team, is_correct, is_top3_correct, loss)
    
    def update_rmse_metrics(self, opponent_team: str, strength: str,
                           shift_errors: Dict[str, float], rest_errors: Dict[str, float]):
        """Update RMSE prediction metrics"""
        self.rmse.add_errors(opponent_team, strength, shift_errors, rest_errors)
    
    def update_matchup_prior(self, opponent_team: str, strength: str, matchup_prior: float, 
                           candidate_id: str = None):
        """Update matchup prior tracking"""
        self.matchup_metrics.update_matchup_prior(opponent_team, strength, matchup_prior, candidate_id)
    
    def log_and_save_metrics(self, epoch: int, phase: str = "validation"):
        """Log all metrics and save to CSV"""
        self.per_opponent.log_summary(phase)
        self.rmse.log_summary(phase)
        self.matchup_metrics.log_detailed_analysis(phase)
        self.per_opponent.write_csv(self.per_opponent_csv, epoch)
        self.matchup_metrics.save_detailed_csv(self.output_path, phase)
    
    def reset(self):
        """Reset all metrics for next epoch"""
        self.per_opponent = PerOpponentMetrics()
        self.rmse = ShiftRestRMSE()
        self.matchup_metrics = MatchupPriorMetrics()
