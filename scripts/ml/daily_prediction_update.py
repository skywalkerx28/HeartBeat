#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

steps = [
    ['python3', str(ROOT / 'scripts/ingest/fetch_player_game_logs.py')],
    ['python3', str(ROOT / 'scripts/transform/aggregate_player_game_logs.py')],
    # Usage ingestion is manual; include if needed in the future
    ['python3', str(ROOT / 'scripts/transform/build_player_priors.py'), '--metric', 'points'],
    ['python3', str(ROOT / 'scripts/transform/build_player_priors.py'), '--metric', 'goals'],
    ['python3', str(ROOT / 'scripts/transform/build_player_priors.py'), '--metric', 'assists'],
    ['python3', str(ROOT / 'scripts/ml/train_forecasts.py'), '--metric', 'points'],
    ['python3', str(ROOT / 'scripts/ml/train_forecasts.py'), '--metric', 'goals'],
    ['python3', str(ROOT / 'scripts/ml/train_forecasts.py'), '--metric', 'assists'],
]

for cmd in steps:
    print('RUN:', ' '.join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print('FAILED:', ' '.join(cmd))
        sys.exit(rc)
print('DAILY UPDATE COMPLETE')
