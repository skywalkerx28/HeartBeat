"""
Market Metrics Computation for NHL Contract Analytics.

Implements contract efficiency index, surplus value calculations,
and market comparable matching algorithms.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContractMetricsCalculator:
    """
    Calculate contract efficiency and market value metrics.
    
    Similar to Performance Form Index (PFI) but for contract value analysis.
    """
    
    # Position-specific weights for efficiency calculation
    FORWARD_WEIGHTS = {
        'points_per_60': 0.40,
        'xg_per_60': 0.25,
        'defensive_metrics': 0.15,
        'age_curve': 0.10,
        'term_penalty': 0.10
    }
    
    DEFENSE_WEIGHTS = {
        'points_per_60': 0.20,
        'xg_per_60': 0.20,
        'defensive_metrics': 0.35,
        'age_curve': 0.15,
        'term_penalty': 0.10
    }
    
    GOALIE_WEIGHTS = {
        'save_percentage': 0.40,
        'goals_saved_above_expected': 0.30,
        'workload': 0.15,
        'age_curve': 0.10,
        'term_penalty': 0.05
    }
    
    def compute_contract_efficiency_index(
        self,
        player_stats: Dict[str, Any],
        contract_details: Dict[str, Any],
        position: str
    ) -> Dict[str, Any]:
        """
        Compute contract efficiency similar to PFI but for value.
        
        Components (position-weighted):
        - Points/60 vs AAV (forwards: 0.40, defense: 0.20)
        - xG/60 vs AAV (forwards: 0.25, defense: 0.20)
        - Defensive metrics vs AAV (0.15 forwards, 0.35 defense)
        - Age curve adjustment (0.10)
        - Term remaining penalty (0.10)
        
        Args:
            player_stats: Player performance statistics
            contract_details: Contract information (cap_hit, term, etc.)
            position: Player position (F, D, G)
            
        Returns:
            Contract efficiency metrics
        """
        position_category = self._categorize_position(position)
        weights = self._get_position_weights(position_category)
        
        # Get league averages for position
        league_avg_cap_hit = self._get_league_avg_cap_hit(position_category)
        
        # Extract metrics
        cap_hit = contract_details.get('cap_hit', 0)
        years_remaining = contract_details.get('years_remaining', 0)
        age = contract_details.get('age', 25)
        
        # Calculate components
        components = {}
        
        if position_category in ['F', 'D']:
            # Offensive production value
            points_60 = player_stats.get('points_per_60', 0)
            components['points_value'] = self._calculate_production_value(
                points_60, cap_hit, league_avg_cap_hit, weights['points_per_60']
            )
            
            # Expected goals value
            xg_60 = player_stats.get('xg_per_60', 0)
            components['xg_value'] = self._calculate_production_value(
                xg_60, cap_hit, league_avg_cap_hit, weights['xg_per_60']
            )
            
            # Defensive value
            defensive_score = player_stats.get('defensive_rating', 50)  # 0-100 scale
            components['defensive_value'] = self._calculate_defensive_value(
                defensive_score, cap_hit, league_avg_cap_hit, weights['defensive_metrics']
            )
            
        elif position_category == 'G':
            # Goalie-specific metrics
            sv_pct = player_stats.get('save_percentage', 0.900)
            gsax = player_stats.get('goals_saved_above_expected', 0)
            
            components['save_pct_value'] = self._calculate_goalie_value(
                sv_pct, cap_hit, league_avg_cap_hit, weights['save_percentage']
            )
            components['gsax_value'] = self._calculate_production_value(
                gsax, cap_hit, league_avg_cap_hit, weights['goals_saved_above_expected']
            )
            
        # Age curve adjustment
        components['age_adjustment'] = self._calculate_age_curve(
            age, weights['age_curve']
        )
        
        # Term penalty (longer term = more risk)
        components['term_penalty'] = self._calculate_term_penalty(
            years_remaining, weights['term_penalty']
        )
        
        # Total efficiency index (0-200 scale, 100 = league average value)
        efficiency_index = sum(components.values())
        
        # Calculate market value and surplus
        market_value = self._estimate_market_value(
            player_stats, position_category, league_avg_cap_hit
        )
        surplus_value = market_value - cap_hit
        
        return {
            'contract_efficiency': efficiency_index,
            'market_value': market_value,
            'surplus_value': surplus_value,
            'components': components,
            'status': self._classify_contract_status(efficiency_index),
            'percentile': self._estimate_percentile(efficiency_index)
        }
        
    def calculate_surplus_value(
        self,
        market_value: float,
        cap_hit: float,
        years_remaining: int
    ) -> Dict[str, Any]:
        """
        Calculate contract surplus/deficit value.
        
        Args:
            market_value: Estimated fair market value
            cap_hit: Actual cap hit
            years_remaining: Years left on contract
            
        Returns:
            Surplus value analysis
        """
        annual_surplus = market_value - cap_hit
        total_surplus = annual_surplus * years_remaining
        
        surplus_percentage = (annual_surplus / cap_hit * 100) if cap_hit > 0 else 0
        
        return {
            'annual_surplus': annual_surplus,
            'total_surplus': total_surplus,
            'surplus_percentage': surplus_percentage,
            'classification': 'bargain' if annual_surplus > 1000000 else
                            'fair' if abs(annual_surplus) <= 1000000 else
                            'overpaid',
            'years_remaining': years_remaining
        }
        
    def compute_market_comparables_score(
        self,
        target_player: Dict[str, Any],
        comparable_player: Dict[str, Any]
    ) -> float:
        """
        Similarity score 0-100 for comparable contracts.
        
        Factors:
        - Age proximity (25%)
        - Production similarity (35%)
        - Position match (15%)
        - Contract era (10%)
        - Team/market context (15%)
        
        Args:
            target_player: Player to find comparables for
            comparable_player: Potential comparable
            
        Returns:
            Similarity score (0-100)
        """
        score = 0.0
        
        # Age proximity (25 points max)
        age_diff = abs(target_player.get('age', 25) - comparable_player.get('age', 25))
        age_score = max(0, 25 - (age_diff * 3))  # -3 points per year difference
        score += age_score
        
        # Production similarity (35 points max)
        target_production = target_player.get('production_last_season', 0)
        comp_production = comparable_player.get('production_last_season', 0)
        
        if target_production > 0 and comp_production > 0:
            production_ratio = min(target_production, comp_production) / max(target_production, comp_production)
            production_score = production_ratio * 35
            score += production_score
        else:
            score += 17.5  # Neutral score if no production data
            
        # Position match (15 points max)
        if target_player.get('position') == comparable_player.get('position'):
            score += 15
        else:
            # Partial credit for same position type (F vs F, D vs D)
            target_pos_type = self._categorize_position(target_player.get('position', ''))
            comp_pos_type = self._categorize_position(comparable_player.get('position', ''))
            if target_pos_type == comp_pos_type:
                score += 7.5
                
        # Contract era (10 points max)
        target_year = target_player.get('signing_year', 2025)
        comp_year = comparable_player.get('signing_year', 2025)
        year_diff = abs(target_year - comp_year)
        era_score = max(0, 10 - year_diff)  # -1 point per year
        score += era_score
        
        # Team/market context (15 points max)
        # Cap hit percentage similarity
        target_cap_pct = target_player.get('cap_hit_percentage', 0)
        comp_cap_pct = comparable_player.get('cap_hit_percentage', 0)
        
        if target_cap_pct > 0 and comp_cap_pct > 0:
            cap_pct_ratio = min(target_cap_pct, comp_cap_pct) / max(target_cap_pct, comp_cap_pct)
            cap_score = cap_pct_ratio * 15
            score += cap_score
        else:
            score += 7.5  # Neutral score
            
        return round(score, 2)
        
    def _categorize_position(self, position: str) -> str:
        """Categorize position into F, D, or G."""
        if position in ['C', 'LW', 'RW', 'W', 'F']:
            return 'F'
        elif position in ['D', 'LD', 'RD']:
            return 'D'
        elif position in ['G']:
            return 'G'
        return 'F'  # Default
        
    def _get_position_weights(self, position: str) -> Dict[str, float]:
        """Get position-specific weights."""
        if position == 'F':
            return self.FORWARD_WEIGHTS
        elif position == 'D':
            return self.DEFENSE_WEIGHTS
        elif position == 'G':
            return self.GOALIE_WEIGHTS
        return self.FORWARD_WEIGHTS
        
    def _get_league_avg_cap_hit(self, position: str) -> float:
        """Get league average cap hit by position (hardcoded for now)."""
        # TODO: Calculate dynamically from data
        averages = {
            'F': 2500000,
            'D': 2800000,
            'G': 2200000
        }
        return averages.get(position, 2500000)
        
    def _calculate_production_value(
        self,
        production: float,
        cap_hit: float,
        league_avg: float,
        weight: float
    ) -> float:
        """Calculate production value component."""
        if cap_hit == 0:
            return 0
            
        # Production per dollar
        value_per_dollar = production / cap_hit if cap_hit > 0 else 0
        league_avg_value = production / league_avg if league_avg > 0 else 0
        
        # Normalize to 0-100 scale where 100 = league average
        normalized = (value_per_dollar / league_avg_value * 100) if league_avg_value > 0 else 50
        
        return min(normalized, 200) * weight  # Cap at 200% efficiency
        
    def _calculate_defensive_value(
        self,
        defensive_score: float,
        cap_hit: float,
        league_avg: float,
        weight: float
    ) -> float:
        """Calculate defensive value component."""
        # Defensive score already on 0-100 scale
        normalized = defensive_score
        return normalized * weight
        
    def _calculate_goalie_value(
        self,
        save_pct: float,
        cap_hit: float,
        league_avg: float,
        weight: float
    ) -> float:
        """Calculate goalie-specific value."""
        # Convert save percentage to relative scale
        # League average ~0.905, elite ~0.920+
        league_sv_pct = 0.905
        normalized = ((save_pct - league_sv_pct) / 0.015 + 1) * 100
        
        return max(0, min(normalized, 200)) * weight
        
    def _calculate_age_curve(self, age: int, weight: float) -> float:
        """
        Calculate age curve adjustment.
        
        Peak ages: 24-28 = 100%, decline after 30
        """
        if 24 <= age <= 28:
            age_factor = 100
        elif age < 24:
            # Young players improving
            age_factor = 85 + (age - 20) * 3.75
        else:
            # Decline after 28
            age_factor = max(50, 100 - (age - 28) * 5)
            
        return age_factor * weight
        
    def _calculate_term_penalty(self, years_remaining: int, weight: float) -> float:
        """
        Calculate term penalty (longer term = more risk).
        
        Sweet spot: 3-5 years = 100%, penalty for very long/short
        """
        if 3 <= years_remaining <= 5:
            term_factor = 100
        elif years_remaining < 3:
            # Short term = less value accumulation
            term_factor = 70 + years_remaining * 10
        else:
            # Long term = more risk
            term_factor = max(60, 100 - (years_remaining - 5) * 5)
            
        return term_factor * weight
        
    def _estimate_market_value(
        self,
        player_stats: Dict[str, Any],
        position: str,
        league_avg: float
    ) -> float:
        """
        Estimate fair market value based on production.
        
        Simplified model - should be enhanced with regression.
        """
        points_60 = player_stats.get('points_per_60', 0)
        
        # Rough market value formula
        if position == 'F':
            base_value = points_60 * 500000  # $500k per point/60
        elif position == 'D':
            base_value = points_60 * 750000  # Defense premium
        else:
            sv_pct = player_stats.get('save_percentage', 0.900)
            base_value = (sv_pct - 0.890) * 50000000  # Goalie valuation
            
        return max(750000, min(base_value, 15000000))  # Floor and ceiling
        
    def _classify_contract_status(self, efficiency_index: float) -> str:
        """Classify contract performance status."""
        if efficiency_index >= 120:
            return 'overperforming'
        elif efficiency_index >= 80:
            return 'fair'
        else:
            return 'underperforming'
            
    def _estimate_percentile(self, efficiency_index: float) -> float:
        """Estimate percentile based on efficiency index."""
        # Rough percentile estimation
        # 100 = 50th percentile, 150 = 90th, 50 = 10th
        if efficiency_index >= 100:
            percentile = 50 + (efficiency_index - 100) * 0.8
        else:
            percentile = efficiency_index * 0.5
            
        return max(0, min(percentile, 100))


# Helper functions for external use

def calculate_contract_efficiency(
    player_stats: Dict[str, Any],
    contract_details: Dict[str, Any],
    position: str
) -> Dict[str, Any]:
    """
    Convenience function to calculate contract efficiency.
    """
    calculator = ContractMetricsCalculator()
    return calculator.compute_contract_efficiency_index(
        player_stats, contract_details, position
    )


def find_comparables(
    target_player: Dict[str, Any],
    all_players: List[Dict[str, Any]],
    min_similarity: float = 70.0,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Find comparable contracts for a target player.
    
    Args:
        target_player: Player to find comparables for
        all_players: Pool of potential comparables
        min_similarity: Minimum similarity score (0-100)
        max_results: Maximum number of comparables to return
        
    Returns:
        List of comparable players with similarity scores
    """
    calculator = ContractMetricsCalculator()
    
    scored_comparables = []
    for player in all_players:
        # Don't compare to self
        if player.get('nhl_player_id') == target_player.get('nhl_player_id'):
            continue
            
        score = calculator.compute_market_comparables_score(target_player, player)
        
        if score >= min_similarity:
            comparable = player.copy()
            comparable['similarity_score'] = score
            scored_comparables.append(comparable)
            
    # Sort by similarity score
    scored_comparables.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return scored_comparables[:max_results]

