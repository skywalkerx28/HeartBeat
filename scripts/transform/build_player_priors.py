#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATAMART_BASE = ROOT / 'data/processed/predictions/datamart'
OUT_BASE = ROOT / 'data/processed/predictions/priors'
OUT_BASE.mkdir(parents=True, exist_ok=True)

METRIC_MAP = {
    'points': 'points_g',
    'goals': 'goals_g',
    'assists': 'assists_g',
    'shots': 'shots_g',
}


def list_seasons():
    seasons = []
    for d in DATAMART_BASE.iterdir():
        if (d / 'regular' / 'player_game_level.parquet').exists():
            seasons.append(d.name)
    seasons.sort()
    return seasons


def build_priors(target_season: str, metric: str, lookback: int = 5, min_games_pseudo: int = 20, max_games_pseudo: int = 150):
    metric_col = METRIC_MAP[metric]
    seasons = list_seasons()
    if target_season not in seasons:
        raise RuntimeError(f'Target season {target_season} not found in datamart')
    idx = seasons.index(target_season)
    past = seasons[max(0, idx - lookback):idx]
    if not past:
        raise RuntimeError('No past seasons available for priors')
    # Recency weights (linear ramp)
    w = np.linspace(0.5, 1.0, num=len(past))
    weights = {s: w[i] for i, s in enumerate(past)}

    totals = []
    for s in past:
        df = pd.read_parquet(DATAMART_BASE / s / 'regular' / 'player_game_level.parquet', columns=['playerId', metric_col])
        g = df.groupby('playerId')[metric_col].agg(['sum','count']).reset_index()
        g['season'] = s
        g['w'] = weights[s]
        totals.append(g)
    allp = pd.concat(totals, ignore_index=True)
    allp['w_sum'] = allp['sum'] * allp['w']
    allp['w_cnt'] = allp['count'] * allp['w']
    agg = allp.groupby('playerId').agg({'w_sum':'sum','w_cnt':'sum'}).reset_index()
    agg['mu_hat'] = agg['w_sum'] / agg['w_cnt']
    # pseudo sample size S
    agg['S'] = agg['w_cnt'].clip(lower=min_games_pseudo, upper=max_games_pseudo)
    agg['alpha0'] = agg['mu_hat'] * agg['S']
    agg['beta0'] = agg['S']
    agg['metric'] = metric
    agg['lookbackSeasons'] = len(past)
    agg['gamesUsedWeighted'] = agg['w_cnt']
    cols = ['playerId','metric','alpha0','beta0','mu_hat','S','gamesUsedWeighted','lookbackSeasons']
    out = agg[cols].copy()
    out['playerId'] = out['playerId'].astype(str)
    out_file = OUT_BASE / f'{metric}_priors_{target_season}.parquet'
    out.to_parquet(out_file, index=False)
    print(f'Wrote priors: {out.shape} -> {out_file}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', required=False)
    parser.add_argument('--metric', default='points', choices=list(METRIC_MAP.keys()))
    parser.add_argument('--lookback', type=int, default=5)
    args = parser.parse_args()
    seasons = list_seasons()
    target = args.season or seasons[-1]
    build_priors(target, args.metric, args.lookback)
