#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DM = ROOT / 'data/processed/predictions/datamart'
USAGE = ROOT / 'data/processed/predictions/features/season_context'
OUT = ROOT / 'data/processed/predictions/features/age_curves'
OUT.mkdir(parents=True, exist_ok=True)

METRICS = {
  'points': 'points_g',
  'goals': 'goals_g',
  'assists': 'assists_g',
  'shots': 'shots_g'
}

# Load all seasons available for regular season
parts = []
for d in DM.iterdir():
    p = d / 'regular' / 'player_game_level.parquet'
    if p.exists():
        try:
            df = pd.read_parquet(p, columns=['playerId','gameDate','age_years'] + list(METRICS.values()))
            df['season'] = d.name
            parts.append(df)
        except Exception:
            pass

if not parts:
    raise SystemExit('No datamart partitions available')

all_df = pd.concat(parts, ignore_index=True)
# bucket age to integer
all_df['age'] = np.floor(all_df['age_years']).astype('Int64')
all_df = all_df[all_df['age'].notna()]

# Attempt to join position group from usage features for each season
pos_map = {}
for d in USAGE.iterdir():
    reg = d / 'regular' / 'usage_all.parquet'
    if reg.exists():
        try:
            u = pd.read_parquet(reg, columns=['playerId','positionGroup'])
            u['playerId'] = u['playerId'].astype(str)
            # keep last occurrence
            u = u.drop_duplicates('playerId', keep='last')
            for _, r in u.iterrows():
                pos_map[str(r['playerId'])] = r.get('positionGroup', None)
        except Exception:
            pass

all_df['playerId'] = all_df['playerId'].astype(str)
all_df['positionGroup'] = all_df['playerId'].map(pos_map)

curves = []
for metric, col in METRICS.items():
    tmp = all_df[['age','positionGroup',col]].copy()
    tmp[col] = pd.to_numeric(tmp[col], errors='coerce').fillna(0.0)
    # per age x position average per game
    g = tmp.groupby(['positionGroup','age'])[col].mean().reset_index()
    # normalize within position to peak=1.0; fallback global
    for pos in g['positionGroup'].dropna().unique().tolist() + [None]:
        if pos is None:
            gg = tmp.groupby(['age'])[col].mean().reset_index()
            gg['positionGroup'] = 'ALL'
        else:
            gg = g[g['positionGroup'] == pos][['age',col]].copy()
            gg['positionGroup'] = pos
        if gg.empty:
            continue
        m = gg[col].max()
        if not np.isfinite(m) or m == 0:
            gg['multiplier'] = 1.0
        else:
            gg['multiplier'] = gg[col] / m
        gg['metric'] = metric
        curves.append(gg[['metric','positionGroup','age','multiplier']])

curve_df = pd.concat(curves, ignore_index=True)
curve_df.to_parquet(OUT / 'age_curve_multipliers.parquet', index=False)
print('Age curves written:', curve_df.shape, '->', OUT / 'age_curve_multipliers.parquet')
