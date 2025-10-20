/**
 * Market Analytics API Client
 * 
 * Provides client-side functions for NHL contract, cap, trade, and market data.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Lightweight in-memory cache with de-duped in-flight requests
type CacheEntry<T = any> = {
  value: T;
  etag?: string;
  expiresAt: number;
};

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes
const cacheStore = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<any>>();

function makeKey(url: string) {
  return url;
}

function peekCache<T = any>(key: string): T | undefined {
  const hit = cacheStore.get(key);
  if (!hit) return undefined;
  if (Date.now() > hit.expiresAt) return hit.value; // allow stale peek; SWR pattern
  return hit.value;
}

async function fetchJsonWithCache<T = any>(
  url: string,
  opts?: { ttlMs?: number; signal?: AbortSignal; force?: boolean }
): Promise<T> {
  const ttlMs = opts?.ttlMs ?? DEFAULT_TTL_MS;
  const key = makeKey(url);

  if (!opts?.force) {
    const hit = cacheStore.get(key);
    if (hit && Date.now() < hit.expiresAt) {
      return hit.value as T;
    }
    if (inflight.has(key)) {
      return inflight.get(key)! as Promise<T>;
    }
  }

  const requestInit: RequestInit = { signal: opts?.signal, headers: {} };
  const existing = cacheStore.get(key);
  if (existing?.etag) {
    (requestInit.headers as Record<string, string>)["If-None-Match"] = existing.etag;
  }

  const p = (async () => {
    const res = await fetch(url, requestInit);
    if (res.status === 304 && existing) {
      // Not modified, extend ttl
      cacheStore.set(key, { ...existing, expiresAt: Date.now() + ttlMs });
      return existing.value as T;
    }
    if (!res.ok) {
      // For market endpoints, degrade gracefully on common server errors
      if (url.includes('/api/v1/market/')) {
        const friendly = {
          success: false,
          error: `Upstream error ${res.status}: ${res.statusText}`,
          source: 'market-api',
          timestamp: new Date().toISOString()
        } as T;
        return friendly;
      }
      throw new Error(`Request failed ${res.status}: ${res.statusText}`);
    }
    const etag = res.headers.get('ETag') ?? undefined;
    const json = (await res.json()) as T;
    cacheStore.set(key, { value: json, etag, expiresAt: Date.now() + ttlMs });
    return json;
  })().finally(() => {
    inflight.delete(key);
  });

  inflight.set(key, p);
  return p;
}

export function prefetchUrl(url: string, ttlMs?: number) {
  // fire-and-forget prefetch; ignore errors
  fetchJsonWithCache(url, { ttlMs }).catch(() => {});
}

export function peekUrl<T = any>(url: string): T | undefined {
  return peekCache<T>(makeKey(url));
}

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
  roster_status: string;  // 'NHL', 'IR', 'Minor', 'Unsigned'
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
 * First tries CSV data (historical CapWages scrapes), then falls back to market analytics
 */
export async function getPlayerContract(
  playerId: number,
  season?: string
): Promise<MarketAnalyticsResponse<PlayerContract>> {
  // Try CSV endpoint first (covers historical data from CapWages scrapes)
  try {
    const csvUrl = `${API_BASE_URL}/api/v1/market/contracts/csv/${playerId}`;
    const csvResponse = await fetchJsonWithCache(csvUrl);
    if (csvResponse && csvResponse.success) {
      return csvResponse;
    }
  } catch (csvError) {
    // CSV not found, fall through to market analytics
    console.log(`CSV contract not found for player ${playerId}, trying market analytics...`);
  }
  
  // Fallback to market analytics endpoint
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  
  const url = `${API_BASE_URL}/api/v1/market/contracts/player/${playerId}${params.toString() ? '?' + params.toString() : ''}`;
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
}

/**
 * Get all contracts for a team
 */
export async function getTeamContracts(
  teamAbbrev: string,
  season?: string,
  includeExpired?: boolean,
  opts?: { signal?: AbortSignal; ttlMs?: number; force?: boolean }
): Promise<MarketAnalyticsResponse<{ team: string; season: string; contracts: PlayerContract[] }>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeExpired !== undefined) params.append('include_expired', includeExpired.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/contracts/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
  return fetchJsonWithCache(url, { signal: opts?.signal, ttlMs: opts?.ttlMs, force: opts?.force });
}

/**
 * Get team cap space, commitments, and projections
 */
export async function getTeamCapSummary(
  teamAbbrev: string,
  season?: string,
  includeProjections?: boolean,
  opts?: { signal?: AbortSignal; ttlMs?: number; force?: boolean }
): Promise<MarketAnalyticsResponse<TeamCapSummary>> {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeProjections !== undefined) params.append('include_projections', includeProjections.toString());
  
  const url = `${API_BASE_URL}/api/v1/market/cap/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
  return fetchJsonWithCache(url, { signal: opts?.signal, ttlMs: opts?.ttlMs, force: opts?.force });
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
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
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
  return fetchJsonWithCache(url);
}

/**
 * Health check for market analytics API
 */
export async function checkMarketApiHealth(): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/market/health`;
  return fetchJsonWithCache(url, { ttlMs: 30_000 });
}

// Convenience helpers tailored for the Market page
export function buildTeamContractsUrl(teamAbbrev: string, season?: string, includeExpired?: boolean) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeExpired !== undefined) params.append('include_expired', includeExpired.toString());
  return `${API_BASE_URL}/api/v1/market/contracts/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
}

export function buildTeamCapUrl(teamAbbrev: string, season?: string, includeProjections?: boolean) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (includeProjections !== undefined) params.append('include_projections', includeProjections.toString());
  return `${API_BASE_URL}/api/v1/market/cap/team/${teamAbbrev}${params.toString() ? '?' + params.toString() : ''}`;
}

export function peekTeamContractsCache(teamAbbrev: string, season?: string, includeExpired?: boolean) {
  const url = buildTeamContractsUrl(teamAbbrev, season, includeExpired);
  return peekUrl<MarketAnalyticsResponse<{ team: string; season: string; contracts: PlayerContract[] }>>(url);
}

export function peekTeamCapSummaryCache(teamAbbrev: string, season?: string, includeProjections?: boolean) {
  const url = buildTeamCapUrl(teamAbbrev, season, includeProjections);
  return peekUrl<MarketAnalyticsResponse<TeamCapSummary>>(url);
}

export function prefetchTeamMarketData(teamAbbrev: string, season?: string) {
  prefetchUrl(buildTeamContractsUrl(teamAbbrev, season, undefined));
  prefetchUrl(buildTeamCapUrl(teamAbbrev, season, true));
}

/**
 * Depth Chart Roster Data
 */
export interface DepthChartPlayer {
  player_id?: number;
  player_name: string;
  position: string;
  roster_status: string;  // 'roster', 'non_roster', 'unsigned'
  dead_cap: boolean;
  jersey_number?: number;
  age?: number;
  birth_date?: string;
  birth_country?: string;
  height_inches?: number;
  weight_pounds?: number;
  shoots_catches?: string;
  drafted_by?: string;
  draft_year?: string;
  draft_round?: string;
  draft_overall?: string;
  must_sign_date?: string;
  headshot?: string;
  scraped_date?: string;
  // Contract data (merged by backend)
  cap_hit?: number;
  cap_percent?: number;
  years_remaining?: number;
  expiry_status?: string;
  contract_type?: string;
  signing_date?: string;
  total_value?: number;
}

export interface TeamDepthChart {
  success: boolean;
  team_code: string;
  total_players: number;
  roster_breakdown: {
    roster: number;
    non_roster: number;
    unsigned: number;
    dead_cap: number;
  };
  data: DepthChartPlayer[];
}

/**
 * Get team depth chart roster data
 * Returns players with their basic info and enrichment data from the depth chart database
 * 
 * @param teamCode - 3-letter team code (e.g., 'MTL', 'VGK')
 * @param rosterStatus - Optional filter: 'roster', 'non_roster', or 'unsigned'
 */
export async function getTeamDepthChart(
  teamCode: string,
  rosterStatus?: 'roster' | 'non_roster' | 'unsigned',
  opts?: { signal?: AbortSignal; ttlMs?: number; force?: boolean }
): Promise<TeamDepthChart> {
  const params = new URLSearchParams();
  if (rosterStatus) params.append('roster_status', rosterStatus);
  
  const url = `${API_BASE_URL}/api/v1/market/depth-chart/${teamCode}${params.toString() ? '?' + params.toString() : ''}`;
  return fetchJsonWithCache(url, { signal: opts?.signal, ttlMs: opts?.ttlMs, force: opts?.force });
}
