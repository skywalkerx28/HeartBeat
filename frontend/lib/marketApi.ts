/**
 * Market Analytics API Client
 * 
 * Provides client-side functions for NHL contract, cap, trade, and market data.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface PlayerContract {
  nhl_player_id: number;
  player_name: string;
  full_name: string;  // Full player name from database
  team_abbrev: string;
  position: string;
  age: number;
  cap_hit: number;  // AAV (Average Annual Value)
  cap_hit_2025_26?: number;  // Season-specific cap hit (may vary from AAV due to bonuses/structure)
  cap_hit_percentage: number;
  years_remaining: number;
  contract_type: string;
  no_trade_clause: boolean;
  no_movement_clause: boolean;
  contract_status: string;
  roster_status: string;  // 'roster', 'soir', 'minors', 'reserve_list'
  performance_index?: number;
  contract_efficiency?: number;
  market_value?: number;
  surplus_value?: number;
  status?: string;
}

export interface TeamCapSummary {
  team_abbrev: string;
  season: string;
  cap_ceiling: number;
  cap_space: number;
  cap_hit_total: number;
  ltir_pool: number;
  deadline_cap_space: number;
  active_contracts: number;
  contracts_expiring: number;
  contracts?: PlayerContract[];
  projections?: Array<{
    season: string;
    projected_cap_ceiling: number;
    committed: number;
    available: number;
  }>;
}

export interface ContractComparable {
  player_id: number;
  player_name: string;
  team: string;
  position: string;
  cap_hit: number;
  age_at_signing: number;
  contract_years: number;
  production_last_season: number;
  similarity_score: number;
}

export interface Trade {
  trade_id: string;
  trade_date: string;
  season: string;
  teams_involved: string[];
  players_moved: Array<{
    player_id: number;
    player_name: string;
    from_team: string;
    to_team: string;
  }>;
  draft_picks_moved?: Array<{
    year: number;
    round: number;
    from_team: string;
    to_team: string;
    conditions?: string;
  }>;
  cap_implications: Array<{
    team: string;
    cap_change: number;
  }>;
  trade_type: string;
  trade_deadline: boolean;
}

export interface MarketAnalyticsResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  source: string;
  timestamp: string;
}

/**
 * Get player contract details by player ID
 */
export async function getPlayerContract(
  playerId: number,
  season?: string
): Promise<MarketAnalyticsResponse<PlayerContract>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/contracts/player/${playerId}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch player contract: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get player contract details by player name
 */
export async function getPlayerContractByName(
  playerName: string,
  team?: string,
  season?: string
): Promise<MarketAnalyticsResponse<PlayerContract>> {
  const params = new URLSearchParams();
  if (team) params.append('team', team);
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/contracts/player/name/${encodeURIComponent(playerName)}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch player contract: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get all contracts for a team
 */
export async function getTeamContracts(
  teamAbbrev: string,
  season?: string,
  includeExpired?: boolean
): Promise<MarketAnalyticsResponse<{ team: string; season: string; contracts: PlayerContract[] }>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeExpired !== undefined) params.append('include_expired', includeExpired.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/contracts/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch team contracts: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get team cap space, commitments, and projections
 */
export async function getTeamCapSummary(
  teamAbbrev: string,
  season?: string,
  includeProjections?: boolean
): Promise<MarketAnalyticsResponse<TeamCapSummary>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeProjections !== undefined) params.append('include_projections', includeProjections.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/cap/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch team cap summary: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get contract efficiency rankings
 */
export async function getContractEfficiencyRankings(
  filters?: {
    position?: string;
    team?: string;
    min_cap_hit?: number;
    limit?: number;
  }
): Promise<MarketAnalyticsResponse<any>> {
  const params = new URLSearchParams();
  if (filters?.position) params.append('position', filters.position);
  if (filters?.team) params.append('team', filters.team);
  if (filters?.min_cap_hit) params.append('min_cap_hit', filters.min_cap_hit.toString());
  if (filters?.limit) params.append('limit', filters.limit.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/efficiency${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch efficiency rankings: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Find comparable contracts for a player
 */
export async function getContractComparables(
  playerId: number,
  limit?: number
): Promise<MarketAnalyticsResponse<{ player_id: number; comparables: ContractComparable[]; count: number }>> {
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/comparables/${playerId}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch contract comparables: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get recent NHL trades with cap implications
 */
export async function getRecentTrades(
  team?: string,
  daysBack?: number,
  season?: string
): Promise<MarketAnalyticsResponse<{ trades: Trade[]; count: number; filters: any }>> {
  const params = new URLSearchParams();
  if (team) params.append('team', team);
  if (daysBack) params.append('days_back', daysBack.toString());
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/trades${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch recent trades: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get league-wide market statistics
 */
export async function getLeagueMarketOverview(
  position?: string,
  season?: string
): Promise<MarketAnalyticsResponse<any>> {
  const params = new URLSearchParams();
  if (position) params.append('position', position);
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/league/overview${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch league market overview: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get contract alerts for a team
 */
export async function getContractAlerts(
  teamAbbrev: string,
  alertTypes?: string[]
): Promise<MarketAnalyticsResponse<any>> {
  const params = new URLSearchParams();
  if (alertTypes && alertTypes.length > 0) {
    alertTypes.forEach(type => params.append('alert_types', type));
  }
  
  const url = `${API_BASE_URL}/api/v1/market/alerts/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch contract alerts: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get detailed contract efficiency analysis for a player
 */
export async function getPlayerEfficiencyAnalysis(
  playerId: number,
  season?: string
): Promise<MarketAnalyticsResponse<any>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/efficiency/player/${playerId}${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch player efficiency analysis: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Health check for market analytics API
 */
export async function checkMarketApiHealth(): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/market/health`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Market API health check failed: ${response.statusText}`);
  }
  
  return response.json();
}

