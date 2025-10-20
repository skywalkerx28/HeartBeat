"""
HeartBeat Engine - Dynamic Layer Scenario Engine (MVP)

Purpose: answer "What should we do, and what would happen if we did?"

This MVP binds AI/LLM actions to ontology objects and CBA rules to simulate
roster/cap scenarios. It focuses on team-level cap compliance and roster size
under simple actions. It is designed to be extended with more actions/metrics.

Key features (initial):
- Loads current roster snapshot and contracts (cap hit)
- Loads current CBA cap limits from views
- Applies actions (add/remove player, call_up/send_down, IR/LTIR placeholders)
- Computes roster count, total cap hit, cap space, basic compliance flags

Extendable design:
- Add more action types: trade, buyout, extend, retain_salary, etc.
- Add objective functions and solvers for optimization
- Add waiver eligibility checks using age/game thresholds (requires more data)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import logging

from google.cloud import bigquery

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------

@dataclass
class Action:
    type: str  # add_player | remove_player | call_up | send_down | place_ir | place_ltir | acquire_player
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Scenario:
    team: str
    actions: List[Action]


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def _parse_date_to_season(date_str: str) -> str:
    """Convert YYYY-MM-DD to NHL season string YYYY-YYYY."""
    import datetime as _dt
    d = _dt.date.fromisoformat(date_str)
    start_year = d.year if d.month >= 7 else d.year - 1
    return f"{start_year}-{start_year+1}"


# -----------------------------------------------------------------------------
# BigQuery helpers
# -----------------------------------------------------------------------------

def _bq(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id)


def _get_current_cap_rules(project_id: str) -> Dict[str, Any]:
    sql = f"""
    SELECT * FROM `{project_id}.cba.analytics_current_cap_rules`
    """
    df = _bq(project_id).query(sql).to_dataframe()
    if df.empty:
        raise RuntimeError("No current cap rules available in cba.analytics_current_cap_rules")
    row = df.iloc[0].to_dict()
    return {
        "cap_ceiling": float(row.get("cap_ceiling", 0) or 0),
        "cap_floor": float(row.get("cap_floor", 0) or 0),
        "performance_bonus_cushion": float(row.get("performance_bonus_cushion", 0) or 0),
    }


def _get_trade_deadline(project_id: str, as_of_date: Optional[str]) -> Optional[str]:
    """Fetch trade deadline text for the season containing as_of_date."""
    if not as_of_date:
        return None
    sql = f"""
    SELECT value_text
    FROM `{project_id}.cba.objects_cba_rule`
    WHERE rule_category = 'Trade Deadline'
      AND effective_from <= DATE(@as_of)
      AND (effective_to IS NULL OR effective_to > DATE(@as_of))
    LIMIT 1
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("as_of", "DATE", as_of_date)]
        ),
    ).to_dataframe()
    if df.empty:
        return None
    return str(df.iloc[0]["value_text"]) if df.iloc[0]["value_text"] else None


def _get_latest_roster(project_id: str, team: str) -> List[Dict[str, Any]]:
    sql = f"""
    WITH latest AS (
      SELECT MAX(snapshot_date) AS d FROM `{project_id}.raw.depth_charts_parquet`
    )
    SELECT DISTINCT CAST(player_id AS INT64) AS player_id,
           player_name,
           position,
           team_abbrev,
           roster_status
    FROM `{project_id}.raw.depth_charts_parquet`, latest
    WHERE snapshot_date = latest.d AND team_abbrev = @team
    """
    job = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("team", "STRING", team)]
        ),
    )
    df = job.to_dataframe()
    return df.to_dict("records")


def _get_cap_hits(project_id: str, player_ids: List[int]) -> Dict[int, float]:
    if not player_ids:
        return {}
    ids_csv = ",".join(str(i) for i in sorted(set(player_ids)))
    sql = f"""
    SELECT CAST(nhl_player_id AS INT64) AS player_id, 
           MAX(CAST(cap_hit AS FLOAT64)) AS cap_hit
    FROM `{project_id}.raw.players_contracts_parquet`
    WHERE CAST(nhl_player_id AS INT64) IN ({ids_csv})
    GROUP BY player_id
    """
    df = _bq(project_id).query(sql).to_dataframe()
    return {int(r["player_id"]): float(r["cap_hit"] or 0.0) for _, r in df.iterrows()}


def _lookup_player_by_name(project_id: str, name: str) -> Optional[Dict[str, Any]]:
    sql = f"""
    SELECT CAST(player_id AS INT64) AS player_id, player_name, team_abbrev, position
    FROM `{project_id}.raw.depth_charts_parquet`
    WHERE LOWER(player_name) LIKE LOWER(@name)
    ORDER BY snapshot_date DESC
    LIMIT 1
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("name", "STRING", f"%{name}%")]
        ),
    ).to_dataframe()
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def _get_cap_hit_for_player(project_id: str, player_id: int) -> float:
    sql = f"""
    SELECT MAX(CAST(cap_hit AS FLOAT64)) AS cap_hit
    FROM `{project_id}.raw.players_contracts_parquet`
    WHERE CAST(nhl_player_id AS INT64) = @pid
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pid", "INT64", int(player_id))]
        ),
    ).to_dataframe()
    if df.empty or df.iloc[0]["cap_hit"] is None:
        return 0.0
    return float(df.iloc[0]["cap_hit"])  # type: ignore


def _get_birthdate(project_id: str, player_id: int) -> Optional[str]:
    sql = f"""
    SELECT birth_date FROM `{project_id}.raw.objects_player` WHERE nhl_player_id = @pid LIMIT 1
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pid", "INT64", int(player_id))]
        ),
    ).to_dataframe()
    if df.empty or not df.iloc[0]["birth_date"]:
        return None
    return str(df.iloc[0]["birth_date"])  # YYYY-MM-DD


def _get_earliest_signing_date(project_id: str, player_id: int) -> Optional[str]:
    sql = f"""
    SELECT CAST(MIN(signing_date) AS DATE) AS sd
    FROM `{project_id}.raw.players_contracts_parquet`
    WHERE CAST(nhl_player_id AS INT64) = @pid
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pid", "INT64", int(player_id))]
        ),
    ).to_dataframe()
    if df.empty or not df.iloc[0]["sd"]:
        return None
    return str(df.iloc[0]["sd"])  # YYYY-MM-DD


def _compute_age_at_date(birth_date: Optional[str], date_str: str) -> Optional[int]:
    if not birth_date:
        return None
    import datetime as _dt
    b = _dt.date.fromisoformat(birth_date)
    d = _dt.date.fromisoformat(date_str)
    age = d.year - b.year - ((d.month, d.day) < (b.month, b.day))
    return age


def _nhl_games_since(project_id: str, player_id: int, start_date: str) -> Tuple[int, int]:
    """Return (games, seasons_count) since start_date using season profiles.
    Approximates pro seasons by counting NHL seasons with any games.
    """
    season_start = _parse_date_to_season(start_date)
    sql = f"""
    SELECT season, CAST(games_count AS INT64) AS gp
    FROM `{project_id}.raw.player_season_profiles_parquet`
    WHERE CAST(player_id AS INT64) = @pid
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pid", "INT64", int(player_id))]
        ),
    ).to_dataframe()
    if df.empty:
        return 0, 0
    def _norm(s):
        if isinstance(s, str) and len(s) == 9 and '-' in s:
            return s
        if isinstance(s, str) and len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:]}"
        return str(s)
    df["season"] = df["season"].map(_norm)
    sel = df[df["season"] >= season_start]
    total_gp = int(sel["gp"].fillna(0).sum())
    seasons = int((sel["gp"].fillna(0) > 0).sum())
    return total_gp, seasons


def _is_waiver_exempt(project_id: str, player_id: int) -> Optional[bool]:
    """Approximate NHL waiver exemption based on age at signing and NHL games/seasons.
    - <=19 at signing: exempt until 160 NHL GP OR 5 pro seasons (whichever first)
    - >=20 at signing: exempt until 80 NHL GP OR 4 pro seasons
    Returns None if insufficient data.
    """
    signing_date = _get_earliest_signing_date(project_id, player_id)
    birth_date = _get_birthdate(project_id, player_id)
    if not signing_date:
        return None
    age = _compute_age_at_date(birth_date, signing_date)
    if age is None:
        return None
    if age <= 19:
        games_thr, seasons_thr = 160, 5
    else:
        games_thr, seasons_thr = 80, 4
    games, seasons = _nhl_games_since(project_id, player_id, signing_date)
    return games < games_thr and seasons < seasons_thr


def _get_player_value_score(project_id: str, player_id: int) -> float:
    """Heuristic on-ice value proxy using latest season metrics if present.
    Uses xg_per_60 or games_count as fallback scaled.
    """
    sql = f"""
    SELECT season, CAST(games_count AS INT64) AS gp
    FROM `{project_id}.raw.player_season_profiles_parquet`
    WHERE CAST(player_id AS INT64) = @pid
    ORDER BY season DESC
    LIMIT 1
    """
    df = _bq(project_id).query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pid", "INT64", int(player_id))]
        ),
    ).to_dataframe()
    if df.empty:
        return 0.0
    gp = float(df.iloc[0].get("gp") or 0)
    return gp / 82.0  # 0..1 scale


# -----------------------------------------------------------------------------
# Scenario application
# -----------------------------------------------------------------------------

def _apply_actions(
    roster: List[Dict[str, Any]],
    actions: List[Action],
    project_id: str,
    team: str,
) -> List[Dict[str, Any]]:
    roster_by_id = {int(r["player_id"]): r for r in roster if r.get("player_id") is not None}

    def _ensure_player_ref(act: Action) -> Optional[Dict[str, Any]]:
        if act.player_id:
            return {"player_id": int(act.player_id)}
        if act.player_name:
            info = _lookup_player_by_name(project_id, act.player_name)
            if info:
                return {"player_id": int(info["player_id"]), "player_name": info["player_name"]}
        return None

    for act in actions:
        kind = act.type.lower()
        ref = _ensure_player_ref(act)
        if ref is None:
            logger.warning(f"Action skipped (unknown player): {asdict(act)}")
            continue
        pid = int(ref["player_id"])

        if kind in ("add_player", "call_up"):
            if pid not in roster_by_id:
                roster_by_id[pid] = {
                    "player_id": pid,
                    "player_name": act.player_name or ref.get("player_name") or f"{pid}",
                    "team_abbrev": team,
                    "position": roster[0].get("position") if roster else None,
                    "roster_status": "roster",
                }
        elif kind in ("remove_player", "send_down"):
            roster_by_id.pop(pid, None)
        elif kind == "acquire_player":
            # Add external player to roster
            if pid not in roster_by_id:
                # Best-effort player name lookup if missing
                name = act.player_name or ref.get("player_name") or str(pid)
                roster_by_id[pid] = {
                    "player_id": pid,
                    "player_name": name,
                    "team_abbrev": team,
                    "position": None,
                    "roster_status": "roster",
                }
        elif kind in ("place_ir", "place_ltir"):
            # Placeholder: Keep player but mark non_roster (affects roster count but not cap unless LTIR implemented)
            if pid in roster_by_id:
                roster_by_id[pid]["roster_status"] = "non_roster"
        else:
            logger.warning(f"Unknown action type '{act.type}' - skipping")

    return list(roster_by_id.values())


def simulate_roster_scenario(
    team: str,
    actions: List[Dict[str, Any]],
    as_of_date: Optional[str] = None,
    project_id: str = "heartbeat-474020",
) -> Dict[str, Any]:
    """Simulate a roster scenario and compute cap/roster outcomes.

    Args:
        team: team abbreviation (e.g., 'MTL')
        actions: list of action dicts: {type, player_id?, player_name?, notes?}
        project_id: BigQuery project
    Returns:
        Summary dict with before/after metrics and compliance flags.
    """
    # Normalize actions
    action_objs = [Action(**a) for a in actions]

    # Load inputs
    cap_rules = _get_current_cap_rules(project_id)
    roster_now = _get_latest_roster(project_id, team)
    ids_now = [int(r["player_id"]) for r in roster_now if r.get("player_id") is not None]
    cap_hits_now = _get_cap_hits(project_id, ids_now)

    def _metrics(roster_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        ids = [int(r["player_id"]) for r in roster_rows if r.get("player_id") is not None]
        cap_hits = _get_cap_hits(project_id, ids)
        roster_count = sum(1 for r in roster_rows if r.get("roster_status") != "non_roster")
        total_cap = float(sum(cap_hits.get(int(pid), 0.0) for pid in ids))

        # LTIR relief: sum cap hits for players placed on LTIR in actions
        ltir_ids = [a.player_id for a in action_objs if a.type.lower() == "place_ltir" and a.player_id]
        ltir_relief = float(sum(cap_hits.get(int(pid), 0.0) for pid in ltir_ids)) if ltir_ids else 0.0
        effective_ceiling = cap_rules["cap_ceiling"] + ltir_relief

        # Position coverage (12F/6D/2G)
        pos_counts = {"F": 0, "D": 0, "G": 0}
        for r in roster_rows:
            if r.get("roster_status") == "non_roster":
                continue
            p = (r.get("position") or "").upper()
            if p in ("C", "LW", "RW"):
                pos_counts["F"] += 1
            elif p == "D":
                pos_counts["D"] += 1
            elif p == "G":
                pos_counts["G"] += 1
        need = {"F": 12, "D": 6, "G": 2}
        cov_pen = sum(max(0, need[k] - pos_counts[k]) for k in need)
        coverage_score = max(0.0, 1.0 - cov_pen / 5.0)

        return {
            "roster_count": roster_count,
            "total_cap_hit": total_cap,
            "cap_space": effective_ceiling - total_cap,
            "ltir_relief": ltir_relief,
            "pos_counts": pos_counts,
            "coverage_score": coverage_score,
        }

    before = _metrics(roster_now)
    roster_after = _apply_actions(roster_now, action_objs, project_id, team)
    after = _metrics(roster_after)

    # Basic compliance checks
    violations: List[str] = []
    eff_ceiling = cap_rules["cap_ceiling"] + after.get("ltir_relief", 0.0)
    if after["total_cap_hit"] > eff_ceiling + 1e-6:
        violations.append("Exceeds cap ceiling")
    if after["total_cap_hit"] < cap_rules["cap_floor"] - 1e-6:
        violations.append("Below cap floor")
    if after["roster_count"] > 23:
        violations.append("Active roster exceeds 23 players")
    # Trade deadline check
    deadline_text = _get_trade_deadline(project_id, as_of_date)
    if as_of_date and deadline_text:
        import datetime as _dt
        try:
            dt = _dt.datetime.strptime(deadline_text.split(' ET')[0], "%Y-%m-%d %I:%M %p")
            if _dt.datetime.fromisoformat(as_of_date + " 00:00:00") > dt:
                if any(a.type.lower() in ("acquire_player","add_player","trade") for a in action_objs):
                    violations.append("After trade deadline")
        except Exception:
            pass

    result = {
        "team": team,
        "cap_rules": cap_rules,
        "before": before,
        "after": after,
        "actions": [asdict(a) for a in action_objs],
        "violations": violations,
        "notes": [
            "Trade deadline validated if as_of_date provided.",
        ],
    }
    return result


def evaluate_acquisition(
    team: str,
    candidate_name: str,
    as_of_date: Optional[str] = None,
    project_id: str = "heartbeat-474020",
    max_suggestions: int = 3,
) -> Dict[str, Any]:
    """Evaluate acquiring a player: cap impact and suggested balancing moves.

    Strategy:
      1) Add candidate to roster (acquire_player)
      2) If cap/roster violations occur, suggest removing/send_down players with highest cap_hit
         until compliant (greedy). Returns recommended moves and final metrics.
    """
    cap_rules = _get_current_cap_rules(project_id)
    roster_now = _get_latest_roster(project_id, team)
    ids_now = [int(r["player_id"]) for r in roster_now if r.get("player_id") is not None]
    cap_hits_now = _get_cap_hits(project_id, ids_now)

    # Identify candidate
    candidate = _lookup_player_by_name(project_id, candidate_name)
    if not candidate:
        return {"error": f"Candidate '{candidate_name}' not found"}
    cand_id = int(candidate["player_id"])
    cand_cap = _get_cap_hit_for_player(project_id, cand_id)

    # Start with acquisition
    actions = [Action(type="acquire_player", player_id=cand_id, player_name=candidate_name)]
    roster_after = _apply_actions(roster_now, actions, project_id, team)

    def _metrics(rows: List[Dict[str, Any]]):
        ids = [int(r["player_id"]) for r in rows if r.get("player_id") is not None]
        hits = _get_cap_hits(project_id, ids)
        roster_count = sum(1 for r in rows if r.get("roster_status") != "non_roster")
        total_cap = float(sum(hits.get(int(pid), 0.0) for pid in ids))
        return roster_count, total_cap

    roster_count, total_cap = _metrics(roster_after)

    # If not compliant, propose waiver-aware removals (simple knapsack)
    recommendations: List[Dict[str, Any]] = []
    working = list(roster_after)
    ids_all = [int(r["player_id"]) for r in working if r.get("player_id") is not None and int(r["player_id"]) != cand_id]
    hits_all = _get_cap_hits(project_id, ids_all)
    pool: List[Tuple[int, float, bool]] = []  # (player_id, cap_hit, waiver_exempt)
    for pid in ids_all:
        ex = _is_waiver_exempt(project_id, pid)
        pool.append((pid, hits_all.get(pid, 0.0), ex if ex is not None else False))

    need_cap = max(0.0, (total_cap - cap_rules["cap_ceiling"]))
    need_cnt = max(0, roster_count - 23)

    def _choose(pool: List[Tuple[int,float,bool]], cap_need: float, cnt_need: int) -> List[int]:
        """Small knapsack: search small combos preferring waiver-exempt.
        Tries k=1..5 combinations; objective minimizes non-exempt count then total cap removed.
        Falls back to greedy if nothing found.
        """
        import itertools
        top = pool[:15]  # limit search space
        best: Tuple[int, float, List[int]] | None = None  # (non_exempt, cap_sum, ids)
        for k in range(1, min(6, len(top)+1)):
            for combo in itertools.combinations(top, k):
                cap_sum = sum(x[1] for x in combo)
                cnt = k
                non_exempt = sum(0 if x[2] else 1 for x in combo)
                if cap_sum + 1e-6 >= cap_need and cnt >= cnt_need:
                    score = (non_exempt, cap_sum)
                    if best is None or score < (best[0], best[1]):
                        best = (non_exempt, cap_sum, [x[0] for x in combo])
            if best:
                return best[2]
        # Fallback greedy
        cur_cap = 0.0
        cur_cnt = 0
        chosen: List[int] = []
        for pid, hit, ex in sorted(pool, key=lambda x: (not x[2], x[1])):
            if cur_cap >= cap_need and cur_cnt >= cnt_need:
                break
            chosen.append(pid)
            cur_cap += hit
            cur_cnt += 1
        return chosen

    if need_cap > 1e-6 or need_cnt > 0:
        plan = _choose(pool, need_cap, need_cnt)
        for drop_pid in plan[:10]:
            waiver_exempt = next((ex for pid, _, ex in pool if pid == drop_pid), False)
            act_type = "send_down" if waiver_exempt else "remove_player"
            drop_name = next((r["player_name"] for r in working if int(r.get("player_id", -1)) == drop_pid), str(drop_pid))
            recommendations.append({"type": act_type, "player_id": drop_pid, "player_name": drop_name, "waiver_exempt": waiver_exempt})
            working = _apply_actions(working, [Action(type=act_type, player_id=drop_pid)], project_id, team)
            roster_count, total_cap = _metrics(working)

    # Final metrics after recommended moves
    final_roster = working
    final_roster_count, final_cap = _metrics(final_roster)
    violations = []
    if final_cap > cap_rules["cap_ceiling"] + 1e-6:
        violations.append("Exceeds cap ceiling")
    if final_cap < cap_rules["cap_floor"] - 1e-6:
        violations.append("Below cap floor")
    if final_roster_count > 23:
        violations.append("Active roster exceeds 23 players")

    # Compute simple objective components
    non_exempt_moves = sum(1 for m in recommendations if not m.get("waiver_exempt", False))
    cand_val = _get_player_value_score(project_id, cand_id)
    removed_val = sum(_get_player_value_score(project_id, m["player_id"]) for m in recommendations)
    value_delta = cand_val - removed_val
    cap_space_norm = max(0.0, min(1.0, (cap_rules["cap_ceiling"] - final_cap) / cap_rules["cap_ceiling"]))
    coverage_score = 0.0  # can be computed by calling simulate_roster_scenario if needed
    overall_score = 0.4 * cap_space_norm + 0.2 * value_delta + 0.3 * coverage_score - 0.1 * non_exempt_moves

    return {
        "team": team,
        "candidate": {"player_id": cand_id, "player_name": candidate_name, "cap_hit": cand_cap},
        "cap_rules": cap_rules,
        "before": {
            "roster_count": len(roster_now),
            "total_cap_hit": float(sum(cap_hits_now.get(pid, 0.0) for pid in ids_now)),
        },
        "after_acquisition": {"roster_count": roster_count, "total_cap_hit": total_cap},
        "recommended_moves": recommendations[: max_suggestions],
        "final_after_moves": {"roster_count": final_roster_count, "total_cap_hit": final_cap},
        "violations": violations,
        "objective": {
            "cap_space_norm": cap_space_norm,
            "value_delta": value_delta,
            "coverage_score": coverage_score,
            "waiver_risk": non_exempt_moves,
            "overall_score": overall_score,
        },
        "notes": [
            "Removals prefer waiver-exempt players; otherwise treated as trade/remove.",
            "Waiver exemptions approximated using age at signing and NHL GP/pro seasons.",
            "Trade deadline can be validated via simulate_roster_scenario(as_of_date).",
        ],
    }
