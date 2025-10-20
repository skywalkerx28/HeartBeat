#!/usr/bin/env python3
"""
Aggregate advanced, per-player metrics from comprehensive extraction outputs.

Pipeline (for initial rollout):
1) Run ComprehensiveHockeyExtractor for MTL games (2024-2025, 2025-2026)
   located under data/processed/analytics/nhl_play_by_play/MTL/<season>/*.csv
2) Read each saved JSON in data/processed/extracted_metrics
3) Build per-game metrics per player, then roll up to per-season aggregates
4) Save under data/processed/player_profiles/advanced_metrics/{playerId}/{season}_{type}_advanced.json

Usage:
    python scripts/transform/aggregate_advanced_player_metrics.py \
      --teams MTL \
      --seasons 20242025,20252026 \
      --run-extractor

Notes:
- We derive the season from the playsequence filename (e.g., ...-20242025-...).
- Game type defaults to "regular" for these directories.
- Player IDs are normalized to canonical numeric strings (e.g., '8482113.0' -> '8482113').
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Dict, Any, List, Optional, Tuple


# ------------------------------
# Helpers
# ------------------------------

def norm_id(token: object) -> str:
    if token is None:
        return ""
    s = str(token).strip().strip('"')
    if not s or s.lower() == 'nan':
        return ""
    try:
        return str(int(float(s)))
    except Exception:
        return s


def parse_season_from_name(stem: str) -> Optional[str]:
    """Extract YYYYYYYY season from playsequence filename.
    Expected format: playsequence-YYYYMMDD-NHL-<match>-YYYYYYYY-<gameId>
    Returns the second-to-last token if it is an 8-digit number; otherwise the
    last 8-digit token found when scanning from right to left.
    """
    parts = stem.split('-')
    # Prefer the penultimate token (typical season position)
    if len(parts) >= 2:
        cand = parts[-2]
        if cand.isdigit() and len(cand) == 8:
            return cand
    # Fallback: search from right to left for an 8-digit token
    for p in reversed(parts):
        if len(p) == 8 and p.isdigit():
            return p
    return None


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ------------------------------
# Aggregation core
# ------------------------------

ENTRY_CTRL = {'CONTROLLED ENTRY INTO OZ', 'OZ ENTRY PASS+', 'O-ZONE ENTRY PASS RECEPTION'}
ENTRY_DUMP = {'DUMP IN+', 'CHIP DUMP+', 'HI PRESS DUMP IN LPR+', 'DUMP IN LPR+', 'OFF LPR OZ', 'OZ REC FACE OFF+'}
EXIT_CTRL = {'CONTROLLED EXIT FROM DZ'}
EXIT_DUMP = {'DUMP OUT+', 'OFF GLASS DUMP OUT+', 'FLIP DUMP OUT+', 'DZ REC FACE OFF+EXIT'}


@dataclass
class PlayerGameMetrics:
    game_id: Optional[int] = None
    game_date: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    # Shifts
    shift_count: int = 0
    toi_game_sec: float = 0.0
    avg_shift_game_sec: Optional[float] = None
    avg_rest_game_sec: Optional[float] = None
    # Events
    lpr_recoveries: int = 0
    pressure_events: int = 0
    turnovers: int = 0
    entries_ctrl_attempts: int = 0
    entries_ctrl_success: int = 0
    entries_dump_attempts: int = 0
    exits_ctrl_attempts: int = 0
    exits_ctrl_success: int = 0
    exits_dump_attempts: int = 0
    actions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    success_by_action: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {'success': 0, 'total': 0}))
    preferred_zones: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    shot_locations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Actions grouped by zone and play section
    actions_by_zone: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(lambda: {'count': 0, 'success': 0, 'total': 0, 'sections': defaultdict(lambda: {'count': 0, 'success': 0, 'total': 0})})))
    # Momentum summary
    momentum_final: Optional[int] = None
    momentum_peak: Optional[int] = None
    momentum_low: Optional[int] = None
    # Top opponents for this game (id -> total_time_sec)
    opponents_time: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    # Opponent appearances (1v1 matchups)
    opponents_appearances: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Line vs Pair appearance counts (forwards perspective)
    line_vs_pair_appearances: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Pair vs Line appearance counts (defense perspective)
    pair_vs_line_appearances: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Time-on-ice vs D-pairs and vs lines (seconds)
    line_vs_pair_time_sec: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    pair_vs_line_time_sec: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    # Trio membership durations and counts
    trio_time_sec: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    trio_shifts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Deployments (zone starts, strengths, faceoff zones)
    deployments_count: int = 0
    deployments_by_zone: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    deployments_by_strength: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    deployments_faceoff_zone: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    deployments_faceoff_shorthand: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class PlayerSeasonAggregate:
    player_id: str = ""
    season: str = ""
    game_type: str = "regular"
    games: Dict[int, PlayerGameMetrics] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Roll-up totals
        toi_values = []
        shift_lens = []
        rests = []
        totals_actions: Dict[str, int] = defaultdict(int)
        totals_success: Dict[str, Dict[str, int]] = defaultdict(lambda: {'success': 0, 'total': 0})
        tzones: Dict[str, int] = defaultdict(int)
        shots_loc: Dict[str, int] = defaultdict(int)
        actions_zone_agg: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'success': 0, 'total': 0, 'sections': defaultdict(lambda: {'count': 0, 'success': 0, 'total': 0})}))
        lpr_total = 0
        pressure_total = 0
        turnovers_total = 0

        entries_c_att = entries_c_succ = entries_d_att = 0
        exits_c_att = exits_c_succ = exits_d_att = 0

        opp_total_time: Dict[str, float] = defaultdict(float)
        opp_total_appearances: Dict[str, int] = defaultdict(int)
        line_vs_pair_total: Dict[str, int] = defaultdict(int)
        pair_vs_line_total: Dict[str, int] = defaultdict(int)
        line_vs_pair_time_total: Dict[str, float] = defaultdict(float)
        pair_vs_line_time_total: Dict[str, float] = defaultdict(float)
        trio_time_total: Dict[str, float] = defaultdict(float)
        trio_shifts_total: Dict[str, int] = defaultdict(int)
        dep_count = 0
        dep_by_zone: Dict[str, int] = defaultdict(int)
        dep_by_strength: Dict[str, int] = defaultdict(int)
        dep_faceoff_zone: Dict[str, int] = defaultdict(int)
        dep_faceoff_sh: Dict[str, int] = defaultdict(int)

        for g in self.games.values():
            if g.toi_game_sec:
                toi_values.append(g.toi_game_sec)
            if g.avg_shift_game_sec is not None:
                shift_lens.append(g.avg_shift_game_sec)
            if g.avg_rest_game_sec is not None:
                rests.append(g.avg_rest_game_sec)
            lpr_total += g.lpr_recoveries
            pressure_total += g.pressure_events
            turnovers_total += g.turnovers
            entries_c_att += g.entries_ctrl_attempts
            entries_c_succ += g.entries_ctrl_success
            entries_d_att += g.entries_dump_attempts
            exits_c_att += g.exits_ctrl_attempts
            exits_c_succ += g.exits_ctrl_success
            exits_d_att += g.exits_dump_attempts
            for a, c in g.actions.items():
                totals_actions[a] += c
            for a, s in g.success_by_action.items():
                totals_success[a]['success'] += s.get('success', 0)
                totals_success[a]['total'] += s.get('total', 0)
            for z, c in g.preferred_zones.items():
                tzones[z] += c
            for sl, c in g.shot_locations.items():
                shots_loc[sl] += c
            # Aggregate actions_by_zone
            for zone, amap in g.actions_by_zone.items():
                for act, meta in amap.items():
                    az = actions_zone_agg[zone][act]
                    az['count'] += int(meta.get('count', 0))
                    az['success'] += int(meta.get('success', 0))
                    az['total'] += int(meta.get('total', 0))
                    for sec, smeta in (meta.get('sections') or {}).items():
                        sz = az['sections'][sec]
                        sz['count'] += int(smeta.get('count', 0))
                        sz['success'] += int(smeta.get('success', 0))
                        sz['total'] += int(smeta.get('total', 0))
            for oid, t in g.opponents_time.items():
                opp_total_time[oid] += t
            for oid, c in g.opponents_appearances.items():
                opp_total_appearances[oid] += c
            for key, c in g.line_vs_pair_appearances.items():
                line_vs_pair_total[key] += c
            for key, c in g.pair_vs_line_appearances.items():
                pair_vs_line_total[key] += c
            for key, secs in g.line_vs_pair_time_sec.items():
                line_vs_pair_time_total[key] += secs
            for key, secs in g.pair_vs_line_time_sec.items():
                pair_vs_line_time_total[key] += secs
            for trio, secs in g.trio_time_sec.items():
                trio_time_total[trio] += secs
            for trio, cnt in g.trio_shifts.items():
                trio_shifts_total[trio] += cnt
            dep_count += g.deployments_count
            for z, c in g.deployments_by_zone.items():
                dep_by_zone[z] += c
            for s, c in g.deployments_by_strength.items():
                dep_by_strength[s] += c
            for z, c in g.deployments_faceoff_zone.items():
                dep_faceoff_zone[z] += c
            for s, c in g.deployments_faceoff_shorthand.items():
                dep_faceoff_sh[s] += c

        # Build success rates
        success_rates = {k: (v['success'] / v['total'] if v['total'] else None) for k, v in totals_success.items()}

        # Top opponents (by total time across games)
        top_opponents = sorted(opp_total_time.items(), key=lambda x: x[1], reverse=True)[:10]

        # Build totals
        totals = {
            'shift_count': sum(g.shift_count for g in self.games.values()),
            'toi_game_sec': sum(toi_values) if toi_values else 0.0,
            'avg_shift_game_sec': (mean(shift_lens) if shift_lens else None),
            'avg_rest_game_sec': (mean(rests) if rests else None),
            'lpr_recoveries': lpr_total,
            'pressure_events': pressure_total,
            'turnovers': turnovers_total,
            'entries': {
                'controlled_attempts': entries_c_att,
                'controlled_success': entries_c_succ,
                'dump_attempts': entries_d_att,
                'controlled_success_rate': (entries_c_succ / entries_c_att) if entries_c_att else None,
            },
            'exits': {
                'controlled_attempts': exits_c_att,
                'controlled_success': exits_c_succ,
                'dump_attempts': exits_d_att,
                'controlled_success_rate': (exits_c_succ / exits_c_att) if exits_c_att else None,
            },
            'actions': dict(totals_actions),
            'success_by_action': totals_success,
            'success_rate_by_action': success_rates,
            'preferred_zones': dict(tzones),
            'preferred_shot_location': dict(shots_loc),
            'actions_by_zone': {z: {a: {
                'count': m['count'],
                'success': m['success'],
                'total': m['total'],
                'sections': {s: dict(v) for s, v in m['sections'].items()}
            } for a, m in amap.items()} for z, amap in actions_zone_agg.items()},
            'top_opponents_by_time': [{'opponent_id': oid, 'total_time_sec': t} for oid, t in top_opponents],
            'opponent_appearances': dict(opp_total_appearances),
            'line_vs_pair_appearances': dict(line_vs_pair_total),
            'pair_vs_line_appearances': dict(pair_vs_line_total),
            'line_vs_pair_time_sec': dict(line_vs_pair_time_total),
            'pair_vs_line_time_sec': dict(pair_vs_line_time_total),
            'trio_time_sec': dict(trio_time_total),
            'trio_shifts': dict(trio_shifts_total),
            'deployments': {
                'count': dep_count,
                'by_zone': dict(dep_by_zone),
                'by_strength': dict(dep_by_strength),
                'faceoff_zone': dict(dep_faceoff_zone),
                'faceoff_shorthand': dict(dep_faceoff_sh),
            },
        }

        # Flatten games to list
        games_list = []
        for gid, g in sorted(self.games.items(), key=lambda kv: kv[0]):
            games_list.append({
                'gameId': gid,
                'gameDate': g.game_date,
                'homeTeam': g.home_team,
                'awayTeam': g.away_team,
                'shift_count': g.shift_count,
                'toi_game_sec': g.toi_game_sec,
                'avg_shift_game_sec': g.avg_shift_game_sec,
                'avg_rest_game_sec': g.avg_rest_game_sec,
                'lpr_recoveries': g.lpr_recoveries,
                'pressure_events': g.pressure_events,
                'turnovers': g.turnovers,
                'entries': {
                    'controlled_attempts': g.entries_ctrl_attempts,
                    'controlled_success': g.entries_ctrl_success,
                    'dump_attempts': g.entries_dump_attempts,
                },
                'exits': {
                    'controlled_attempts': g.exits_ctrl_attempts,
                    'controlled_success': g.exits_ctrl_success,
                    'dump_attempts': g.exits_dump_attempts,
                },
                'actions': dict(g.actions),
                'success_by_action': g.success_by_action,
                'preferred_zones': dict(g.preferred_zones),
                'preferred_shot_location': dict(g.shot_locations),
                'actions_by_zone': {z: {a: {
                    'count': m['count'],
                    'success': m['success'],
                    'total': m['total'],
                    'sections': {s: dict(v) for s, v in m['sections'].items()}
                } for a, m in amap.items()} for z, amap in g.actions_by_zone.items()},
                'momentum': {
                    'final': g.momentum_final,
                    'peak': g.momentum_peak,
                    'low': g.momentum_low,
                },
                'top_opponents_by_time': sorted(
                    [{'opponent_id': oid, 'total_time_sec': t} for oid, t in g.opponents_time.items()],
                    key=lambda x: x['total_time_sec'], reverse=True
                )[:5]
                ,
                'opponent_appearances': dict(g.opponents_appearances),
                'line_vs_pair_appearances': dict(g.line_vs_pair_appearances),
                'pair_vs_line_appearances': dict(g.pair_vs_line_appearances),
                'line_vs_pair_time_sec': dict(g.line_vs_pair_time_sec),
                'pair_vs_line_time_sec': dict(g.pair_vs_line_time_sec),
                'trio_time_sec': dict(g.trio_time_sec),
                'trio_shifts': dict(g.trio_shifts),
                'deployments': {
                    'count': g.deployments_count,
                    'by_zone': dict(g.deployments_by_zone),
                    'by_strength': dict(g.deployments_by_strength),
                    'faceoff_zone': dict(g.deployments_faceoff_zone),
                    'faceoff_shorthand': dict(g.deployments_faceoff_shorthand),
                }
            })

        return {
            'playerId': self.player_id,
            'season': self.season,
            'gameType': self.game_type,
            'lastUpdated': None,
            'totals': totals,
            'games': games_list,
        }


def collect_per_game_metrics(extraction: Dict[str, Any], dpair_min_overlap_sec: float = 3.0) -> Dict[str, PlayerGameMetrics]:
    """Return per-player per-game metrics for a single game extraction JSON."""
    game_id = None
    home_code = None
    away_code = None
    gi = extraction.get('game_info') or {}
    try:
        game_id = int(gi.get('game_id')) if gi.get('game_id') is not None else None
    except Exception:
        game_id = None
    # team codes preferred
    home_code = gi.get('home_team') or gi.get('home_team_name')
    away_code = gi.get('away_team') or gi.get('away_team_name')

    per_player: Dict[str, PlayerGameMetrics] = {}

    # Tendencies → actions, success_by_action, zones, shot locations, entries/exits from events
    pt = extraction.get('player_tendencies') or {}
    for raw_pid, pdata in pt.items():
        pid = norm_id(raw_pid)
        g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
        # Actions
        for a, c in (pdata.get('actions') or {}).items():
            g.actions[a] += int(c)
        # Success
        for a, info in (pdata.get('success_by_action') or {}).items():
            succ = int(info.get('success', 0) or 0)
            tot = int(info.get('total', 0) or 0)
            s = g.success_by_action[a]
            s['success'] += succ
            s['total'] += tot
        # Zones / shots
        for z, c in (pdata.get('preferred_zones') or {}).items():
            g.preferred_zones[z] += int(c)
        for sl, c in (pdata.get('preferred_shot_location') or {}).items():
            g.shot_locations[sl] += int(c)
        # Entries/exits/LPR/Pressure/Turnovers from per-event timeline
        for ev in (pdata.get('events') or []):
            sh = str(ev.get('shorthand')) if ev.get('shorthand') is not None else ''
            outcome_success = str(ev.get('outcome', '')).lower() == 'successful'
            zone_val = ev.get('zone')
            zone_key = str(zone_val).upper() if zone_val is not None else None
            play_sec = ev.get('playSection')
            if zone_key and sh:
                az = g.actions_by_zone[zone_key][sh]
                az['count'] += 1
                # outcome increments
                if ev.get('outcome') is not None:
                    az['total'] += 1
                    if outcome_success:
                        az['success'] += 1
                if play_sec:
                    sz = az['sections'][str(play_sec)]
                    sz['count'] += 1
                    if ev.get('outcome') is not None:
                        sz['total'] += 1
                        if outcome_success:
                            sz['success'] += 1
            if sh in ENTRY_CTRL:
                g.entries_ctrl_attempts += 1
                if outcome_success:
                    g.entries_ctrl_success += 1
            elif sh in ENTRY_DUMP:
                g.entries_dump_attempts += 1
            if sh in EXIT_CTRL:
                g.exits_ctrl_attempts += 1
                if outcome_success:
                    g.exits_ctrl_success += 1
            elif sh in EXIT_DUMP:
                g.exits_dump_attempts += 1
            # LPR / Pressure / Turnovers using shorthand patterns (align with sequence-level sets)
            if ('LPR+' in sh) or sh in {'LPR+ DZ', 'LPR+ NZ', 'LPR+ OZ', 'REB LPR OZ+', 'LPRREB+', 'CONT REB LPR OZ+'}:
                g.lpr_recoveries += 1
            if sh in {'SHOT PRESSURE', 'OZ STICK CHK+', 'DZ STICK CHK+', 'BLOCK OPPOSITION PASS+', 'BLOCK OPPOSITION SHOT+', 'PREVENT RECEPTION DZ'}:
                g.pressure_events += 1
            if ('FAILED PASS TRAJECTORY' in sh) or (sh == 'BLOCK OPPOSITION PASS-'):
                g.turnovers += 1

    # Shifts → shift lengths and rest, per player
    shifts = (extraction.get('player_shifts') or {}).get('shifts') or []
    by_pid: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for sh in shifts:
        pid = norm_id(sh.get('player_id'))
        if not pid:
            continue
        by_pid[pid].append(sh)
    for pid, lst in by_pid.items():
        g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
        g.shift_count += len(lst)
        toi = 0.0
        lens = []
        rests = []
        for sh in lst:
            if sh.get('shift_game_length') is not None:
                val = float(sh['shift_game_length'])
                toi += val
                lens.append(val)
            if sh.get('rest_game_next') is not None:
                rests.append(float(sh['rest_game_next']))
        g.toi_game_sec += toi
        g.avg_shift_game_sec = (mean(lens) if lens else g.avg_shift_game_sec)
        g.avg_rest_game_sec = (mean(rests) if rests else g.avg_rest_game_sec)

    # Momentum → per player
    momentum = extraction.get('shift_momentum') or {}
    for raw_pid, m in momentum.items():
        pid = norm_id(raw_pid)
        g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
        g.momentum_final = int(m.get('final_momentum')) if m.get('final_momentum') is not None else g.momentum_final
        g.momentum_peak = int(m.get('peak_momentum')) if m.get('peak_momentum') is not None else g.momentum_peak
        g.momentum_low = int(m.get('low_momentum')) if m.get('low_momentum') is not None else g.momentum_low

    # Opponents time from matchup_durations: keys "A_vs_B" with total_time
    md = extraction.get('matchup_durations') or {}
    for key, v in md.items():
        if not isinstance(key, str) or '_vs_' not in key:
            continue
        a, b = key.split('_vs_', 1)
        a = norm_id(a)
        b = norm_id(b)
        t = float(v.get('total_time') or 0.0)
        if a:
            g = per_player.setdefault(a, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_time[b] += t
        if b:
            g = per_player.setdefault(b, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_time[a] += t

    # Opponent appearances from individual_matchups (F_vs_F, F_vs_D, D_vs_D)
    im = extraction.get('individual_matchups') or {}
    for key, mapping in (im.get('F_vs_F') or {}).items():
        # key like "A_vs_B" -> count
        if not isinstance(key, str) or '_vs_' not in key:
            continue
        a, b = key.split('_vs_', 1)
        a = norm_id(a); b = norm_id(b)
        c = int(mapping)
        if a:
            g = per_player.setdefault(a, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[b] += c
        if b:
            g = per_player.setdefault(b, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[a] += c
    for key, c in (im.get('F_vs_D') or {}).items():
        if not isinstance(key, str) or '_vs_' not in key:
            continue
        a, b = key.split('_vs_', 1)
        a = norm_id(a); b = norm_id(b)
        c = int(c)
        if a:
            g = per_player.setdefault(a, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[b] += c
        if b:
            g = per_player.setdefault(b, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[a] += c
    for key, c in (im.get('D_vs_D') or {}).items():
        if not isinstance(key, str) or '_vs_' not in key:
            continue
        a, b = key.split('_vs_', 1)
        a = norm_id(a); b = norm_id(b)
        c = int(c)
        if a:
            g = per_player.setdefault(a, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[b] += c
        if b:
            g = per_player.setdefault(b, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.opponents_appearances[a] += c

    # Line vs D-Pair appearances (per-player, counted per shift exposure not per trio variant)
    # Strategy: derive opponent D-pair timeline from line_rotation_sequence; then for each player's shift,
    # count each distinct opposing D-pair that overlapped that shift by at least `dpair_min_overlap_sec` seconds.
    # Also accumulate overlap time in seconds per pair for potential downstream use.
    try:
        lrs = extraction.get('line_rotation_sequence') or {}
        info = extraction.get('game_info') or {}
        # Build ordered D-pair segments for both sides
        def build_pair_segments(side: str) -> List[tuple]:
            seq = (lrs.get(side) or {}).get('defense') or []
            # sort by start time
            seq_sorted = sorted([x for x in seq if x and x.get('group') and x.get('start_game_time') is not None], key=lambda r: float(r['start_game_time']))
            # determine game end time from last available player_shifts or last event
            last_time = None
            if extraction.get('player_shifts') and (extraction['player_shifts'].get('shifts')):
                for sh in extraction['player_shifts']['shifts']:
                    if sh.get('end_game_time') is not None:
                        t = float(sh['end_game_time'])
                        last_time = t if (last_time is None or t > last_time) else last_time
            if last_time is None and not (extraction.get('shift_momentum') is None):
                # fallback: max of momentum keys that might carry timing; else leave None and skip
                pass
            segments: List[tuple] = []  # (start,end, (id1,id2))
            for i, r in enumerate(seq_sorted):
                s = float(r['start_game_time'])
                e = float(seq_sorted[i+1]['start_game_time']) if i+1 < len(seq_sorted) else (last_time if last_time is not None else s)
                ids = tuple(sorted([norm_id(x) for x in (r.get('group') or [])]))
                if len(ids) == 2 and e > s:
                    segments.append((s, e, ids))
            return segments

        home_pair_segments = build_pair_segments('home')
        away_pair_segments = build_pair_segments('away')

        # Build forward-trio segments for both sides for D-vs-Line exposures
        def build_line_segments(side: str) -> List[tuple]:
            seq = (lrs.get(side) or {}).get('forwards') or []
            seq_sorted = sorted([x for x in seq if x and x.get('group') and x.get('start_game_time') is not None], key=lambda r: float(r['start_game_time']))
            last_time = None
            if extraction.get('player_shifts') and (extraction['player_shifts'].get('shifts')):
                for sh in extraction['player_shifts']['shifts']:
                    if sh.get('end_game_time') is not None:
                        t = float(sh['end_game_time'])
                        last_time = t if (last_time is None or t > last_time) else last_time
            segments: List[tuple] = []  # (start,end,(id1,id2,id3))
            for i, r in enumerate(seq_sorted):
                s = float(r['start_game_time'])
                e = float(seq_sorted[i+1]['start_game_time']) if i+1 < len(seq_sorted) else (last_time if last_time is not None else s)
                ids = tuple(sorted([norm_id(x) for x in (r.get('group') or [])]))
                if len(ids) == 3 and e > s:
                    segments.append((s, e, ids))
            return segments

        home_line_segments = build_line_segments('home')
        away_line_segments = build_line_segments('away')

        # Quick helper to aggregate exposures into per_player metrics
        def add_exposures_for_player(pid: str, team_side: str, s_start: float, s_end: float):
            if s_start is None or s_end is None or s_end <= s_start:
                return
            segments = away_pair_segments if team_side == 'home' else home_pair_segments
            if not segments:
                return
            seen_this_shift: set = set()
            for seg_start, seg_end, pair_ids in segments:
                # overlap of segment with shift
                ovl = min(s_end, seg_end) - max(s_start, seg_start)
                if ovl > 0:
                    # accumulate overlap time regardless of threshold
                    key = str(tuple(pair_ids))
                    g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                    g.line_vs_pair_time_sec[key] += float(ovl)
                if ovl >= dpair_min_overlap_sec:
                    key = str(tuple(pair_ids))
                    seen_this_shift.add(key)
                    g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                    g.line_vs_pair_appearances[key] += 0  # ensure key exists before final add
            # finalize once per shift
            if seen_this_shift:
                g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                for key in seen_this_shift:
                    g.line_vs_pair_appearances[key] += 1

        # For defensemen: accumulate pair_vs_line_time_sec using forward-trio segments on the opponent side.
        def add_d_vs_line_exposures_for_player(pid: str, team_side: str, s_start: float, s_end: float):
            if s_start is None or s_end is None or s_end <= s_start:
                return
            segments = away_line_segments if team_side == 'home' else home_line_segments
            if not segments:
                return
            seen: set = set()
            for seg_start, seg_end, trio_ids in segments:
                ovl = min(s_end, seg_end) - max(s_start, seg_start)
                if ovl > 0:
                    key = str(tuple(trio_ids))
                    g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                    g.pair_vs_line_time_sec[key] += float(ovl)
                if ovl >= dpair_min_overlap_sec:
                    key = str(tuple(trio_ids))
                    seen.add(key)
            if seen:
                g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                for key in seen:
                    g.pair_vs_line_appearances[key] += 1

        # Walk through player shifts and accumulate dpair exposures per shift
        psh = (extraction.get('player_shifts') or {}).get('shifts') or []
        for sh in psh:
            pid = norm_id(sh.get('player_id'))
            if not pid:
                continue
            s_start = sh.get('start_game_time')
            s_end = sh.get('end_game_time')
            team_side = sh.get('team_side')  # 'home' or 'away'
            if s_start is None or s_end is None or not team_side:
                continue
            add_exposures_for_player(pid, team_side, float(s_start), float(s_end))
            add_d_vs_line_exposures_for_player(pid, team_side, float(s_start), float(s_end))
    except Exception:
        # Fallback to legacy aggregation from precomputed line_vs_dpair counts if anything goes wrong
        lvp = extraction.get('line_vs_dpair') or {}
        for key, cnt in lvp.items():
            try:
                if '_vs_' not in key:
                    continue
                a_str, b_str = key.split('_vs_', 1)
                def parse_tuple(s: str) -> List[str]:
                    s = s.strip()
                    if s.startswith('(') and s.endswith(')'):
                        inner = s[1:-1]
                        parts = [p.strip().strip("'\"") for p in inner.split(',') if p.strip()]
                        return [norm_id(p) for p in parts]
                    return [norm_id(x) for x in s.split(',') if x.strip()]
                line = parse_tuple(a_str)
                pair = parse_tuple(b_str)
            except Exception:
                continue
            cnt = int(cnt)
            for pid in line:
                g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                g.line_vs_pair_appearances[str(tuple(pair))] += cnt
            for pid in pair:
                g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
                g.pair_vs_line_appearances[str(tuple(line))] += cnt

    # Trio rotation pattern durations per player (forward-only)
    rotations = extraction.get('rotation_patterns') or {}
    for combo_key, info in rotations.items():
        # combo_key like "TeamName_('id1','id2','id3')"
        if "_(" not in combo_key or not isinstance(info, dict):
            continue
        trio_part = combo_key.split("_(", 1)[1]
        trio_str = '(' + trio_part  # restore leading '('
        if trio_str.endswith(')'):
            pass

        # Compute total trio time robustly:
        # 1) Prefer exact per-period sum if available
        # 2) Fallback to avg_shift_length * total_shifts
        # 3) Last resort: sum of (possibly truncated) shift_pattern
        total_time = 0.0
        try:
            per_period = info.get('per_period') or {}
            if isinstance(per_period, dict) and per_period:
                total_time = float(sum(float(v.get('total_time') or 0.0) for v in per_period.values()))
        except Exception:
            # ignore and try fallbacks
            total_time = 0.0
        if not total_time:
            try:
                avg_len = float(info.get('avg_shift_length') or 0.0)
                tsh = int(info.get('total_shifts') or 0)
                est = avg_len * tsh
                if est > 0:
                    total_time = float(est)
            except Exception:
                pass
        if not total_time:
            durations = info.get('shift_pattern') or []
            try:
                total_time = float(sum(durations)) if durations else 0.0
            except Exception:
                total_time = 0.0

        # Parse ids from trio_str
        inner = trio_str.strip()[1:-1]
        ids = [norm_id(p.strip().strip("'\"")) for p in inner.split(',') if p.strip()]
        trio_key = str(tuple(ids))
        for pid in ids:
            g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.trio_time_sec[trio_key] += total_time
            g.trio_shifts[trio_key] += int(info.get('total_shifts') or 0)

    # Deployments per player
    dep_res = extraction.get('whistle_deployments') or {}
    for d in dep_res.get('deployments', []) if isinstance(dep_res, dict) else []:
        strength = d.get('strength') or ''
        home_zone = d.get('home_zone') or None
        away_zone = d.get('away_zone') or None
        fz = d.get('faceoff_zone') or None
        fsh = d.get('faceoff_shorthand') or None
        # Enumerate players on both sides
        home_players = list(d.get('home_forwards') or []) + list(d.get('home_defense') or [])
        away_players = list(d.get('away_forwards') or []) + list(d.get('away_defense') or [])
        for pid in [norm_id(x) for x in home_players]:
            g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.deployments_count += 1
            if home_zone:
                g.deployments_by_zone[str(home_zone)] += 1
            if strength:
                g.deployments_by_strength[str(strength)] += 1
            if fz:
                g.deployments_faceoff_zone[str(fz)] += 1
            if fsh:
                g.deployments_faceoff_shorthand[str(fsh)] += 1
        for pid in [norm_id(x) for x in away_players]:
            g = per_player.setdefault(pid, PlayerGameMetrics(game_id=game_id, home_team=home_code, away_team=away_code))
            g.deployments_count += 1
            if away_zone:
                g.deployments_by_zone[str(away_zone)] += 1
            if strength:
                g.deployments_by_strength[str(strength)] += 1
            if fz:
                g.deployments_faceoff_zone[str(fz)] += 1
            if fsh:
                g.deployments_faceoff_shorthand[str(fsh)] += 1

    return per_player


def run_extractor_on_csv(csv_path: Path, output_dir: Path) -> Optional[Path]:
    """Run ComprehensiveHockeyExtractor on the given CSV, saving to output_dir.
    Returns path to the comprehensive JSON if success, else None.
    """
    try:
        # Import locally to avoid heavy import if not used
        import sys
        sys.path.append(str(Path(__file__).resolve().parent))  # scripts/
        from comprehensive_hockey_extraction import ComprehensiveHockeyExtractor  # type: ignore

        extractor = ComprehensiveHockeyExtractor(str(csv_path))
        extractor.run_complete_extraction()
        extractor.save_results(str(output_dir))
        out_file = output_dir / f"{csv_path.stem}_comprehensive_metrics.json"
        if out_file.exists():
            return out_file
        return None
    except Exception as e:
        print(f"Extractor failed for {csv_path}: {e}")
        return None


def aggregate_for_team(team_abbrev: str, seasons: List[str], run_extractor: bool = False, clean: bool = False, dpair_min_overlap_sec: float = 3.0) -> None:
    # Search both processed analytics and raw mtl_play_by_play folders
    base_dirs = [
        Path('data/processed/analytics/nhl_play_by_play') / team_abbrev,
        Path('data') / 'mtl_play_by_play',
    ]
    extracted_dir = Path('data/processed/extracted_metrics')
    profiles_base = Path('data/processed/player_profiles')
    advanced_base = profiles_base / 'advanced_metrics'

    ensure_dir(extracted_dir)
    ensure_dir(advanced_base)

    # Optional cleanup of stale advanced files for requested seasons
    if clean:
        adv_team_dir = advanced_base
        if adv_team_dir.exists():
            for pdir in adv_team_dir.iterdir():
                if not pdir.is_dir():
                    continue
                for season in seasons:
                    stale = pdir / f"{season}_regular_advanced.json"
                    if stale.exists():
                        try:
                            stale.unlink()
                        except Exception:
                            pass

    # Map playerId -> season -> aggregate
    aggregates: Dict[Tuple[str, str], PlayerSeasonAggregate] = {}

    # Process each season
    for base_pbp in base_dirs:
        for season_folder in base_pbp.glob('*'):
            if not season_folder.is_dir():
                continue
            # Convert '2024-2025' to '20242025'
            season_raw = season_folder.name
            if len(season_raw) == 9 and season_raw[4] == '-':
                season_str = season_raw.replace('-', '')
            else:
                season_str = None
            if seasons and season_str not in seasons:
                continue

            for csv_path in season_folder.glob('*.csv'):
                # Ensure extractor output exists (optional run)
                out_json = extracted_dir / f"{csv_path.stem}_comprehensive_metrics.json"
                if run_extractor:
                    if (not out_json.exists()):
                        print(f"Running extractor for: {csv_path}")
                        result = run_extractor_on_csv(csv_path, extracted_dir)
                        if not result:
                            print(f"Skipping {csv_path}, extractor failed")
                            continue
                if not out_json.exists():
                    # Try to find an existing file by stem even if directories differ
                    candidates = list(extracted_dir.glob(f"{csv_path.stem}_comprehensive_metrics.json"))
                    if not candidates:
                        print(f"No extraction JSON found for {csv_path.stem}, skipping")
                        continue
                    out_json = candidates[0]

                # Load extraction JSON
                try:
                    with open(out_json, 'r') as f:
                        extraction = json.load(f)
                except Exception as e:
                    print(f"Failed to read {out_json}: {e}")
                    continue

                # Per-game per-player metrics
                per_player = collect_per_game_metrics(extraction, dpair_min_overlap_sec=dpair_min_overlap_sec)

                # Determine season string (prefer season token from filename, fallback to directory)
                season_from_file = parse_season_from_name(csv_path.stem) or season_str or ''
                game_type = 'regular'

                # Attach game date from filename if available (YYYY-MM-DD)
                parts = csv_path.stem.split('-')
                game_date_token = parts[1] if len(parts) > 1 else ''
                game_date = None
                if game_date_token.isdigit() and len(game_date_token) == 8:
                    game_date = f"{game_date_token[0:4]}-{game_date_token[4:6]}-{game_date_token[6:8]}"
                if game_date:
                    for pg in per_player.values():
                        pg.game_date = game_date

                # Accumulate into season aggregate
                for pid, pg in per_player.items():
                    key = (pid, season_from_file)
                    ag = aggregates.get(key)
                    if ag is None:
                        ag = PlayerSeasonAggregate(player_id=pid, season=season_from_file, game_type=game_type)
                        aggregates[key] = ag
                    # Sanity: skip if we somehow failed season detection
                    if not season_from_file:
                        continue
                    if pg.game_id is not None:
                        ag.games[pg.game_id] = pg

    # Write out season aggregates
    for (pid, season_str), ag in aggregates.items():
        out_dir = advanced_base / pid
        ensure_dir(out_dir)
        out_file = out_dir / f"{season_str}_regular_advanced.json"
        # Validate season consistency: all games should fall within season years
        try:
            if not ag.games:
                continue
            with open(out_file, 'w') as f:
                json.dump(ag.to_dict(), f, indent=2)
            print(f"Saved advanced metrics: {out_file}")
        except Exception as e:
            print(f"Failed to save {out_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Aggregate advanced player metrics by game and season.')
    parser.add_argument('--teams', type=str, default='MTL', help='Comma-separated team abbreviations to process (default: MTL)')
    parser.add_argument('--seasons', type=str, default='20242025,20252026', help='Comma-separated seasons (YYYYYYYY) to include')
    parser.add_argument('--run-extractor', action='store_true', help='Run the comprehensive extractor for missing CSVs before aggregation')
    parser.add_argument('--clean', action='store_true', help='Delete existing advanced files for the target seasons before writing')
    parser.add_argument('--dpair-min-overlap-sec', type=float, default=3.0, help='Minimum overlap seconds to count a D-pair exposure within a player shift (default: 3.0s)')

    args = parser.parse_args()

    teams = [t.strip().upper() for t in args.teams.split(',') if t.strip()]
    seasons = [s.strip() for s in args.seasons.split(',') if s.strip()]

    for team in teams:
        print(f"Processing team {team} for seasons {seasons}...")
        aggregate_for_team(
            team,
            seasons,
            run_extractor=args.run_extractor,
            clean=args.clean,
            dpair_min_overlap_sec=args.dpair_min_overlap_sec,
        )


if __name__ == '__main__':
    main()
