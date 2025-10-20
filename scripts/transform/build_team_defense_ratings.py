#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DM = ROOT / 'data/processed/predictions/datamart'
OUT = ROOT / 'data/processed/predictions/features/team_defense'
OUT.mkdir(parents=True, exist_ok=True)

# Build simple opponent defensive rating per date: goals conceded per team per day (rolling 10)
for d in DM.iterdir():
    p = d / 'regular' / 'player_game_level.parquet'
    if not p.exists():
        continue
    df = pd.read_parquet(p, columns=['gameDate','opponent','goals_g'])
    df = df.dropna(subset=['gameDate','opponent'])
    t = df.groupby(['gameDate','opponent'])['goals_g'].sum().reset_index()
    # rolling per team sorted by date
    t = t.sort_values(['opponent','gameDate'])
    t['ga_roll10'] = t.groupby('opponent')['goals_g'].transform(lambda s: s.rolling(10, min_periods=3).mean())
    out_dir = OUT / d.name
    out_dir.mkdir(parents=True, exist_ok=True)
    t.rename(columns={'opponent':'teamAbbrev'}, inplace=True)
    t.to_parquet(out_dir / 'defense_regular.parquet', index=False)
    print('Team defense written:', d.name, t.shape)
