#!/usr/bin/env python3
"""
Build season-level training datasets by merging per-game parquet shards
produced by comprehensive_hockey_extraction.py.

Outputs (by season):
  - data/processed/training/event_stream/<season>/_all_event_stream.parquet
  - data/processed/training/next_action/<season>/_all_next_action.parquet
  - data/processed/training/sequence_windows/<season>/_all_sequence_windows.parquet
  - data/processed/training/transition_stats/<season>/_global_transition_stats.parquet
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE = Path('data/processed/training')

def concat_parquets(dir_path: Path, pattern: str) -> pd.DataFrame:
    files = sorted(dir_path.glob(pattern))
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_parquet(f))
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def build_for_season(season: str) -> None:
    # Event stream
    es_dir = BASE / 'event_stream' / season
    if es_dir.exists():
        es = concat_parquets(es_dir, '*_event_stream.parquet')
        if not es.empty:
            es.to_parquet(es_dir / '_all_event_stream.parquet', compression='zstd', index=False)
            print(f"Saved merged event_stream for {season}: {es_dir / '_all_event_stream.parquet'}")

    # Next action
    na_dir = BASE / 'next_action' / season
    if na_dir.exists():
        na = concat_parquets(na_dir, '*_next_action.parquet')
        if not na.empty:
            na.to_parquet(na_dir / '_all_next_action.parquet', compression='zstd', index=False)
            print(f"Saved merged next_action for {season}: {na_dir / '_all_next_action.parquet'}")

    # Sequence windows
    sw_dir = BASE / 'sequence_windows' / season
    if sw_dir.exists():
        sw = concat_parquets(sw_dir, '*_sequence_windows.parquet')
        if not sw.empty:
            sw.to_parquet(sw_dir / '_all_sequence_windows.parquet', compression='zstd', index=False)
            print(f"Saved merged sequence_windows for {season}: {sw_dir / '_all_sequence_windows.parquet'}")

    # Transition stats aggregated
    ts_dir = BASE / 'transition_stats' / season
    if ts_dir.exists():
        ts = concat_parquets(ts_dir, '*_transition_stats.parquet')
        if not ts.empty:
            ts['count'] = ts['count'].astype(int)
            grp = ts.groupby(['action_t','action_t1','strength_state','zone'], as_index=False)['count'].sum()
            grp.to_parquet(ts_dir / '_global_transition_stats.parquet', compression='zstd', index=False)
            print(f"Saved global transition stats for {season}: {ts_dir / '_global_transition_stats.parquet'}")

def main():
    seasons = []
    for sub in (BASE / 'event_stream').glob('*'):
        if sub.is_dir():
            seasons.append(sub.name)
    for s in seasons:
        build_for_season(s)

if __name__ == '__main__':
    main()

