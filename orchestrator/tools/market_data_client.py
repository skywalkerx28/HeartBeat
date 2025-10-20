"""
Market Data Client for NHL contract and cap analytics.

Provides production-grade access to contract, cap, trade, and market data
with BigQuery-first architecture and Parquet fallback for resilience.
"""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.api_core import exceptions
import logging

logger = logging.getLogger(__name__)


class MarketDataClient:
    """
    Production client for NHL contract and market analytics.
    
    Data Sources (priority order):
    1. BigQuery native tables (fast, frequently queried)
    2. BigQuery external tables (cost-effective, comprehensive)
    3. Local Parquet files (fallback when BigQuery unavailable)
    4. In-memory cache for real-time queries
    """
    
    # Class-level cache for pre-loaded data (shared across instances)
    _global_data_cache: Dict[str, pd.DataFrame] = {}
    _cache_loaded_at: Optional[datetime] = None
    
    def __init__(
        self,
        bigquery_client: Optional[bigquery.Client] = None,
        parquet_fallback_path: str = "data/processed/market",
        project_id: str = "heartbeat-474020",
        dataset_id: str = "market",
        enable_cache: bool = True,
        cache_ttl_seconds: int = 600
    ):
        self.bq_client = bigquery_client
        self.parquet_root = Path(parquet_fallback_path)
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        
        # Pre-load data on first init
        self._ensure_global_cache_loaded()
        
    def _get_table_ref(self, table_name: str) -> str:
        """Get fully qualified table reference."""
        return f"{self.project_id}.{self.dataset_id}.{table_name}"
        
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from cache if valid."""
        if not self.enable_cache:
            return None
            
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                logger.info(f"Cache hit: {cache_key}")
                return cached_data
                
        return None
        
    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache."""
        if self.enable_cache:
            self._cache[cache_key] = (datetime.now(), data)
            
    async def _query_bigquery(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """Execute BigQuery query with error handling."""
        if not self.bq_client:
            raise ValueError("BigQuery client not initialized")
            
        try:
            job_config = bigquery.QueryJobConfig()
            if params:
                job_config.query_parameters = params
                
            query_job = self.bq_client.query(query, job_config=job_config)
            df = query_job.to_dataframe()
            logger.info(f"BigQuery query returned {len(df)} rows")
            return df
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"BigQuery error: {e}")
            raise
            
    def _ensure_global_cache_loaded(self):
        """Pre-load frequently accessed data into class-level cache for fast access."""
        # Cache for 10 minutes
        if (MarketDataClient._cache_loaded_at and 
            (datetime.now() - MarketDataClient._cache_loaded_at).seconds < 600):
            return
        
        try:
            # Pre-load players_contracts (most frequently accessed)
            contracts_path = self.parquet_root / "players_contracts.parquet"
            if contracts_path.exists():
                MarketDataClient._global_data_cache['players_contracts'] = pd.read_parquet(contracts_path)
                MarketDataClient._cache_loaded_at = datetime.now()
                logger.info(f"✅ Pre-loaded {len(MarketDataClient._global_data_cache['players_contracts'])} contracts into global cache")
        except Exception as e:
            logger.warning(f"Could not pre-load global cache: {e}")
    
    async def _load_parquet_fallback(
        self,
        table_name: str,
        filters: Optional[List[Tuple]] = None
    ) -> pd.DataFrame:
        """Load data from local Parquet files as fallback."""
        # Check global cache first for instant access
        if table_name in MarketDataClient._global_data_cache:
            df = MarketDataClient._global_data_cache[table_name].copy()
            logger.info(f"⚡ Loaded {table_name} from global cache ({len(df)} rows)")
            return df
        
        parquet_path = self.parquet_root / f"{table_name}.parquet"
        
        if not parquet_path.exists():
            # Try pattern match for dated files
            pattern_files = list(self.parquet_root.glob(f"{table_name}_*.parquet"))
            if pattern_files:
                parquet_path = max(pattern_files)  # Get most recent
            else:
                raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
                
        logger.info(f"Loading Parquet fallback: {parquet_path}")
        df = pd.read_parquet(parquet_path, filters=filters)
        return df
        
    async def get_player_contract(
        self,
        player_name: Optional[str] = None,
        nhl_player_id: Optional[int] = None,
        team: Optional[str] = None,
        season: str = "2025-2026"
    ) -> Dict[str, Any]:
        """
        Get contract details for a player.
        
        Args:
            player_name: Player full name (e.g., 'Nick Suzuki')
            nhl_player_id: NHL player ID for exact match
            team: Team abbreviation filter
            season: Season (defaults to current)
            
        Returns:
            Contract details dictionary
        """
        cache_key = f"contract_{nhl_player_id or player_name}_{team}_{season}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        # If BigQuery is disabled/unavailable, jump straight to Parquet fallback
        if self.bq_client is None:
            try:
                df = await self._load_parquet_fallback("players_contracts")
                mask = df['season'] == season
                if nhl_player_id:
                    mask &= df['nhl_player_id'] == nhl_player_id
                elif player_name:
                    mask &= df['full_name'].str.contains(player_name, case=False, na=False)
                if team:
                    mask &= df['team_abbrev'] == team.upper()
                filtered = df[mask]
                if filtered.empty:
                    return {"error": "Player contract not found", "source": "parquet"}
                result = filtered.iloc[0].to_dict()
                result["source"] = "parquet"
                self._set_cache(cache_key, result)
                return result
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return {"error": str(fallback_error), "source": "error"}

        try:
            # Build query
            query = f"""
            SELECT 
                c.*,
                p.performance_index,
                p.contract_efficiency,
                p.market_value,
                p.surplus_value,
                p.status as performance_status
            FROM `{self._get_table_ref('active_contracts')}` c
            WHERE c.season = @season
            """
            
            params = [
                bigquery.ScalarQueryParameter("season", "STRING", season)
            ]
            
            if nhl_player_id:
                query += " AND c.nhl_player_id = @player_id"
                params.append(bigquery.ScalarQueryParameter("player_id", "INT64", nhl_player_id))
            elif player_name:
                query += " AND LOWER(c.full_name) LIKE LOWER(@player_name)"
                params.append(bigquery.ScalarQueryParameter("player_name", "STRING", f"%{player_name}%"))
                
            if team:
                query += " AND c.team_abbrev = @team"
                params.append(bigquery.ScalarQueryParameter("team", "STRING", team.upper()))
                
            query += " LIMIT 1"
            
            df = await self._query_bigquery(query, params)
            
            if df.empty:
                return {"error": "Player contract not found", "source": "bigquery"}
                
            result = df.iloc[0].to_dict()
            result["source"] = "bigquery"
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            # Fallback to Parquet
            try:
                df = await self._load_parquet_fallback("players_contracts")
                
                mask = df['season'] == season
                if nhl_player_id:
                    mask &= df['nhl_player_id'] == nhl_player_id
                elif player_name:
                    mask &= df['full_name'].str.contains(player_name, case=False, na=False)
                if team:
                    mask &= df['team_abbrev'] == team.upper()
                    
                filtered = df[mask]
                if filtered.empty:
                    return {"error": "Player contract not found", "source": "parquet"}
                    
                result = filtered.iloc[0].to_dict()
                result["source"] = "parquet"
                return result
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return {"error": str(fallback_error), "source": "error"}
                
    async def get_team_cap_summary(
        self,
        team: str,
        season: str = "2025-2026",
        include_projections: bool = True
    ) -> Dict[str, Any]:
        """
        Get team cap space, commitments, and projections.
        
        Args:
            team: Team abbreviation
            season: Season (defaults to current)
            include_projections: Include future season projections
            
        Returns:
            Cap summary with projections
        """
        cache_key = f"cap_{team}_{season}_{include_projections}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        try:
            query = f"""
            SELECT *
            FROM `{self._get_table_ref('team_cap_summary')}`
            WHERE team_abbrev = @team
                AND season = @season
            """
            
            params = [
                bigquery.ScalarQueryParameter("team", "STRING", team.upper()),
                bigquery.ScalarQueryParameter("season", "STRING", season)
            ]
            
            df = await self._query_bigquery(query, params)
            
            if df.empty:
                return {"error": "Team cap data not found", "source": "bigquery"}
                
            result = df.iloc[0].to_dict()
            result["source"] = "bigquery"
            
            # Add contract details
            contracts_query = f"""
            SELECT full_name, position, cap_hit, years_remaining, contract_type
            FROM `{self._get_table_ref('players_contracts')}`
            WHERE team_abbrev = @team
                AND season = @season
                AND contract_status = 'active'
            ORDER BY cap_hit DESC
            """
            
            contracts_df = await self._query_bigquery(contracts_query, params)
            result["contracts"] = contracts_df.to_dict('records')
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            try:
                cap_df = await self._load_parquet_fallback("team_cap_management")
                mask = (cap_df['team_abbrev'] == team.upper()) & (cap_df['season'] == season)
                filtered = cap_df[mask]
                
                if filtered.empty:
                    return {"error": "Team cap data not found", "source": "parquet"}
                    
                result = filtered.iloc[0].to_dict()
                result["source"] = "parquet"
                
                # Load individual player contracts from players_contracts.parquet
                try:
                    contracts_df = await self._load_parquet_fallback("players_contracts")
                    contracts_mask = (
                        (contracts_df['team_abbrev'] == team.upper()) & 
                        (contracts_df['contract_status'] == 'active')
                    )
                    team_contracts = contracts_df[contracts_mask].copy()
                    
                    # Calculate NHL cap hit (CRITICAL: only NHL + IR count, not Minor league or soir)
                    # Players in minors (AHL) don't count towards NHL cap even if signed
                    # soir = Sent On IR (does NOT count towards cap)
                    # Use season-specific cap_hit_YYYY_YY column, not AAV
                    if 'roster_status' in team_contracts.columns:
                        roster_mask = team_contracts['roster_status'].isin(['NHL', 'IR'])
                        
                        # Use season-specific cap hit if available (e.g., cap_hit_2025_26)
                        season_cap_col = f"cap_hit_{season.replace('-', '_')}"
                        if season_cap_col in team_contracts.columns:
                            nhl_cap_hit = team_contracts.loc[roster_mask, season_cap_col].fillna(0).sum()
                            logger.info(f"Using season-specific cap hit column: {season_cap_col}")
                        else:
                            # Fallback to AAV if season column not available
                            nhl_cap_hit = team_contracts.loc[roster_mask, 'cap_hit'].sum()
                            logger.warning(f"Season column {season_cap_col} not found, using AAV cap_hit")
                        
                        result['cap_hit_total'] = float(nhl_cap_hit)
                        result['roster_players_count'] = int(roster_mask.sum())
                        result['minor_league_count'] = int((team_contracts['roster_status'] == 'Minor').sum())
                        result['unsigned_prospects_count'] = int((team_contracts['contract_status'] == 'unsigned').sum())
                        logger.info(f"NHL cap hit: ${nhl_cap_hit/1e6:.1f}M ({result['roster_players_count']} NHL + IR)")
                    
                    # Load performance index and merge
                    try:
                        perf_df = await self._load_parquet_fallback("contract_performance_index")
                        perf_mask = perf_df['season'] == season
                        perf_filtered = perf_df[perf_mask]
                        
                        # Merge performance data with contracts
                        team_contracts = team_contracts.merge(
                            perf_filtered[['nhl_player_id', 'performance_index', 'contract_efficiency', 
                                          'market_value', 'surplus_value', 'status']],
                            on='nhl_player_id',
                            how='left'
                        )
                        logger.info(f"Merged performance data for {len(team_contracts)} contracts")
                    except Exception as perf_error:
                        logger.warning(f"Could not load performance index: {perf_error}")
                    
                    team_contracts = team_contracts.sort_values('cap_hit', ascending=False)
                    result["contracts"] = team_contracts.to_dict('records')
                except Exception as contracts_error:
                    logger.warning(f"Could not load team contracts: {contracts_error}")
                    result["contracts"] = []
                
                return result
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return {"error": str(fallback_error), "source": "error"}
                
    async def get_contract_comparables(
        self,
        player_id: int,
        position: str,
        age_range: Optional[Tuple[int, int]] = None,
        production_range: Optional[Tuple[float, float]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find comparable contracts for market analysis.
        
        Args:
            player_id: Player to find comparables for
            position: Position filter
            age_range: Optional (min_age, max_age) filter
            production_range: Optional (min_production, max_production) filter
            limit: Max comparables to return
            
        Returns:
            List of comparable contracts with similarity scores
        """
        cache_key = f"comparables_{player_id}_{position}_{age_range}_{production_range}_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        try:
            query = f"""
            SELECT *
            FROM `{self._get_table_ref('market_comparables')}`
            WHERE player_id = @player_id
            LIMIT 1
            """
            
            params = [bigquery.ScalarQueryParameter("player_id", "INT64", player_id)]
            df = await self._query_bigquery(query, params)
            
            if df.empty:
                return []
                
            comparables_data = df.iloc[0]['comparable_players']
            result = comparables_data[:limit] if comparables_data else []
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            try:
                df = await self._load_parquet_fallback("market_comparables")
                mask = df['player_id'] == player_id
                filtered = df[mask]
                
                if filtered.empty:
                    return []
                    
                comparables_data = filtered.iloc[0]['comparable_players']
                return comparables_data[:limit] if comparables_data else []
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return []
                
    async def get_league_market_summary(
        self,
        position: Optional[str] = None,
        season: str = "2025-2026"
    ) -> Dict[str, Any]:
        """
        Get league-wide market metrics by position.
        
        Args:
            position: Filter by position (C, RW, LW, D, G)
            season: Season (defaults to current)
            
        Returns:
            Market statistics and tier breakdowns
        """
        cache_key = f"market_summary_{position}_{season}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        try:
            query = f"""
            SELECT 
                position,
                COUNT(*) as total_contracts,
                AVG(cap_hit) as avg_cap_hit,
                PERCENTILE_CONT(cap_hit, 0.5) OVER() as median_cap_hit,
                MIN(cap_hit) as min_cap_hit,
                MAX(cap_hit) as max_cap_hit
            FROM `{self._get_table_ref('players_contracts')}`
            WHERE season = @season
                AND contract_status = 'active'
            """
            
            params = [bigquery.ScalarQueryParameter("season", "STRING", season)]
            
            if position:
                query += " AND position = @position"
                params.append(bigquery.ScalarQueryParameter("position", "STRING", position))
                
            query += " GROUP BY position"
            
            df = await self._query_bigquery(query, params)
            result = df.to_dict('records')
            
            self._set_cache(cache_key, result)
            return {"positions": result, "source": "bigquery"}
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            try:
                df = await self._load_parquet_fallback("players_contracts")
                mask = (df['season'] == season) & (df['contract_status'] == 'active')
                if position:
                    mask &= df['position'] == position
                    
                filtered = df[mask]
                
                summary = filtered.groupby('position')['cap_hit'].agg([
                    ('avg_cap_hit', 'mean'),
                    ('median_cap_hit', 'median'),
                    ('min_cap_hit', 'min'),
                    ('max_cap_hit', 'max'),
                    ('total_contracts', 'count')
                ]).reset_index()
                
                result = summary.to_dict('records')
                return {"positions": result, "source": "parquet"}
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return {"error": str(fallback_error), "source": "error"}
                
    async def get_recent_trades(
        self,
        team: Optional[str] = None,
        days_back: int = 30,
        include_cap_impact: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades with cap implications.
        
        Args:
            team: Filter by team (optional)
            days_back: Days to look back (default 30)
            include_cap_impact: Include cap impact analysis
            
        Returns:
            List of recent trades
        """
        cache_key = f"trades_{team}_{days_back}_{include_cap_impact}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
            
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            query = f"""
            SELECT *
            FROM `{self._get_table_ref('trade_history')}`
            WHERE trade_date >= @cutoff_date
            """
            
            params = [
                bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date.date())
            ]
            
            if team:
                query += " AND @team IN UNNEST(teams_involved)"
                params.append(bigquery.ScalarQueryParameter("team", "STRING", team.upper()))
                
            query += " ORDER BY trade_date DESC LIMIT 50"
            
            df = await self._query_bigquery(query, params)
            result = df.to_dict('records')
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            try:
                df = await self._load_parquet_fallback("trade_history")
                cutoff_date = datetime.now() - timedelta(days=days_back)
                
                mask = pd.to_datetime(df['trade_date']) >= cutoff_date
                if team:
                    mask &= df['teams_involved'].apply(lambda x: team.upper() in x)
                    
                filtered = df[mask].sort_values('trade_date', ascending=False).head(50)
                return filtered.to_dict('records')
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return []
                
    async def calculate_contract_efficiency(
        self,
        player_id: int,
        season: str = "2025-2026"
    ) -> Dict[str, Any]:
        """
        Calculate performance vs contract value efficiency.
        
        Links player stats from nhl_player_stats with contract data.
        
        Args:
            player_id: NHL player ID
            season: Season for calculation
            
        Returns:
            Efficiency metrics
        """
        try:
            query = f"""
            SELECT *
            FROM `{self._get_table_ref('contract_performance_index')}`
            WHERE nhl_player_id = @player_id
                AND season = @season
            """
            
            params = [
                bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
                bigquery.ScalarQueryParameter("season", "STRING", season)
            ]
            
            df = await self._query_bigquery(query, params)
            
            if df.empty:
                return {"error": "Performance index not found", "source": "bigquery"}
                
            return df.iloc[0].to_dict()
            
        except Exception as e:
            logger.warning(f"BigQuery failed, trying Parquet fallback: {e}")
            
            try:
                df = await self._load_parquet_fallback("contract_performance_index")
                mask = (df['nhl_player_id'] == player_id) & (df['season'] == season)
                filtered = df[mask]
                
                if filtered.empty:
                    return {"error": "Performance index not found", "source": "parquet"}
                    
                return filtered.iloc[0].to_dict()
                
            except Exception as fallback_error:
                logger.error(f"Parquet fallback failed: {fallback_error}")
                return {"error": str(fallback_error), "source": "error"}
