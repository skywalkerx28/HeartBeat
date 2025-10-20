# Comprehensive NHL Play-by-Play Extraction System

## Overview
End-to-end extractor that converts NHL play-by-play CSVs into rich analytics for players and teams. It implements shift-based matchups, deterministic deployment/sequence linkage, whistle-to-whistle analytics, player tendencies with per-event context, and detailed shift breakdowns.

## Core Components

- Comprehensive Hockey Extractor (`scripts/ingest/comprehensive_hockey_extraction.py`): parses a single game and writes JSON/CSV outputs.
- Batch Extraction Processor (`scripts/ingest/batch_extraction_processor.py`): optional parallel wrapper for many games.

## Extracted Metrics Categories

### Matchup Data

1) Individual 1v1 matchups (shift-based)
- Types: F_vs_F, F_vs_D, D_vs_D.
- Counting rule: increment once when two players first share the ice after a personnel change; do not recount until they separate.
- Duration model: for every active pair, accumulate total_time with first_appearance/last_appearance and appearances count.

2) Line vs Pairing matchups
- 3F line vs 2D pairing (both directions). Only counted when exactly 3F and 2D are on for the teams. Shift-based, not event-based.

### Deployment Analysis

1) Whistle deployments (deterministic IDs)
- One deployment per whistle with a single deployment_id shared by both teams’ groups.
- Fields: deployment_id, whistle_event_index, whistle_time, period, home_forwards, home_defense, away_forwards, away_defense, home_skaters, away_skaters, strength, manpowerSituation, home_team_code/away_team_code, home_team_id/away_team_id.
- Faceoff metadata: faceoff_time, faceoff_zone, faceoff_x/y, faceoff_x_adj/y_adj, faceoff_shorthand (verbatim CSV), faceoff_flags, faceoff_winner_team.
- Team zones derived from the faceoff: home_zone, away_zone (OZ/DZ/NZ).

2) Rotation patterns (true trio shifts)
- Tracks contiguous trio (3F) shifts per side; closes when any of the three changes.
- Per-trio duration list plus per-period totals and averages.

3) Line rotation sequence
- Chronological list of 3F trios and 2D pairings as they appear, with period, period_time, gameTime, and home_score_diff.

### Whistle-to-Whistle Sequences

- Deterministic sequence_id assignment: interval from whistle i to whistle i+1.
- Each sequence links to the deployment_id of the starting whistle.
- Per-event maps: event_index → sequence_id and event_index → deployment_id.
- Sequence metrics:
  - Duration, length (events), start/end period, gameTime, periodTime.
  - Zone time for both teams (OZ/NZ/DZ attribution by acting team).
  - Possession time per team (teamInPossession).
  - Entry/exit attempts and controlled success (home/away).
  - Shots per team (on, missed, blocked, total) and totals.
  - Passes, LPR recoveries, pressure events, turnovers.
  - Start_zone/end_zone and zones_visited.

### Individual Player Tendencies

- Per-player summary: top_zones, top_actions, success_by_action, preferred shot locations.
- Full per-event timeline with context:
  - event_index, period, periodTime, gameTime, timecode, team, zone, name, shorthand, outcome, flags.
  - Coordinates: x, y, x_adj, y_adj.
  - On-ice actors: teammates_on_ice_ids, opponents_on_ice_ids, team_trio_id, team_pair_id, opponent_trio_id, opponent_pair_id, team_goalie_id, opponent_goalie_id.
  - Deterministic linkage: sequence_id, deployment_id for every event.

### Player Shifts

- Shift boundaries: start when a player appears; end when they leave. End-time snaps to prior whistle if immediately preceded by a whistle; otherwise uses midpoint between last-on and first-off events for sub-second accuracy in gameTime and timecode.
- Outputs: shift_game_length, shift_real_length, rest_game_next, rest_real_next, cumulative TOI (game/real), per-player running averages.
- Context fields: start/end period and periodTime, strength_start, manpower_start.
- Opponent coverage: opponents_seen_ids contains all unique opponent skaters faced during the shift (goalies excluded). Also aggregates sequence_ids and deployment_ids encountered during the shift to simplify joins.

### Unique Hockey Metrics

- Puck touch chains: first 100 chains with chain length and possession id.
- Pressure cascades: map pressure events to subsequent turnovers with success flag.
- Entry-to-shot time: latency from entry to team’s next shot, with success classification.
- Recovery time: time between possession changes by team.
- Pass networks: directed weighted graphs from passer to receiver; outputs summary graph metrics.
- Shift momentum: per-player momentum trajectory over continuous ice time.

## Deterministic IDs and Linkage

- deployment_id: one per whistle; includes both sides’ groups.
- sequence_id: one per whistle interval (i → i+1).
- event-level maps: event_to_sequence_id and event_to_deployment_id.
- These IDs are injected into whistle sequence CSV, player timeline CSV, and aggregated into player shifts (sequence_ids/deployment_ids arrays).

## Usage

Extract one game:
```bash
python scripts/ingest/comprehensive_hockey_extraction.py
```

Batch process (optional wrapper):
```bash
python scripts/ingest/batch_extraction_processor.py \
  --base-dir data/processed/analytics/nhl_play_by_play \
  --output-dir data/processed/extracted_metrics \
  --max-workers 8
```

## Output Files

- Main JSON: `<game>_comprehensive_metrics.json` (all results with JSON-safe types).
- Matchup CSVs: `<game>_F_vs_F_matchups.csv`, `<game>_F_vs_D_matchups.csv`, `<game>_D_vs_D_matchups.csv`.
- Whistle sequences CSV: `<game>_whistle_sequences.csv` (sequence_id, deployment_id, metrics).
- Player tendencies CSV: `<game>_player_tendencies.csv` (per-action counts + success); timeline CSV: `<game>_player_tendencies_timeline.csv` (event-level with sequence_id/deployment_id).
- Period openers CSV: `<game>_period_openers.csv`.

## Performance Snapshot (BOS vs FLA sample)

- 3,981 events processed
- 54 whistles (54 deployments, 54 sequences)
- 38 players with full tendency timelines

## Roadmap

- Faceoff dot classification from adjusted coordinates (nine-dots mapping).
- Expanded entry/exit vocab and reception detection to improve transition coverage.
- Per-shot expected goals and aggregations per sequence/deployment/trio.
- Additional network metrics (PageRank, betweenness) for passes.
- Optional exclusion of goalie shifts if desired in downstream analyses.
