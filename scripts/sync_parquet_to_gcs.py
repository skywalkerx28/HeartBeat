"""
HeartBeat Engine - Sync Local Parquet to GCS Silver Tier
Upload processed Parquet files to GCS data lake with proper partitioning
"""
import os
from pathlib import Path
import re
import json
import pandas as pd
from google.cloud import storage
import logging
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "heartbeat-474020")
BUCKET_NAME = os.getenv("GCS_LAKE_BUCKET", "heartbeat-474020-lake")
LOCAL_DATA_ROOT = Path(__file__).parent.parent / "data" / "processed"

class ParquetToGCSSync:
    """Sync local Parquet files to GCS silver tier."""
    
    def __init__(self, bucket_name: str, local_root: Path):
        self.bucket_name = bucket_name
        self.local_root = local_root
        self.storage_client = storage.Client(project=PROJECT_ID)
        self.bucket = self.storage_client.bucket(bucket_name)

    # -----------------------------
    # Bronze uploads (raw JSON)
    # -----------------------------
    def sync_extracted_json(self) -> int:
        """
        Upload per-game comprehensive metrics JSON to bronze/extracted_metrics/season=YYYYYYYY/ and
        write lightweight team pointers for fast team/season filtering without duplicating payloads.

        Source: data/processed/extracted_metrics/*_comprehensive_metrics.json
        """
        logger.info("Syncing extracted metrics JSON (bronze)...")
        src_dir = self.local_root / "extracted_metrics"
        if not src_dir.exists():
            logger.warning(f"Extracted metrics directory not found: {src_dir}")
            return 0

        def _infer_season_from_name(name: str) -> str:
            # Prefer explicit season code 20252026 found near the end of the filename
            m = re.search(r"-(20\d{2})(\d{2})-\d+", name)
            if m:
                return f"{m.group(1)}{m.group(2)}"
            # Fallback: infer season from play date (YYYYMMDD)
            m2 = re.search(r"playsequence-(\d{4})(\d{2})(\d{2})", name)
            if m2:
                y = int(m2.group(1)); mm = int(m2.group(2))
                # NHL season starts in Oct (10)
                start_year = y if mm >= 10 else y - 1
                return f"{start_year}{start_year+1}"
            return "unknown"

        def _infer_teams_from_name(name: str) -> tuple[str | None, str | None]:
            # Expect segment like -TEAMAvsTEAMB-
            m = re.search(r"-([A-Z]{2,3})vs([A-Z]{2,3})-", name)
            if m:
                return m.group(1), m.group(2)
            return None, None

        def _infer_game_code(name: str) -> str | None:
            m = re.search(r"-(\d+)\.(?:json|csv)$", name)
            return m.group(1) if m else None

        uploaded = 0
        for jf in sorted(src_dir.glob("*_comprehensive_metrics.json")):
            fname = jf.name
            season = _infer_season_from_name(fname)
            team_a, team_b = _infer_teams_from_name(fname)
            game_code = _infer_game_code(fname)

            # Upload canonical payload (single copy per game) under correct season
            gcs_payload_path = f"bronze/extracted_metrics/season={season}/{fname}"
            payload_blob = self.bucket.blob(gcs_payload_path)
            if not payload_blob.exists():
                logger.info(f"  Uploading {fname} -> {gcs_payload_path}")
                payload_blob.upload_from_filename(str(jf))
                uploaded += 1

            # Write lightweight team pointers for fast per-team discovery (no duplication)
            for team in (team_a, team_b):
                if not team:
                    continue
                pointer = {
                    "source_uri": f"gs://{self.bucket_name}/{gcs_payload_path}",
                    "season": season,
                    "team": team,
                    "game_code": game_code,
                    "file": fname,
                }
                pointer_name = fname.replace(".json", ".pointer.json")
                pointer_path = f"bronze/extracted_metrics/by_team/season={season}/team={team}/{pointer_name}"
                pointer_blob = self.bucket.blob(pointer_path)
                if pointer_blob.exists():
                    continue
                logger.info(f"  Writing pointer for {team}: {pointer_path}")
                pointer_blob.upload_from_string(
                    data=json.dumps(pointer),
                    content_type="application/json",
                )

        logger.info(f"✓ Synced extracted JSON payloads and team pointers")
        return uploaded
        
    def sync_rosters(self) -> int:
        """
        Sync roster Parquet files to silver/dim/rosters/
        
        Source: data/processed/dim/rosters/*.parquet (converted from depth_charts)
        """
        logger.info("Syncing roster files...")
        
        roster_dir = self.local_root / "dim" / "rosters"
        if not roster_dir.exists():
            logger.warning(f"Roster directory not found: {roster_dir}")
            logger.info("  Run: python3 scripts/convert_csv_to_parquet.py first")
            return 0
        
        uploaded = 0
        for parquet_file in roster_dir.glob("*.parquet"):
            # Upload to silver/dim/rosters/
            gcs_path = f"silver/dim/rosters/{parquet_file.name}"
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {parquet_file.name} (already exists)")
                continue
            
            logger.info(f"  Uploading {parquet_file.name}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} roster files")
        return uploaded
    
    def sync_depth_charts(self) -> int:
        """
        Sync depth chart Parquet files to silver/dim/depth_charts/
        
        Source: data/processed/dim/depth_charts/*.parquet (converted from CSV)
        """
        logger.info("Syncing depth chart files...")
        
        depth_charts_dir = self.local_root / "dim" / "depth_charts"
        if not depth_charts_dir.exists():
            logger.warning(f"Depth charts directory not found: {depth_charts_dir}")
            return 0
        
        uploaded = 0
        for parquet_file in depth_charts_dir.glob("*.parquet"):
            # Upload to silver/dim/depth_charts/
            gcs_path = f"silver/dim/depth_charts/{parquet_file.name}"
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {parquet_file.name} (already exists)")
                continue
            
            logger.info(f"  Uploading {parquet_file.name}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} depth chart files")
        return uploaded
    
    def sync_play_by_play(self) -> int:
        """Sync play-by-play Parquet files to silver/fact/pbp/"""
        logger.info("Syncing play-by-play files...")
        
        pbp_dir = self.local_root / "fact" / "pbp"
        if not pbp_dir.exists():
            logger.warning(f"PBP directory not found: {pbp_dir}")
            return 0
        
        uploaded = 0
        for parquet_file in pbp_dir.glob("*.parquet"):
            # Extract season from filename if present (e.g., unified_pbp_2024-25.parquet)
            filename = parquet_file.name
            
            # Try to read metadata to get season info
            try:
                table = pq.read_table(parquet_file)
                if 'season' in table.column_names:
                    # Use Hive-style partitioning: season=YYYY-YYYY/
                    seasons = table.column('season').unique().to_pylist()
                    if seasons:
                        season = seasons[0]
                        gcs_path = f"silver/fact/pbp/season={season}/{filename}"
                    else:
                        gcs_path = f"silver/fact/pbp/{filename}"
                else:
                    gcs_path = f"silver/fact/pbp/{filename}"
            except Exception as e:
                logger.warning(f"  Could not read metadata from {filename}: {e}")
                gcs_path = f"silver/fact/pbp/{filename}"
            
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {filename} (already exists)")
                continue
            
            logger.info(f"  Uploading {filename} to {gcs_path}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} play-by-play files")
        return uploaded

    def sync_training(self) -> int:
        """
        Sync training Parquet files to silver/fact/{event_stream,next_action,sequence_windows,transition_stats}/season=YYYYYYYY/
        Source: data/processed/training/<type>/<season>/*.parquet
        """
        logger.info("Syncing training parquet files...")
        base = self.local_root / "training"
        if not base.exists():
            logger.warning(f"Training directory not found: {base}")
            return 0

        uploaded = 0
        subdirs = ["event_stream", "next_action", "sequence_windows", "transition_stats"]
        for sub in subdirs:
            subdir = base / sub
            if not subdir.exists():
                continue
            for season_dir in sorted([p for p in subdir.iterdir() if p.is_dir()]):
                season = season_dir.name
                for parquet_file in season_dir.glob("*.parquet"):
                    rel_name = parquet_file.name
                    gcs_path = f"silver/fact/{sub}/season={season}/{rel_name}"
                    blob = self.bucket.blob(gcs_path)
                    if blob.exists():
                        continue
                    logger.info(f"  Uploading {parquet_file} -> {gcs_path}")
                    blob.upload_from_filename(str(parquet_file))
                    uploaded += 1

        logger.info(f"✓ Synced {uploaded} training files")
        return uploaded
    
    def sync_market_contracts(self) -> int:
        """
        Sync contract Parquet files to silver/market/contracts/
        
        Source: data/processed/market/contracts/*.parquet (converted from CSV)
        """
        logger.info("Syncing contract files...")
        
        contracts_dir = self.local_root / "market" / "contracts"
        if not contracts_dir.exists():
            # Try existing market dir for backward compatibility
            contracts_dir = self.local_root / "market"
            if not contracts_dir.exists():
                logger.warning(f"Contract directory not found: {contracts_dir}")
                logger.info("  Run: python3 scripts/convert_csv_to_parquet.py first")
                return 0
        
        uploaded = 0
        for parquet_file in contracts_dir.glob("*.parquet"):
            gcs_path = f"silver/market/contracts/{parquet_file.name}"
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {parquet_file.name} (already exists)")
                continue
            
            logger.info(f"  Uploading {parquet_file.name}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} contract files")
        return uploaded
    
    def sync_player_profiles(self) -> int:
        """
        Sync player profile Parquet indexes to silver/dim/player_profiles/
        
        Source: data/processed/player_profiles/*.parquet (index files only)
        """
        logger.info("Syncing player profile indexes...")
        
        profiles_dir = self.local_root / "player_profiles"
        if not profiles_dir.exists():
            logger.warning(f"Player profiles directory not found: {profiles_dir}")
            return 0
        
        uploaded = 0
        # Only sync the index Parquet files, not individual JSONs
        for parquet_file in profiles_dir.glob("*.parquet"):
            gcs_path = f"silver/dim/player_profiles/{parquet_file.name}"
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {parquet_file.name} (already exists)")
                continue
            
            logger.info(f"  Uploading {parquet_file.name}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} player profile index files")
        return uploaded

    def _build_player_season_profiles_parquet(self) -> int:
        """
        Build compact Parquet summaries for player season profiles from JSON advanced metrics.
        Writes to data/processed/player_profiles/parquet/season=YYYYYYYY/player_season_advanced.parquet
        """
        logger.info("Building player season profiles parquet...")
        adv_dir = self.local_root / "player_profiles" / "advanced_metrics"
        out_root = self.local_root / "player_profiles" / "parquet"
        if not adv_dir.exists():
            logger.warning(f"Advanced metrics directory not found: {adv_dir}")
            return 0

        rows_by_season = {}
        for pdir in sorted(adv_dir.iterdir()):
            if not pdir.is_dir():
                continue
            for jf in pdir.glob("*_regular_advanced.json"):
                m = re.search(r"(\d{8})", jf.name)
                if not m:
                    continue
                season = m.group(1)
                try:
                    with open(jf, "r") as f:
                        doc = json.load(f)
                except Exception:
                    continue
                totals = doc.get("totals", {})
                entries = totals.get("entries", {}) if isinstance(totals, dict) else {}
                exits = totals.get("exits", {}) if isinstance(totals, dict) else {}
                games = doc.get("games", [])
                rows_by_season.setdefault(season, []).append({
                    "player_id": str(doc.get("playerId", "")),
                    "season": season,
                    "game_type": str(doc.get("gameType", "")),
                    "games_count": int(len(games)),
                    "shift_count": int(totals.get("shift_count", 0) or 0),
                    "toi_game_sec": float(totals.get("toi_game_sec", 0.0) or 0.0),
                    "avg_shift_game_sec": totals.get("avg_shift_game_sec"),
                    "avg_rest_game_sec": totals.get("avg_rest_game_sec"),
                    "lpr_recoveries": int(totals.get("lpr_recoveries", 0) or 0),
                    "pressure_events": int(totals.get("pressure_events", 0) or 0),
                    "turnovers": int(totals.get("turnovers", 0) or 0),
                    "entries_c_att": int(entries.get("controlled_attempts", 0) or 0),
                    "entries_c_succ": int(entries.get("controlled_success", 0) or 0),
                    "entries_d_att": int(entries.get("dump_attempts", 0) or 0),
                    "exits_c_att": int(exits.get("controlled_attempts", 0) or 0),
                    "exits_c_succ": int(exits.get("controlled_success", 0) or 0),
                    "exits_d_att": int(exits.get("dump_attempts", 0) or 0),
                })

        written = 0
        for season, rows in rows_by_season.items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            out_dir = out_root / f"season={season}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "player_season_advanced.parquet"
            df.to_parquet(out_file, index=False)
            written += len(rows)
            logger.info(f"  Wrote {len(rows)} player rows -> {out_file}")
        logger.info(f"✓ Built player season parquet rows: {written}")
        return written

    def _build_team_season_profiles_parquet(self) -> int:
        """
        Build compact Parquet summaries for team season profiles from JSON advanced metrics.
        Writes to data/processed/team_profiles/parquet/season=YYYYYYYY/team_season_advanced.parquet
        """
        logger.info("Building team season profiles parquet...")
        adv_dir = self.local_root / "team_profiles" / "advanced_metrics"
        out_root = self.local_root / "team_profiles" / "parquet"
        if not adv_dir.exists():
            logger.warning(f"Team advanced metrics directory not found: {adv_dir}")
            return 0

        rows_by_season = {}
        for team_dir in sorted(adv_dir.iterdir()):
            if not team_dir.is_dir():
                continue
            team_code = team_dir.name
            for jf in team_dir.glob("*_team_advanced.json"):
                m = re.search(r"(\d{8})", jf.name)
                if not m:
                    continue
                season = m.group(1)
                try:
                    with open(jf, "r") as f:
                        doc = json.load(f)
                except Exception:
                    continue
                totals = (doc.get("totals") or {}) if isinstance(doc, dict) else {}
                zt = totals.get("zone_time") or {}
                ent = totals.get("entries") or {}
                exi = totals.get("exits") or {}
                # shots_for_total may be nested
                s_for_total = 0.0
                try:
                    if isinstance(totals.get("shots_for"), dict):
                        s_for_total = float(totals["shots_for"].get("total", 0.0) or 0.0)
                    else:
                        s_for_total = float(totals.get("shots_for_total", 0.0) or 0.0)
                except Exception:
                    s_for_total = 0.0
                s_against_total = float(totals.get("shots_against_total", 0.0) or 0.0)
                rows_by_season.setdefault(season, []).append({
                    "team": team_code,
                    "season": season,
                    "games_count": int(totals.get("games_count", len(doc.get("games", [])) if isinstance(doc.get("games"), list) else 0)),
                    "shots_for_total": s_for_total,
                    "shots_against_total": s_against_total,
                    "oz_time": float(zt.get("oz", 0.0) or 0.0) if isinstance(zt, dict) else 0.0,
                    "nz_time": float(zt.get("nz", 0.0) or 0.0) if isinstance(zt, dict) else 0.0,
                    "dz_time": float(zt.get("dz", 0.0) or 0.0) if isinstance(zt, dict) else 0.0,
                    "possession_time": float(totals.get("possession_time", 0.0) or 0.0) if isinstance(totals, dict) else 0.0,
                    "entries_c_att": float(ent.get("controlled_attempts", 0.0) or 0.0) if isinstance(ent, dict) else 0.0,
                    "entries_c_succ": float(ent.get("controlled_success", 0.0) or 0.0) if isinstance(ent, dict) else 0.0,
                    "entries_d_att": float(ent.get("dump_attempts", 0.0) or 0.0) if isinstance(ent, dict) else 0.0,
                    "exits_c_att": float(exi.get("controlled_attempts", 0.0) or 0.0) if isinstance(exi, dict) else 0.0,
                    "exits_c_succ": float(exi.get("controlled_success", 0.0) or 0.0) if isinstance(exi, dict) else 0.0,
                    "exits_d_att": float(exi.get("dump_attempts", 0.0) or 0.0) if isinstance(exi, dict) else 0.0,
                })

        written = 0
        for season, rows in rows_by_season.items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            out_dir = out_root / f"season={season}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "team_season_advanced.parquet"
            df.to_parquet(out_file, index=False)
            written += len(rows)
            logger.info(f"  Wrote {len(rows)} team rows -> {out_file}")
        logger.info(f"✓ Built team season parquet rows: {written}")
        return written

    def sync_player_season_profiles(self) -> int:
        """Upload built player season parquet files to silver/dim/player_season_profiles/season=YYYYYYYY/"""
        base = self.local_root / "player_profiles" / "parquet"
        if not base.exists():
            return 0
        uploaded = 0
        for season_dir in sorted([p for p in base.iterdir() if p.is_dir() and p.name.startswith("season=")]):
            season = season_dir.name.split("=", 1)[-1]
            for pf in season_dir.glob("*.parquet"):
                rel = f"season={season}/{pf.name}"
                gcs_path = f"silver/dim/player_season_profiles/{rel}"
                blob = self.bucket.blob(gcs_path)
                if blob.exists():
                    continue
                logger.info(f"  Uploading {pf} -> {gcs_path}")
                blob.upload_from_filename(str(pf))
                uploaded += 1
        logger.info(f"✓ Synced {uploaded} player season profile parquet files")
        return uploaded

    def sync_team_season_profiles(self) -> int:
        """Upload built team season parquet files to silver/dim/team_season_profiles/season=YYYYYYYY/"""
        base = self.local_root / "team_profiles" / "parquet"
        if not base.exists():
            return 0
        uploaded = 0
        for season_dir in sorted([p for p in base.iterdir() if p.is_dir() and p.name.startswith("season=")]):
            season = season_dir.name.split("=", 1)[-1]
            for pf in season_dir.glob("*.parquet"):
                rel = f"season={season}/{pf.name}"
                gcs_path = f"silver/dim/team_season_profiles/{rel}"
                blob = self.bucket.blob(gcs_path)
                if blob.exists():
                    continue
                logger.info(f"  Uploading {pf} -> {gcs_path}")
                blob.upload_from_filename(str(pf))
                uploaded += 1
        logger.info(f"✓ Synced {uploaded} team season profile parquet files")
        return uploaded
    
    def sync_league_player_stats(self) -> int:
        """
        Sync league player stats Parquet files to silver/fact/league_player_stats/
        
        Source: data/processed/league_player_stats/parquet/season=*/*.parquet
        """
        logger.info("Syncing league player stats...")
        
        league_stats_dir = self.local_root / "league_player_stats" / "parquet"
        if not league_stats_dir.exists():
            logger.warning(f"League player stats directory not found: {league_stats_dir}")
            logger.info("  Run: python3 scripts/convert_csv_to_parquet.py first")
            return 0
        
        uploaded = 0
        
        # Recursively find all Parquet files with Hive partitioning
        for parquet_file in league_stats_dir.rglob("*.parquet"):
            # Preserve season partitioning: season=YYYY-YYYY/*.parquet
            rel_path = parquet_file.relative_to(league_stats_dir)
            gcs_path = f"silver/fact/league_player_stats/{rel_path}"
            
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {rel_path} (already exists)")
                continue
            
            logger.info(f"  Uploading {rel_path}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} league player stats files")
        return uploaded
    
    def sync_analytics(self) -> int:
        """Sync analytics Parquet files to silver tier."""
        logger.info("Syncing analytics files...")
        
        analytics_dir = self.local_root / "analytics"
        if not analytics_dir.exists():
            logger.warning(f"Analytics directory not found: {analytics_dir}")
            return 0
        
        uploaded = 0
        
        # Recursively find all Parquet files in analytics subdirectories
        for parquet_file in analytics_dir.rglob("*.parquet"):
            # Preserve directory structure relative to analytics/
            rel_path = parquet_file.relative_to(analytics_dir)
            gcs_path = f"silver/analytics/{rel_path}"
            
            blob = self.bucket.blob(gcs_path)
            
            if blob.exists():
                logger.info(f"  Skipping {rel_path} (already exists)")
                continue
            
            logger.info(f"  Uploading {rel_path}...")
            blob.upload_from_filename(str(parquet_file))
            uploaded += 1
        
        logger.info(f"✓ Synced {uploaded} analytics files")
        return uploaded

    # -----------------------------
    # Extracted metrics → Parquet indexes
    # -----------------------------
    def _build_extracted_metrics_indexes(self) -> dict:
        """
        Build compact Parquet indexes from local extracted metrics JSON filenames.
        Produces two datasets under data/processed/fact:
          - game_metrics_index/season=YYYYYYYY/*.parquet (one row per game)
          - team_game_metrics/season=YYYYYYYY/*.parquet (one row per team per game)
        """
        src_dir = self.local_root / "extracted_metrics"
        if not src_dir.exists():
            return {"game_index_rows": 0, "team_index_rows": 0}

        import pandas as pd  # Lazy import
        import re
        rows_game = []
        rows_team = []

        def _infer(fname: str):
            # season code 20252026 pattern near end
            m_season = re.search(r"-(20\d{2})(\d{2})-\d+", fname)
            if m_season:
                season = f"{m_season.group(1)}{m_season.group(2)}"
            else:
                # Fallback to date → season
                m_date = re.search(r"playsequence-(\d{4})(\d{2})(\d{2})", fname)
                if m_date:
                    y = int(m_date.group(1)); mm = int(m_date.group(2))
                    start = y if mm >= 10 else y - 1
                    season = f"{start}{start+1}"
                else:
                    season = "unknown"
            m_teams = re.search(r"-([A-Z]{2,3})vs([A-Z]{2,3})-", fname)
            team_a = m_teams.group(1) if m_teams else None
            team_b = m_teams.group(2) if m_teams else None
            m_code = re.search(r"-(\d+)_(?:comprehensive|.*)\.json$|-(\d+)\.json$", fname)
            game_code = m_code.group(1) if (m_code and m_code.group(1)) else (m_code.group(2) if m_code else None)
            m_date2 = re.search(r"playsequence-(\d{4})(\d{2})(\d{2})", fname)
            game_date = f"{m_date2.group(1)}-{m_date2.group(2)}-{m_date2.group(3)}" if m_date2 else None
            return season, team_a, team_b, game_code, game_date

        for jf in sorted(src_dir.glob("*_comprehensive_metrics.json")):
            season, team_a, team_b, game_code, game_date = _infer(jf.name)
            # game index row
            rows_game.append({
                "season": season,
                "game_code": game_code,
                "game_date": game_date,
                "team_a": team_a,
                "team_b": team_b,
                "source_file": jf.name,
            })
            # team rows
            for team in (team_a, team_b):
                if not team:
                    continue
                rows_team.append({
                    "season": season,
                    "team_abbrev": team,
                    "game_code": game_code,
                    "game_date": game_date,
                    "opponent": team_b if team == team_a else team_a,
                    "source_file": jf.name,
                })

        # Write out
        game_written = 0
        team_written = 0
        if rows_game:
            df_g = pd.DataFrame(rows_game)
            for season, gdf in df_g.groupby("season"):
                out_dir = self.local_root / "fact" / "game_metrics_index" / f"season={season}"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"game_metrics_index_{season}.parquet"
                gdf.to_parquet(out_file, index=False)
                game_written += len(gdf)
                logger.info(f"  Built game_metrics_index: {season} rows={len(gdf)} -> {out_file}")
        if rows_team:
            df_t = pd.DataFrame(rows_team)
            for season, tdf in df_t.groupby("season"):
                out_dir = self.local_root / "fact" / "team_game_metrics" / f"season={season}"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"team_game_metrics_{season}.parquet"
                tdf.to_parquet(out_file, index=False)
                team_written += len(tdf)
                logger.info(f"  Built team_game_metrics: {season} rows={len(tdf)} -> {out_file}")
        return {"game_index_rows": game_written, "team_index_rows": team_written}

    def _sync_extracted_metrics_indexes(self) -> int:
        """Upload Parquet indexes to silver/fact/ paths."""
        uploaded = 0
        # game index
        g_base = self.local_root / "fact" / "game_metrics_index"
        if g_base.exists():
            for season_dir in sorted(p for p in g_base.iterdir() if p.is_dir()):
                season = season_dir.name.replace("season=", "")
                for parquet_file in season_dir.glob("*.parquet"):
                    rel = f"silver/fact/game_metrics_index/season={season}/{parquet_file.name}"
                    blob = self.bucket.blob(rel)
                    if blob.exists():
                        continue
                    logger.info(f"  Uploading {parquet_file} -> {rel}")
                    blob.upload_from_filename(str(parquet_file))
                    uploaded += 1
        # team index
        t_base = self.local_root / "fact" / "team_game_metrics"
        if t_base.exists():
            for season_dir in sorted(p for p in t_base.iterdir() if p.is_dir()):
                season = season_dir.name.replace("season=", "")
                for parquet_file in season_dir.glob("*.parquet"):
                    rel = f"silver/fact/team_game_metrics/season={season}/{parquet_file.name}"
                    blob = self.bucket.blob(rel)
                    if blob.exists():
                        continue
                    logger.info(f"  Uploading {parquet_file} -> {rel}")
                    blob.upload_from_filename(str(parquet_file))
                    uploaded += 1
        return uploaded
    
    def run_full_sync(self) -> dict:
        """Run complete sync of all Parquet files."""
        logger.info(f"Starting full sync: {self.local_root} -> gs://{self.bucket_name}/silver/")
        logger.info(f"Local data root: {self.local_root}")
        
        if not self.local_root.exists():
            logger.error(f"Local data root does not exist: {self.local_root}")
            return {"error": "Local data root not found"}
        
        # Build compact Parquet summaries prior to upload
        try:
            built_player = self._build_player_season_profiles_parquet()
        except Exception as e:
            logger.warning(f"Failed to build player season parquet: {e}")
            built_player = 0
        try:
            built_team = self._build_team_season_profiles_parquet()
        except Exception as e:
            logger.warning(f"Failed to build team season parquet: {e}")
            built_team = 0
        # Build extracted metrics indexes
        try:
            built_idx = self._build_extracted_metrics_indexes()
            built_game_idx = built_idx.get("game_index_rows", 0)
            built_team_idx = built_idx.get("team_index_rows", 0)
        except Exception as e:
            logger.warning(f"Failed to build extracted metrics indexes: {e}")
            built_game_idx = 0
            built_team_idx = 0

        results = {
            "rosters": self.sync_rosters(),
            "depth_charts": self.sync_depth_charts(),
            "play_by_play": self.sync_play_by_play(),
            "training": self.sync_training(),
            "contracts": self.sync_market_contracts(),
            "player_profiles": self.sync_player_profiles(),
            "player_season_profiles": self.sync_player_season_profiles(),
            "team_season_profiles": self.sync_team_season_profiles(),
            "extracted_json": self.sync_extracted_json(),
            "extracted_metrics_indexes": self._sync_extracted_metrics_indexes(),
            "league_player_stats": self.sync_league_player_stats(),
            "analytics": self.sync_analytics()
        }
        
        total = sum(results.values())
        logger.info("")
        logger.info("========================================")
        logger.info(f"✓ SYNC COMPLETE: {total} files uploaded")
        logger.info("========================================")
        logger.info(f"  Rosters:              {results['rosters']}")
        logger.info(f"  Depth charts:         {results['depth_charts']}")
        logger.info(f"  Play-by-play:         {results['play_by_play']}")
        logger.info(f"  Contracts:            {results['contracts']}")
        logger.info(f"  Training:             {results['training']}")
        logger.info(f"  Player profiles:      {results['player_profiles']}")
        logger.info(f"  Player seasons:       {results['player_season_profiles']} (built {built_player})")
        logger.info(f"  Team seasons:         {results['team_season_profiles']} (built {built_team})")
        logger.info(f"  Extracted JSON:       {results['extracted_json']}")
        logger.info(f"  League player stats:  {results['league_player_stats']}")
        logger.info(f"  Extracted metrics idx: {results['extracted_metrics_indexes']} (built game={built_game_idx}, team={built_team_idx})")
        logger.info(f"  Analytics:            {results['analytics']}")
        logger.info("")
        
        return results


def main():
    """Run Parquet to GCS sync."""
    print("HeartBeat Engine - Parquet to GCS Sync")
    print("=" * 50)
    print(f"Project:      {PROJECT_ID}")
    print(f"Bucket:       {BUCKET_NAME}")
    print(f"Local root:   {LOCAL_DATA_ROOT}")
    print("")
    
    syncer = ParquetToGCSSync(BUCKET_NAME, LOCAL_DATA_ROOT)
    results = syncer.run_full_sync()
    
    if "error" in results:
        logger.error(f"Sync failed: {results['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
