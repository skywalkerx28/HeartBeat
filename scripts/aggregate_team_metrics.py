#!/usr/bin/env python3
"""
Aggregate advanced, per-team metrics from comprehensive extraction outputs.

What this produces
------------------
- Per-game team metrics derived from whistle-to-whistle sequence summaries
  (zone time, possession, entries/exits, shot attempts, on/missed/blocked,
   passes, LPR recoveries, pressure events, turnovers)
- Derived rates such as Corsi For %, offensive-zone share, possession share
- Strength splits (e.g., 5v5, 5v4) when present in deployment metadata
- Deployment distributions (faceoff zones, strengths)
- Pass-network summary (nodes, edges, avg degree) per game (when available)

Output layout
-------------
data/processed/team_profiles/advanced_metrics/<TEAM>/<SEASON>_team_advanced.json

Usage
-----
    python scripts/aggregate_team_metrics.py \
      --teams MTL,FLA \
      --seasons 20242025 \
      --run-extractor

Notes
-----
- We consider playsequence CSVs located under
  data/processed/analytics/nhl_play_by_play/<TEAM>/<YYYY-YYYY>/*.csv
- We expect comprehensive extraction JSONs in data/processed/extracted_metrics.
- If --run-extractor is supplied, missing JSONs will be produced using
  ComprehensiveHockeyExtractor directly.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# ------------------------------
# Helpers
# ------------------------------

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def parse_season_from_name(stem: str) -> Optional[str]:
    """Extract YYYYYYYY season from playsequence filename.
    Expected format: playsequence-YYYYMMDD-NHL-<match>-YYYYYYYY-<gameId>
    Returns the second-to-last token if it is an 8-digit number; otherwise the
    last 8-digit token found when scanning from right to left.
    """
    parts = stem.split('-')
    if len(parts) >= 2:
        cand = parts[-2]
        if cand.isdigit() and len(cand) == 8:
            return cand
    for p in reversed(parts):
        if len(p) == 8 and p.isdigit():
            return p
    return None


def run_extractor_on_csv(csv_path: Path, output_dir: Path) -> Optional[Path]:
    """Run ComprehensiveHockeyExtractor for a CSV and save outputs to output_dir.
    Returns the comprehensive metrics JSON path if successful.
    """
    try:
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


# ------------------------------
# Data containers
# ------------------------------

@dataclass
class TeamGameMetrics:
    game_id: Optional[int] = None
    game_date: Optional[str] = None
    season: Optional[str] = None
    team_code: Optional[str] = None
    opponent_code: Optional[str] = None
    home_away: Optional[str] = None  # 'home' | 'away'
    # Whether game went to OT/SO
    went_to_ot: bool = False

    # Raw totals from sequences (for team perspective)
    zone_time: Dict[str, float] = field(default_factory=lambda: {'oz': 0.0, 'nz': 0.0, 'dz': 0.0})
    opp_zone_time: Dict[str, float] = field(default_factory=lambda: {'oz': 0.0, 'nz': 0.0, 'dz': 0.0})
    possession_time: float = 0.0
    opp_possession_time: float = 0.0
    entries: Dict[str, int] = field(default_factory=lambda: {
        'controlled_attempts': 0,
        'controlled_success': 0,
        'dump_attempts': 0,
    })
    exits: Dict[str, int] = field(default_factory=lambda: {
        'controlled_attempts': 0,
        'controlled_success': 0,
        'dump_attempts': 0,
    })
    shots_for_on: int = 0
    shots_for_missed: int = 0
    shots_for_blocked: int = 0
    shots_for_total: int = 0
    shots_against_total: int = 0
    passes: int = 0
    lpr_recoveries: int = 0
    pressure_events: int = 0
    turnovers: int = 0

    # Opponent per-game counts (for comparison overlays)
    opp_passes: int = 0
    opp_lpr_recoveries: int = 0
    opp_pressure_events: int = 0
    opp_turnovers: int = 0

    # Final score (totals for this game)
    goals_for: int = 0
    goals_against: int = 0

    # Splits by reported deployment strength (e.g., '5v5', '5v4')
    by_strength: Dict[str, Dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: {
        'shots_for_total': 0.0,
        'shots_against_total': 0.0,
        'oz_time': 0.0,
        'dz_time': 0.0,
        'nz_time': 0.0,
        'possession_time': 0.0,
        'entries_c_att': 0.0,
        'entries_d_att': 0.0,
        'entries_c_succ': 0.0,
        'exits_c_att': 0.0,
        'exits_d_att': 0.0,
        'exits_c_succ': 0.0,
    }))

    # Deployment distributions (from whistle deployments)
    deployments_by_zone: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    deployments_by_strength: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Pass network (when available)
    pass_network: Optional[Dict[str, float]] = None  # {'nodes':..., 'edges':..., 'avg_degree':...}

    def to_dict(self) -> Dict[str, Any]:
        # Derived shares
        total_zone = sum(self.zone_time.values())
        off_share = (self.zone_time.get('oz', 0.0) / total_zone) if total_zone else None
        nz_share = (self.zone_time.get('nz', 0.0) / total_zone) if total_zone else None
        def_share = (self.zone_time.get('dz', 0.0) / total_zone) if total_zone else None

        # Corsi For % based on shot attempts (on+missed+blocked)
        cf = float(self.shots_for_total)
        ca = float(self.shots_against_total)
        cf_pct = (cf / (cf + ca)) if (cf + ca) > 0 else None

        # Possession share
        poss_total = float(self.possession_time + self.opp_possession_time)
        poss_share = (float(self.possession_time) / poss_total) if poss_total > 0 else None

        # Entry/Exit controlled success rate (success over attempts)
        e_ctrl_att = int(self.entries.get('controlled_attempts', 0) or 0)
        e_ctrl_succ = int(self.entries.get('controlled_success', 0) or 0)
        x_ctrl_att = int(self.exits.get('controlled_attempts', 0) or 0)
        x_dump_att = int(self.exits.get('dump_attempts', 0) or 0)
        entry_ctrl_rate = (e_ctrl_succ / e_ctrl_att) if e_ctrl_att > 0 else None
        # Data has no explicit failed-controlled-exit rows; approximate by
        # controlled share of exits (controlled vs controlled+dump)
        x_denom = x_ctrl_att + x_dump_att
        exit_ctrl_rate = (x_ctrl_att / x_denom) if x_denom > 0 else None

        # Strength splits derived rates
        strength_splits: Dict[str, Dict[str, Optional[float] | float]] = {}
        for s, m in self.by_strength.items():
            s_cf = float(m['shots_for_total'])
            s_ca = float(m['shots_against_total'])
            s_total_zone = float(m['oz_time'] + m['dz_time'] + m['nz_time'])
            s_e_ctrl = float(m.get('entries_c_att', 0.0))
            s_e_succ = float(m.get('entries_c_succ', 0.0))
            s_x_ctrl = float(m.get('exits_c_att', 0.0))
            s_x_dump = float(m.get('exits_d_att', 0.0))
            strength_splits[s] = {
                'cf': s_cf,
                'ca': s_ca,
                'cf_pct': (s_cf / (s_cf + s_ca)) if (s_cf + s_ca) > 0 else None,
                'oz_share': (m['oz_time'] / s_total_zone) if s_total_zone > 0 else None,
                'possession_time': m['possession_time'],
                'entry_ctrl_rate': (s_e_succ / s_e_ctrl) if s_e_ctrl > 0 else None,
                'exit_ctrl_rate': (s_x_ctrl / (s_x_ctrl + s_x_dump)) if (s_x_ctrl + s_x_dump) > 0 else None,
            }

        return {
            'gameId': self.game_id,
            'gameDate': self.game_date,
            'season': self.season,
            'team': self.team_code,
            'opponent': self.opponent_code,
            'homeAway': self.home_away,
            'went_to_ot': self.went_to_ot,
            'zone_time': dict(self.zone_time),
            'possession_time': self.possession_time,
            'entries': dict(self.entries),
            'exits': dict(self.exits),
            'shots_for': {
                'on': self.shots_for_on,
                'missed': self.shots_for_missed,
                'blocked': self.shots_for_blocked,
                'total': self.shots_for_total,
            },
            'shots_against_total': self.shots_against_total,
            'passes': self.passes,
            'lpr_recoveries': self.lpr_recoveries,
            'pressure_events': self.pressure_events,
            'turnovers': self.turnovers,
            # Opponent counts for overlay comparisons
            'opponent_passes': self.opp_passes,
            'opponent_lpr_recoveries': self.opp_lpr_recoveries,
            'opponent_pressure_events': self.opp_pressure_events,
            'opponent_turnovers': self.opp_turnovers,
            'goals_for': int(self.goals_for or 0),
            'goals_against': int(self.goals_against or 0),
            'derived': {
                'corsi_for': cf,
                'corsi_against': ca,
                'corsi_for_pct': cf_pct,
                'offensive_zone_share': off_share,
                'neutral_zone_share': nz_share,
                'defensive_zone_share': def_share,
                'possession_share': poss_share,
                'entry_controlled_success_rate': entry_ctrl_rate,
                'exit_controlled_success_rate': exit_ctrl_rate,
            },
            'strength_splits': strength_splits,
            'deployments': {
                'by_zone': dict(self.deployments_by_zone),
                'by_strength': dict(self.deployments_by_strength),
            },
            'pass_network': self.pass_network,
        }


@dataclass
class TeamSeasonAggregate:
    team_code: str = ''
    season: str = ''  # YYYYYYYY
    game_type: str = 'regular'
    games: Dict[int, TeamGameMetrics] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Totals across games
        zone = defaultdict(float)
        opp_zone = defaultdict(float)
        entries = defaultdict(int)
        exits = defaultdict(int)
        shots_for = {'on': 0, 'missed': 0, 'blocked': 0, 'total': 0}
        shots_against_total = 0
        passes = 0
        lpr = 0
        pressure = 0
        turnovers = 0
        # Opponent totals (season)
        opp_passes = 0
        opp_lpr = 0
        opp_pressure = 0
        opp_turnovers = 0
        poss = 0.0
        opp_poss = 0.0
        by_strength: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        dep_zone: Dict[str, int] = defaultdict(int)
        dep_strength: Dict[str, int] = defaultdict(int)

        net_nodes: List[float] = []
        net_edges: List[float] = []
        net_degree: List[float] = []
        goals_for_sum = 0
        goals_against_sum = 0

        for g in self.games.values():
            for k, v in g.zone_time.items():
                zone[k] += float(v or 0.0)
            for k, v in g.opp_zone_time.items():
                opp_zone[k] += float(v or 0.0)
            poss += float(g.possession_time or 0.0)
            opp_poss += float(g.opp_possession_time or 0.0)
            for k, v in g.entries.items():
                entries[k] += int(v or 0)
            for k, v in g.exits.items():
                exits[k] += int(v or 0)
            shots_for['on'] += int(g.shots_for_on)
            shots_for['missed'] += int(g.shots_for_missed)
            shots_for['blocked'] += int(g.shots_for_blocked)
            shots_for['total'] += int(g.shots_for_total)
            shots_against_total += int(g.shots_against_total)
            passes += int(g.passes)
            lpr += int(g.lpr_recoveries)
            pressure += int(g.pressure_events)
            turnovers += int(g.turnovers)
            # Opponent season sums
            opp_passes += int(getattr(g, 'opp_passes', 0))
            opp_lpr += int(getattr(g, 'opp_lpr_recoveries', 0))
            opp_pressure += int(getattr(g, 'opp_pressure_events', 0))
            opp_turnovers += int(getattr(g, 'opp_turnovers', 0))
            for s, m in g.by_strength.items():
                bs = by_strength[s]
                for mk, mv in m.items():
                    bs[mk] = bs.get(mk, 0.0) + float(mv or 0.0)
            for k, v in g.deployments_by_zone.items():
                dep_zone[k] += int(v)
            for k, v in g.deployments_by_strength.items():
                dep_strength[k] += int(v)
            if g.pass_network:
                if g.pass_network.get('nodes') is not None:
                    net_nodes.append(float(g.pass_network['nodes']))
                if g.pass_network.get('edges') is not None:
                    net_edges.append(float(g.pass_network['edges']))
                if g.pass_network.get('avg_degree') is not None:
                    net_degree.append(float(g.pass_network['avg_degree']))
            # accumulate final score
            try:
                goals_for_sum += int(getattr(g, 'goals_for', 0) or 0)
                goals_against_sum += int(getattr(g, 'goals_against', 0) or 0)
            except Exception:
                pass

        # Derived metrics
        cf = float(shots_for['total'])
        ca = float(shots_against_total)
        cf_pct = (cf / (cf + ca)) if (cf + ca) > 0 else None
        z_total = float(zone['oz'] + zone['dz'] + zone['nz'])
        oz_share = (zone['oz'] / z_total) if z_total > 0 else None
        poss_total = float(poss + opp_poss)
        poss_share = (poss / poss_total) if poss_total > 0 else None
        e_att = entries['controlled_attempts']
        e_succ = entries['controlled_success']
        x_att = exits['controlled_attempts']
        x_succ = exits['controlled_success']

        by_strength_rates: Dict[str, Dict[str, Optional[float] | float]] = {}
        for s, m in by_strength.items():
            s_cf = float(m.get('shots_for_total', 0.0))
            s_ca = float(m.get('shots_against_total', 0.0))
            s_z = float(m.get('oz_time', 0.0) + m.get('dz_time', 0.0) + m.get('nz_time', 0.0))
            by_strength_rates[s] = {
                'cf': s_cf,
                'ca': s_ca,
                'cf_pct': (s_cf / (s_cf + s_ca)) if (s_cf + s_ca) > 0 else None,
                'oz_share': (m.get('oz_time', 0.0) / s_z) if s_z > 0 else None,
                'entry_ctrl_rate': (m.get('entries_c_succ', 0.0) / m.get('entries_c_att', 0.0)) if m.get('entries_c_att', 0.0) > 0 else None,
                'exit_ctrl_rate': (m.get('exits_c_succ', 0.0) / m.get('exits_c_att', 0.0)) if m.get('exits_c_att', 0.0) > 0 else None,
            }

        # Opponent head-to-head summary across games
        opp_summary: Dict[str, Dict[str, Any]] = {}
        for gid, g in sorted(self.games.items(), key=lambda kv: kv[0]):
            opp = str(g.opponent_code or '?')
            row = opp_summary.setdefault(opp, {
                'gamesPlayed': 0,
                'wins': 0,
                'losses': 0,
                'otLosses': 0,
                'goalsFor': 0,
                'goalsAgainst': 0,
                'lastGame': None,
            })
            row['gamesPlayed'] += 1
            gf = int(getattr(g, 'goals_for', 0) or 0)
            ga = int(getattr(g, 'goals_against', 0) or 0)
            row['goalsFor'] += gf
            row['goalsAgainst'] += ga
            if gf > ga:
                row['wins'] += 1
            elif gf < ga:
                if getattr(g, 'went_to_ot', False):
                    row['otLosses'] += 1
                else:
                    row['losses'] += 1
            d = getattr(g, 'game_date', None)
            if d:
                lg = row.get('lastGame')
                if not lg or str(d) > str(lg):
                    row['lastGame'] = d

        return {
            'team': self.team_code,
            'season': self.season,
            'gameType': self.game_type,
            'lastUpdated': None,
            'totals': {
                'zone_time': dict(zone),
                'possession_time': poss,
                'entries': dict(entries),
                'exits': dict(exits),
                'shots_for': shots_for,
                'shots_against_total': shots_against_total,
                'passes': passes,
                'lpr_recoveries': lpr,
                'pressure_events': pressure,
                'turnovers': turnovers,
                'goals_for': goals_for_sum,
                'goals_against': goals_against_sum,
                # Opponent season totals for overlay summaries
                'opponent_passes': opp_passes,
                'opponent_lpr_recoveries': opp_lpr,
                'opponent_pressure_events': opp_pressure,
                'opponent_turnovers': opp_turnovers,
                'derived': {
                    'corsi_for': cf,
                    'corsi_against': ca,
                    'corsi_for_pct': cf_pct,
                    'offensive_zone_share': oz_share,
                    'possession_share': poss_share,
                    'entry_controlled_success_rate': (e_succ / e_att) if e_att else None,
                    'exit_controlled_success_rate': (x_succ / x_att) if x_att else None,
                },
                'strength_splits': by_strength_rates,
                'deployments': {
                    'by_zone': dict(dep_zone),
                    'by_strength': dict(dep_strength),
                },
                'pass_network_avg': {
                    'nodes': mean(net_nodes) if net_nodes else None,
                    'edges': mean(net_edges) if net_edges else None,
                    'avg_degree': mean(net_degree) if net_degree else None,
                },
                'opponents': opp_summary,
            },
            'games': [g.to_dict() for _, g in sorted(self.games.items(), key=lambda kv: kv[0])],
        }


# ------------------------------
# Aggregation logic
# ------------------------------

def _sum_dict(a: Dict[str, float], b: Dict[str, float], keys: List[str]) -> None:
    for k in keys:
        a[k] = float(a.get(k, 0.0)) + float(b.get(k, 0.0))


def collect_team_game_metrics(extraction: Dict[str, Any], team_code: str, game_date: Optional[str], season: Optional[str]) -> Optional[TeamGameMetrics]:
    info = (extraction or {}).get('game_info') or {}
    home_code = info.get('home_team')
    away_code = info.get('away_team')
    team_name_home = info.get('home_team_name')
    team_name_away = info.get('away_team_name')

    if not home_code or not away_code:
        return None
    if team_code not in (home_code, away_code):
        # Not this team's game
        return None

    side = 'home' if team_code == home_code else 'away'
    opp_side = 'away' if side == 'home' else 'home'
    opponent_code = away_code if side == 'home' else home_code

    gm = TeamGameMetrics(
        game_id=info.get('game_id'),
        game_date=game_date,
        season=season,
        team_code=team_code,
        opponent_code=opponent_code,
        home_away=side,
    )

    # Detect OT/SO presence (period >= 4 or sequences ending in >= 4)
    try:
        pos = (extraction.get('period_openers') or [])
        if any(int(p.get('period') or 0) >= 4 for p in pos):
            gm.went_to_ot = True
        else:
            ws_tmp = (extraction.get('whistle_sequences') or {}).get('sequences') or []
            if any(int(s.get('end_period') or 0) >= 4 for s in ws_tmp):
                gm.went_to_ot = True
    except Exception:
        pass

    # Whistle-to-whistle sequences
    ws = (extraction.get('whistle_sequences') or {}).get('sequences') or []
    for seq in ws:
        t = (seq.get(side) or {})
        o = (seq.get(opp_side) or {})
        # Zone time
        _sum_dict(gm.zone_time, t.get('zone_time') or {}, ['oz', 'nz', 'dz'])
        _sum_dict(gm.opp_zone_time, o.get('zone_time') or {}, ['oz', 'nz', 'dz'])
        # Possession time
        gm.possession_time += float(t.get('possession_time') or 0.0)
        gm.opp_possession_time += float(o.get('possession_time') or 0.0)
        # Entries
        et = t.get('entries') or {}
        gm.entries['controlled_attempts'] += int(et.get('controlled_attempts') or 0)
        gm.entries['controlled_success'] += int(et.get('controlled_success') or 0)
        gm.entries['dump_attempts'] += int(et.get('dump_attempts') or 0)
        # Exits
        ex = t.get('exits') or {}
        gm.exits['controlled_attempts'] += int(ex.get('controlled_attempts') or 0)
        gm.exits['controlled_success'] += int(ex.get('controlled_success') or 0)
        gm.exits['dump_attempts'] += int(ex.get('dump_attempts') or 0)
        # Shots
        ts = t.get('shots') or {}
        os = o.get('shots') or {}
        gm.shots_for_on += int(ts.get('on') or 0)
        gm.shots_for_missed += int(ts.get('missed') or 0)
        gm.shots_for_blocked += int(ts.get('blocked') or 0)
        gm.shots_for_total += int(ts.get('total') or 0)
        gm.shots_against_total += int(os.get('total') or 0)
        # Other counts
        gm.passes += int(t.get('passes') or 0)
        gm.lpr_recoveries += int(t.get('lpr_recoveries') or 0)
        gm.pressure_events += int(t.get('pressure_events') or 0)
        gm.turnovers += int(t.get('turnovers') or 0)
        # Opponent side counts for comparison
        gm.opp_passes += int(o.get('passes') or 0)
        gm.opp_lpr_recoveries += int(o.get('lpr_recoveries') or 0)
        gm.opp_pressure_events += int(o.get('pressure_events') or 0)
        gm.opp_turnovers += int(o.get('turnovers') or 0)

        # Strength split (if deployments were linked)
        strength = seq.get('deployment_strength')
        if strength:
            bs = gm.by_strength[str(strength)]
            bs['shots_for_total'] += float(ts.get('total') or 0.0)
            bs['shots_against_total'] += float(os.get('total') or 0.0)
            tz = t.get('zone_time') or {}
            bs['oz_time'] += float(tz.get('oz') or 0.0)
            bs['dz_time'] += float(tz.get('dz') or 0.0)
            bs['nz_time'] += float(tz.get('nz') or 0.0)
            bs['possession_time'] += float(t.get('possession_time') or 0.0)
            bs['entries_c_att'] += float(et.get('controlled_attempts') or 0.0)
            bs['entries_d_att'] += float(et.get('dump_attempts') or 0.0)
            bs['entries_c_succ'] += float(et.get('controlled_success') or 0.0)
            bs['exits_c_att'] += float(ex.get('controlled_attempts') or 0.0)
            bs['exits_d_att'] += float(ex.get('dump_attempts') or 0.0)
            bs['exits_c_succ'] += float(ex.get('controlled_success') or 0.0)

    # Deployments (faceoff + on-ice snapshot metadata)
    wd = (extraction.get('whistle_deployments') or {}).get('deployments') or []
    for dep in wd:
        # Count by the team's side
        dep_zone = dep.get('home_zone') if side == 'home' else dep.get('away_zone')
        if dep_zone:
            gm.deployments_by_zone[str(dep_zone)] += 1
        strength = dep.get('strength')
        if strength:
            gm.deployments_by_strength[str(strength)] += 1

    # Pass networks (keyed by team full name in extractor)
    pn = extraction.get('pass_networks') or {}
    tname = team_name_home if side == 'home' else team_name_away
    if tname and pn.get(tname):
        net = pn.get(tname) or {}
        gm.pass_network = {
            'nodes': float(net.get('nodes') or 0.0),
            'edges': float(net.get('edges') or 0.0),
            'avg_degree': float(net.get('avg_degree') or 0.0),
        }

    return gm


def aggregate_team(team_abbrev: str, seasons: List[str], run_extractor: bool = False, clean: bool = False) -> None:
    base_dirs = [
        Path('data/processed/analytics/nhl_play_by_play') / team_abbrev,
        Path('data') / 'mtl_play_by_play',  # legacy/fallback
    ]
    extracted_dir = Path('data/processed/extracted_metrics')
    out_base = Path('data/processed/team_profiles/advanced_metrics') / team_abbrev

    ensure_dir(extracted_dir)
    ensure_dir(out_base)

    # Optional cleanup of existing season files
    if clean:
        for s in seasons:
            f = out_base / f"{s}_team_advanced.json"
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass

    aggregates: Dict[str, TeamSeasonAggregate] = {}

    for base_pbp in base_dirs:
        for season_folder in base_pbp.glob('*'):
            if not season_folder.is_dir():
                continue
            # Convert '2024-2025' -> '20242025'
            season_raw = season_folder.name
            if len(season_raw) == 9 and season_raw[4] == '-':
                season_str = season_raw.replace('-', '')
            else:
                season_str = None
            if seasons and season_str not in seasons:
                continue

            for csv_path in season_folder.glob('*.csv'):
                # Ensure extraction exists (or run if requested)
                out_json = extracted_dir / f"{csv_path.stem}_comprehensive_metrics.json"
                if run_extractor and not out_json.exists():
                    print(f"Running extractor for: {csv_path}")
                    produced = run_extractor_on_csv(csv_path, extracted_dir)
                    if not produced:
                        print(f"Skipping {csv_path}, extractor failed")
                        continue
                if not out_json.exists():
                    candidates = list(extracted_dir.glob(f"{csv_path.stem}_comprehensive_metrics.json"))
                    if not candidates:
                        print(f"No extraction JSON found for {csv_path.stem}, skipping")
                        continue
                    out_json = candidates[0]

                try:
                    with open(out_json, 'r') as f:
                        extraction = json.load(f)
                except Exception as e:
                    print(f"Failed to read {out_json}: {e}")
                    continue

                # Determine season string from filename as canonical
                season_from_file = parse_season_from_name(csv_path.stem) or season_str or ''
                if not season_from_file:
                    continue

                # Game date from filename token YYYYMMDD
                parts = csv_path.stem.split('-')
                game_date_token = parts[1] if len(parts) > 1 else ''
                game_date = None
                if game_date_token.isdigit() and len(game_date_token) == 8:
                    game_date = f"{game_date_token[0:4]}-{game_date_token[4:6]}-{game_date_token[6:8]}"

                # Per-game metrics for this team
                gm = collect_team_game_metrics(extraction, team_abbrev, game_date, season_from_file)
                # Attach final score (goals for/against) from PBP CSV
                try:
                    info = extraction.get('game_info', {}) if isinstance(extraction, dict) else {}
                    home_code = str(info.get('home_team') or '').upper()
                    away_code = str(info.get('away_team') or '').upper()
                    home_name = info.get('home_team_name') or home_code
                    away_name = info.get('away_team_name') or away_code
                    alias_to_code = {
                        'Utah Mammoth': 'UTA',
                        'Montréal Canadiens': 'MTL',
                    }
                    df = pd.read_csv(csv_path)
                    is_goal = df['shorthand'].astype(str).str.contains('GOAL', na=False) | (df['name'].astype(str).str.lower() == 'goal')
                    goals_team = df.loc[is_goal, 'team'].astype(str)
                    home_goals = int(((goals_team == home_name) | (goals_team == home_code) | (goals_team.map(alias_to_code.get) == home_code)).sum())
                    away_goals = int(((goals_team == away_name) | (goals_team == away_code) | (goals_team.map(alias_to_code.get) == away_code)).sum())
                    if team_abbrev.upper() == home_code:
                        gm.goals_for = home_goals
                        gm.goals_against = away_goals
                    elif team_abbrev.upper() == away_code:
                        gm.goals_for = away_goals
                        gm.goals_against = home_goals
                except Exception:
                    pass
                if not gm:
                    continue

                ag = aggregates.get(season_from_file)
                if ag is None:
                    ag = TeamSeasonAggregate(team_code=team_abbrev, season=season_from_file)
                    aggregates[season_from_file] = ag
                if gm.game_id is not None:
                    ag.games[int(gm.game_id)] = gm

    # Save one file per season
    for season_key, ag in aggregates.items():
        out_file = out_base / f"{season_key}_team_advanced.json"
        try:
            data = ag.to_dict()
            with open(out_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved team advanced metrics: {out_file}")
        except Exception as e:
            print(f"Failed to save {out_file}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Aggregate advanced team metrics by game and season.')
    parser.add_argument('--teams', type=str, default='MTL', help='Comma-separated team abbreviations to process (default: MTL)')
    parser.add_argument('--seasons', type=str, default='20242025,20252026', help='Comma-separated seasons (YYYYYYYY) to include')
    parser.add_argument('--run-extractor', action='store_true', help='Run the comprehensive extractor for missing CSVs before aggregation')
    parser.add_argument('--clean', action='store_true', help='Delete existing team season files before writing')

    args = parser.parse_args()
    teams = [t.strip().upper() for t in (args.teams or '').split(',') if t.strip()]
    seasons = [s.strip() for s in (args.seasons or '').split(',') if s.strip()]

    for t in teams:
        print(f"Processing team {t} for seasons {seasons}...")
        aggregate_team(t, seasons, run_extractor=args.run_extractor, clean=args.clean)


if __name__ == '__main__':
    main()
