"""
Entity tagging utilities for HeartBeat.bot

Extracts teams and players from news content and stores normalized tags
for cross-linking with player/team profile pages.
"""

from __future__ import annotations

import os
import re
import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from .config import NHL_TEAMS
from . import db


def _normalize_text(text: str) -> str:
    return (text or "").strip()


def _build_team_aliases() -> Dict[str, List[str]]:
    """Build team alias dictionary from NHL_TEAMS config.

    Returns mapping team_code -> list of lowercase alias strings.
    """
    aliases: Dict[str, List[str]] = {}
    for code, info in NHL_TEAMS.items():
        name = info["name"]
        tokens = name.split()
        last = tokens[-1].lower() if tokens else ""
        last_two = " ".join(tokens[-2:]).lower() if len(tokens) >= 2 else last
        extra: List[str] = []
        # Common nicknames (minimal set; can expand later)
        nickname_map = {
            "MTL": ["habs", "canadiens"],
            "TOR": ["leafs", "maple leafs"],
            "TBL": ["lightning", "bolts"],
            "DET": ["red wings", "wings"],
            "NYR": ["rangers"],
            "NYI": ["islanders"],
            "NJD": ["devils"],
            "PIT": ["penguins", "pens"],
            "PHI": ["flyers"],
            "WSH": ["capitals", "caps"],
            "BOS": ["bruins"],
            "BUF": ["sabres"],
            "OTT": ["senators", "sens"],
            "FLA": ["panthers"],
            "LAK": ["kings"],
            "SJS": ["sharks"],
            "CGY": ["flames"],
            "EDM": ["oilers"],
            "VAN": ["canucks"],
            "VGK": ["golden knights", "knights"],
            "SEA": ["kraken"],
            "COL": ["avalanche", "avs"],
            "STL": ["blues"],
            "DAL": ["stars"],
            "MIN": ["wild"],
            "NSH": ["predators", "preds"],
            "WPG": ["jets"],
            "CHI": ["blackhawks", "hawks"],
            "UTA": ["utah", "mammoth"],
            "ANA": ["ducks"],
        }
        extra.extend(nickname_map.get(code, []))

        aliases[code] = list({
            code.lower(),
            name.lower(),
            last,
            last_two,
            *extra,
        })
    return aliases


TEAM_ALIASES = _build_team_aliases()


def _compile_team_patterns() -> List[Tuple[str, re.Pattern]]:
    patterns: List[Tuple[str, re.Pattern]] = []
    for code, names in TEAM_ALIASES.items():
        for n in names:
            if not n:
                continue
            # Word-boundary match for phrases
            pattern = re.compile(rf"(?<!\w){re.escape(n)}(?!\w)", re.IGNORECASE)
            patterns.append((code, pattern))
    return patterns


TEAM_PATTERNS = _compile_team_patterns()


def seed_players_registry_from_stats(root_dir: str = "../data/nhl_player_stats") -> int:
    """Seed players_registry from local stats CSVs if empty.

    Returns number of players inserted.
    """
    inserted = 0
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), root_dir))
    if not os.path.exists(root):
        return 0

    with db.get_connection() as conn:
        # If already populated, skip heavy work
        count = conn.execute("SELECT COUNT(*) FROM players_registry").fetchone()[0]
        if count and count > 0:
            return 0

        for team_code in NHL_TEAMS.keys():
            team_dir = os.path.join(root, team_code)
            if not os.path.isdir(team_dir):
                continue
            for season in os.listdir(team_dir):
                season_dir = os.path.join(team_dir, season)
                if not os.path.isdir(season_dir):
                    continue
                for cat in ["forwards_stats", "defenseman_stats", "goalie_stats"]:
                    cat_dir = os.path.join(season_dir, cat)
                    if not os.path.isdir(cat_dir):
                        continue
                    for fname in os.listdir(cat_dir):
                        if not fname.lower().endswith(".csv"):
                            continue
                        path = os.path.join(cat_dir, fname)
                        try:
                            with open(path, newline="", encoding="utf-8") as f:
                                # Skip commented header lines that start with '#'
                                rows = [row for row in csv.reader(f) if row and not row[0].startswith('#')]
                                if not rows:
                                    continue
                                header = rows[0]
                                # Find column indices
                                name_idx = header.index("Player Name") if "Player Name" in header else 0
                                for r in rows[1:]:
                                    if len(r) <= name_idx:
                                        continue
                                    player_name = r[name_idx].strip()
                                    if not player_name:
                                        continue
                                    db.upsert_player_registry(conn, player_name=player_name, team_code=team_code)
                                    inserted += 1
                        except Exception:
                            # Best-effort seeding; continue on parse issues
                            continue
    return inserted


def seed_players_registry_from_unified_roster(roster_path: str = "../../data/processed/rosters/unified_roster_20252026.json") -> int:
    """Seed players_registry from canonical unified roster JSON.

    Returns number of players inserted. Uses fields: id, name, team(code).
    """
    # Resolve path relative to backend/bot/
    abs_path = Path(__file__).parent.joinpath(roster_path).resolve()
    if not abs_path.exists():
        return 0
    try:
        data = json.loads(abs_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    players = data.get("players", [])
    inserted = 0
    with db.get_connection() as conn:
        for p in players:
            name = (p.get("name") or "").strip()
            if not name:
                continue
            pid = str(p.get("id")) if p.get("id") is not None else None
            team = p.get("team") or p.get("teamCode") or None
            db.upsert_player_registry(conn, player_name=name, team_code=team, player_id=pid)
            inserted += 1
    return inserted


def overlay_registry_with_unified_roster(roster_path: str = "../../data/processed/rosters/unified_roster_20252026.json") -> int:
    """Overlay players_registry with canonical roster data.

    Always upserts (adds missing and fills missing player_id/team_code).
    Returns number of upserts performed.
    """
    abs_path = Path(__file__).parent.joinpath(roster_path).resolve()
    if not abs_path.exists():
        return 0
    try:
        data = json.loads(abs_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    players = data.get("players", [])
    upserts = 0
    with db.get_connection() as conn:
        for p in players:
            name = (p.get("name") or "").strip()
            if not name:
                continue
            pid = str(p.get("id")) if p.get("id") is not None else None
            team = p.get("team") or p.get("teamCode") or None
            db.upsert_player_registry(conn, player_name=name, team_code=team, player_id=pid)
            upserts += 1
    return upserts


def _build_players_index(conn) -> Dict[str, Dict[str, str]]:
    """Return mapping lower(player_name) -> {player_id, team_code} from registry."""
    rows = conn.execute("SELECT player_name, COALESCE(player_id, ''), COALESCE(team_code, '') FROM players_registry").fetchall()
    idx: Dict[str, Dict[str, str]] = {}
    for name, pid, team in rows:
        key = name.lower()
        if key not in idx:
            idx[key] = {"player_id": pid or None, "team_code": team or None}
    return idx


def extract_entities(title: str, summary: str = "", content: str = "") -> Dict[str, Any]:
    """Extract teams and players from text using rule-based patterns and registry.

    Returns: {
      'teams': [{'team_code': 'MTL', 'confidence': 0.95}, ...],
      'players': [{'player_name': 'Nick Suzuki', 'player_id': None, 'team_code': 'MTL', 'confidence': 0.9}, ...]
    }
    """
    text = " ".join([_normalize_text(title), _normalize_text(summary), _normalize_text(content)])
    text_lower = text.lower()

    teams_found: Dict[str, float] = {}
    for code, pattern in TEAM_PATTERNS:
        if pattern.search(text_lower):
            # Basic confidence; could weigh by multiple hits
            teams_found[code] = max(teams_found.get(code, 0.0), 0.9)

    # Find full-name player matches by scanning registry
    players: List[Dict[str, Any]] = []
    with db.get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM players_registry").fetchone()[0] == 0:
            # Prefer canonical roster, fall back to stats CSVs
            added = seed_players_registry_from_unified_roster()
            if added == 0:
                seed_players_registry_from_stats()
        pindex = _build_players_index(conn)
        for pname, meta in pindex.items():
            if pname and pname in text_lower:
                players.append({
                    "player_name": pname.title(),
                    "player_id": meta.get("player_id"),
                    "team_code": meta.get("team_code"),
                    "confidence": 0.9
                })

    teams = [{"team_code": code, "confidence": conf} for code, conf in teams_found.items()]

    return {"teams": teams, "players": players}


def tag_news_item(news_id: int, title: str, summary: str = "", content: str = "") -> None:
    """Extract entities and write tags for a given news item id."""
    entities = extract_entities(title, summary, content)
    rows: List[Dict[str, Any]] = []
    for t in entities.get("teams", []):
        rows.append({
            "entity_type": "team",
            "team_code": t.get("team_code"),
            "player_id": None,
            "player_name": None,
            "confidence": t.get("confidence", 0.9)
        })
    for p in entities.get("players", []):
        rows.append({
            "entity_type": "player",
            "team_code": p.get("team_code"),
            "player_id": p.get("player_id"),
            "player_name": p.get("player_name"),
            "confidence": p.get("confidence", 0.9)
        })
    with db.get_connection() as conn:
        db.bulk_insert_news_entities(conn, news_id, rows)


