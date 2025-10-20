#!/usr/bin/env python3
"""
Extract team-level line rotation sequences (both benches) from play-by-play CSVs.

Outputs parquet with one row per rotation event including:
 - team, opponent, game_id, season
 - from/to forward and defense groups (player-id pipes)
 - replacements at forward/defense (player-out -> player-in pairs)
 - timing context: period, period_time, game_time, timecode, time deltas
 - game context: score differential (team perspective), strength_state, stoppage_type

File: data/processed/line_matchup_engine/team_line_rotations.parquet
"""

from pathlib import Path
import argparse
import logging

import importlib.util
import sys

# Load DataProcessor directly from file to avoid heavy package __init__ imports
HERE = Path(__file__).resolve().parent
DP_PATH = HERE / 'line_matchup_engine' / 'data_processor.py'
spec = importlib.util.spec_from_file_location("hb_lme_data_processor", DP_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load DataProcessor module from {DP_PATH}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)  # type: ignore[attr-defined]
DataProcessor = getattr(module, 'DataProcessor')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("extract_team_rotations")


def main():
    parser = argparse.ArgumentParser(description="Extract team line rotation sequences from PBP CSVs")
    parser.add_argument('--data-dir', type=str,
                        default=str(Path('data/raw/mtl_play_by_play').resolve()),
                        help='Directory containing playsequence-*.csv files')
    parser.add_argument('--player-map', type=str,
                        default=str(Path('data/processed/dim/player_ids.csv').resolve()),
                        help='CSV with player id -> team map')
    parser.add_argument('--out-dir', type=str,
                        default=str(Path('data/processed/line_matchup_engine').resolve()),
                        help='Directory to write parquet outputs')

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    player_map = Path(args.player_map)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir}")
    if not player_map.exists():
        logger.warning(f"Player mapping file not found: {player_map} — proceeding (team mapping may be limited)")

    # Initialize and process
    processor = DataProcessor(data_path=data_dir, player_mapping_path=player_map)
    logger.info("Processing all games to extract rotation sequences...")
    processor.process_all_games()

    # Persist events + rotation logs
    processor.save_processed_data(out_dir)
    logger.info("Done.")


if __name__ == '__main__':
    main()
