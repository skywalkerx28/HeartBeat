#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATAMART_BASE = ROOT / 'data/processed/predictions/datamart'
PRIORS_BASE = ROOT / 'data/processed/predictions/priors'
OUT_BASE = ROOT / 'data/processed/predictions'

METRIC_MAP = {
    'points': 'points_g',
    'goals': 'goals_g',
    'assists': 'assists_g',
    'shots': 'shots_g'
}

rng = np.random.default_rng(123)


def list_seasons():
    seasons = []
    for d in DATAMART_BASE.iterdir():
        if (d / 'regular' / 'player_game_level.parquet').exists():
            seasons.append(d.name)
    seasons.sort()
    return seasons


def negbin_params(mu: float, var: float):
    if var <= mu or not np.isfinite(var) or not np.isfinite(mu) or mu <= 0:
        return None
    n = (mu * mu) / (var - mu)
    if n <= 0:
        return None
    p = n / (n + mu)
    p = min(max(p, 1e-6), 1-1e-6)
    return n, p


def simulate_future(mu: float, var: float, steps: int, sims: int = 2000):
    if steps <= 0:
        return np.zeros((steps,))
    nb = negbin_params(mu, var)
    if nb is None:
        draws = rng.poisson(lam=max(mu, 1e-6), size=(sims, steps))
    else:
        n, p = nb
        draws = rng.negative_binomial(n, p, size=(sims, steps))
    cum = np.cumsum(draws, axis=1)
    p10 = np.percentile(cum, 10, axis=0)
    p50 = np.percentile(cum, 50, axis=0)
    p90 = np.percentile(cum, 90, axis=0)
    mean = cum.mean(axis=0)
    var  = cum.var(axis=0)
    return p10, p50, p90, mean, var


def train(season: str, metric: str):
    metric_col = METRIC_MAP[metric]
    dm = pd.read_parquet(DATAMART_BASE / season / 'regular' / 'player_game_level.parquet')
    dm.sort_values(['playerId','gameDate'], inplace=True)
    # Load priors (fallback to weak prior if missing)
    priors_file = PRIORS_BASE / f'{metric}_priors_{season}.parquet'
    priors = None
    if priors_file.exists():
        priors = pd.read_parquet(priors_file)
        priors['playerId'] = priors['playerId'].astype(str)
    out_rows = []
    for pid, g in dm.groupby('playerId'):
        g = g.reset_index(drop=True)
        games_played = int(g['gameNumber'].max()) if pd.notna(g['gameNumber']).any() else len(g)
        y_sum = float(g[metric_col].sum())
        # Prior
        if priors is not None:
            row = priors[priors['playerId'] == str(pid)]
            if not row.empty:
                alpha0 = float(row['alpha0'].iloc[0])
                beta0  = float(row['beta0'].iloc[0])
            else:
                alpha0, beta0 = 1.0, 1.0
        else:
            alpha0, beta0 = 1.0, 1.0
        # Posterior for per-game rate lambda
        alpha_post = alpha0 + y_sum
        beta_post  = beta0 + games_played
        mu_post = alpha_post / max(beta_post, 1e-6)
        var_post = alpha_post / (max(beta_post, 1e-6)**2)
        remaining = max(0, 82 - games_played)
        if remaining == 0:
            continue
        p10, p50, p90, mean, var = simulate_future(mu_post, mu_post + var_post * remaining, remaining)
        season_total_to_date = float((g['points'] if metric=='points' else g[metric_col].cumsum()).iloc[-1])
        steps = np.arange(1, remaining+1)
        out = pd.DataFrame({
            'playerId': str(pid),
            'season': season,
            'metric': metric,
            'step': steps,
            'gamesRemaining': remaining - steps + 1,
            'p10': p10,
            'p50': p50,
            'p90': p90,
            'mean': mean,
            'var': var,
            'currentTotal': season_total_to_date,
            'projectedTotal_p50': season_total_to_date + p50,
            'projectedTotal_mean': season_total_to_date + mean,
            'alpha_post': alpha_post,
            'beta_post': beta_post
        })
        out_rows.append(out)
    if not out_rows:
        print('No players to forecast')
        return
    all_out = pd.concat(out_rows, ignore_index=True)
    season_out_dir = OUT_BASE / 'forecasts' / season / 'regular' / metric
    season_out_dir.mkdir(parents=True, exist_ok=True)
    for pid, g in all_out.groupby('playerId'):
        pdir = season_out_dir / str(pid)
        pdir.mkdir(parents=True, exist_ok=True)
        g.to_parquet(pdir / 'forecast.parquet', index=False)
    all_out.to_parquet(season_out_dir / 'forecasts_union.parquet', index=False)
    print(f'Forecasts (priors) written: {all_out.shape} for {metric} {season}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season')
    parser.add_argument('--metric', default='points', choices=list(METRIC_MAP.keys()))
    args = parser.parse_args()
    seasons = list_seasons()
    season = args.season or seasons[-1]
    # Build priors if missing
    pf = PRIORS_BASE / f'{args.metric}_priors_{season}.parquet'
    if not pf.exists():
        print('Priors missing; run build_player_priors.py first')
    train(season, args.metric)
