"""
HeartBeat Engine - BigQuery Analytics Client
BigQuery-native analytics data access (mirrors ParquetDataClientV2)

Provides GCP-native data access with automatic fallback to Parquet.
Optimized for hot fact queries with partitioned/clustered tables.
"""

from google.cloud import bigquery
from google.api_core import exceptions
from typing import Dict, Any, Optional, List
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class AnalyticsDataClientBQ:
    """
    BigQuery-native analytics client.
    
    Mirrors ParquetDataClientV2 methods but queries BigQuery core tables.
    Designed for high-performance queries on hot facts (recent seasons).
    """
    
    def __init__(
        self,
        project_id: str = "heartbeat-474020",
        dataset_core: str = "core",
        dataset_raw: str = "raw"
    ):
        """
        Initialize BigQuery analytics client.
        
        Args:
            project_id: GCP project ID
            dataset_core: Native core tables dataset
            dataset_raw: External (BigLake) tables dataset
        """
        self.project_id = project_id
        self.dataset_core = dataset_core
        self.dataset_raw = dataset_raw
        
        try:
            self.bq_client = bigquery.Client(project=project_id)
            logger.info(
                f"AnalyticsDataClientBQ initialized: "
                f"{project_id}.{dataset_core}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    async def get_player_stats(
        self,
        player_name: str,
        season: str = "2024-2025",
        team: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get player statistics from BigQuery.
        
        Mirrors: ParquetDataClientV2.get_player_stats()
        
        Args:
            player_name: Player name (case-insensitive partial match)
            season: NHL season (e.g., "2024-2025")
            team: Optional team filter
            
        Returns:
            Player statistics dictionary
        """
        # Note: This assumes a fact_player_game_stats table exists
        # Adjust schema based on actual BigQuery table structure
        
        query = f"""
        SELECT 
          player_name,
          team_abbrev,
          position,
          COUNT(DISTINCT game_id) as games_played,
          SUM(goals) as goals,
          SUM(assists) as assists,
          SUM(points) as points,
          SUM(shots) as shots,
          SUM(toi_seconds) as total_toi_seconds,
          AVG(toi_seconds / 60.0) as avg_toi_minutes
        FROM `{self.project_id}.{self.dataset_core}.fact_player_game_stats`
        WHERE season = @season
          AND LOWER(player_name) LIKE LOWER(@player_name)
        """
        
        params = [
            bigquery.ScalarQueryParameter("season", "STRING", season),
            bigquery.ScalarQueryParameter("player_name", "STRING", f"%{player_name}%")
        ]
        
        if team:
            query += " AND team_abbrev = @team"
            params.append(bigquery.ScalarQueryParameter("team", "STRING", team.upper()))
        
        query += " GROUP BY player_name, team_abbrev, position LIMIT 1"
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.bq_client.query(query, job_config=job_config)
            df = query_job.to_dataframe()
            
            if df.empty:
                return {
                    "analysis_type": "player_stats",
                    "error": f"Player '{player_name}' not found",
                    "source": "bigquery",
                    "season": season
                }
            
            row = df.iloc[0]
            
            return {
                "analysis_type": "player_stats",
                "source": "bigquery",
                "player_name": row['player_name'],
                "team": row['team_abbrev'],
                "position": row.get('position', 'N/A'),
                "season": season,
                "games_played": int(row['games_played']),
                "goals": int(row['goals']) if pd.notna(row['goals']) else 0,
                "assists": int(row['assists']) if pd.notna(row['assists']) else 0,
                "points": int(row['points']) if pd.notna(row['points']) else 0,
                "shots": int(row['shots']) if pd.notna(row['shots']) else 0,
                "total_toi": float(row['total_toi_seconds']) if pd.notna(row['total_toi_seconds']) else 0,
                "avg_toi_minutes": float(row['avg_toi_minutes']) if pd.notna(row['avg_toi_minutes']) else 0
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"BigQuery query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_player_stats: {e}")
            raise
    
    async def get_matchup_data(
        self,
        opponent: str,
        season: str = "2024-2025",
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get matchup data for MTL vs specific opponent.
        
        Mirrors: ParquetDataClientV2.get_matchup_data()
        
        Args:
            opponent: Opponent team abbreviation
            season: NHL season
            metrics: Specific metrics to retrieve
            
        Returns:
            Matchup analysis dictionary
        """
        # Query external table (matchup reports live in BigLake)
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset_raw}.matchup_reports_parquet`
        WHERE season = @season
        LIMIT 100
        """
        
        params = [
            bigquery.ScalarQueryParameter("season", "STRING", season)
        ]
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.bq_client.query(query, job_config=job_config)
            df = query_job.to_dataframe()
            
            if df.empty:
                return {
                    "analysis_type": "matchup",
                    "error": f"No matchup data for {season}",
                    "opponent": opponent,
                    "season": season,
                    "source": "bigquery"
                }
            
            # Filter for opponent column (wide-format data)
            opponent_normalized = self._normalize_team_name(opponent)
            
            if opponent_normalized not in df.columns:
                return {
                    "analysis_type": "matchup",
                    "error": f"No data for opponent {opponent_normalized}",
                    "opponent": opponent,
                    "season": season,
                    "source": "bigquery"
                }
            
            matchup_df = df[['Metric Label', 'Montreal', opponent_normalized]].dropna()
            
            key_metrics = {}
            for _, row in matchup_df.iterrows():
                metric_label = row['Metric Label']
                if metric_label:
                    key_metrics[metric_label] = {
                        "mtl": float(row['Montreal']) if pd.notna(row['Montreal']) else 0,
                        "opponent": float(row[opponent_normalized]) if pd.notna(row[opponent_normalized]) else 0,
                        "difference": float(row['Montreal'] - row[opponent_normalized]) if pd.notna(row['Montreal']) and pd.notna(row[opponent_normalized]) else 0
                    }
            
            return {
                "analysis_type": "matchup",
                "team": "Montreal Canadiens",
                "opponent": opponent_normalized,
                "season": season,
                "source": "bigquery",
                "total_matchup_rows": len(matchup_df),
                "key_metrics": key_metrics,
                "matchups": matchup_df.to_dict('records')
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"BigQuery matchup query failed: {e}")
            raise
    
    async def get_season_results(
        self,
        season: str = "2024-2025",
        opponent: Optional[str] = None,
        date_filter: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get season game results.
        
        Mirrors: ParquetDataClientV2.get_season_results()
        
        Args:
            season: NHL season
            opponent: Filter for specific opponent
            date_filter: Date range filter
            
        Returns:
            Game-by-game results
        """
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset_raw}.season_results_parquet`
        WHERE season = @season
        """
        
        params = [
            bigquery.ScalarQueryParameter("season", "STRING", season)
        ]
        
        if opponent:
            query += " AND LOWER(opponent) = LOWER(@opponent)"
            params.append(bigquery.ScalarQueryParameter("opponent", "STRING", opponent))
        
        if date_filter:
            if 'start' in date_filter:
                query += " AND game_date >= @start_date"
                params.append(bigquery.ScalarQueryParameter("start_date", "DATE", date_filter['start']))
            if 'end' in date_filter:
                query += " AND game_date <= @end_date"
                params.append(bigquery.ScalarQueryParameter("end_date", "DATE", date_filter['end']))
        
        query += " ORDER BY game_date DESC LIMIT 100"
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.bq_client.query(query, job_config=job_config)
            df = query_job.to_dataframe()
            
            if df.empty:
                return {
                    "analysis_type": "season_results",
                    "error": f"No results for {season}",
                    "season": season,
                    "source": "bigquery"
                }
            
            # Calculate record if Result column exists
            record = {}
            if 'Result' in df.columns:
                wins = len(df[df['Result'] == 'W'])
                losses = len(df[df['Result'] == 'L'])
                ot_losses = len(df[df['Result'] == 'OTL'])
                record = {
                    "wins": wins,
                    "losses": losses,
                    "ot_losses": ot_losses,
                    "record_string": f"{wins}-{losses}-{ot_losses}"
                }
            
            return {
                "analysis_type": "season_results",
                "season": season,
                "team": "Montreal Canadiens",
                "source": "bigquery",
                "total_games": len(df),
                "games": df.to_dict('records'),
                "record": record,
                "recent_games": df.head(10).to_dict('records')
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"BigQuery season results query failed: {e}")
            raise

    async def get_recent_game_events(
        self,
        team: str,
        season: str = "2025-2026",
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Fetch recent play-by-play events for a team from BigLake external tables.

        Requires external tables named raw.pbp_YYYY_YYYY_parquet.
        """
        table_season = season.replace('-', '_')
        table_id = f"{self.project_id}.{self.dataset_raw}.pbp_{table_season}_parquet"

        # Some deployments might not have this season yet; handle gracefully
        try:
            query = f"""
            SELECT *
            FROM `{table_id}`
            WHERE team_abbrev = @team
            ORDER BY game_date DESC
            LIMIT @lim
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("team", "STRING", team.upper()),
                    bigquery.ScalarQueryParameter("lim", "INT64", int(limit)),
                ]
            )
            df = self.bq_client.query(query, job_config=job_config).to_dataframe()
            return {
                "analysis_type": "game_events",
                "source": "bigquery",
                "team": team.upper(),
                "season": season,
                "rows": len(df),
                "events": df.to_dict('records')
            }
        except exceptions.GoogleAPIError as e:
            logger.error(f"BigQuery game events query failed: {e}")
            raise
    
    def _normalize_team_name(self, team: str) -> str:
        """
        Normalize team names to consistent format.
        
        Args:
            team: Team name or abbreviation
            
        Returns:
            Standardized team name
        """
        team_mappings = {
            'toronto': 'Toronto',
            'tor': 'Toronto',
            'boston': 'Boston',
            'bos': 'Boston',
            'tampa': 'Tampa Bay',
            'tbl': 'Tampa Bay',
            'florida': 'Florida',
            'fla': 'Florida',
            'detroit': 'Detroit',
            'det': 'Detroit',
            'ottawa': 'Ottawa',
            'ott': 'Ottawa',
            'buffalo': 'Buffalo',
            'buf': 'Buffalo'
        }
        
        return team_mappings.get(team.lower(), team.title())
