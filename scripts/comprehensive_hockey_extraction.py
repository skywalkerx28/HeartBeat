#!/usr/bin/env python3
"""
Comprehensive Hockey Analytics Extraction System
Extracts all advanced metrics from NHL play-by-play sequence files
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, deque
from datetime import datetime
import networkx as nx


class ComprehensiveHockeyExtractor:
    """Extract all advanced metrics from NHL play-by-play data"""
    
    def __init__(self, pbp_file: str, roster_dir: str = None):
        """Initialize extractor with play-by-play file and optional roster directory"""
        self.pbp_file = pbp_file
        self.roster_dir = Path(roster_dir) if roster_dir else None
        self.data = None
        self.player_map = {}
        self.results = defaultdict(dict)
        self.team_code_to_name = {
            'ANA': 'Anaheim Ducks',
            'ARI': 'Arizona Coyotes',
            'BOS': 'Boston Bruins',
            'BUF': 'Buffalo Sabres',
            'CGY': 'Calgary Flames',
            'CAR': 'Carolina Hurricanes',
            'CHI': 'Chicago Blackhawks',
            'COL': 'Colorado Avalanche',
            'CBJ': 'Columbus Blue Jackets',
            'DAL': 'Dallas Stars',
            'DET': 'Detroit Red Wings',
            'EDM': 'Edmonton Oilers',
            'FLA': 'Florida Panthers',
            'LAK': 'Los Angeles Kings',
            'MIN': 'Minnesota Wild',
            'MTL': 'Montreal Canadiens',
            'NSH': 'Nashville Predators',
            'NJD': 'New Jersey Devils',
            'NYI': 'New York Islanders',
            'NYR': 'New York Rangers',
            'OTT': 'Ottawa Senators',
            'PHI': 'Philadelphia Flyers',
            'PIT': 'Pittsburgh Penguins',
            'SEA': 'Seattle Kraken',
            'SJS': 'San Jose Sharks',
            'STL': 'St. Louis Blues',
            'TBL': 'Tampa Bay Lightning',
            'TOR': 'Toronto Maple Leafs',
            'UTA': 'Utah Hockey Club',
            'VAN': 'Vancouver Canucks',
            'VGK': 'Vegas Golden Knights',
            'WPG': 'Winnipeg Jets',
            'WSH': 'Washington Capitals',
        }
        # Official NHL team IDs
        self.team_code_to_id = {
            'MTL': 8,
            'TOR': 10,
            'BOS': 6,
            'BUF': 7,
            'OTT': 9,
            'DET': 17,
            'FLA': 13,
            'TBL': 14,
            'NYR': 3,
            'NYI': 2,
            'PHI': 4,
            'WSH': 15,
            'CAR': 12,
            'NJD': 1,
            'CBJ': 29,
            'PIT': 5,
            'COL': 21,
            'DAL': 25,
            'MIN': 30,
            'NSH': 18,
            'STL': 19,
            'WPG': 52,
            'CHI': 16,
            'UTA': 59,  # Utah Hockey Club
            'VGK': 54,
            'SEA': 55,
            'LAK': 26,
            'SJS': 28,
            'ANA': 24,
            'VAN': 23,
            'CGY': 20,
            'EDM': 22,
            'ARI': 59  # Historical mapping to Utah franchise id
        }
        # Reverse lookups
        self.team_name_to_code = {v: k for k, v in self.team_code_to_name.items()}
        # Common aliases
        self.team_name_alias_to_code = {
            'Montréal Canadiens': 'MTL',
            'Utah Mammoth': 'UTA',
        }
    
    # ------------------------------
    # Helpers
    # ------------------------------
    @staticmethod
    def _parse_season_from_stem(stem: str) -> Optional[str]:
        parts = stem.split('-')
        for p in reversed(parts):
            if len(p) == 8 and p.isdigit():
                return p
        return None

    @staticmethod
    def _safe_float(val):
        try:
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return None
            return float(val)
        except Exception:
            return None
    def _timecode_to_seconds(self, tc: object) -> Optional[float]:
        if tc is None or (isinstance(tc, float) and np.isnan(tc)):
            return None
        s = str(tc)
        parts = s.split(':')
        try:
            if len(parts) >= 3:
                hh = int(parts[-4]) if len(parts) == 4 else 0
                mm = int(parts[-3])
                ss = float(parts[-2])
                # ignore frames (parts[-1]) as sub-second precision is not required here
                return hh * 3600 + mm * 60 + ss
            return float(s)
        except Exception:
            return None
    def _json_safe(self, obj):
        """Recursively convert numpy/pandas NaN/NA and dtypes to JSON-safe types."""
        if obj is None:
            return None
        # numpy scalars
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return None if np.isnan(obj) else float(obj)
        # plain float NaN
        if isinstance(obj, float):
            return None if np.isnan(obj) else obj
        if isinstance(obj, (str, int, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: self._json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._json_safe(v) for v in obj]
        # Fallback to string
        return str(obj)
    def _norm_id(self, token: object) -> str:
        """Normalize a player id token to a canonical numeric string (e.g., '8482113.0' -> '8482113').
        Accepts str/int/float and safely coerces to string first.
        """
        t = str(token).strip().strip('"')
        if not t or t.lower() == 'nan':
            return ''
        try:
            return str(int(float(t)))
        except Exception:
            return t

    def _parse_ids(self, value) -> List[str]:
        """Parse an id list from fields that look like "\t8480185, 8482113, 8482713" or "8480185, 8482113".
        Returns a list of normalized id strings.
        """
        if pd.isna(value):
            return []
        s = str(value).strip().strip('"').lstrip('\t ').rstrip()
        if not s:
            return []
        parts = [self._norm_id(p) for p in s.split(',')]
        return [p for p in parts if p]

    def _get_teams(self) -> List[str]:
        """Return the two absolute team names present in the file (e.g., 'Boston Bruins', 'Florida Panthers')."""
        teams_in_file = [t for t in self.data['team'].dropna().unique().tolist() if t]
        # Defensive fallback in case some rows don't have 'team'
        if len(teams_in_file) >= 2:
            return teams_in_file[:2]
        return teams_in_file

    def _team_name_or_code_to_id(self, value: str):
        """Return NHL team id given a team code (BOS) or full name (Boston Bruins)."""
        if value is None:
            return None
        t = str(value).strip()
        if not t:
            return None
        # If appears as code
        if len(t) <= 3 and t.upper() in self.team_code_to_id:
            return self.team_code_to_id.get(t.upper())
        # Try direct name mapping
        code = self.team_name_to_code.get(t)
        if code and code in self.team_code_to_id:
            return self.team_code_to_id[code]
        # Try aliases
        alias_code = self.team_name_alias_to_code.get(t)
        if alias_code and alias_code in self.team_code_to_id:
            return self.team_code_to_id[alias_code]
        return None
        
    def load_data(self) -> None:
        """Load play-by-play data and clean it"""
        print(f"Loading play-by-play data from {self.pbp_file}")
        self.data = pd.read_csv(self.pbp_file)
        print(f"Loaded {len(self.data)} events")
        
    def extract_game_info(self) -> Dict:
        """Extract basic game information"""
        # Parse filename for teams
        filename = Path(self.pbp_file).name
        if 'vs' in filename:
            teams = filename.split('-')[3].split('vs')
            away_code = teams[0]
            home_code = teams[1].split('-')[0] if '-' in teams[1] else teams[1]
            away_team = away_code
            home_team = home_code
        else:
            away_team = 'AWAY'
            home_team = 'HOME'
        # Resolve full names if possible
        away_team_name = self.team_code_to_name.get(away_team, None)
        home_team_name = self.team_code_to_name.get(home_team, None)
        if not away_team_name or not home_team_name:
            # Fallback: infer names from data
            uniq_names = [t for t in self.data['team'].dropna().unique().tolist() if t]
            if len(uniq_names) >= 2:
                # Heuristic: pick by name containing city code substring
                away_team_name = away_team_name or uniq_names[0]
                home_team_name = home_team_name or uniq_names[1]

        return {
            'game_id': self.data['gameReferenceId'].iloc[0] if not self.data.empty else None,
            'away_team': away_team,
            'home_team': home_team,
            'away_team_name': away_team_name,
            'home_team_name': home_team_name,
            'away_team_id': self._team_name_or_code_to_id(away_team) or self._team_name_or_code_to_id(away_team_name),
            'home_team_id': self._team_name_or_code_to_id(home_team) or self._team_name_or_code_to_id(home_team_name),
            'home_has_last_change': True
        }
    
    # ==========================
    # MATCHUP EXTRACTION
    # ==========================
    
    def extract_individual_matchups(self) -> Dict:
        """Extract 1v1 player matchup data based on absolute on-ice sets per team.
        A matchup is counted once when two players first become on-ice together and not recounted until they separate.
        We canonicalize pair keys to avoid double-counting due to perspective flips.
        """
        matchups: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        teams = self._get_teams()
        if len(teams) < 2:
            return dict(matchups)
        team_a, team_b = teams[0], teams[1]

        # Absolute on-ice state per team
        on_ice = {
            team_a: {'F': set(), 'D': set()},
            team_b: {'F': set(), 'D': set()},
        }

        # Active pairs per type (for appearance counting)
        active_ff: Set[Tuple[str, str]] = set()  # symmetric pairs (min, max)
        active_fd: Set[Tuple[str, str]] = set()  # (forward, defense)
        active_dd: Set[Tuple[str, str]] = set()  # symmetric pairs (min, max)

        for _, row in self.data.iterrows():
            team = row['team'] if not pd.isna(row['team']) else None
            if team not in (team_a, team_b):
                # Skip rows that don't update on-ice info
                continue

            other = team_b if team == team_a else team_a

            # Update absolute on-ice using this row's perspective
            on_ice[team]['F'] = set(self._parse_ids(row['teamForwardsOnIceRefs']))
            on_ice[team]['D'] = set(self._parse_ids(row['teamDefencemenOnIceRefs']))
            on_ice[other]['F'] = set(self._parse_ids(row['opposingTeamForwardsOnIceRefs']))
            on_ice[other]['D'] = set(self._parse_ids(row['opposingTeamDefencemenOnIceRefs']))

            # Build current cross-team pairs (canonicalized)
            current_ff: Set[Tuple[str, str]] = set()
            for fa in on_ice[team_a]['F']:
                for fb in on_ice[team_b]['F']:
                    key = tuple(sorted((fa, fb)))
                    current_ff.add(key)

            current_fd: Set[Tuple[str, str]] = set()
            # Forwards from A vs D from B
            for fa in on_ice[team_a]['F']:
                for db in on_ice[team_b]['D']:
                    current_fd.add((fa, db))
            # Forwards from B vs D from A
            for fb in on_ice[team_b]['F']:
                for da in on_ice[team_a]['D']:
                    current_fd.add((fb, da))

            current_dd: Set[Tuple[str, str]] = set()
            for da in on_ice[team_a]['D']:
                for db in on_ice[team_b]['D']:
                    key = tuple(sorted((da, db)))
                    current_dd.add(key)

            # Count only newly-started pairs
            for pair in current_ff - active_ff:
                matchups['F_vs_F'][f"{pair[0]}_vs_{pair[1]}"] += 1
            for pair in current_fd - active_fd:
                # already oriented (forward, defense)
                matchups['F_vs_D'][f"{pair[0]}_vs_{pair[1]}"] += 1
            for pair in current_dd - active_dd:
                matchups['D_vs_D'][f"{pair[0]}_vs_{pair[1]}"] += 1

            # Update active sets
            active_ff, active_fd, active_dd = current_ff, current_fd, current_dd

        return dict(matchups)
    
    def extract_matchup_durations(self) -> Dict:
        """Extract matchup durations for absolute pairs (F-F, F-D, D-D) across the game timeline."""
        durations = defaultdict(lambda: {
            'appearances': 0,
            'total_time': 0.0,
            'first_appearance': None,
            'last_appearance': None
        })

        teams = self._get_teams()
        if len(teams) < 2:
            return dict(durations)
        team_a, team_b = teams[0], teams[1]

        on_ice = {
            team_a: {'F': set(), 'D': set()},
            team_b: {'F': set(), 'D': set()},
        }

        active_start_times_ff: Dict[Tuple[str, str], float] = {}
        active_start_times_fd: Dict[Tuple[str, str], float] = {}
        active_start_times_dd: Dict[Tuple[str, str], float] = {}

        last_time = None

        for _, row in self.data.iterrows():
            team = row['team'] if not pd.isna(row['team']) else None
            if team not in (team_a, team_b):
                continue

            t = float(row['gameTime'])
            other = team_b if team == team_a else team_a

            # Update absolute on-ice
            on_ice[team]['F'] = set(self._parse_ids(row['teamForwardsOnIceRefs']))
            on_ice[team]['D'] = set(self._parse_ids(row['teamDefencemenOnIceRefs']))
            on_ice[other]['F'] = set(self._parse_ids(row['opposingTeamForwardsOnIceRefs']))
            on_ice[other]['D'] = set(self._parse_ids(row['opposingTeamDefencemenOnIceRefs']))

            # Compute current pairs
            current_ff = {tuple(sorted((fa, fb))) for fa in on_ice[team_a]['F'] for fb in on_ice[team_b]['F']}
            current_fd = set()
            current_fd.update({(fa, db) for fa in on_ice[team_a]['F'] for db in on_ice[team_b]['D']})
            current_fd.update({(fb, da) for fb in on_ice[team_b]['F'] for da in on_ice[team_a]['D']})
            current_dd = {tuple(sorted((da, db))) for da in on_ice[team_a]['D'] for db in on_ice[team_b]['D']}

            # Close ended pairs
            if last_time is not None:
                for pair in set(active_start_times_ff.keys()) - current_ff:
                    start = active_start_times_ff.pop(pair)
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['total_time'] += t - start
                    durations[key]['last_appearance'] = t
                for pair in set(active_start_times_fd.keys()) - current_fd:
                    start = active_start_times_fd.pop(pair)
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['total_time'] += t - start
                    durations[key]['last_appearance'] = t
                for pair in set(active_start_times_dd.keys()) - current_dd:
                    start = active_start_times_dd.pop(pair)
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['total_time'] += t - start
                    durations[key]['last_appearance'] = t

            # Start new pairs
            for pair in current_ff:
                if pair not in active_start_times_ff:
                    active_start_times_ff[pair] = t
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['appearances'] += 1
                    if durations[key]['first_appearance'] is None:
                        durations[key]['first_appearance'] = t
            for pair in current_fd:
                if pair not in active_start_times_fd:
                    active_start_times_fd[pair] = t
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['appearances'] += 1
                    if durations[key]['first_appearance'] is None:
                        durations[key]['first_appearance'] = t
            for pair in current_dd:
                if pair not in active_start_times_dd:
                    active_start_times_dd[pair] = t
                    key = f"{pair[0]}_vs_{pair[1]}"
                    durations[key]['appearances'] += 1
                    if durations[key]['first_appearance'] is None:
                        durations[key]['first_appearance'] = t

            last_time = t

        # Close pairs still active at end
        if last_time is not None:
            for pair, start in active_start_times_ff.items():
                key = f"{pair[0]}_vs_{pair[1]}"
                durations[key]['total_time'] += last_time - start
                durations[key]['last_appearance'] = last_time
            for pair, start in active_start_times_fd.items():
                key = f"{pair[0]}_vs_{pair[1]}"
                durations[key]['total_time'] += last_time - start
                durations[key]['last_appearance'] = last_time
            for pair, start in active_start_times_dd.items():
                key = f"{pair[0]}_vs_{pair[1]}"
                durations[key]['total_time'] += last_time - start
                durations[key]['last_appearance'] = last_time

        # Compute averages into result map per pair
        result = {}
        for key, d in durations.items():
            d['avg_shift_length'] = d['total_time'] / d['appearances'] if d['appearances'] else 0.0
            result[key] = dict(d)
        return result
    
    def extract_line_vs_dpair_matchups(self) -> Dict:
        """Extract forward line vs defense pairing matchups (absolute, shift-based).
        Counts one appearance when a specific 3F line faces a specific 2D pair on the other team.
        Skips non-5v5 formations to avoid inflation.
        """
        matchups = defaultdict(int)
        teams = self._get_teams()
        if len(teams) < 2:
            return dict(matchups)
        team_a, team_b = teams[0], teams[1]

        on_ice = {team_a: {'F': set(), 'D': set()}, team_b: {'F': set(), 'D': set()}}
        active_keys: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()

        for _, row in self.data.iterrows():
            team = row['team'] if not pd.isna(row['team']) else None
            if team not in (team_a, team_b):
                continue
            other = team_b if team == team_a else team_a

            # Update absolute on-ice
            on_ice[team]['F'] = set(self._parse_ids(row['teamForwardsOnIceRefs']))
            on_ice[team]['D'] = set(self._parse_ids(row['teamDefencemenOnIceRefs']))
            on_ice[other]['F'] = set(self._parse_ids(row['opposingTeamForwardsOnIceRefs']))
            on_ice[other]['D'] = set(self._parse_ids(row['opposingTeamDefencemenOnIceRefs']))

            current_keys: Set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
            # A-line vs B-pair
            if len(on_ice[team_a]['F']) == 3 and len(on_ice[team_b]['D']) == 2:
                line_a = tuple(sorted(on_ice[team_a]['F']))
                pair_b = tuple(sorted(on_ice[team_b]['D']))
                current_keys.add((line_a, pair_b))
            # B-line vs A-pair
            if len(on_ice[team_b]['F']) == 3 and len(on_ice[team_a]['D']) == 2:
                line_b = tuple(sorted(on_ice[team_b]['F']))
                pair_a = tuple(sorted(on_ice[team_a]['D']))
                current_keys.add((line_b, pair_a))

            for key in current_keys - active_keys:
                matchups[f"{key[0]}_vs_{key[1]}"] += 1
            active_keys = current_keys

        return dict(matchups)
    
    def extract_dpair_vs_line_matchups(self) -> Dict:
        """Alias to line_vs_dpair for compatibility (we track both directions together)."""
        # Using the same absolute logic avoids double counting. This method returns the same as line_vs_dpair.
        return self.extract_line_vs_dpair_matchups()
    
    # ==========================
    # DEPLOYMENT ANALYSIS
    # ==========================
    
    def extract_whistle_deployments(self) -> Dict:
        """Extract deployments precisely from the first on-ice snapshot after a whistle.
        NHL last change occurs before play resumes, so both away and home deployments are present in the
        same first event after the whistle (often the Face-Off row).
        We map home/away correctly using the row's team perspective.
        """
        deployments = []
        info = self.extract_game_info()
        # Prefer full team names when available, else fall back to codes
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')
        home_team_code = self.team_name_to_code.get(home_team, info.get('home_team'))
        away_team_code = self.team_name_to_code.get(away_team, info.get('away_team'))
        home_team_id = self._team_name_or_code_to_id(home_team_code or home_team)
        away_team_id = self._team_name_or_code_to_id(away_team_code or away_team)

        whistles = self.data[self.data['shorthand'] == 'Whistle'].index.tolist()
        deployment_counter = 0

        for whistle_idx in whistles:
            scan_end = min(whistle_idx + 40, len(self.data))
            # find first row after whistle where both sides' on-ice lists are populated
            picked_idx = None
            for idx in range(whistle_idx + 1, scan_end):
                r = self.data.loc[idx]
                t_for = self._parse_ids(r['teamForwardsOnIceRefs'])
                t_def = self._parse_ids(r['teamDefencemenOnIceRefs'])
                o_for = self._parse_ids(r['opposingTeamForwardsOnIceRefs'])
                o_def = self._parse_ids(r['opposingTeamDefencemenOnIceRefs'])
                if (t_for or t_def) and (o_for or o_def):
                    picked_idx = idx
                    break
            if picked_idx is None:
                continue

            r = self.data.loc[picked_idx]
            row_team = r['team'] if not pd.isna(r['team']) else None
            t_for = self._parse_ids(r['teamForwardsOnIceRefs'])
            t_def = self._parse_ids(r['teamDefencemenOnIceRefs'])
            o_for = self._parse_ids(r['opposingTeamForwardsOnIceRefs'])
            o_def = self._parse_ids(r['opposingTeamDefencemenOnIceRefs'])
            # Skater counts and strength
            t_skaters = int(r['teamSkatersOnIce']) if not pd.isna(r['teamSkatersOnIce']) else None
            o_skaters = int(r['opposingTeamSkatersOnIce']) if not pd.isna(r['opposingTeamSkatersOnIce']) else None
            manpower = r['manpowerSituation'] if not pd.isna(r['manpowerSituation']) else None

            # Map to absolute home/away by row perspective
            if row_team == home_team:
                home_forwards, home_defense = t_for, t_def
                away_forwards, away_defense = o_for, o_def
                home_skaters, away_skaters = t_skaters, o_skaters
            elif row_team == away_team:
                home_forwards, home_defense = o_for, o_def
                away_forwards, away_defense = t_for, t_def
                home_skaters, away_skaters = o_skaters, t_skaters
            else:
                # If row team is missing, try to infer by roster sizes (fallback)
                home_forwards, home_defense = o_for, o_def
                away_forwards, away_defense = t_for, t_def
                home_skaters, away_skaters = o_skaters, t_skaters

            # Find the most informative faceoff row after the whistle to capture FO metadata
            faceoff_idx = None
            # Prefer a 'name' == 'faceoff' row that includes zone/coords (REC FACE OFF variants)
            for j in range(whistle_idx + 1, scan_end):
                rj = self.data.loc[j]
                if str(rj['name']) == 'faceoff' and (not pd.isna(rj['zone']) or not pd.isna(rj['xCoord']) or not pd.isna(rj['xAdjCoord'])):
                    faceoff_idx = j
                    break
            # Fallback to a plain 'Face-Off' shorthand row if informative one not found
            if faceoff_idx is None:
                for j in range(whistle_idx + 1, scan_end):
                    rj = self.data.loc[j]
                    if str(rj['shorthand']) == 'Face-Off':
                        faceoff_idx = j
                        break

            faceoff_meta = {
                'faceoff_time': None,
                'faceoff_zone': None,
                'faceoff_x': None,
                'faceoff_y': None,
                'faceoff_x_adj': None,
                'faceoff_y_adj': None,
                'faceoff_shorthand': None,
                'faceoff_flags': None,
                'faceoff_winner_team': None
            }
            if faceoff_idx is not None:
                fr = self.data.loc[faceoff_idx]
                faceoff_meta['faceoff_time'] = float(fr['gameTime']) if not pd.isna(fr['gameTime']) else None
                faceoff_meta['faceoff_zone'] = fr['zone'] if not pd.isna(fr['zone']) else None
                faceoff_meta['faceoff_x'] = float(fr['xCoord']) if not pd.isna(fr['xCoord']) else None
                faceoff_meta['faceoff_y'] = float(fr['yCoord']) if not pd.isna(fr['yCoord']) else None
                faceoff_meta['faceoff_x_adj'] = float(fr['xAdjCoord']) if not pd.isna(fr['xAdjCoord']) else None
                faceoff_meta['faceoff_y_adj'] = float(fr['yAdjCoord']) if not pd.isna(fr['yAdjCoord']) else None
                # Use the exact 'shorthand' text from the CSV (e.g., "OZ REC FACE OFF+SON")
                faceoff_meta['faceoff_shorthand'] = fr['shorthand'] if not pd.isna(fr['shorthand']) else None
                faceoff_meta['faceoff_flags'] = fr['flags'] if not pd.isna(fr['flags']) else None
                # Determine winner: prefer the 'name' == 'faceoff' row's team if present; else scan ahead
                winner = fr['team'] if not pd.isna(fr['team']) else None
                if not winner:
                    for j in range(faceoff_idx, min(faceoff_idx + 6, len(self.data))):
                        rowj = self.data.loc[j]
                        if str(rowj['name']) == 'faceoff' and str(rowj['outcome']).lower() == 'successful' and not pd.isna(rowj['team']):
                            winner = rowj['team']
                            break
                faceoff_meta['faceoff_winner_team'] = winner

            # Derive team zones for this deployment
            def invert_zone(z):
                if z == 'oz':
                    return 'dz'
                if z == 'dz':
                    return 'oz'
                return 'nz' if z == 'nz' else None

            home_zone = None
            away_zone = None
            if faceoff_idx is not None and faceoff_meta['faceoff_zone']:
                fr = self.data.loc[faceoff_idx]
                fo_team = fr['team'] if not pd.isna(fr['team']) else None
                z = faceoff_meta['faceoff_zone']
                if fo_team == home_team:
                    home_zone = z
                    away_zone = invert_zone(z)
                elif fo_team == away_team:
                    away_zone = z
                    home_zone = invert_zone(z)
                else:
                    # If the row uses codes while we hold names (or vice versa), try partial match
                    if isinstance(fo_team, str):
                        if (info.get('home_team') in fo_team) or (info.get('home_team_name') == fo_team):
                            home_zone = z
                            away_zone = invert_zone(z)
                        elif (info.get('away_team') in fo_team) or (info.get('away_team_name') == fo_team):
                            away_zone = z
                            home_zone = invert_zone(z)
            # Fallback: use picked row perspective if still missing
            if (home_zone is None or away_zone is None) and not pd.isna(r['zone']):
                z = r['zone']
                if row_team == home_team:
                    home_zone = home_zone or z
                    away_zone = away_zone or invert_zone(z)
                elif row_team == away_team:
                    away_zone = away_zone or z
                    home_zone = home_zone or invert_zone(z)

            dep = {
                'deployment_id': deployment_counter,
                'whistle_time': float(self.data.loc[whistle_idx]['gameTime']) if not pd.isna(self.data.loc[whistle_idx]['gameTime']) else None,
                'whistle_event_index': int(whistle_idx),
                'period': int(self.data.loc[whistle_idx]['period']) if not pd.isna(self.data.loc[whistle_idx]['period']) else None,
                'away_forwards': away_forwards,
                'away_defense': away_defense,
                'home_forwards': home_forwards,
                'home_defense': home_defense,
                'home_matched': True,
                'away_skaters': away_skaters,
                'home_skaters': home_skaters,
                'strength': (f"{away_skaters}v{home_skaters}" if away_skaters is not None and home_skaters is not None else None),
                'manpowerSituation': manpower,
                'home_team_code': home_team_code,
                'away_team_code': away_team_code,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_zone': home_zone,
                'away_zone': away_zone,
                **faceoff_meta
            }
            deployments.append(dep)
            deployment_counter += 1

        return {'deployments': deployments, 'total_whistles': len(whistles)}
    
    def extract_rotation_patterns(self) -> Dict:
        """Extract line rotation and shift patterns (true contiguous trios).
        A trio shift is one contiguous interval where the set of 3 forwards on ice stays identical.
        We end a shift the instant any one of the three changes.
        """
        # State per absolute team side: current trio and its start time
        current_trio_by_team: Dict[str, Dict[str, object]] = {}
        # Accumulator: (team_display, trio_tuple) -> list of durations
        trio_durations: Dict[Tuple[str, Tuple[str, str, str]], List[float]] = defaultdict(list)
        # Accumulator per period: (team_display, trio_tuple) -> {period_int: [durations...]}
        trio_period_durations: Dict[Tuple[str, Tuple[str, str, str]], Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))

        # Resolve home/away naming for stable keys
        info = self.extract_game_info()
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')
        home_name = home_team
        away_name = away_team

        def parse_trios_for_row(row) -> Tuple[Optional[Tuple[str, str, str]], Optional[Tuple[str, str, str]]]:
            """Return (home_trio, away_trio) as sorted 3-tuples of player IDs or (None, None) if not exactly 3."""
            event_team = None if pd.isna(row['team']) else str(row['team'])
            # Determine which side is 'team' for this row
            is_home_event = False
            if event_team is not None:
                if event_team == home_name or self.team_name_to_code.get(event_team) == self.team_name_to_code.get(home_name) or event_team == self.team_name_to_code.get(home_name):
                    is_home_event = True
                elif event_team == away_name or self.team_name_to_code.get(event_team) == self.team_name_to_code.get(away_name) or event_team == self.team_name_to_code.get(away_name):
                    is_home_event = False
                else:
                    # Fallback: compare containment (codes inside names)
                    hn = info.get('home_team')
                    an = info.get('away_team')
                    if hn and hn in event_team:
                        is_home_event = True
                    elif an and an in event_team:
                        is_home_event = False

            # Parse both sides from the proper columns for this row
            if is_home_event:
                home_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                away_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
            else:
                home_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                away_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []

            home_trio = tuple(sorted(home_f)) if len(home_f) == 3 else None
            away_trio = tuple(sorted(away_f)) if len(away_f) == 3 else None
            return home_trio, away_trio

        # Iterate chronologically, updating both sides each row
        for _, row in self.data.iterrows():
            if pd.isna(row['gameTime']):
                continue
            t = float(row['gameTime'])
            p = None if pd.isna(row['period']) else int(row['period'])

            home_trio, away_trio = parse_trios_for_row(row)

            # Helper to update a side (home/away)
            def update_side(side_name: str, trio_opt: Optional[Tuple[str, str, str]]):
                state = current_trio_by_team.get(side_name)
                if trio_opt is None:
                    # Special teams or not exactly 3 — close any existing shift
                    if state and state['start'] is not None and t > state['start']:
                        prev_trio = tuple(sorted(state['trio']))
                        dur = t - state['start']
                        trio_durations[(side_name, prev_trio)].append(dur)
                        sp = state.get('start_period')
                        if isinstance(sp, int):
                            trio_period_durations[(side_name, prev_trio)][sp].append(dur)
                    current_trio_by_team[side_name] = {'trio': None, 'start': None, 'start_period': None}
                    return
                trio_set = frozenset(trio_opt)
                if state is None or state.get('trio') is None:
                    current_trio_by_team[side_name] = {'trio': trio_set, 'start': t, 'start_period': p}
                    return
                if state['trio'] == trio_set:
                    return
                # Trio changed: close and start new
                if state['start'] is not None and t > state['start']:
                    prev_trio = tuple(sorted(state['trio']))
                    dur = t - state['start']
                    trio_durations[(side_name, prev_trio)].append(dur)
                    sp = state.get('start_period')
                    if isinstance(sp, int):
                        trio_period_durations[(side_name, prev_trio)][sp].append(dur)
                current_trio_by_team[side_name] = {'trio': trio_set, 'start': t, 'start_period': p}

            update_side(home_name, home_trio)
            update_side(away_name, away_trio)

        # Close any ongoing trios at end of game using last gameTime
        last_time = None
        if not self.data.empty and 'gameTime' in self.data.columns:
            last_valid = self.data['gameTime'].dropna()
            if not last_valid.empty:
                last_time = float(last_valid.iloc[-1])

        if last_time is not None:
            for team_display, state in current_trio_by_team.items():
                start_time = state['start']
                if start_time is not None and last_time > start_time:
                    prev_trio = tuple(sorted(state['trio']))
                    dur = last_time - start_time
                    trio_durations[(team_display, prev_trio)].append(dur)
                    sp = state.get('start_period')
                    if isinstance(sp, int):
                        trio_period_durations[(team_display, prev_trio)][sp].append(dur)

        # Build output
        rotations: Dict[str, Dict[str, object]] = {}
        for (team_display, trio) in trio_durations:
            durations = trio_durations[(team_display, trio)]
            key = f"{team_display}_{trio}"
            # Build per-period summary
            per_period = {}
            pp = trio_period_durations[(team_display, trio)]
            for per, durs in sorted(pp.items()):
                per_period[int(per)] = {
                    'total_shifts': len(durs),
                    'avg_shift_length': float(np.mean(durs)) if durs else 0.0,
                    'total_time': float(np.sum(durs)) if durs else 0.0
                }
            rotations[key] = {
                'total_shifts': len(durations),
                'avg_shift_length': float(np.mean(durations)) if durations else 0.0,
                'shift_pattern': durations[:10],
                'per_period': per_period
            }

        return rotations

    def extract_line_rotation_sequence(self) -> Dict:
        """Chronological line/pairing rotation for each team.
        Emits an entry WHEN a new trio (3F) or pairing (2D) comes on.
        For each entry: period, periodTime, gameTime, score (home diff), ids.
        """
        info = self.extract_game_info()
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')

        def map_side(row):
            team_val = None if pd.isna(row['team']) else str(row['team'])
            # Determine if row perspective is home or away
            if team_val == home_team or self.team_name_to_code.get(team_val) == self.team_name_to_code.get(home_team) or team_val == self.team_name_to_code.get(home_team):
                return 'home'
            if team_val == away_team or self.team_name_to_code.get(team_val) == self.team_name_to_code.get(away_team) or team_val == self.team_name_to_code.get(away_team):
                return 'away'
            # Fallback: partial match on codes
            hn = info.get('home_team')
            an = info.get('away_team')
            if hn and team_val and hn in team_val:
                return 'home'
            if an and team_val and an in team_val:
                return 'away'
            return None

        def parse_groups(row):
            side = map_side(row)
            if side == 'home':
                home_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
                away_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
            else:
                home_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
                away_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
            home_trio = tuple(sorted(home_f)) if len(home_f) == 3 else None
            home_pair = tuple(sorted(home_d)) if len(home_d) == 2 else None
            away_trio = tuple(sorted(away_f)) if len(away_f) == 3 else None
            away_pair = tuple(sorted(away_d)) if len(away_d) == 2 else None
            return home_trio, home_pair, away_trio, away_pair

        # Maintain last groups to avoid duplicates within contiguous intervals
        last_home = {'F': None, 'D': None}
        last_away = {'F': None, 'D': None}

        # Maintain last known home score differential
        last_home_diff = None

        def current_home_diff(row):
            nonlocal last_home_diff
            if pd.isna(row['scoreDifferential']):
                return last_home_diff
            sd = float(row['scoreDifferential'])
            side = map_side(row)
            if side == 'home':
                last_home_diff = sd
            elif side == 'away':
                last_home_diff = -sd
            return last_home_diff

        home_seq_F, home_seq_D = [], []
        away_seq_F, away_seq_D = [], []

        for _, row in self.data.iterrows():
            if pd.isna(row['gameTime']):
                continue
            t = float(row['gameTime'])
            p = None if pd.isna(row['period']) else int(row['period'])
            pt = None if pd.isna(row['periodTime']) else float(row['periodTime'])
            hdiff = current_home_diff(row)

            home_trio, home_pair, away_trio, away_pair = parse_groups(row)

            # Home forwards
            if home_trio is not None and home_trio != last_home['F']:
                home_seq_F.append({
                    'team': home_team,
                    'type': 'F',
                    'group': list(home_trio),
                    'start_game_time': t,
                    'period': p,
                    'period_time': pt,
                    'home_score_diff': hdiff
                })
                last_home['F'] = home_trio
            # Home defense
            if home_pair is not None and home_pair != last_home['D']:
                home_seq_D.append({
                    'team': home_team,
                    'type': 'D',
                    'group': list(home_pair),
                    'start_game_time': t,
                    'period': p,
                    'period_time': pt,
                    'home_score_diff': hdiff
                })
                last_home['D'] = home_pair

            # Away forwards
            if away_trio is not None and away_trio != last_away['F']:
                away_seq_F.append({
                    'team': away_team,
                    'type': 'F',
                    'group': list(away_trio),
                    'start_game_time': t,
                    'period': p,
                    'period_time': pt,
                    'home_score_diff': hdiff
                })
                last_away['F'] = away_trio
            # Away defense
            if away_pair is not None and away_pair != last_away['D']:
                away_seq_D.append({
                    'team': away_team,
                    'type': 'D',
                    'group': list(away_pair),
                    'start_game_time': t,
                    'period': p,
                    'period_time': pt,
                    'home_score_diff': hdiff
                })
                last_away['D'] = away_pair

        return {
            'home': {'forwards': home_seq_F, 'defense': home_seq_D},
            'away': {'forwards': away_seq_F, 'defense': away_seq_D}
        }

    def extract_team_rotation_events(self) -> Dict:
        """Team-agnostic rotation events with replacements and context.
        Emits one row per rotation change per bench (home/away).
        Includes: team/opponent codes, timing, strength, score diff (team-oriented),
        event_index, sequence_id/deployment_id linkage, and player-for-player replacements.
        """
        if self.data is None or self.data.empty:
            return {'events': [], 'transitions': []}

        info = self.extract_game_info()
        home_name = info.get('home_team_name') or info.get('home_team')
        away_name = info.get('away_team_name') or info.get('away_team')
        home_code = self.team_name_to_code.get(home_name, info.get('home_team'))
        away_code = self.team_name_to_code.get(away_name, info.get('away_team'))

        # Sequence/deployment linkage and scoreboard snapshots (optional)
        ws = self.results.get('whistle_sequences', {}) if isinstance(self.results, dict) else {}
        ev_to_seq = (ws or {}).get('event_to_sequence_id', {})
        ev_to_dep = (ws or {}).get('event_to_deployment_id', {})
        sb = (ws or {}).get('scoreboard', {})
        sb_home = sb.get('home_score', []) if isinstance(sb, dict) else []
        sb_away = sb.get('away_score', []) if isinstance(sb, dict) else []

        # Helpers
        def map_side(row):
            team_val = None if pd.isna(row['team']) else str(row['team'])
            if team_val == home_name or team_val == home_code or self.team_name_to_code.get(team_val) == home_code:
                return 'home'
            if team_val == away_name or team_val == away_code or self.team_name_to_code.get(team_val) == away_code:
                return 'away'
            # Partial code in string fallback
            if isinstance(team_val, str):
                if info.get('home_team') and info.get('home_team') in team_val:
                    return 'home'
                if info.get('away_team') and info.get('away_team') in team_val:
                    return 'away'
            return None

        def parse_groups(row):
            side = map_side(row)
            if side == 'home':
                home_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
                away_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
            else:
                home_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
                away_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
            return sorted(list(set(home_f))), sorted(list(set(home_d))), \
                   sorted(list(set(away_f))), sorted(list(set(away_d)))

        def compute_replacements(prev_list, curr_list):
            prev_only = sorted(list(set(prev_list) - set(curr_list)))
            curr_only = sorted(list(set(curr_list) - set(prev_list)))
            pairs = []
            for out_p, in_p in list(zip(prev_only, curr_only)):
                pairs.append({'out': out_p, 'in': in_p})
            for out_p in prev_only[len(pairs):]:
                pairs.append({'out': out_p, 'in': None})
            for in_p in curr_only[len(pairs):]:
                pairs.append({'out': None, 'in': in_p})
            return pairs

        def team_score_diff(team_code: str, idx: int, row):
            # Try scoreboard snapshot first
            if idx is not None and idx < len(sb_home) and idx < len(sb_away):
                hs = sb_home[idx]
                as_ = sb_away[idx]
                if hs is not None and as_ is not None:
                    if team_code == home_code:
                        return int(hs - as_)
                    if team_code == away_code:
                        return int(as_ - hs)
            # Fallback to row-level scoreDifferential oriented to action team
            raw = None
            if 'scoreDifferential' in row and not pd.isna(row['scoreDifferential']):
                raw = row['scoreDifferential']
            elif 'scoreDiff' in row and not pd.isna(row['scoreDiff']):
                raw = row['scoreDiff']
            if raw is not None:
                try:
                    val = int(raw)
                except Exception:
                    try:
                        val = int(float(raw))
                    except Exception:
                        val = 0
                row_team = self.team_name_to_code.get(str(row['team']), str(row['team'])) if not pd.isna(row['team']) else None
                if row_team in (home_code, away_code):
                    return val if row_team == team_code else -val
            return 0

        def norm_strength(val: object) -> Optional[str]:
            s = str(val) if val is not None and not pd.isna(val) else None
            if not s:
                return None
            s_lower = s.lower()
            if 'even' in s_lower:
                return 'evenStrength'
            if 'power' in s_lower or s_lower in ('pp', '5v4', '4v3', '5v3'):
                return 'powerPlay'
            if 'short' in s_lower or s_lower in ('pk', '4v5', '3v4', '3v5'):
                return 'shortHanded'
            return s

        # Keep last-state per team
        last = {
            home_code: {'F': [], 'D': [], 'timecode': None, 'game_time': None},
            away_code: {'F': [], 'D': [], 'timecode': None, 'game_time': None},
        }
        seq_index = {home_code: 0, away_code: 0}

        # Derive season label from filename if present
        season_label = None
        try:
            stem_parts = Path(self.pbp_file).stem.split('-')
            if len(stem_parts) >= 6 and stem_parts[4].isdigit() and len(stem_parts[4]) == 8:
                sraw = stem_parts[4]
                season_label = f"{sraw[:4]}-{sraw[4:]}"
        except Exception:
            season_label = None

        events = []
        for idx, row in self.data.iterrows():
            if pd.isna(row['gameTime']):
                continue
            t = float(row['gameTime'])
            p = None if pd.isna(row['period']) else int(row['period'])
            pt = None if pd.isna(row['periodTime']) else float(row['periodTime'])
            tc = self._timecode_to_seconds(row['timecode']) if 'timecode' in self.data.columns else None
            hf, hd, af, ad = parse_groups(row)
            strength_state = norm_strength(row.get('manpowerSituation'))

            def log_if_changed(team_code: str, new_f: list, new_d: list, opponent_code: str):
                prev = last[team_code]
                changed = (new_f != prev['F']) or (new_d != prev['D'])
                if not changed:
                    return
                if prev['F'] or prev['D']:
                    events.append({
                        'game_id': self.data.loc[0, 'gameReferenceId'] if 'gameReferenceId' in self.data.columns else None,
                        'season': season_label,
                        'team': team_code,
                        'opponent': opponent_code,
                        'period': p,
                        'period_time': pt,
                        'game_time': t,
                        'timecode': tc,
                        'event_index': int(idx),
                        'sequence_index': seq_index[team_code] + 1,
                        'stoppage_type': row['shorthand'] if not pd.isna(row['shorthand']) else None,
                        'strength_state': strength_state,
                        'score_differential': team_score_diff(team_code, int(idx), row),
                        'from_forwards': '|'.join(prev['F']),
                        'from_defense': '|'.join(prev['D']),
                        'to_forwards': '|'.join(new_f),
                        'to_defense': '|'.join(new_d),
                        'time_between_real': (tc - prev['timecode']) if (tc is not None and prev['timecode'] is not None) else None,
                        'time_between_game': (t - prev['game_time']) if (t is not None and prev['game_time'] is not None) else None,
                        'replacements_f': compute_replacements(prev['F'], new_f),
                        'replacements_d': compute_replacements(prev['D'], new_d),
                        'sequence_id': ev_to_seq.get(int(idx)),
                        'deployment_id': ev_to_dep.get(int(idx)),
                        'source': 'CHE',
                    })
                    seq_index[team_code] += 1
                last[team_code] = {'F': new_f, 'D': new_d, 'timecode': tc, 'game_time': t}

            log_if_changed(home_code, hf, hd, away_code)
            log_if_changed(away_code, af, ad, home_code)

        # Aggregate from->to counts for quick transitions view
        def mk_key(f, d):
            return f"F:{'|'.join(f)}_D:{'|'.join(d)}"
        trans = {}
        for ev in events:
            from_key = f"F:{ev.get('from_forwards','')}_D:{ev.get('from_defense','')}"
            to_key = f"F:{ev.get('to_forwards','')}_D:{ev.get('to_defense','')}"
            k = (ev['team'], ev.get('strength_state'), from_key, to_key, ev.get('season'))
            trans[k] = trans.get(k, 0) + 1
        transitions = [
            {'team': k[0], 'strength_state': k[1], 'from_line': k[2], 'to_line': k[3], 'season': k[4], 'count': v, 'source': 'CHE'}
            for k, v in trans.items()
        ]

        return {'events': events, 'transitions': transitions}

    def extract_player_shifts(self) -> Dict:
        """Extract every player's shifts with lengths and rest between shifts (game and real time).
        - Shift starts when a player appears on-ice; ends when they leave.
        - Rest to next shift is computed between consecutive shifts per player.
        """
        if self.data.empty:
            return {'shifts': []}

        # Precompute absolute real-time offset per period using max period timecode seconds
        period_end_tc: Dict[int, float] = {}
        for p, grp in self.data.groupby('period'):
            tcs = grp['timecode'].apply(self._timecode_to_seconds).dropna()
            if not tcs.empty:
                period_end_tc[int(p)] = float(tcs.iloc[-1])
        # cumulative offsets
        periods_sorted = sorted([int(p) for p in period_end_tc.keys()])
        period_offset: Dict[int, float] = {}
        acc = 0.0
        for p in periods_sorted:
            period_offset[p] = acc
            acc += period_end_tc[p]

        def abs_timecode(row) -> Optional[float]:
            sec = self._timecode_to_seconds(row['timecode'])
            if sec is None or pd.isna(row['period']):
                return None
            po = period_offset.get(int(row['period']), 0.0)
            return po + sec

        # Helper to parse on-ice sets for home/away absolute
        info = self.extract_game_info()
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')

        def parse_on_ice_sets(row):
            team_val = None if pd.isna(row['team']) else str(row['team'])
            is_home_event = False
            if team_val == home_team or self.team_name_to_code.get(team_val) == self.team_name_to_code.get(home_team) or team_val == self.team_name_to_code.get(home_team):
                is_home_event = True
            elif team_val == away_team or self.team_name_to_code.get(team_val) == self.team_name_to_code.get(away_team) or team_val == self.team_name_to_code.get(away_team):
                is_home_event = False
            else:
                hn = info.get('home_team')
                an = info.get('away_team')
                if hn and team_val and hn in team_val:
                    is_home_event = True
                elif an and team_val and an in team_val:
                    is_home_event = False

            if is_home_event:
                home_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
                home_g = [self._norm_id(row['teamGoalieOnIceRef'])] if not pd.isna(row['teamGoalieOnIceRef']) else []
                away_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
                away_g = [self._norm_id(row['opposingTeamGoalieOnIceRef'])] if not pd.isna(row['opposingTeamGoalieOnIceRef']) else []
            else:
                home_f = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
                home_d = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
                home_g = [self._norm_id(row['opposingTeamGoalieOnIceRef'])] if not pd.isna(row['opposingTeamGoalieOnIceRef']) else []
                away_f = self._parse_ids(row['teamForwardsOnIceRefs']) if not pd.isna(row['teamForwardsOnIceRefs']) else []
                away_d = self._parse_ids(row['teamDefencemenOnIceRefs']) if not pd.isna(row['teamDefencemenOnIceRefs']) else []
                away_g = [self._norm_id(row['teamGoalieOnIceRef'])] if not pd.isna(row['teamGoalieOnIceRef']) else []

            home_set = set([pid for pid in home_f + home_d + home_g if pid])
            away_set = set([pid for pid in away_f + away_d + away_g if pid])
            return home_set, away_set, (home_f, home_d, home_g, away_f, away_d, away_g)

        prev_home_set: Set[str] = set()
        prev_away_set: Set[str] = set()
        prev_gt: Optional[float] = None
        prev_tc_abs: Optional[float] = None
        prev_ptime: Optional[float] = None
        prev_shorthand: Optional[str] = None

        # Maps from whistle sequences to allow deterministic linkage
        ws = self.results.get('whistle_sequences', {}) if isinstance(self.results.get('whistle_sequences', {}), dict) else {}
        ev_to_seq = ws.get('event_to_sequence_id', {}) if isinstance(ws, dict) else {}
        ev_to_dep = ws.get('event_to_deployment_id', {}) if isinstance(ws, dict) else {}

        active: Dict[str, Dict[str, object]] = {}
        shifts: List[Dict[str, object]] = []

        for idx, row in self.data.iterrows():
            if pd.isna(row['gameTime']):
                continue
            gt = float(row['gameTime'])
            tca = abs_timecode(row)
            p = int(row['period']) if not pd.isna(row['period']) else None
            ms = row['manpowerSituation'] if 'manpowerSituation' in self.data.columns and not pd.isna(row['manpowerSituation']) else None
            pt = float(row['periodTime']) if 'periodTime' in self.data.columns and not pd.isna(row['periodTime']) else None

            home_set, away_set, parsed = parse_on_ice_sets(row)
            curr_short = None if pd.isna(row['shorthand']) else str(row['shorthand'])
            # Consider sets valid only if we actually have players parsed
            has_sets = (len(home_set) + len(away_set)) > 0
            perform_diff = has_sets and (curr_short != 'Whistle')

            if perform_diff:
                curr_all = home_set | away_set
                prev_all = prev_home_set | prev_away_set

                # Players leaving -> close shifts using whistle-aware end time
                left = prev_all - curr_all
                if gt is not None and tca is not None:
                    for pid in left:
                        st = active.get(pid)
                        if st and st.get('start_gt') is not None:
                            # If last event was a whistle, end at the whistle time; else use midpoint between prev and current
                            if prev_shorthand == 'Whistle':
                                end_gt = prev_gt
                                end_tc = prev_tc_abs
                                end_pt = prev_ptime
                            else:
                                end_gt = ((prev_gt + gt) / 2.0) if (prev_gt is not None) else gt
                                end_tc = ((prev_tc_abs + tca) / 2.0) if (prev_tc_abs is not None) else tca
                                end_pt = ((prev_ptime + pt) / 2.0) if (prev_ptime is not None and pt is not None) else pt
                            shifts.append({
                                'player_id': pid,
                                'team_side': st.get('team_side'),
                                'team': st.get('team_name'),
                                'team_code': st.get('team_code'),
                                'team_id': self._team_name_or_code_to_id(st.get('team_code')) if st.get('team_code') else None,
                                'start_game_time': st['start_gt'],
                                'end_game_time': end_gt,
                                'shift_game_length': (end_gt - st['start_gt']) if (end_gt is not None and end_gt >= st['start_gt']) else None,
                                'start_timecode_abs': st['start_tc_abs'],
                                'end_timecode_abs': end_tc,
                                'shift_real_length': (end_tc - st['start_tc_abs']) if (end_tc is not None and st['start_tc_abs'] is not None) else None,
                                'start_period': st.get('start_period'),
                                'end_period': p,
                                'start_period_time': st.get('start_period_time'),
                                'end_period_time': end_pt,
                                'strength_start': st.get('strength'),
                                'manpower_start': st.get('manpower'),
                                'opponents_seen_ids': sorted(list(st.get('opponents_seen', set()))) if st.get('opponents_seen') is not None else [],
                                'sequence_ids': sorted(list(st.get('seq_ids', set()))) if st.get('seq_ids') is not None else [],
                                'deployment_ids': sorted(list(st.get('dep_ids', set()))) if st.get('dep_ids') is not None else []
                            })
                        active.pop(pid, None)

                # Players joining -> open shifts
                joined = curr_all - prev_all
            else:
                # If we don't perform diff (e.g., whistle or unknown sets), treat joined as empty
                joined = set()
            # counts for strength independent of side
            team_count = len(parsed[0]) + len(parsed[1])  # home F + home D
            opp_count = len(parsed[3]) + len(parsed[4])  # away F + away D
            strength = f"{team_count}v{opp_count}"

            for pid in joined:
                team_side = 'home' if pid in home_set else 'away' if pid in away_set else None
                team_name = home_team if team_side == 'home' else away_team if team_side == 'away' else None
                team_code = self.team_name_to_code.get(team_name, None) if team_name else None
                active[pid] = {
                    'start_gt': gt,
                    'start_tc_abs': tca,
                    'start_period': p,
                    'start_period_time': pt,
                    'team_side': team_side,
                    'team_name': team_name,
                    'team_code': team_code,
                    'strength': strength,
                    'manpower': ms,
                    'opponents_seen': set(),
                    'seq_ids': set(),
                    'dep_ids': set()
                }

            # Update opponents_seen for all active players currently on ice
            # Exclude goalies: only count F+D from the opponent side
            home_non_goalies = set(parsed[0] + parsed[1])  # home F + home D
            away_non_goalies = set(parsed[3] + parsed[4])  # away F + away D

            if home_set:
                for pid in home_set:
                    st = active.get(pid)
                    if st is not None:
                        st.setdefault('opponents_seen', set()).update(away_non_goalies)
            if away_set:
                for pid in away_set:
                    st = active.get(pid)
                    if st is not None:
                        st.setdefault('opponents_seen', set()).update(home_non_goalies)

            # Track sequence/deployment IDs for all active players based on current event index
            seq_id = ev_to_seq.get(int(idx))
            dep_id = ev_to_dep.get(int(idx))
            if seq_id is not None or dep_id is not None:
                for st in active.values():
                    if seq_id is not None:
                        st.setdefault('seq_ids', set()).add(int(seq_id))
                    if dep_id is not None:
                        st.setdefault('dep_ids', set()).add(int(dep_id))

            # Persist last known on-ice sets only when we have valid sets from the row
            if has_sets:
                prev_home_set, prev_away_set = home_set, away_set
            prev_gt, prev_tc_abs, prev_ptime = gt, tca, pt
            prev_shorthand = curr_short

        # Close any remaining at game end using last known timestamps
        if prev_gt is not None and prev_tc_abs is not None:
            for pid, st in list(active.items()):
                shifts.append({
                    'player_id': pid,
                    'team_side': st.get('team_side'),
                    'team': st.get('team_name'),
                    'team_code': st.get('team_code'),
                    'team_id': self._team_name_or_code_to_id(st.get('team_code')) if st.get('team_code') else None,
                    'start_game_time': st['start_gt'],
                    'end_game_time': prev_gt,
                    'shift_game_length': prev_gt - st['start_gt'] if prev_gt >= st['start_gt'] else None,
                    'start_timecode_abs': st['start_tc_abs'],
                    'end_timecode_abs': prev_tc_abs,
                    'shift_real_length': prev_tc_abs - st['start_tc_abs'] if prev_tc_abs is not None and st['start_tc_abs'] is not None else None,
                    'start_period': st.get('start_period'),
                    'end_period': st.get('start_period'),
                    'start_period_time': st.get('start_period_time'),
                    'end_period_time': prev_ptime,
                    'strength_start': st.get('strength'),
                    'manpower_start': st.get('manpower'),
                    'opponents_seen_ids': sorted(list(st.get('opponents_seen', set()))) if st.get('opponents_seen') is not None else [],
                    'sequence_ids': sorted(list(st.get('seq_ids', set()))) if st.get('seq_ids') is not None else [],
                    'deployment_ids': sorted(list(st.get('dep_ids', set()))) if st.get('dep_ids') is not None else []
                })

        # Merge micro-gaps: whistles/faceoffs where players remain on-ice should not split shifts
        MERGE_GAP_GAME_SEC = 3.0   # if next shift starts within 3s of previous end, merge
        MERGE_GAP_REAL_SEC = 5.0   # or within 5s in real time

        def merge_two(a: Dict[str, object], b: Dict[str, object]) -> Dict[str, object]:
            # Merge b into a and return a (mutated)
            # Extend end times and recompute lengths
            end_gt_a = a.get('end_game_time')
            end_tc_a = a.get('end_timecode_abs')
            end_ptime_a = a.get('end_period_time')
            end_period_a = a.get('end_period')
            end_gt_b = b.get('end_game_time')
            end_tc_b = b.get('end_timecode_abs')
            end_ptime_b = b.get('end_period_time')
            end_period_b = b.get('end_period')

            # choose max end
            a['end_game_time'] = max([x for x in [end_gt_a, end_gt_b] if x is not None]) if (end_gt_a is not None or end_gt_b is not None) else None
            a['end_timecode_abs'] = max([x for x in [end_tc_a, end_tc_b] if x is not None]) if (end_tc_a is not None or end_tc_b is not None) else None
            # prefer later period/time when available
            a['end_period'] = end_period_b if (end_period_b is not None) else end_period_a
            a['end_period_time'] = end_ptime_b if (end_ptime_b is not None) else end_ptime_a

            # recompute lengths
            if a.get('start_game_time') is not None and a.get('end_game_time') is not None:
                a['shift_game_length'] = float(a['end_game_time']) - float(a['start_game_time'])
            if a.get('start_timecode_abs') is not None and a.get('end_timecode_abs') is not None:
                a['shift_real_length'] = float(a['end_timecode_abs']) - float(a['start_timecode_abs'])

            # union id sets/lists
            for key in ('opponents_seen_ids', 'sequence_ids', 'deployment_ids'):
                aset = set(a.get(key) or [])
                bset = set(b.get(key) or [])
                a[key] = sorted(list(aset | bset))

            # clear rest fields; will be recomputed later
            a.pop('rest_game_next', None)
            a.pop('rest_real_next', None)
            return a

        # Compute rests per player (next-start minus current-end), with merge step first
        by_player: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for sh in shifts:
            by_player[str(sh['player_id'])].append(sh)

        for pid, lst in by_player.items():
            # Sort and then merge small gaps
            lst.sort(key=lambda s: (s['start_game_time'], s['end_game_time']))
            merged: List[Dict[str, object]] = []
            for sh in lst:
                if not merged:
                    merged.append(sh)
                    continue
                prev = merged[-1]
                # compute gaps (can be negative if overlaps due to midpoint end timing)
                game_gap = None
                real_gap = None
                if prev.get('end_game_time') is not None and sh.get('start_game_time') is not None:
                    game_gap = float(sh['start_game_time']) - float(prev['end_game_time'])
                if prev.get('end_timecode_abs') is not None and sh.get('start_timecode_abs') is not None:
                    real_gap = float(sh['start_timecode_abs']) - float(prev['end_timecode_abs'])
                # decide if should merge
                cond_game = (game_gap is not None and game_gap <= MERGE_GAP_GAME_SEC)
                cond_real = (real_gap is not None and real_gap <= MERGE_GAP_REAL_SEC)
                cond_overlap = (game_gap is not None and game_gap < 0) or (real_gap is not None and real_gap < 0)
                if cond_game or cond_real or cond_overlap:
                    merge_two(prev, sh)
                else:
                    merged.append(sh)

            # Replace with merged list
            by_player[pid] = merged

        # Now compute rests and running aggregates on merged lists
        for pid, lst in by_player.items():
            # Ensure sort after merges
            lst.sort(key=lambda s: (s['start_game_time'], s['end_game_time']))
            cum_toi_game = 0.0
            cum_toi_real = 0.0
            cum_rest_game = 0.0
            cum_rest_real = 0.0
            rest_count_g = 0
            rest_count_r = 0
            for i, sh in enumerate(lst):
                if i + 1 < len(lst):
                    nxt = lst[i + 1]
                    sh['rest_game_next'] = nxt['start_game_time'] - sh['end_game_time'] if (nxt.get('start_game_time') is not None and sh.get('end_game_time') is not None) else None
                    sh['rest_real_next'] = nxt.get('start_timecode_abs') - sh.get('end_timecode_abs') if (nxt.get('start_timecode_abs') is not None and sh.get('end_timecode_abs') is not None) else None
                else:
                    sh['rest_game_next'] = None
                    sh['rest_real_next'] = None
                if sh.get('shift_game_length') is not None:
                    cum_toi_game += float(sh['shift_game_length'])
                if sh.get('shift_real_length') is not None:
                    cum_toi_real += float(sh['shift_real_length'])
                sh['toi_game_to_date'] = cum_toi_game
                sh['toi_real_to_date'] = cum_toi_real
                sh['avg_shift_game_length_to_date'] = cum_toi_game / float(i + 1)
                sh['avg_shift_real_length_to_date'] = cum_toi_real / float(i + 1)
                if i > 0:
                    prev = lst[i - 1]
                    if prev.get('rest_game_next') is not None:
                        cum_rest_game += float(prev['rest_game_next'])
                        rest_count_g += 1
                    if prev.get('rest_real_next') is not None:
                        cum_rest_real += float(prev['rest_real_next'])
                        rest_count_r += 1
                sh['avg_game_rest_to_date'] = (cum_rest_game / rest_count_g) if rest_count_g > 0 else None
                sh['avg_real_rest_to_date'] = (cum_rest_real / rest_count_r) if rest_count_r > 0 else None

        # Flatten back
        all_shifts = [sh for lst in by_player.values() for sh in lst]
        return {'shifts': all_shifts}
    
    # ==========================
    # UNIQUE HOCKEY METRICS
    # ==========================

    def extract_period_openers(self) -> List[Dict]:
        """Capture the first faceoff (and deployments) of each period for both teams.
        This helps the model learn which players typically start periods.
        """
        info = self.extract_game_info()
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')
        home_team_code = self.team_name_to_code.get(home_team, info.get('home_team'))
        away_team_code = self.team_name_to_code.get(away_team, info.get('away_team'))
        home_team_id = self._team_name_or_code_to_id(home_team_code or home_team)
        away_team_id = self._team_name_or_code_to_id(away_team_code or away_team)

        period_openers: List[Dict] = []
        periods = [p for p in sorted(self.data['period'].dropna().unique().tolist()) if str(p).isdigit()]

        for p in periods:
            # Window for the given period
            period_rows = self.data[self.data['period'] == p]
            if period_rows.empty:
                continue
            # Find the first informative faceoff row in this period
            opener_idx = None
            for idx, rj in period_rows.iterrows():
                if str(rj['name']) == 'faceoff' and (not pd.isna(rj['zone']) or not pd.isna(rj['xCoord']) or not pd.isna(rj['xAdjCoord'])):
                    opener_idx = idx
                    break
            if opener_idx is None:
                # Fallback to the first "Face-Off" shorthand
                for idx, rj in period_rows.iterrows():
                    if str(rj['shorthand']) == 'Face-Off':
                        opener_idx = idx
                        break
            if opener_idx is None:
                continue

            r = self.data.loc[opener_idx]
            # Parse on-ice
            t_for = self._parse_ids(r['teamForwardsOnIceRefs'])
            t_def = self._parse_ids(r['teamDefencemenOnIceRefs'])
            o_for = self._parse_ids(r['opposingTeamForwardsOnIceRefs'])
            o_def = self._parse_ids(r['opposingTeamDefencemenOnIceRefs'])
            t_skaters = int(r['teamSkatersOnIce']) if not pd.isna(r['teamSkatersOnIce']) else None
            o_skaters = int(r['opposingTeamSkatersOnIce']) if not pd.isna(r['opposingTeamSkatersOnIce']) else None

            row_team = r['team'] if not pd.isna(r['team']) else None
            if row_team == home_team:
                home_forwards, home_defense = t_for, t_def
                away_forwards, away_defense = o_for, o_def
                home_skaters, away_skaters = t_skaters, o_skaters
            elif row_team == away_team:
                home_forwards, home_defense = o_for, o_def
                away_forwards, away_defense = t_for, t_def
                home_skaters, away_skaters = o_skaters, t_skaters
            else:
                # Fallback
                home_forwards, home_defense = o_for, o_def
                away_forwards, away_defense = t_for, t_def
                home_skaters, away_skaters = o_skaters, t_skaters

            opener = {
                'period': int(p),
                'faceoff_time': float(r['gameTime']) if not pd.isna(r['gameTime']) else None,
                'faceoff_zone': r['zone'] if not pd.isna(r['zone']) else None,
                'faceoff_shorthand': r['shorthand'] if not pd.isna(r['shorthand']) else None,
                'faceoff_flags': r['flags'] if not pd.isna(r['flags']) else None,
                'home_team_code': home_team_code,
                'away_team_code': away_team_code,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_forwards': home_forwards,
                'home_defense': home_defense,
                'away_forwards': away_forwards,
                'away_defense': away_defense,
                'home_skaters': home_skaters,
                'away_skaters': away_skaters,
                'strength': (f"{away_skaters}v{home_skaters}" if away_skaters is not None and home_skaters is not None else None)
            }
            period_openers.append(opener)

        return period_openers
    
    def extract_puck_touch_chains(self) -> Dict:
        """Extract sequences of who touched the puck"""
        chains = []
        current_chain = []
        current_possession = None
        
        for _, row in self.data.iterrows():
            if not pd.isna(row['playerReferenceId']) and row['isPossessionEvent']:
                player_id = row['playerReferenceId']
                team = row['team']
                
                # Check if possession changed
                if current_possession != row['currentPossession']:
                    if current_chain:
                        chains.append({
                            'chain': current_chain,
                            'length': len(current_chain),
                            'possession_id': current_possession
                        })
                    current_chain = [(player_id, team, row['shorthand'])]
                    current_possession = row['currentPossession']
                else:
                    current_chain.append((player_id, team, row['shorthand']))
        
        # Analyze chains
        return {
            'chains': chains[:100],  # First 100 chains
            'avg_chain_length': np.mean([c['length'] for c in chains]) if chains else 0,
            'max_chain_length': max([c['length'] for c in chains]) if chains else 0
        }
    
    def extract_pressure_cascades(self) -> Dict:
        """Extract how defensive pressure creates turnovers"""
        cascades = []
        pressure_events = ['SHOT PRESSURE', 'OZ STICK CHK+', 'BLOCK OPPOSITION PASS+', 
                          'BLOCK OPPOSITION SHOT+', 'DZ STICK CHK+']
        
        for i, row in self.data.iterrows():
            if row['shorthand'] in pressure_events:
                # Look ahead for turnover
                future_events = self.data.iloc[i:min(i+10, len(self.data))]
                
                for j, future in future_events.iterrows():
                    if future['isPossessionBreaking'] or future['isLastPlayOfPossession']:
                        cascade = {
                            'pressure_type': row['shorthand'],
                            'pressure_player': row['playerReferenceId'],
                            'pressure_zone': row['zone'],
                            'turnover_time': future['gameTime'] - row['gameTime'],
                            'turnover_type': future['shorthand'],
                            'success': future['outcome'] == 'successful'
                        }
                        cascades.append(cascade)
                        break
        
        return {
            'cascades': cascades[:50],  # First 50 cascades
            'total_pressure_events': len(cascades),
            'turnover_rate': sum(1 for c in cascades if c['success']) / len(cascades) if cascades else 0
        }
    
    def extract_entry_to_shot_time(self) -> Dict:
        """Extract speed of offensive execution from zone entry to shot"""
        entry_to_shot = []
        entry_events = ['CONTROLLED ENTRY INTO OZ', 'DUMP IN+', 'CARRY OVER REDLINE']
        shot_events = ['SLOT SHOT FOR ONNET', 'OUTSIDE SHOT FOR ONNET', 'OUTSIDE SHOT FOR MISSED']
        
        for i, row in self.data.iterrows():
            if row['shorthand'] in entry_events:
                entry_time = row['gameTime']
                entry_team = row['team']
                
                # Look for shot by same team
                future_events = self.data.iloc[i:min(i+50, len(self.data))]
                
                for _, future in future_events.iterrows():
                    if future['team'] == entry_team and future['shorthand'] in shot_events:
                        time_to_shot = future['gameTime'] - entry_time
                        entry_to_shot.append({
                            'entry_type': row['shorthand'],
                            'shot_type': future['shorthand'],
                            'time_to_shot': time_to_shot,
                            'zone': future['zone'],
                            'success': 'ONNET' in future['shorthand']
                        })
                        break
        
        successful_shots = [e for e in entry_to_shot if e['success']]
        
        return {
            'entries_with_shots': len(entry_to_shot),
            'avg_time_to_shot': np.mean([e['time_to_shot'] for e in entry_to_shot]) if entry_to_shot else 0,
            'quickest_shot': min([e['time_to_shot'] for e in entry_to_shot]) if entry_to_shot else 0,
            'shot_success_rate': len(successful_shots) / len(entry_to_shot) if entry_to_shot else 0
        }
    
    def extract_recovery_time(self) -> Dict:
        """Extract how quickly teams regain possession"""
        recoveries = []
        
        for i in range(1, len(self.data)):
            current = self.data.iloc[i]
            previous = self.data.iloc[i-1]
            
            # Check for possession change
            if (not pd.isna(current['teamInPossession']) and 
                not pd.isna(previous['teamInPossession']) and
                current['teamInPossession'] != previous['teamInPossession']):
                
                recovery_time = current['gameTime'] - previous['gameTime']
                recoveries.append({
                    'team': current['teamInPossession'],
                    'recovery_time': recovery_time,
                    'zone': current['zone'],
                    'recovery_type': current['shorthand']
                })
        
        # Group by team
        team_recoveries = defaultdict(list)
        for r in recoveries:
            if not pd.isna(r['team']):
                team_recoveries[r['team']].append(r['recovery_time'])
        
        return {
            'avg_recovery_time': {team: np.mean(times) for team, times in team_recoveries.items()},
            'quickest_recoveries': sorted(recoveries, key=lambda x: x['recovery_time'])[:10]
        }
    
    def extract_pass_network(self) -> Dict:
        """Build pass network graph for teams"""
        networks = defaultdict(lambda: nx.DiGraph())
        
        pass_events = self.data[self.data['name'] == 'pass']
        
        for i, row in pass_events.iterrows():
            if pd.isna(row['playerReferenceId']) or pd.isna(row['team']):
                continue
            
            passer = str(row['playerReferenceId'])
            team = row['team']
            
            # Look for next event to find receiver
            if i + 1 < len(self.data):
                next_event = self.data.iloc[i + 1]
                if (next_event['team'] == team and 
                    not pd.isna(next_event['playerReferenceId']) and
                    'reception' in str(next_event['name'])):
                    
                    receiver = str(next_event['playerReferenceId'])
                    
                    # Add edge to network
                    if networks[team].has_edge(passer, receiver):
                        networks[team][passer][receiver]['weight'] += 1
                    else:
                        networks[team].add_edge(passer, receiver, weight=1)
        
        # Calculate network metrics
        network_metrics = {}
        for team, G in networks.items():
            if G.number_of_nodes() > 0:
                network_metrics[team] = {
                    'nodes': G.number_of_nodes(),
                    'edges': G.number_of_edges(),
                    'avg_degree': np.mean([d for n, d in G.degree()]),
                    'most_connected': sorted(G.degree(), key=lambda x: x[1], reverse=True)[:5]
                }
        
        return network_metrics
    
    def extract_shift_momentum(self) -> Dict:
        """Track performance trajectory during shifts"""
        shift_momentum = defaultdict(list)
        
        # Track events by player during continuous ice time
        player_shifts = defaultdict(list)
        
        for _, row in self.data.iterrows():
            if pd.isna(row['teamForwardsOnIceRefs']):
                continue
            
            # Get all players on ice
            forwards = [p.strip() for p in str(row['teamForwardsOnIceRefs']).strip('\t ').split(',') if p.strip() and p.strip() != 'nan']
            defense = [p.strip() for p in str(row['teamDefencemenOnIceRefs']).strip('\t ').split(',') if p.strip() and p.strip() != 'nan']
            
            for player in forwards + defense:
                if player.strip():
                    player_shifts[player.strip()].append({
                        'time': row['gameTime'],
                        'event': row['shorthand'],
                        'outcome': row['outcome'],
                        'zone': row['zone']
                    })
        
        # Analyze momentum for each player's shifts
        for player, events in player_shifts.items():
            if len(events) > 5:
                # Calculate momentum based on positive/negative events
                momentum_score = 0
                momentum_trajectory = []
                
                for event in events:
                    if event['outcome'] == 'successful':
                        momentum_score += 1
                    elif event['outcome'] == 'failed':
                        momentum_score -= 1
                    momentum_trajectory.append(momentum_score)
                
                shift_momentum[player] = {
                    'total_events': len(events),
                    'final_momentum': momentum_score,
                    'peak_momentum': max(momentum_trajectory) if momentum_trajectory else 0,
                    'low_momentum': min(momentum_trajectory) if momentum_trajectory else 0
                }
        
        return dict(shift_momentum)
    
    def extract_whistle_to_whistle_sequences(self) -> Dict:
        """Extract complete play sequences between whistles and link deterministically to deployments.
        Adds explicit sequence_id and deployment_id and returns per-event maps for downstream attachment.
        Team-attributed outputs include zone_time, possession_time, entries/exits, shots, passes, pressure, turnovers.
        """
        sequences = []
        event_to_sequence_id: Dict[int, int] = {}
        event_to_deployment_id: Dict[int, Optional[int]] = {}

        # Find whistles
        whistle_indices = self.data[self.data['shorthand'] == 'Whistle'].index.tolist()
        if 0 not in whistle_indices:
            whistle_indices.insert(0, 0)
        if len(self.data) - 1 not in whistle_indices:
            whistle_indices.append(len(self.data) - 1)

        # Link map to deployments deterministically by whistle event index
        deployments_res = (self.results.get('whistle_deployments', {}) or {})
        deployments = deployments_res.get('deployments', [])
        dep_by_id = {int(d['deployment_id']): d for d in deployments if d.get('deployment_id') is not None}
        whistle_to_dep = {int(d['whistle_event_index']): int(d['deployment_id']) for d in deployments if d.get('whistle_event_index') is not None}

        # Resolve home/away identifiers
        info = self.results.get('game_info') or self.extract_game_info()
        home_team = info.get('home_team_name') or info.get('home_team')
        away_team = info.get('away_team_name') or info.get('away_team')
        home_code = self.team_name_to_code.get(home_team, info.get('home_team'))
        away_code = self.team_name_to_code.get(away_team, info.get('away_team'))

        def which_side(val):
            if pd.isna(val):
                return None
            s = str(val)
            # Direct matches
            if s == home_team or s == home_code:
                return 'home'
            if s == away_team or s == away_code:
                return 'away'
            # Map full name to code then compare
            code = self.team_name_to_code.get(s)
            if code == home_code:
                return 'home'
            if code == away_code:
                return 'away'
            # Try known aliases (e.g., Utah Mammoth -> UTA)
            alias_code = self.team_name_alias_to_code.get(s)
            if alias_code == home_code:
                return 'home'
            if alias_code == away_code:
                return 'away'
            return None

        # ------------------------------
        # Precompute per-event scoreboard and strength snapshot
        # ------------------------------
        n = len(self.data)
        home_score_at_start = [0] * n
        away_score_at_start = [0] * n
        home_skaters = [None] * n
        away_skaters = [None] * n
        period_list = [None] * n
        t_remain_period = [None] * n
        period_type = [None] * n
        h, a = 0, 0
        for idx, row in self.data.iterrows():
            # snapshot BEFORE applying current row
            home_score_at_start[idx] = h
            away_score_at_start[idx] = a
            # period and time remaining
            p = None if pd.isna(row['period']) else int(row['period'])
            period_list[idx] = p
            # time remaining in period (approx 20*60 sec regulation periods)
            try:
                pt_val = float(row['periodTime']) if not pd.isna(row['periodTime']) and isinstance(row['periodTime'], (int, float)) else None
            except Exception:
                pt_val = None
            if pt_val is None and 'gameTime' in self.data.columns and not pd.isna(row['gameTime']) and p is not None:
                # Fallback: compute from gameTime modulo 1200 when reliable
                try:
                    gt = float(row['gameTime'])
                    # naive remainder
                    pt_val = gt - 1200.0 * max(0, (p - 1))
                except Exception:
                    pt_val = None
            t_remain_period[idx] = (1200.0 - float(pt_val)) if (pt_val is not None) else None
            period_type[idx] = 'OT' if (p is not None and p > 3) else 'REG'
            # skaters snapshot based on current row perspective
            side = which_side(row['team'])
            try:
                ts = int(row['teamSkatersOnIce']) if 'teamSkatersOnIce' in self.data.columns and not pd.isna(row['teamSkatersOnIce']) else None
                oskat = int(row['opposingTeamSkatersOnIce']) if 'opposingTeamSkatersOnIce' in self.data.columns and not pd.isna(row['opposingTeamSkatersOnIce']) else None
            except Exception:
                ts = oskat = None
            if side == 'home':
                home_skaters[idx] = ts
                away_skaters[idx] = oskat
            elif side == 'away':
                home_skaters[idx] = oskat
                away_skaters[idx] = ts
            # apply GOAL to update for next row snapshot
            try:
                is_goal = (str(row['name']).lower() == 'goal') or ('GOAL' in str(row['shorthand']))
            except Exception:
                is_goal = False
            if is_goal:
                s = which_side(row['team'])
                if s == 'home':
                    h += 1
                elif s == 'away':
                    a += 1

        # ------------------------------
        # Micro-trends (bounded lookbacks)
        # Windows: 30s, 60s, 120s
        # Metrics: goals, shot_attempts, entries_controlled_att, entries_controlled_succ
        # Computed strictly from prior events (< current time) to avoid leakage
        # ------------------------------
        windows = {'w30': 30.0, 'w60': 60.0, 'w120': 120.0, 'w300': 300.0}
        # Allocate arrays
        def make_metric_arrays():
            return {wl: [0]*n for wl in windows.keys()}
        micro_home = {
            'goals': make_metric_arrays(),
            'shot_attempts': make_metric_arrays(),
            'entries_c_att': make_metric_arrays(),
            'entries_c_succ': make_metric_arrays(),
            'pressure_events': make_metric_arrays(),
            'turnovers': make_metric_arrays(),
        }
        micro_away = {
            'goals': make_metric_arrays(),
            'shot_attempts': make_metric_arrays(),
            'entries_c_att': make_metric_arrays(),
            'entries_c_succ': make_metric_arrays(),
            'pressure_events': make_metric_arrays(),
            'turnovers': make_metric_arrays(),
        }
        # Prepare deques per side/metric/window
        def make_metric_deques():
            return {wl: deque() for wl in windows.keys()}
        dq_home = {
            'goals': make_metric_deques(),
            'shot_attempts': make_metric_deques(),
            'entries_c_att': make_metric_deques(),
            'entries_c_succ': make_metric_deques(),
            'pressure_events': make_metric_deques(),
            'turnovers': make_metric_deques(),
        }
        dq_away = {
            'goals': make_metric_deques(),
            'shot_attempts': make_metric_deques(),
            'entries_c_att': make_metric_deques(),
            'entries_c_succ': make_metric_deques(),
            'pressure_events': make_metric_deques(),
            'turnovers': make_metric_deques(),
        }

        # Helper: shot detection
        def is_any_shot(sh: object) -> bool:
            t = str(sh)
            return 'SHOT' in t
        def is_pressure_event(sh: object) -> bool:
            t = str(sh)
            return (
                'SHOT PRESSURE' in t or 'STICK CHK+' in t or 'BLOCK OPPOSITION PASS+' in t or
                'BLOCK OPPOSITION SHOT+' in t or 'PREVENT RECEPTION DZ' in t
            )
        def is_turnover_event(sh: object) -> bool:
            t = str(sh)
            return ('FAILED PASS TRAJECTORY' in t) or (t == 'BLOCK OPPOSITION PASS-') or ('TURNOVER' in t)

        # Iterate chronologically
        for idx, row in self.data.iterrows():
            try:
                cur_time = float(row['gameTime']) if not pd.isna(row['gameTime']) else 0.0
            except Exception:
                cur_time = 0.0
            side = which_side(row['team'])

            # expire old events (<= current_time - window)
            for wl, sec in windows.items():
                for key in dq_home.keys():
                    while dq_home[key][wl] and dq_home[key][wl][0] <= cur_time - sec:
                        dq_home[key][wl].popleft()
                    while dq_away[key][wl] and dq_away[key][wl][0] <= cur_time - sec:
                        dq_away[key][wl].popleft()
                # snapshot counts BEFORE processing current row
                micro_home['goals'][wl][idx] = len(dq_home['goals'][wl])
                micro_home['shot_attempts'][wl][idx] = len(dq_home['shot_attempts'][wl])
                micro_home['entries_c_att'][wl][idx] = len(dq_home['entries_c_att'][wl])
                micro_home['entries_c_succ'][wl][idx] = len(dq_home['entries_c_succ'][wl])
                micro_away['goals'][wl][idx] = len(dq_away['goals'][wl])
                micro_away['shot_attempts'][wl][idx] = len(dq_away['shot_attempts'][wl])
                micro_away['entries_c_att'][wl][idx] = len(dq_away['entries_c_att'][wl])
                micro_away['entries_c_succ'][wl][idx] = len(dq_away['entries_c_succ'][wl])
                micro_home['pressure_events'][wl][idx] = len(dq_home['pressure_events'][wl])
                micro_home['turnovers'][wl][idx] = len(dq_home['turnovers'][wl])
                micro_away['pressure_events'][wl][idx] = len(dq_away['pressure_events'][wl])
                micro_away['turnovers'][wl][idx] = len(dq_away['turnovers'][wl])

            # Now push current event where applicable
            # Goals
            is_goal = False
            try:
                is_goal = (str(row['name']).lower() == 'goal') or ('GOAL' in str(row['shorthand']))
            except Exception:
                is_goal = False
            if is_goal and side in ('home','away'):
                for wl in windows.keys():
                    if side == 'home':
                        dq_home['goals'][wl].append(cur_time)
                    else:
                        dq_away['goals'][wl].append(cur_time)

            # Shot attempts (any shot)
            if is_any_shot(row['shorthand']) and side in ('home','away'):
                for wl in windows.keys():
                    if side == 'home':
                        dq_home['shot_attempts'][wl].append(cur_time)
                    else:
                        dq_away['shot_attempts'][wl].append(cur_time)

            # Pressure events
            if is_pressure_event(row['shorthand']) and side in ('home','away'):
                for wl in windows.keys():
                    if side == 'home':
                        dq_home['pressure_events'][wl].append(cur_time)
                    else:
                        dq_away['pressure_events'][wl].append(cur_time)

            # Controlled entry attempts/success (attacker is opposite of row team)
            name_l = str(row['name']).lower()
            sh_s = str(row['shorthand'])
            is_cea = ('CONTROLLED ENTRY AGAINST' in sh_s) or (name_l == 'controlledentryagainst')
            if is_cea:
                def_side = side
                if def_side in ('home','away'):
                    att_side = 'home' if def_side == 'away' else 'away'
                    for wl in windows.keys():
                        if att_side == 'home':
                            dq_home['entries_c_att'][wl].append(cur_time)
                            if not pd.isna(row['outcome']) and str(row['outcome']).lower() == 'successful':
                                dq_home['entries_c_succ'][wl].append(cur_time)
                        else:
                            dq_away['entries_c_att'][wl].append(cur_time)
                            if not pd.isna(row['outcome']) and str(row['outcome']).lower() == 'successful':
                                dq_away['entries_c_succ'][wl].append(cur_time)
            # Turnovers (from defender perspective patterns)
            if is_turnover_event(row['shorthand']) and side in ('home','away'):
                # Turnover credited to the side specified (defensive success), so count against attacker implicitly
                for wl in windows.keys():
                    if side == 'home':
                        dq_home['turnovers'][wl].append(cur_time)
                    else:
                        dq_away['turnovers'][wl].append(cur_time)

        ENTRY_CTRL = {'CONTROLLED ENTRY INTO OZ', 'OZ ENTRY PASS+', 'O-ZONE ENTRY PASS RECEPTION'}
        ENTRY_DUMP = {'DUMP IN+', 'CHIP DUMP+', 'HI PRESS DUMP IN LPR+', 'DUMP IN LPR+', 'OFF LPR OZ', 'OZ REC FACE OFF+'}
        EXIT_CTRL = {'CONTROLLED EXIT FROM DZ'}
        EXIT_DUMP = {'DUMP OUT+', 'OFF GLASS DUMP OUT+', 'FLIP DUMP OUT+', 'DZ REC FACE OFF+EXIT'}
        LPR_POS = {'LPR+ DZ', 'LPR+ NZ', 'LPR+ OZ', 'REB LPR OZ+', 'LPRREB+', 'CONT REB LPR OZ+'}
        PRESSURE_POS = {'SHOT PRESSURE', 'OZ STICK CHK+', 'DZ STICK CHK+', 'BLOCK OPPOSITION PASS+', 'BLOCK OPPOSITION SHOT+', 'PREVENT RECEPTION DZ'}

        def shot_class(s):
            t = str(s)
            return (
                ('ONNET' in t),
                ('MISSED' in t),
                ('BLOCKED' in t),
                ('SHOT' in t)
            )

        for i in range(len(whistle_indices) - 1):
            sidx = int(whistle_indices[i])
            eidx = int(whistle_indices[i + 1])
            df = self.data.iloc[sidx:eidx]
            if len(df) < 2:
                continue
            sequence_id = i
            deployment_id = whistle_to_dep.get(sidx)

            st = float(df.iloc[0]['gameTime']) if not pd.isna(df.iloc[0]['gameTime']) else None
            et = float(df.iloc[-1]['gameTime']) if not pd.isna(df.iloc[-1]['gameTime']) else None
            spt = float(df.iloc[0]['periodTime']) if ('periodTime' in df.columns and not pd.isna(df.iloc[0]['periodTime'])) else None
            ept = float(df.iloc[-1]['periodTime']) if ('periodTime' in df.columns and not pd.isna(df.iloc[-1]['periodTime'])) else None
            sp = int(df.iloc[0]['period']) if not pd.isna(df.iloc[0]['period']) else None
            ep = int(df.iloc[-1]['period']) if not pd.isna(df.iloc[-1]['period']) else None

            zone_time = {'oz': 0.0, 'nz': 0.0, 'dz': 0.0}
            home_zone_time = {'oz': 0.0, 'nz': 0.0, 'dz': 0.0}
            away_zone_time = {'oz': 0.0, 'nz': 0.0, 'dz': 0.0}
            shots_on, shots_miss, shots_blk, shots_tot = 0, 0, 0, 0
            home_shots = {'on': 0, 'missed': 0, 'blocked': 0, 'total': 0}
            away_shots = {'on': 0, 'missed': 0, 'blocked': 0, 'total': 0}
            passes_tot = int((df['name'].astype(str) == 'pass').sum())
            home_passes = int(((df['name'].astype(str) == 'pass') & (df['team'].apply(which_side) == 'home')).sum())
            away_passes = int(((df['name'].astype(str) == 'pass') & (df['team'].apply(which_side) == 'away')).sum())
            ent_c, ent_d, ex_c, ex_d = 0, 0, 0, 0
            home_ent_c_attempts = home_ent_c_success = 0
            home_ent_d_attempts = 0
            away_ent_c_attempts = away_ent_c_success = 0
            away_ent_d_attempts = 0
            home_ex_c_attempts = home_ex_c_success = 0
            home_ex_d_attempts = 0
            away_ex_c_attempts = away_ex_c_success = 0
            away_ex_d_attempts = 0
            lpr_rec, pressure_cnt = 0, 0
            home_lpr = away_lpr = 0
            home_pressure = away_pressure = 0
            turnovers = 0
            home_turnovers = away_turnovers = 0
            poss_time_home = poss_time_away = 0.0
            zones_order = []

            for j in range(len(df) - 1):
                cur, nxt = df.iloc[j], df.iloc[j + 1]
                z = None if pd.isna(cur['zone']) else str(cur['zone'])
                if z and z not in zones_order:
                    zones_order.append(z)
                if not pd.isna(cur['gameTime']) and not pd.isna(nxt['gameTime']) and z in zone_time:
                    dt = float(nxt['gameTime']) - float(cur['gameTime'])
                    if dt > 0:
                        zone_time[z] += dt
                        side = which_side(cur['team'])
                        # Attribute OZ/DZ time to both teams consistently; NZ to both equally
                        if z == 'nz':
                            home_zone_time['nz'] += dt
                            away_zone_time['nz'] += dt
                        elif z == 'oz':
                            if side == 'home':
                                home_zone_time['oz'] += dt
                                away_zone_time['dz'] += dt
                            elif side == 'away':
                                away_zone_time['oz'] += dt
                                home_zone_time['dz'] += dt
                        elif z == 'dz':
                            if side == 'home':
                                home_zone_time['dz'] += dt
                                away_zone_time['oz'] += dt
                            elif side == 'away':
                                away_zone_time['dz'] += dt
                                home_zone_time['oz'] += dt
                        # possession time by teamInPossession
                        pos_side = which_side(cur['teamInPossession'])
                        if pos_side == 'home':
                            poss_time_home += dt
                        elif pos_side == 'away':
                            poss_time_away += dt
                sh = cur['shorthand']
                on, miss, blk, anyshot = shot_class(sh)
                if anyshot:
                    shots_tot += 1
                    if on: shots_on += 1
                    elif miss: shots_miss += 1
                    elif blk: shots_blk += 1
                    side = which_side(cur['team'])
                    if side == 'home':
                        home_shots['total'] += 1
                        if on: home_shots['on'] += 1
                        elif miss: home_shots['missed'] += 1
                        elif blk: home_shots['blocked'] += 1
                    elif side == 'away':
                        away_shots['total'] += 1
                        if on: away_shots['on'] += 1
                        elif miss: away_shots['missed'] += 1
                        elif blk: away_shots['blocked'] += 1
                if sh in ENTRY_CTRL: ent_c += 1
                elif sh in ENTRY_DUMP: ent_d += 1
                if sh in EXIT_CTRL: ex_c += 1
                elif sh in EXIT_DUMP: ex_d += 1
                # Team-attributed entries/exits (attempts) and successes via outcome == 'successful'
                side = which_side(cur['team'])
                outcome_success = (not pd.isna(cur['outcome']) and str(cur['outcome']).lower() == 'successful')
                # Controlled entry attempts should be sourced from the
                # "CONTROLLED ENTRY AGAINST" events which encode both
                # attempts and outcomes (successful vs failed). The
                # ENTRY_CTRL events above represent successful entries
                # only and would double-count attempts if used.
                if ('CONTROLLED ENTRY AGAINST' in str(sh)) or (str(cur['name']).lower() == 'controlledentryagainst'):
                    # The event is recorded from defender's perspective (team on ice)
                    # so attacker is the opposite side
                    def_side = side
                    att_side = 'home' if def_side == 'away' else 'away'
                    if att_side == 'home':
                        home_ent_c_attempts += 1
                        if outcome_success:
                            home_ent_c_success += 1
                    elif att_side == 'away':
                        away_ent_c_attempts += 1
                        if outcome_success:
                            away_ent_c_success += 1
                elif sh in ENTRY_CTRL:
                    # Keep sequence counters, but do not touch attempts/success tallies
                    pass
                elif sh in ENTRY_DUMP:
                    if side == 'home':
                        home_ent_d_attempts += 1
                    elif side == 'away':
                        away_ent_d_attempts += 1
                if sh in EXIT_CTRL:
                    if side == 'home':
                        home_ex_c_attempts += 1
                        if outcome_success: home_ex_c_success += 1
                    elif side == 'away':
                        away_ex_c_attempts += 1
                        if outcome_success: away_ex_c_success += 1
                elif sh in EXIT_DUMP:
                    if side == 'home':
                        home_ex_d_attempts += 1
                    elif side == 'away':
                        away_ex_d_attempts += 1
                # Recoveries / pressure / turnovers per team
                if (sh in LPR_POS) or ('LPR+' in str(sh)):
                    lpr_rec += 1
                    if side == 'home':
                        home_lpr += 1
                    elif side == 'away':
                        away_lpr += 1
                if sh in PRESSURE_POS:
                    pressure_cnt += 1
                    if side == 'home':
                        home_pressure += 1
                    elif side == 'away':
                        away_pressure += 1
                if 'FAILED PASS TRAJECTORY' in str(sh) or sh == 'BLOCK OPPOSITION PASS-':
                    turnovers += 1
                    if side == 'home':
                        home_turnovers += 1
                    elif side == 'away':
                        away_turnovers += 1

            # Neutral zone is neutral: mirror total NZ time to both teams
            nz_total = zone_time.get('nz', 0.0)
            home_zone_time['nz'] = nz_total
            away_zone_time['nz'] = nz_total

            # Game state snapshots
            hs_before = home_score_at_start[sidx]
            as_before = away_score_at_start[sidx]
            hs_after = home_score_at_start[eidx] if eidx < n else home_score_at_start[-1]
            as_after = away_score_at_start[eidx] if eidx < n else away_score_at_start[-1]
            hsk_before = home_skaters[sidx]
            ask_before = away_skaters[sidx]
            hsk_after = home_skaters[eidx-1] if eidx-1 < n and eidx-1 >=0 else home_skaters[sidx]
            ask_after = away_skaters[eidx-1] if eidx-1 < n and eidx-1 >=0 else away_skaters[sidx]

            # Build microtrend-60 snapshots for convenience
            mt_wl = 'w60'
            mt_before = {
                'home': {
                    'goals': micro_home['goals'][mt_wl][sidx],
                    'shot_attempts': micro_home['shot_attempts'][mt_wl][sidx],
                    'entries_c_att': micro_home['entries_c_att'][mt_wl][sidx],
                    'entries_c_succ': micro_home['entries_c_succ'][mt_wl][sidx],
                    'pressure_events': micro_home['pressure_events'][mt_wl][sidx],
                    'turnovers': micro_home['turnovers'][mt_wl][sidx],
                },
                'away': {
                    'goals': micro_away['goals'][mt_wl][sidx],
                    'shot_attempts': micro_away['shot_attempts'][mt_wl][sidx],
                    'entries_c_att': micro_away['entries_c_att'][mt_wl][sidx],
                    'entries_c_succ': micro_away['entries_c_succ'][mt_wl][sidx],
                    'pressure_events': micro_away['pressure_events'][mt_wl][sidx],
                    'turnovers': micro_away['turnovers'][mt_wl][sidx],
                }
            }
            idx_after = eidx if eidx < n else (n-1)
            mt_after = {
                'home': {
                    'goals': micro_home['goals'][mt_wl][idx_after],
                    'shot_attempts': micro_home['shot_attempts'][mt_wl][idx_after],
                    'entries_c_att': micro_home['entries_c_att'][mt_wl][idx_after],
                    'entries_c_succ': micro_home['entries_c_succ'][mt_wl][idx_after],
                    'pressure_events': micro_home['pressure_events'][mt_wl][idx_after],
                    'turnovers': micro_home['turnovers'][mt_wl][idx_after],
                },
                'away': {
                    'goals': micro_away['goals'][mt_wl][idx_after],
                    'shot_attempts': micro_away['shot_attempts'][mt_wl][idx_after],
                    'entries_c_att': micro_away['entries_c_att'][mt_wl][idx_after],
                    'entries_c_succ': micro_away['entries_c_succ'][mt_wl][idx_after],
                    'pressure_events': micro_away['pressure_events'][mt_wl][idx_after],
                    'turnovers': micro_away['turnovers'][mt_wl][idx_after],
                }
            }

            seq = {
                'sequence_id': sequence_id,
                'deployment_id': deployment_id,
                'start_whistle_index': sidx,
                'end_whistle_index': eidx,
                'length': int(len(df)),
                'duration': (et - st) if (st is not None and et is not None) else None,
                'start_period': sp,
                'end_period': ep,
                'start_game_time': st,
                'end_game_time': et,
                'start_period_time': spt,
                'end_period_time': ept,
                'zones_visited': list(pd.Series(zones_order).dropna().unique()),
                'game_state_before': {
                    'home_score': hs_before,
                    'away_score': as_before,
                    'score_diff': (hs_before - as_before) if (hs_before is not None and as_before is not None) else None,
                    'home_skaters': hsk_before,
                    'away_skaters': ask_before,
                    'strength': (f"{hsk_before}v{ask_before}" if (hsk_before is not None and ask_before is not None) else None),
                    'period': sp,
                    'time_remaining_period': (1200.0 - float(spt)) if spt is not None else None,
                    'period_type': 'OT' if (sp is not None and sp > 3) else 'REG',
                    'microtrend_60': mt_before,
                },
                'game_state_after': {
                    'home_score': hs_after,
                    'away_score': as_after,
                    'score_diff': (hs_after - as_after) if (hs_after is not None and as_after is not None) else None,
                    'home_skaters': hsk_after,
                    'away_skaters': ask_after,
                    'strength': (f"{hsk_after}v{ask_after}" if (hsk_after is not None and ask_after is not None) else None),
                    'period': ep,
                    'time_remaining_period': (1200.0 - float(ept)) if ept is not None else None,
                    'period_type': 'OT' if (ep is not None and ep > 3) else 'REG',
                    'microtrend_60': mt_after,
                },
                'home': {
                    'zone_time': home_zone_time,
                    'possession_time': poss_time_home,
                    'entries': {
                        'controlled_attempts': home_ent_c_attempts,
                        'controlled_success': home_ent_c_success,
                        'dump_attempts': home_ent_d_attempts
                    },
                    'exits': {
                        'controlled_attempts': home_ex_c_attempts,
                        'controlled_success': home_ex_c_success,
                        'dump_attempts': home_ex_d_attempts
                    },
                    'shots': home_shots,
                    'passes': home_passes,
                    'lpr_recoveries': home_lpr,
                    'pressure_events': home_pressure,
                    'turnovers': home_turnovers
                },
                'away': {
                    'zone_time': away_zone_time,
                    'possession_time': poss_time_away,
                    'entries': {
                        'controlled_attempts': away_ent_c_attempts,
                        'controlled_success': away_ent_c_success,
                        'dump_attempts': away_ent_d_attempts
                    },
                    'exits': {
                        'controlled_attempts': away_ex_c_attempts,
                        'controlled_success': away_ex_c_success,
                        'dump_attempts': away_ex_d_attempts
                    },
                    'shots': away_shots,
                    'passes': away_passes,
                    'lpr_recoveries': away_lpr,
                    'pressure_events': away_pressure,
                    'turnovers': away_turnovers
                },
                'possession_changes': int(df['teamInPossession'].dropna().nunique()),
                'shots_total': shots_tot,
                'shots_on_net': shots_on,
                'shots_missed': shots_miss,
                'shots_blocked': shots_blk,
                'passes': passes_tot,
                'oz_entries_controlled': ent_c,
                'oz_entries_dump': ent_d,
                'dz_exits_controlled': ex_c,
                'dz_exits_dump': ex_d,
                'lpr_recoveries': lpr_rec,
                'pressure_events': pressure_cnt,
                'turnovers': turnovers,
                'start_zone': None if pd.isna(df.iloc[0]['zone']) else df.iloc[0]['zone'],
                'end_zone': None if pd.isna(df.iloc[-1]['zone']) else df.iloc[-1]['zone'],
            }

            if deployment_id is not None and deployment_id in dep_by_id:
                d = dep_by_id[deployment_id]
                seq.update({
                    'deployment_strength': d.get('strength'),
                    'deployment_home_zone': d.get('home_zone'),
                    'deployment_away_zone': d.get('away_zone'),
                    'deployment_home_team_id': d.get('home_team_id'),
                    'deployment_away_team_id': d.get('away_team_id')
                })

            sequences.append(seq)

            # Fill per-event maps for downstream attachment
            for ev_idx in range(sidx, eidx):
                event_to_sequence_id[ev_idx] = sequence_id
                event_to_deployment_id[ev_idx] = deployment_id
        return {
            'sequences': sequences,
            'event_to_sequence_id': event_to_sequence_id,
            'event_to_deployment_id': event_to_deployment_id,
            'scoreboard': {
                'home_score': home_score_at_start,
                'away_score': away_score_at_start,
                'home_skaters': home_skaters,
                'away_skaters': away_skaters,
                'period': period_list,
                'time_remaining_period': t_remain_period,
                'period_type': period_type,
            },
            'microtrends': {
                'windows_sec': windows,
                'home': micro_home,
                'away': micro_away,
            }
        }
    
    def extract_player_tendencies(self) -> Dict:
        """Extract individual player tendencies and preferences"""
        player_tendencies = defaultdict(lambda: {
            'preferred_zones': defaultdict(int),
            'preferred_actions': defaultdict(int),
            'success_by_action': defaultdict(lambda: {'success': 0, 'total': 0}),
            'preferred_shot_location': defaultdict(int),
            'events': []  # per-event timeline for this player
        })
        
        for _, row in self.data.iterrows():
            if pd.isna(row['playerReferenceId']):
                continue
            
            player = str(row['playerReferenceId'])
            
            # Track zones
            if not pd.isna(row['zone']):
                player_tendencies[player]['preferred_zones'][row['zone']] += 1
            
            # Track actions
            if not pd.isna(row['shorthand']):
                player_tendencies[player]['preferred_actions'][row['shorthand']] += 1
                
                # Track success rate
                if not pd.isna(row['outcome']):
                    player_tendencies[player]['success_by_action'][row['shorthand']]['total'] += 1
                    if row['outcome'] == 'successful':
                        player_tendencies[player]['success_by_action'][row['shorthand']]['success'] += 1
            
            # Track shot locations
            if 'shot' in str(row['name']).lower() and not pd.isna(row['playSection']):
                player_tendencies[player]['preferred_shot_location'][row['playSection']] += 1
            
            # Build on-ice actor context
            team_forwards = self._parse_ids(row['teamForwardsOnIceRefs']) if 'teamForwardsOnIceRefs' in self.data.columns and not pd.isna(row['teamForwardsOnIceRefs']) else []
            team_defence = self._parse_ids(row['teamDefencemenOnIceRefs']) if 'teamDefencemenOnIceRefs' in self.data.columns and not pd.isna(row['teamDefencemenOnIceRefs']) else []
            opp_forwards = self._parse_ids(row['opposingTeamForwardsOnIceRefs']) if 'opposingTeamForwardsOnIceRefs' in self.data.columns and not pd.isna(row['opposingTeamForwardsOnIceRefs']) else []
            opp_defence = self._parse_ids(row['opposingTeamDefencemenOnIceRefs']) if 'opposingTeamDefencemenOnIceRefs' in self.data.columns and not pd.isna(row['opposingTeamDefencemenOnIceRefs']) else []
            team_goalie = self._norm_id(row['teamGoalieOnIceRef']) if 'teamGoalieOnIceRef' in self.data.columns and not pd.isna(row['teamGoalieOnIceRef']) else ''
            opp_goalie = self._norm_id(row['opposingTeamGoalieOnIceRef']) if 'opposingTeamGoalieOnIceRef' in self.data.columns and not pd.isna(row['opposingTeamGoalieOnIceRef']) else ''
            team_on_ice = team_forwards + team_defence + ([team_goalie] if team_goalie else [])
            opp_on_ice = opp_forwards + opp_defence + ([opp_goalie] if opp_goalie else [])
            team_trio = team_forwards if len(team_forwards) == 3 else None
            team_pair = team_defence if len(team_defence) == 2 else None
            opp_trio = opp_forwards if len(opp_forwards) == 3 else None
            opp_pair = opp_defence if len(opp_defence) == 2 else None

            # Append per-event timeline entry
            event_entry = {
                'event_index': int(row.name) if isinstance(row.name, (int,)) else None,
                'period': int(row['period']) if not pd.isna(row['period']) else None,
                'periodTime': row['periodTime'] if 'periodTime' in self.data.columns else None,
                'gameTime': row['gameTime'] if 'gameTime' in self.data.columns else None,
                'timecode': row['timecode'] if 'timecode' in self.data.columns else None,
                'team': None if pd.isna(row['team']) else row['team'],
                'zone': None if pd.isna(row['zone']) else row['zone'],
                'playSection': None if 'playSection' not in self.data.columns or pd.isna(row['playSection']) else row['playSection'],
                'name': None if pd.isna(row['name']) else row['name'],
                'shorthand': None if pd.isna(row['shorthand']) else row['shorthand'],
                'outcome': row['outcome'] if 'outcome' in self.data.columns else None,
                'flags': None if pd.isna(row['flags']) else row['flags'],
                'x': float(row['xCoord']) if 'xCoord' in self.data.columns and not pd.isna(row['xCoord']) else None,
                'y': float(row['yCoord']) if 'yCoord' in self.data.columns and not pd.isna(row['yCoord']) else None,
                'x_adj': float(row['xAdjCoord']) if 'xAdjCoord' in self.data.columns and not pd.isna(row['xAdjCoord']) else None,
                'y_adj': float(row['yAdjCoord']) if 'yAdjCoord' in self.data.columns and not pd.isna(row['yAdjCoord']) else None,
                'teammates_on_ice_ids': team_on_ice if team_on_ice else None,
                'opponents_on_ice_ids': opp_on_ice if opp_on_ice else None,
                'team_trio_id': team_trio,
                'team_pair_id': team_pair,
                'opponent_trio_id': opp_trio,
                'opponent_pair_id': opp_pair,
                'team_goalie_id': team_goalie if team_goalie else None,
                'opponent_goalie_id': opp_goalie if opp_goalie else None
            }
            player_tendencies[player]['events'].append(event_entry)
        
        # Calculate summary statistics and keep full action counts
        summary = {}
        for player, tendencies in player_tendencies.items():
            # Get top preferences
            top_zones = sorted(tendencies['preferred_zones'].items(), 
                             key=lambda x: x[1], reverse=True)[:3]
            top_actions = sorted(tendencies['preferred_actions'].items(), 
                               key=lambda x: x[1], reverse=True)[:5]

            # Calculate success rates and keep raw success counters
            action_success_rate = {}
            raw_success_map = {}
            for action, stats in tendencies['success_by_action'].items():
                total = stats['total']
                succ = stats['success']
                if total > 0:
                    action_success_rate[action] = succ / total
                raw_success_map[action] = {'success': succ, 'total': total}

            # Sort per-player events by time for ordered timeline
            ordered_events = sorted(
                tendencies['events'],
                key=lambda e: (e['gameTime'] if e['gameTime'] is not None else float('inf'),
                               e['event_index'] if e['event_index'] is not None else float('inf'))
            )

            summary[player] = {
                'top_zones': top_zones,
                'top_actions': top_actions,
                'best_success_action': max(action_success_rate.items(), key=lambda x: x[1])
                    if action_success_rate else None,
                'total_events': sum(tendencies['preferred_actions'].values()),
                # Full per-action counts for downstream saving
                'actions': dict(tendencies['preferred_actions']),
                'success_by_action': raw_success_map,
                # Full per-event timeline
                'events': ordered_events
            }

        return summary
    
    def run_complete_extraction(self) -> Dict:
        """Run all extraction methods and compile results"""
        print("Starting comprehensive extraction...")
        
        # Load data
        self.load_data()
        
        # Game info
        print("Extracting game info...")
        self.results['game_info'] = self.extract_game_info()
        
        # Matchup data
        print("Extracting individual matchups (shift-based)...")
        self.results['individual_matchups'] = self.extract_individual_matchups()
        
        print("Extracting matchup durations and detailed metrics...")
        self.results['matchup_durations'] = self.extract_matchup_durations()
        
        print("Extracting line vs defense pairing matchups...")
        self.results['line_vs_dpair'] = self.extract_line_vs_dpair_matchups()
        
        print("Extracting defense pairing vs line matchups...")
        self.results['dpair_vs_line'] = self.extract_dpair_vs_line_matchups()
        
        # Deployment analysis
        print("Extracting whistle deployments...")
        self.results['whistle_deployments'] = self.extract_whistle_deployments()
        
        print("Extracting rotation patterns...")
        self.results['rotation_patterns'] = self.extract_rotation_patterns()
        
        print("Extracting line rotation sequence...")
        self.results['line_rotation_sequence'] = self.extract_line_rotation_sequence()
        
        # Unique hockey metrics
        print("Extracting puck touch chains...")
        self.results['puck_touch_chains'] = self.extract_puck_touch_chains()
        
        print("Extracting pressure cascades...")
        self.results['pressure_cascades'] = self.extract_pressure_cascades()
        
        print("Extracting entry to shot times...")
        self.results['entry_to_shot'] = self.extract_entry_to_shot_time()
        
        print("Extracting recovery times...")
        self.results['recovery_time'] = self.extract_recovery_time()
        
        print("Building pass networks...")
        self.results['pass_networks'] = self.extract_pass_network()
        
        print("Analyzing shift momentum...")
        self.results['shift_momentum'] = self.extract_shift_momentum()
        
        print("Extracting whistle-to-whistle sequences...")
        ws = self.extract_whistle_to_whistle_sequences()
        self.results['whistle_sequences'] = ws
        
        # Team rotation events (team-agnostic with replacements), requires whistle_sequences for linkage
        print("Extracting team rotation events...")
        self.results['team_rotation_events'] = self.extract_team_rotation_events()
        
        print("Analyzing player tendencies...")
        self.results['player_tendencies'] = self.extract_player_tendencies()

        print("Extracting period openers...")
        self.results['period_openers'] = self.extract_period_openers()
        
        print("Extracting player shifts...")
        self.results['player_shifts'] = self.extract_player_shifts()
        
        print("Extraction complete!")
        return dict(self.results)
    
    def generate_matchup_summary(self) -> Dict:
        """Generate a summary of matchup statistics"""
        if 'individual_matchups' not in self.results:
            return {}
        
        summary = {
            'total_unique_matchups': sum(len(m) for m in self.results['individual_matchups'].values()),
            'by_type': {}
        }
        
        # Analyze each matchup type
        for matchup_type, matchups in self.results['individual_matchups'].items():
            if matchups:
                values = list(matchups.values())
                summary['by_type'][matchup_type] = {
                    'count': len(matchups),
                    'avg_appearances': np.mean(values),
                    'max_appearances': max(values),
                    'min_appearances': min(values)
                }
        
        # Add player shift estimates (assuming 5v5)
        if 'F_vs_F' in self.results['individual_matchups']:
            # Estimate shifts per player based on matchup appearances
            player_appearances = defaultdict(int)
            for matchup_key in self.results['individual_matchups']['F_vs_F'].keys():
                players = matchup_key.split('_vs_')
                for player in players:
                    player_appearances[player] += 1
            
            if player_appearances:
                avg_opponents = np.mean(list(player_appearances.values()))
                summary['estimated_avg_opponents_per_player'] = avg_opponents
                summary['estimated_shifts_per_player'] = avg_opponents / 3  # Rough estimate
        
        return summary
    
    def save_results(self, output_dir: str = 'data/processed/extracted_metrics'):
        """Save extraction results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from input
        game_id = Path(self.pbp_file).stem
        
        # Save main results as JSON
        output_file = output_path / f"{game_id}_comprehensive_metrics.json"
        with open(output_file, 'w') as f:
            # Convert to strict JSON (null instead of NaN/Infinity) and cast numpy types
            serializable_results = self._json_safe(self.results)
            json.dump(serializable_results, f, indent=2, allow_nan=False)
        
        print(f"Results saved to {output_file}")
        
        # Save specific CSV files for key metrics
        
        # Individual matchups
        if 'individual_matchups' in self.results:
            for matchup_type, matchups in self.results['individual_matchups'].items():
                df = pd.DataFrame.from_dict(matchups, orient='index', columns=['time_together'])
                df.to_csv(output_path / f"{game_id}_{matchup_type}_matchups.csv")
        
        # Player tendencies - detailed per-action counts per player (long form)
        if 'player_tendencies' in self.results:
            action_rows = []
            timeline_rows = []
            # Pull mapping dicts for event->sequence/deployment and scoreboard
            ws = self.results.get('whistle_sequences', {})
            ev_to_seq = ws.get('event_to_sequence_id', {}) if isinstance(ws, dict) else {}
            ev_to_dep = ws.get('event_to_deployment_id', {}) if isinstance(ws, dict) else {}
            sb = ws.get('scoreboard', {}) if isinstance(ws, dict) else {}
            sb_home = sb.get('home_score', [])
            sb_away = sb.get('away_score', [])
            sb_hsk = sb.get('home_skaters', [])
            sb_ask = sb.get('away_skaters', [])
            sb_trp = sb.get('time_remaining_period', [])
            sb_ptype = sb.get('period_type', [])
            for player, pdata in self.results['player_tendencies'].items():
                total_events = pdata.get('total_events', 0)
                # Use the summarized full per-action map saved as 'actions'
                action_counts = pdata.get('actions', {})
                success_map = pdata.get('success_by_action', {})
                for action, count in action_counts.items():
                    succ_info = success_map.get(action, {'success': 0, 'total': count})
                    succ_count = succ_info.get('success', 0)
                    attempts = succ_info.get('total', count)
                    succ_rate = (succ_count / attempts) if attempts else None
                    action_rows.append({
                        'player_id': player,
                        'action': action,
                        'count': count,
                        'success': succ_count,
                        'attempts': attempts,
                        'success_rate': succ_rate,
                        'total_player_events': total_events
                    })
                # Build timeline rows
                for ev in pdata.get('events', []):
                    ei = ev.get('event_index')
                    hs = sb_home[ei] if (ei is not None and ei < len(sb_home)) else None
                    as_ = sb_away[ei] if (ei is not None and ei < len(sb_away)) else None
                    hsk = sb_hsk[ei] if (ei is not None and ei < len(sb_hsk)) else None
                    ask = sb_ask[ei] if (ei is not None and ei < len(sb_ask)) else None
                    trp = sb_trp[ei] if (ei is not None and ei < len(sb_trp)) else None
                    ptyp = sb_ptype[ei] if (ei is not None and ei < len(sb_ptype)) else None
                    # Microtrend 60s values at event index (home/away)
                    mt = ws.get('microtrends', {}) if isinstance(ws, dict) else {}
                    def get_mt(m_side: str, metric: str) -> int | None:
                        try:
                            arr = mt.get(m_side, {}).get(metric, {}).get('w60', [])
                            return arr[ei] if (ei is not None and ei < len(arr)) else None
                        except Exception:
                            return None
                    h_w60_goals = get_mt('home', 'goals')
                    h_w60_shots = get_mt('home', 'shot_attempts')
                    h_w60_e_att = get_mt('home', 'entries_c_att')
                    h_w60_e_suc = get_mt('home', 'entries_c_succ')
                    h_w60_press = get_mt('home', 'pressure_events')
                    h_w60_turn = get_mt('home', 'turnovers')
                    a_w60_goals = get_mt('away', 'goals')
                    a_w60_shots = get_mt('away', 'shot_attempts')
                    a_w60_e_att = get_mt('away', 'entries_c_att')
                    a_w60_e_suc = get_mt('away', 'entries_c_succ')
                    a_w60_press = get_mt('away', 'pressure_events')
                    a_w60_turn = get_mt('away', 'turnovers')
                    timeline_rows.append({
                        'player_id': player,
                        'period': ev.get('period'),
                        'periodTime': ev.get('periodTime'),
                        'gameTime': ev.get('gameTime'),
                        'timecode': ev.get('timecode'),
                        'team': ev.get('team'),
                        'team_code': self.team_name_to_code.get(ev.get('team')) if ev.get('team') else None,
                        'team_id': self._team_name_or_code_to_id(self.team_name_to_code.get(ev.get('team')) if ev.get('team') else None),
                        'zone': ev.get('zone'),
                        'name': ev.get('name'),
                        'action': ev.get('shorthand'),
                        'outcome': ev.get('outcome'),
                        'flags': ev.get('flags'),
                        'x': ev.get('x'),
                        'y': ev.get('y'),
                        'x_adj': ev.get('x_adj'),
                        'y_adj': ev.get('y_adj'),
                        'teammates_on_ice_ids': ev.get('teammates_on_ice_ids'),
                        'opponents_on_ice_ids': ev.get('opponents_on_ice_ids'),
                        'team_trio_id': ev.get('team_trio_id'),
                        'team_pair_id': ev.get('team_pair_id'),
                        'opponent_trio_id': ev.get('opponent_trio_id'),
                        'opponent_pair_id': ev.get('opponent_pair_id'),
                        'team_goalie_id': ev.get('team_goalie_id'),
                        'opponent_goalie_id': ev.get('opponent_goalie_id'),
                        'sequence_id': ev_to_seq.get(ev.get('event_index')),
                        'deployment_id': ev_to_dep.get(ev.get('event_index')),
                        # Scoreboard snapshot at this event
                        'home_score': hs,
                        'away_score': as_,
                        'score_diff': (hs - as_) if (hs is not None and as_ is not None) else None,
                        'home_skaters': hsk,
                        'away_skaters': ask,
                        'time_remaining_period': trp,
                        'period_type': ptyp,
                        # Microtrend 60s counts (home/away)
                        'home_w60_goals': h_w60_goals,
                        'home_w60_shot_attempts': h_w60_shots,
                        'home_w60_entries_c_att': h_w60_e_att,
                        'home_w60_entries_c_succ': h_w60_e_suc,
                        'home_w60_pressure_events': h_w60_press,
                        'home_w60_turnovers': h_w60_turn,
                        'away_w60_goals': a_w60_goals,
                        'away_w60_shot_attempts': a_w60_shots,
                        'away_w60_entries_c_att': a_w60_e_att,
                        'away_w60_entries_c_succ': a_w60_e_suc,
                        'away_w60_pressure_events': a_w60_press,
                        'away_w60_turnovers': a_w60_turn,
                    })
            if action_rows:
                pd.DataFrame(action_rows).to_csv(
                    output_path / f"{game_id}_player_tendencies.csv", index=False
                )
            if timeline_rows:
                df_tl = pd.DataFrame(timeline_rows)
                # Order by player then gameTime, period, periodTime as backup
                sort_cols = [c for c in ['player_id', 'gameTime', 'period', 'periodTime'] if c in df_tl.columns]
                df_tl = df_tl.sort_values(by=sort_cols)
                df_tl.to_csv(output_path / f"{game_id}_player_tendencies_timeline.csv", index=False)

        # Period openers
        if 'period_openers' in self.results and self.results['period_openers']:
            pd.DataFrame(self.results['period_openers']).to_csv(
                output_path / f"{game_id}_period_openers.csv", index=False
            )
        # Save whistle sequences with ids
        if 'whistle_sequences' in self.results and isinstance(self.results['whistle_sequences'], dict):
            ws = self.results['whistle_sequences']
            if ws.get('sequences'):
                pd.DataFrame(ws['sequences']).to_csv(
                    output_path / f"{game_id}_whistle_sequences.csv", index=False
                )
        
        print(f"All extraction files saved to {output_path}")

        # Additionally, persist team rotation logs in LME-compatible parquet files for backend routes
        try:
            tro = (self.results or {}).get('team_rotation_events') or {}
            events = tro.get('events') or []
            transitions = tro.get('transitions') or []
            if events:
                lme_dir = Path('data/processed/line_matchup_engine')
                lme_dir.mkdir(parents=True, exist_ok=True)
                events_df = pd.DataFrame(events)
                if 'source' not in events_df.columns:
                    events_df['source'] = 'CHE'
                rot_file = lme_dir / 'team_line_rotations.parquet'
                if rot_file.exists():
                    try:
                        prev = pd.read_parquet(rot_file)
                        events_df = pd.concat([prev, events_df], ignore_index=True)
                        # If source column exists, prefer CHE rows when duplicates on (game_id, team, event_index, sequence_index)
                        if {'game_id','team','event_index','sequence_index'}.issubset(events_df.columns):
                            events_df = (events_df
                                         .sort_values(by=['source'])
                                         .drop_duplicates(subset=['game_id','team','event_index','sequence_index'], keep='first'))
                    except Exception:
                        pass
                events_df.to_parquet(rot_file, compression='zstd', index=False)
            if transitions:
                lme_dir = Path('data/processed/line_matchup_engine')
                lme_dir.mkdir(parents=True, exist_ok=True)
                trans_df = pd.DataFrame(transitions)
                if 'source' not in trans_df.columns:
                    trans_df['source'] = 'CHE'
                trans_file = lme_dir / 'team_line_rotation_transitions.parquet'
                if trans_file.exists():
                    try:
                        prev = pd.read_parquet(trans_file)
                        trans_df = pd.concat([prev, trans_df], ignore_index=True)
                        # collapse duplicates by sum of counts
                        group_cols = ['team','strength_state','from_line','to_line']
                        if 'season' in trans_df.columns:
                            group_cols.append('season')
                        trans_df = trans_df.groupby(group_cols, as_index=False).agg({'count':'sum','source':'first'})
                    except Exception:
                        pass
                trans_df.to_parquet(trans_file, compression='zstd', index=False)
        except Exception as e:
            print(f"Warning: failed to persist team rotation parquet outputs: {e}")

        # ==============================
        # Training-friendly exports
        # ==============================
        try:
            # Build per-event stream
            es_rows = []
            ws = self.results.get('whistle_sequences', {}) if isinstance(self.results, dict) else {}
            ev_to_seq = (ws or {}).get('event_to_sequence_id', {})
            ev_to_dep = (ws or {}).get('event_to_deployment_id', {})

            info = self.results.get('game_info') or self.extract_game_info()
            home_team = info.get('home_team_name') or info.get('home_team')
            away_team = info.get('away_team_name') or info.get('away_team')
            home_code = self.team_name_to_code.get(home_team, info.get('home_team'))
            away_code = self.team_name_to_code.get(away_team, info.get('away_team'))

            def which_side(val):
                if pd.isna(val):
                    return None
                s = str(val)
                if s in (home_team, home_code):
                    return 'home'
                if s in (away_team, away_code):
                    return 'away'
                code = self.team_name_to_code.get(s)
                if code == home_code:
                    return 'home'
                if code == away_code:
                    return 'away'
                alias_code = self.team_name_alias_to_code.get(s)
                if alias_code == home_code:
                    return 'home'
                if alias_code == away_code:
                    return 'away'
                return None

            home_score = 0
            away_score = 0
            prev_time = None
            prev_x = None
            prev_y = None

            for idx, row in self.data.iterrows():
                gtime = self._safe_float(row.get('gameTime')) or 0.0
                x_adj = self._safe_float(row.get('xAdjCoord'))
                y_adj = self._safe_float(row.get('yAdjCoord'))
                time_since_prev = (gtime - prev_time) if (prev_time is not None) else None
                dist_from_prev = None
                if prev_x is not None and prev_y is not None and x_adj is not None and y_adj is not None:
                    try:
                        dist_from_prev = float(((x_adj - prev_x)**2 + (y_adj - prev_y)**2) ** 0.5)
                    except Exception:
                        dist_from_prev = None

                def parse_list(col):
                    if col in self.data.columns and not pd.isna(row[col]):
                        return [p.strip() for p in str(row[col]).strip('\t ').split(',') if p.strip() and p.strip() != 'nan']
                    return []
                team_fw = parse_list('teamForwardsOnIceRefs')
                team_df = parse_list('teamDefencemenOnIceRefs') if 'teamDefencemenOnIceRefs' in self.data.columns else parse_list('teamDefence')
                opp_fw = parse_list('opposingTeamForwardsOnIceRefs')
                opp_df = parse_list('opposingTeamDefencemenOnIceRefs')
                team_goalie = str(row.get('teamGoalieOnIceRef')) if 'teamGoalieOnIceRef' in self.data.columns and not pd.isna(row.get('teamGoalieOnIceRef')) else None
                opp_goalie = str(row.get('opposingTeamGoalieOnIceRef')) if 'opposingTeamGoalieOnIceRef' in self.data.columns and not pd.isna(row.get('opposingTeamGoalieOnIceRef')) else None

                ts = self._safe_float(row.get('teamSkatersOnIce'))
                oskat = self._safe_float(row.get('opposingTeamSkatersOnIce')) if 'opposingTeamSkatersOnIce' in self.data.columns else None
                strength_state = None
                if ts is not None and oskat is not None:
                    strength_state = f"{int(ts)}v{int(oskat)}"
                elif isinstance(row.get('manpowerSituation'), str):
                    mps = row.get('manpowerSituation')
                    if 'power' in mps.lower():
                        strength_state = 'PP'
                    elif 'short' in mps.lower():
                        strength_state = 'SH'
                    elif 'even' in mps.lower():
                        strength_state = '5v5'

                es_rows.append({
                    'game_id': info.get('game_id'),
                    'event_index': int(idx),
                    'period': int(row['period']) if not pd.isna(row['period']) else None,
                    'game_time': gtime,
                    'abs_timecode': row.get('timecode'),
                    'team': None if pd.isna(row['team']) else row['team'],
                    'action': None if pd.isna(row['shorthand']) else row['shorthand'],
                    'outcome': row.get('outcome'),
                    'zone': None if pd.isna(row['zone']) else row['zone'],
                    'x_adj': x_adj,
                    'y_adj': y_adj,
                    'strength_state': strength_state,
                    'score_diff': (home_score - away_score),
                    'sequence_id': ev_to_seq.get(int(idx)),
                    'deployment_id': ev_to_dep.get(int(idx)),
                    'teammates_on_ice_ids': (team_fw + team_df + ([team_goalie] if team_goalie else [])) or None,
                    'opponents_on_ice_ids': (opp_fw + opp_df + ([opp_goalie] if opp_goalie else [])) or None,
                    'team_trio_id': team_fw if len(team_fw) == 3 else None,
                    'team_pair_id': team_df if len(team_df) == 2 else None,
                    'opponent_trio_id': opp_fw if len(opp_fw) == 3 else None,
                    'opponent_pair_id': opp_df if len(opp_df) == 2 else None,
                    'team_goalie_id': team_goalie,
                    'opponent_goalie_id': opp_goalie,
                    'faceoff_flags': row.get('flags'),
                    'stoppage_type': 'Whistle' if str(row.get('shorthand')) == 'Whistle' else None,
                    'time_since_prev_event': time_since_prev,
                    'distance_from_prev': dist_from_prev,
                    'home_or_away': which_side(row.get('team')),
                })

                prev_time = gtime
                prev_x = x_adj
                prev_y = y_adj
                try:
                    is_goal = (str(row.get('name','')).lower() == 'goal') or ('GOAL' in str(row.get('shorthand')))
                except Exception:
                    is_goal = False
                if is_goal:
                    s = which_side(row.get('team'))
                    if s == 'home':
                        home_score += 1
                    elif s == 'away':
                        away_score += 1

            if es_rows:
                es_df = pd.DataFrame(es_rows).sort_values(by=['game_time','event_index'])
                season = self._parse_season_from_stem(Path(self.pbp_file).stem) or 'unknown'
                out_dir = Path('data/processed/training/event_stream') / season
                out_dir.mkdir(parents=True, exist_ok=True)
                es_df.to_parquet(out_dir / f"{info.get('game_id')}_event_stream.parquet", compression='zstd', index=False)
                print(f"Saved event_stream: {out_dir}/{info.get('game_id')}_event_stream.parquet")

                # Next action rows
                K = 5
                horizon_goal = 10.0
                horizon_shot = 5.0
                horizon_entry = 10.0
                rows_na = []
                actions = es_df['action'].astype(str).tolist()
                times = es_df['game_time'].astype(float).tolist()
                zones = es_df['zone'].astype(str).tolist()
                strengths = es_df['strength_state'].astype(str).tolist()
                names_col = es_df['action'].astype(str).tolist()
                for i in range(0, len(es_df) - 1):
                    next_action = actions[i+1]
                    time_to_next = times[i+1] - times[i] if times[i+1] is not None and times[i] is not None else None
                    # Lookahead
                    j = i + 1
                    goal_within = False
                    shot_within = False
                    entry_within = False
                    while j < len(es_df) and (times[j] - times[i]) <= max(horizon_goal, horizon_shot, horizon_entry):
                        a = actions[j]
                        n = names_col[j]
                        if 'GOAL' in a or 'goal' in str(n).lower():
                            if (times[j] - times[i]) <= horizon_goal:
                                goal_within = True
                        if 'SHOT' in a:
                            if (times[j] - times[i]) <= horizon_shot:
                                shot_within = True
                        if 'ENTRY' in a:
                            if (times[j] - times[i]) <= horizon_entry:
                                entry_within = True
                        j += 1
                    ctx_actions = [actions[max(0, i-k)] for k in range(K,0,-1)]
                    ctx_zones = [zones[max(0, i-k)] for k in range(K,0,-1)]
                    ctx_dt = []
                    for k in range(K,0,-1):
                        idxp = max(0, i-k)
                        dt = times[i] - times[idxp] if times[i] is not None and times[idxp] is not None else None
                        ctx_dt.append(dt)

                    possession_id = 0
                    for t in range(0, i+1):
                        a = actions[t]
                        if a == 'Whistle' or 'TURNOVER' in a or 'FAILED PASS TRAJECTORY' in a:
                            possession_id += 1

                    rows_na.append({
                        'game_id': info.get('game_id'),
                        'event_index': int(es_df.iloc[i]['event_index']),
                        'period': int(es_df.iloc[i]['period']) if pd.notna(es_df.iloc[i]['period']) else None,
                        'game_time': times[i],
                        'team': es_df.iloc[i]['team'],
                        'strength_state': strengths[i],
                        'score_diff': es_df.iloc[i]['score_diff'],
                        'zone': zones[i],
                        'x_adj': es_df.iloc[i]['x_adj'],
                        'y_adj': es_df.iloc[i]['y_adj'],
                        'possession_id': possession_id,
                        **{f'ctx_action_{k}': ctx_actions[k-1] for k in range(1, K+1)},
                        **{f'ctx_zone_{k}': ctx_zones[k-1] for k in range(1, K+1)},
                        **{f'ctx_dt_{k}': ctx_dt[k-1] for k in range(1, K+1)},
                        'next_action': next_action,
                        'goal_next_10s': goal_within,
                        'shot_next_5s': shot_within,
                        'entry_next_10s': entry_within,
                        'time_to_next': time_to_next,
                    })

                if rows_na:
                    na_df = pd.DataFrame(rows_na)
                    out_dir = Path('data/processed/training/next_action') / season
                    out_dir.mkdir(parents=True, exist_ok=True)
                    na_df.to_parquet(out_dir / f"{info.get('game_id')}_next_action.parquet", compression='zstd', index=False)
                    print(f"Saved next_action_rows: {out_dir}/{info.get('game_id')}_next_action.parquet")

                # sequence windows
                try:
                    if ws and ws.get('sequences'):
                        sw_df = pd.DataFrame(ws['sequences'])
                        out_dir = Path('data/processed/training/sequence_windows') / season
                        out_dir.mkdir(parents=True, exist_ok=True)
                        sw_df.to_parquet(out_dir / f"{info.get('game_id')}_sequence_windows.parquet", compression='zstd', index=False)
                        print(f"Saved sequence_windows: {out_dir}/{info.get('game_id')}_sequence_windows.parquet")
                except Exception as e:
                    print(f"Warning: failed to save sequence_windows parquet: {e}")

                # transition stats
                try:
                    trans = []
                    for i in range(0, len(es_df) - 1):
                        trans.append({
                            'action_t': actions[i],
                            'action_t1': actions[i+1],
                            'strength_state': strengths[i] if strengths[i] else None,
                            'zone': zones[i] if zones[i] else None,
                        })
                    if trans:
                        ts_df = pd.DataFrame(trans)
                        ts_df['count'] = 1
                        grp = ts_df.groupby(['action_t','action_t1','strength_state','zone'], as_index=False)['count'].sum()
                        out_dir = Path('data/processed/training/transition_stats') / season
                        out_dir.mkdir(parents=True, exist_ok=True)
                        grp.to_parquet(out_dir / f"{info.get('game_id')}_transition_stats.parquet", compression='zstd', index=False)
                        print(f"Saved transition_stats: {out_dir}/{info.get('game_id')}_transition_stats.parquet")
                except Exception as e:
                    print(f"Warning: failed to save transition_stats parquet: {e}")
        except Exception as e:
            print(f"Warning: failed training exports: {e}")


def main():
    """Main execution function"""
    # Example usage
    pbp_file = "../data/processed/analytics/nhl_play_by_play/BOS/2024-2025/playsequence-20241008-NHL-BOSvsFLA-20242025-20004.csv"
    
    # Initialize extractor
    extractor = ComprehensiveHockeyExtractor(pbp_file)
    
    # Run complete extraction
    results = extractor.run_complete_extraction()
    
    # Save results
    extractor.save_results()
    
    # Print summary
    print("\n=== EXTRACTION SUMMARY ===")
    print(f"Game: {results['game_info']}")
    print(f"Total individual matchups tracked: {sum(len(m) for m in results['individual_matchups'].values())}")
    print(f"Whistle deployments analyzed: {results['whistle_deployments']['total_whistles']}")
    print(f"Pass network nodes: {len(results['pass_networks'])}")
    print(f"Player tendencies analyzed: {len(results['player_tendencies'])}")
    print(f"Puck touch chains: {len(results['puck_touch_chains']['chains'])}")
    print(f"Pressure cascades: {results['pressure_cascades']['total_pressure_events']}")


if __name__ == "__main__":
    main()
