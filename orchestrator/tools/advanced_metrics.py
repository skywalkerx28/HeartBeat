"""
Advanced Metrics Computation Layer
HeartBeat Engine - Montreal Canadiens Analytics

Production-grade metrics computation:
- Player Form Index (PFI): Recency-weighted player performance composite
- Team Momentum/Trend: Rolling xGF%, special teams, pace indicators
- Rival Threat Index (RTI): Composite threat score for Atlantic division rivals
- Fan Sentiment Proxy (FSP): Statistical proxy for fan sentiment based on team performance

All functions are pure Pandas with typed outputs for API serialization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def compute_player_form_index(
    df_player_games: pd.DataFrame,
    window: int = 10,
    current_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Compute Player Form Index (PFI) for Montreal Canadiens players.
    
    PFI is a recency-weighted z-score composite measuring recent performance.
    
    Formula Components (weights):
    - EV Primary Points/60: 0.35
    - Individual xG/60: 0.25  
    - Shot Assists/60: 0.15
    - Controlled Entries Leading to Shots/60: 0.15
    - On-Ice xGF%: 0.10
    
    Args:
        df_player_games: DataFrame with player game-by-game stats
        window: Number of recent games to consider (default: 10)
        current_date: Optional date filter for "as of" calculations
        
    Returns:
        List of player PFI dictionaries with scores, trends, and breakdowns
    """
    try:
        if df_player_games.empty:
            return []
        
        # Filter to recent games (last window games)
        df = df_player_games.copy()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values('Date', ascending=False)
        elif 'Game Date' in df.columns:
            df['Game Date'] = pd.to_datetime(df['Game Date'], errors='coerce')
            df = df.sort_values('Game Date', ascending=False)
        
        # Group by player and take last N games
        if 'Player Name' not in df.columns and 'Player' in df.columns:
            df['Player Name'] = df['Player']
        
        player_recent = []
        for player, group in df.groupby('Player Name'):
            recent_games = group.head(window)
            if len(recent_games) >= 3:  # Minimum 3 games for PFI
                player_recent.append(recent_games)
        
        if not player_recent:
            return []
        
        df_recent = pd.concat(player_recent, ignore_index=True)
        
        # Compute per-60 metrics (normalize by TOI)
        # Map column names flexibly
        toi_col = None
        for col in ['TOI', 'TOI/GP (min)', 'Player ES TOI (Minutes)', 'Time On Ice']:
            if col in df_recent.columns:
                toi_col = col
                break
        
        if toi_col is None:
            logger.warning("No TOI column found, using games played as proxy")
            df_recent['TOI_minutes'] = 20.0  # Default assumption
        else:
            # Convert TOI to minutes
            if df_recent[toi_col].dtype == 'object':
                # Format might be "MM:SS" or just minutes
                df_recent['TOI_minutes'] = df_recent[toi_col].apply(
                    lambda x: _parse_toi_to_minutes(x) if pd.notna(x) else 20.0
                )
            else:
                df_recent['TOI_minutes'] = pd.to_numeric(df_recent[toi_col], errors='coerce').fillna(20.0)
        
        # Component metrics calculation
        # 1. EV Primary Points/60
        ev_points_col = _find_column(df_recent, ['EV Points', 'Even Strength Points', 'ES Points'])
        if ev_points_col:
            df_recent['ev_points_per60'] = (
                pd.to_numeric(df_recent[ev_points_col], errors='coerce').fillna(0) / 
                (df_recent['TOI_minutes'] / 60.0)
            )
        else:
            df_recent['ev_points_per60'] = 0
        
        # 2. Individual xG/60
        ixg_col = _find_column(df_recent, ['ixG', 'Individual xG', 'Player xG', 'xG'])
        if ixg_col:
            df_recent['ixg_per60'] = (
                pd.to_numeric(df_recent[ixg_col], errors='coerce').fillna(0) / 
                (df_recent['TOI_minutes'] / 60.0)
            )
        else:
            df_recent['ixg_per60'] = 0
        
        # 3. Shot Assists/60
        shot_assists_col = _find_column(df_recent, ['Shot Assists', 'Shots Assisted', 'Primary Assists'])
        if shot_assists_col:
            df_recent['shot_assists_per60'] = (
                pd.to_numeric(df_recent[shot_assists_col], errors='coerce').fillna(0) / 
                (df_recent['TOI_minutes'] / 60.0)
            )
        else:
            df_recent['shot_assists_per60'] = 0
        
        # 4. Controlled Entries Leading to Shots/60
        entries_col = _find_column(df_recent, ['Controlled Entries', 'Zone Entries', 'OZ Entries'])
        if entries_col:
            df_recent['entries_per60'] = (
                pd.to_numeric(df_recent[entries_col], errors='coerce').fillna(0) / 
                (df_recent['TOI_minutes'] / 60.0)
            )
        else:
            df_recent['entries_per60'] = 0
        
        # 5. On-Ice xGF%
        xgf_pct_col = _find_column(df_recent, ['On-Ice xGF%', 'xGF%', 'Expected Goals For %'])
        if xgf_pct_col:
            df_recent['xgf_pct'] = pd.to_numeric(df_recent[xgf_pct_col], errors='coerce').fillna(50.0)
        else:
            df_recent['xgf_pct'] = 50.0
        
        # Aggregate by player
        player_metrics = df_recent.groupby('Player Name').agg({
            'ev_points_per60': 'mean',
            'ixg_per60': 'mean',
            'shot_assists_per60': 'mean',
            'entries_per60': 'mean',
            'xgf_pct': 'mean',
            'TOI_minutes': 'sum'
        }).reset_index()

        # Compute per-player TRend using recent vs. prior slice composites
        # Use raw (non z-score) component means with the same weights
        trend_weights = {
            'ev_points_per60': 0.35,
            'ixg_per60': 0.25,
            'shot_assists_per60': 0.15,
            'entries_per60': 0.15,
            'xgf_pct': 0.10,
        }

        deltas: List[float] = []
        player_delta_map: Dict[str, float] = {}
        games_count: Dict[str, int] = {}

        # Ensure df_recent is sorted by most-recent first (it should be already)
        # but do a stable sort if a date column exists
        if 'Date' in df_recent.columns:
            df_recent = df_recent.sort_values('Date', ascending=False)
        elif 'Game Date' in df_recent.columns:
            df_recent = df_recent.sort_values('Game Date', ascending=False)

        for player, sub in df_recent.groupby('Player Name'):
            sub = sub.head(window)
            games_count[player] = len(sub)
            k = min(5, max(2, len(sub) // 2))
            if len(sub) < k * 2:
                player_delta_map[player] = 0.0
                deltas.append(0.0)
                continue
            recent_slice = sub.iloc[:k]
            prior_slice = sub.iloc[k: k * 2]

            def comp(frame: pd.DataFrame) -> float:
                total = 0.0
                for m, w in trend_weights.items():
                    try:
                        total += float(pd.to_numeric(frame[m], errors='coerce').mean()) * w
                    except Exception:
                        total += 0.0
                return total

            delta = comp(recent_slice) - comp(prior_slice)
            player_delta_map[player] = float(delta)
            deltas.append(float(delta))
        
        # Compute z-scores for each metric
        for metric in ['ev_points_per60', 'ixg_per60', 'shot_assists_per60', 'entries_per60', 'xgf_pct']:
            mean = player_metrics[metric].mean()
            std = player_metrics[metric].std()
            if std > 0:
                player_metrics[f'{metric}_zscore'] = (player_metrics[metric] - mean) / std
            else:
                player_metrics[f'{metric}_zscore'] = 0
        
        # Weighted composite (PFI raw score)
        weights = {
            'ev_points_per60_zscore': 0.35,
            'ixg_per60_zscore': 0.25,
            'shot_assists_per60_zscore': 0.15,
            'entries_per60_zscore': 0.15,
            'xgf_pct_zscore': 0.10
        }
        
        player_metrics['pfi_raw'] = sum(
            player_metrics[metric] * weight 
            for metric, weight in weights.items()
        )
        
        # Scale to 0-100
        min_pfi = player_metrics['pfi_raw'].min()
        max_pfi = player_metrics['pfi_raw'].max()
        if max_pfi > min_pfi:
            player_metrics['pfi'] = 50 + (
                (player_metrics['pfi_raw'] - player_metrics['pfi_raw'].mean()) / 
                (player_metrics['pfi_raw'].std() + 0.01)
            ) * 15
        else:
            player_metrics['pfi'] = 50
        
        player_metrics['pfi'] = player_metrics['pfi'].clip(0, 100).round(1)
        
        # Add trend arrow based on recent vs earlier games (threshold by cohort std)
        if deltas:
            try:
                std = float(np.std(deltas))
            except Exception:
                std = 0.0
            threshold = max(0.05, 0.35 * std) if std > 0 else 0.1
        else:
            threshold = 0.1

        trend_map: Dict[str, str] = {}
        for _, row in player_metrics.iterrows():
            name = row['Player Name']
            delta = player_delta_map.get(name, 0.0)
            if delta > threshold:
                trend_map[name] = 'up'
            elif delta < -threshold:
                trend_map[name] = 'down'
            else:
                trend_map[name] = 'stable'
        
        # Sort by PFI and prepare output
        player_metrics = player_metrics.sort_values('pfi', ascending=False)
        
        results = []
        for _, row in player_metrics.iterrows():
            results.append({
                'player_name': row['Player Name'],
                'pfi_score': float(row['pfi']),
                'trend': trend_map.get(row['Player Name'], 'stable'),
                'games_analyzed': int(games_count.get(row['Player Name'], window)),
                'total_toi_minutes': float(row['TOI_minutes']),
                'breakdown': {
                    'ev_points_per60': round(float(row['ev_points_per60']), 2),
                    'ixg_per60': round(float(row['ixg_per60']), 2),
                    'shot_assists_per60': round(float(row['shot_assists_per60']), 2),
                    'entries_per60': round(float(row['entries_per60']), 2),
                    'xgf_pct': round(float(row['xgf_pct']), 1)
                }
            })
        
        return results[:10]  # Top 10 players
        
    except Exception as e:
        logger.error(f"Error computing PFI: {str(e)}")
        return []


def compute_team_trends(
    df_team_games: pd.DataFrame,
    window: int = 10
) -> Dict[str, Any]:
    """
    Compute Team Momentum/Trend indicators for Montreal Canadiens.
    
    Metrics:
    - Rolling xGF% (5 and 10 game windows)
    - Net Special Teams (PP% + PK% relative to league)
    - Pace (CF/60 vs CA/60)
    - PDO guardrails (shooting % + save %)
    
    Args:
        df_team_games: DataFrame with team game-by-game stats
        window: Rolling window size (default: 10)
        
    Returns:
        Dictionary with trend metrics and gauges
    """
    try:
        if df_team_games.empty:
            return _empty_team_trends()
        
        df = df_team_games.copy()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values('Date', ascending=False)
        
        # Take recent games
        df_recent = df.head(window)
        
        # xGF%
        xgf_col = _find_column(df_recent, ['XGF', 'xGF', 'Expected Goals For'])
        xga_col = _find_column(df_recent, ['XGA', 'xGA', 'Expected Goals Against'])
        
        xgf_pct = 50.0
        if xgf_col and xga_col:
            xgf_total = pd.to_numeric(df_recent[xgf_col], errors='coerce').sum()
            xga_total = pd.to_numeric(df_recent[xga_col], errors='coerce').sum()
            if (xgf_total + xga_total) > 0:
                xgf_pct = (xgf_total / (xgf_total + xga_total)) * 100
        
        # Special teams
        pp_pct = 20.0  # League average baseline
        pk_pct = 80.0
        
        pp_col = _find_column(df_recent, ['PP%', 'Power Play %', 'PP Percentage'])
        pk_col = _find_column(df_recent, ['PK%', 'Penalty Kill %', 'PK Percentage'])
        
        if pp_col:
            pp_pct = pd.to_numeric(df_recent[pp_col], errors='coerce').mean()
            if pd.isna(pp_pct):
                pp_pct = 20.0
        if pk_col:
            pk_pct = pd.to_numeric(df_recent[pk_col], errors='coerce').mean()
            if pd.isna(pk_pct):
                pk_pct = 80.0
        
        special_teams_net = pp_pct + pk_pct - 100  # Relative to league baseline (20+80=100)
        
        # Pace (Corsi For/60 vs Corsi Against/60)
        cf_col = _find_column(df_recent, ['CF', 'Corsi For', 'Shot Attempts For'])
        ca_col = _find_column(df_recent, ['CA', 'Corsi Against', 'Shot Attempts Against'])
        
        cf_per60 = 60.0
        ca_per60 = 60.0
        
        if cf_col and ca_col:
            cf_per60 = pd.to_numeric(df_recent[cf_col], errors='coerce').mean()
            ca_per60 = pd.to_numeric(df_recent[ca_col], errors='coerce').mean()
            if pd.isna(cf_per60):
                cf_per60 = 60.0
            if pd.isna(ca_per60):
                ca_per60 = 60.0
        
        # PDO
        sh_pct = 10.0  # Default
        sv_pct = 90.0
        
        sh_col = _find_column(df_recent, ['SH%', 'Shooting %', 'Shooting Percentage'])
        sv_col = _find_column(df_recent, ['SV%', 'Save %', 'Save Percentage'])
        
        if sh_col:
            sh_pct = pd.to_numeric(df_recent[sh_col], errors='coerce').mean()
            if pd.isna(sh_pct):
                sh_pct = 10.0
        if sv_col:
            sv_pct = pd.to_numeric(df_recent[sv_col], errors='coerce').mean()
            if pd.isna(sv_pct):
                sv_pct = 90.0
        
        pdo = sh_pct + sv_pct
        
        return {
            'window_games': window,
            'xgf_pct_rolling': round(float(xgf_pct), 1),
            'special_teams_net': round(float(special_teams_net), 1),
            'pace': {
                'cf_per60': round(float(cf_per60), 1),
                'ca_per60': round(float(ca_per60), 1),
                'cf_pct': round((cf_per60 / (cf_per60 + ca_per60) * 100), 1) if (cf_per60 + ca_per60) > 0 else 50.0
            },
            'pdo': {
                'value': round(float(pdo), 1),
                'shooting_pct': round(float(sh_pct), 1),
                'save_pct': round(float(sv_pct), 1),
                'status': 'sustainable' if 98 <= pdo <= 102 else ('hot' if pdo > 102 else 'cold')
            }
        }
        
    except Exception as e:
        logger.error(f"Error computing team trends: {str(e)}")
        return _empty_team_trends()


def compute_rival_threat_index(
    df_division_teams: pd.DataFrame,
    division: str = 'Atlantic',
    window: int = 10
) -> List[Dict[str, Any]]:
    """
    Compute Rival Threat Index (RTI) for Atlantic Division rivals.
    
    RTI is a composite threat score based on:
    - Rolling xGF%: 0.30
    - Schedule-adjusted points%: 0.20
    - Special teams net: 0.20
    - 5v5 goal share: 0.15
    - Goalie workload/xGA trend: 0.10
    - Rest/travel adjustment: 0.05
    
    Args:
        df_division_teams: DataFrame with team stats for division
        division: Division name (default: 'Atlantic')
        window: Rolling window for recent performance
        
    Returns:
        List of team RTI dictionaries sorted by threat level
    """
    try:
        if df_division_teams.empty:
            return _default_atlantic_teams()
        
        df = df_division_teams.copy()
        
        teams = []
        for team, group in df.groupby('Team'):
            if len(group) < 3:
                continue
            
            recent = group.tail(window)
            
            # xGF%
            xgf = pd.to_numeric(recent.get('XGF', 0), errors='coerce').sum()
            xga = pd.to_numeric(recent.get('XGA', 0), errors='coerce').sum()
            xgf_pct = (xgf / (xgf + xga) * 100) if (xgf + xga) > 0 else 50.0
            
            # Points%
            points = pd.to_numeric(recent.get('Points', 0), errors='coerce').sum()
            games = len(recent)
            points_pct = (points / (games * 2) * 100) if games > 0 else 50.0
            
            # Special teams
            pp_pct = pd.to_numeric(recent.get('PP%', 20), errors='coerce').mean()
            pk_pct = pd.to_numeric(recent.get('PK%', 80), errors='coerce').mean()
            # Guard against NaNs when no values are present
            if pd.isna(pp_pct):
                pp_pct = 20.0
            if pd.isna(pk_pct):
                pk_pct = 80.0
            st_net = pp_pct + pk_pct - 100
            if pd.isna(st_net):
                st_net = 0.0
            
            # 5v5 goal share
            gf_5v5 = pd.to_numeric(recent.get('GF_5v5', 0), errors='coerce').sum()
            ga_5v5 = pd.to_numeric(recent.get('GA_5v5', 0), errors='coerce').sum()
            goal_share_5v5 = (gf_5v5 / (gf_5v5 + ga_5v5) * 100) if (gf_5v5 + ga_5v5) > 0 else 50.0
            
            # Compute RTI
            rti_raw = (
                xgf_pct * 0.30 +
                points_pct * 0.20 +
                (st_net + 100) * 0.20 +  # Normalize to 0-100 scale
                goal_share_5v5 * 0.15 +
                50 * 0.15  # Goalie workload placeholder
            )
            # Final NaN guard
            try:
                rti_val = float(rti_raw)
                if pd.isna(rti_val):
                    rti_val = 50.0
            except Exception:
                rti_val = 50.0
            
            teams.append({
                'team': team,
                'rti_score': round(rti_val, 1),
                'xgf_pct': round(float(xgf_pct), 1),
                'points_pct': round(float(points_pct), 1),
                'special_teams_net': round(float(st_net), 1),
                'goal_share_5v5': round(float(goal_share_5v5), 1),
                'recent_record': f"{len(recent[recent.get('Result', '') == 'W'])}-{len(recent[recent.get('Result', '') == 'L'])}" if 'Result' in recent.columns else "N/A"
            })
        
        return sorted(teams, key=lambda x: x['rti_score'], reverse=True)
        
    except Exception as e:
        logger.error(f"Error computing RTI: {str(e)}")
        return _default_atlantic_teams()


def compute_fan_sentiment_proxy(
    team_trends: Dict[str, Any],
    top_players_pfi: List[Dict[str, Any]],
    season_baseline: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compute Fan Sentiment Proxy (FSP) - statistical proxy for fan sentiment.
    
    Formula components:
    - Points% last 10 vs season baseline
    - Goal differential vs expected
    - Special teams trend
    - Star player PFI delta
    - Losing streak penalty
    
    Output: 0-100 score with qualitative banding
    
    Args:
        team_trends: Team trend metrics from compute_team_trends
        top_players_pfi: Player Form Index results
        season_baseline: Optional season baseline for comparison
        
    Returns:
        FSP dictionary with score, sentiment, and factors
    """
    try:
        base_score = 50.0
        
        # xGF% impact (±20 points)
        xgf_pct = team_trends.get('xgf_pct_rolling', 50.0)
        xgf_impact = (xgf_pct - 50.0) * 0.4
        
        # Special teams impact (±15 points)
        st_net = team_trends.get('special_teams_net', 0)
        st_impact = st_net * 0.75
        
        # PDO stability (±10 points)
        pdo_status = team_trends.get('pdo', {}).get('status', 'sustainable')
        pdo_impact = 5 if pdo_status == 'hot' else (-5 if pdo_status == 'cold' else 0)
        
        # Star player performance (±15 points)
        star_impact = 0
        if top_players_pfi:
            avg_pfi = sum(p['pfi_score'] for p in top_players_pfi[:3]) / 3
            star_impact = (avg_pfi - 50) * 0.3
        
        # Compute final FSP
        fsp = base_score + xgf_impact + st_impact + pdo_impact + star_impact
        fsp = max(0, min(100, fsp))
        
        # Sentiment banding
        if fsp >= 70:
            sentiment = 'Very Positive'
            emoji_proxy = 'High Energy'
        elif fsp >= 55:
            sentiment = 'Positive'
            emoji_proxy = 'Optimistic'
        elif fsp >= 45:
            sentiment = 'Neutral'
            emoji_proxy = 'Cautious'
        elif fsp >= 30:
            sentiment = 'Concerned'
            emoji_proxy = 'Frustrated'
        else:
            sentiment = 'Very Concerned'
            emoji_proxy = 'Disappointed'
        
        return {
            'fsp_score': round(float(fsp), 1),
            'sentiment': sentiment,
            'sentiment_description': emoji_proxy,
            'factors': {
                'xgf_impact': round(float(xgf_impact), 1),
                'special_teams_impact': round(float(st_impact), 1),
                'pdo_impact': float(pdo_impact),
                'star_player_impact': round(float(star_impact), 1)
            },
            'note': 'Statistical proxy based on team performance indicators'
        }
        
    except Exception as e:
        logger.error(f"Error computing FSP: {str(e)}")
        return {
            'fsp_score': 50.0,
            'sentiment': 'Neutral',
            'sentiment_description': 'Calculating',
            'factors': {},
            'error': str(e)
        }


# Helper functions

def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find first matching column name from candidates."""
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _parse_toi_to_minutes(toi_str: Any) -> float:
    """Parse TOI string (MM:SS or just minutes) to float minutes."""
    try:
        if pd.isna(toi_str):
            return 0.0
        
        s = str(toi_str)
        
        if ':' in s:
            parts = s.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1]) if len(parts) > 1 else 0
            return minutes + seconds / 60.0
        else:
            return float(s)
    except Exception:
        return 0.0


def _empty_team_trends() -> Dict[str, Any]:
    """Return empty team trends structure."""
    return {
        'window_games': 0,
        'xgf_pct_rolling': 50.0,
        'special_teams_net': 0.0,
        'pace': {'cf_per60': 60.0, 'ca_per60': 60.0, 'cf_pct': 50.0},
        'pdo': {'value': 100.0, 'shooting_pct': 10.0, 'save_pct': 90.0, 'status': 'sustainable'}
    }


def _default_atlantic_teams() -> List[Dict[str, Any]]:
    """Return default Atlantic division teams."""
    teams = ['BOS', 'TOR', 'FLA', 'TBL', 'BUF', 'DET', 'OTT', 'MTL']
    return [
        {
            'team': team,
            'rti_score': 50.0,
            'xgf_pct': 50.0,
            'points_pct': 50.0,
            'special_teams_net': 0.0,
            'goal_share_5v5': 50.0,
            'recent_record': 'N/A'
        }
        for team in teams
    ]
