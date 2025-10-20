/**
 * HeartBeat Profile API
 * Data fetching for player and team profile pages
 * Integrates NHL API with local advanced analytics
 */

// API base (same convention as marketApi)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
// NHL API Base URL - use backend proxy (absolute URL to avoid Next.js /api collision)
const NHL_API_BASE = `${API_BASE_URL}/api/nhl`

// Team mappings for division/conference (since NHL API doesn't include this in basic calls)
const TEAM_INFO_MAP: Record<string, { division: string; conference: string; city: string }> = {
  MTL: { division: 'Atlantic', conference: 'Eastern', city: 'Montreal' },
  TOR: { division: 'Atlantic', conference: 'Eastern', city: 'Toronto' },
  BOS: { division: 'Atlantic', conference: 'Eastern', city: 'Boston' },
  NYI: { division: 'Metropolitan', conference: 'Eastern', city: 'New York' },
  NYR: { division: 'Metropolitan', conference: 'Eastern', city: 'New York' },
  PHI: { division: 'Metropolitan', conference: 'Eastern', city: 'Philadelphia' },
  WSH: { division: 'Metropolitan', conference: 'Eastern', city: 'Washington' },
  CAR: { division: 'Metropolitan', conference: 'Eastern', city: 'Carolina' },
  NJD: { division: 'Metropolitan', conference: 'Eastern', city: 'New Jersey' },
  CBJ: { division: 'Metropolitan', conference: 'Eastern', city: 'Columbus' },
  PIT: { division: 'Metropolitan', conference: 'Eastern', city: 'Pittsburgh' },
  FLA: { division: 'Atlantic', conference: 'Eastern', city: 'Florida' },
  TBL: { division: 'Atlantic', conference: 'Eastern', city: 'Tampa Bay' },
  BUF: { division: 'Atlantic', conference: 'Eastern', city: 'Buffalo' },
  OTT: { division: 'Atlantic', conference: 'Eastern', city: 'Ottawa' },
  DET: { division: 'Atlantic', conference: 'Eastern', city: 'Detroit' },
  // Western Conference teams
  COL: { division: 'Central', conference: 'Western', city: 'Colorado' },
  DAL: { division: 'Central', conference: 'Western', city: 'Dallas' },
  MIN: { division: 'Central', conference: 'Western', city: 'Minnesota' },
  NSH: { division: 'Central', conference: 'Western', city: 'Nashville' },
  STL: { division: 'Central', conference: 'Western', city: 'St. Louis' },
  WPG: { division: 'Central', conference: 'Western', city: 'Winnipeg' },
  CHI: { division: 'Central', conference: 'Western', city: 'Chicago' },
  UTA: { division: 'Central', conference: 'Western', city: 'Utah' },
  ARI: { division: 'Central', conference: 'Western', city: 'Utah' }, // Legacy mapping
  VGK: { division: 'Pacific', conference: 'Western', city: 'Vegas' },
  SEA: { division: 'Pacific', conference: 'Western', city: 'Seattle' },
  LAK: { division: 'Pacific', conference: 'Western', city: 'Los Angeles' },
  SJS: { division: 'Pacific', conference: 'Western', city: 'San Jose' },
  ANA: { division: 'Pacific', conference: 'Western', city: 'Anaheim' },
  VAN: { division: 'Pacific', conference: 'Western', city: 'Vancouver' },
  CGY: { division: 'Pacific', conference: 'Western', city: 'Calgary' },
  EDM: { division: 'Pacific', conference: 'Western', city: 'Edmonton' },
}

export interface TeamProfile {
  // Enhanced with NHL API data
  teamId: string
  id: number                    // NHL team ID
  name: string
  abbreviation: string
  city: string
  division: string
  conference: string
  
  // Season record (from NHL API aggregation)
  record: {
    wins: number
    losses: number
    otLosses: number
    points: number
    gamesPlayed: number
  }
  
  // Season stats (calculated from NHL API data)
  stats: {
    goalsFor: number
    goalsAgainst: number
    ppPercent: number
    pkPercent: number
    shotsPerGame: number
    shotsAgainstPerGame: number
  }
  
  // Visual assets (from NHL API)
  logoUrl: string
  darkLogoUrl: string
}

export interface PlayerProfile {
  // Enhanced with NHL API data
  playerId: string | number
  id: number                    // NHL player ID
  name: string
  firstName: string
  lastName: string
  position: string              // "L", "C", "R", "D", "G"
  jerseyNumber: number
  
  // Team context (from NHL API)
  teamId: string               // Team abbreviation
  teamName: string
  teamFullName: string
  
  // Current season stats (from NHL API aggregation)
  seasonStats: {
    gamesPlayed: number
    goals: number
    assists: number
    points: number
    plusMinus: number
    pim: number
    shots: number
    shootingPct: number
    timeOnIce: string          // Average TOI per game
    powerPlayGoals: number
    powerPlayPoints: number
    shortHandedGoals: number
    hits: number
    blockedShots: number
    takeaways: number
    giveaways: number
    faceoffWinPct?: number     // Only for centers
  }
  
  // Career stats (from NHL API)
  careerStats?: {
    gamesPlayed: number
    goals: number
    assists: number
    points: number
    plusMinus: number
    pim: number
    shots: number
    shootingPct: number
    powerPlayGoals: number
    powerPlayPoints: number
    shortHandedGoals: number
    shortHandedPoints: number
    gameWinningGoals: number
    otGoals: number
  }
  
  // Contract data (from HeartBeat market analytics)
  contract?: {
    aav: number
    yearsRemaining: number
    status: string
  }
  
  // Bio data (from NHL API)
  birthDate?: string
  birthCity?: string
  birthStateProvince?: string
  birthCountry?: string
  birthplace?: string          // Formatted "City, Province/State, Country"
  heightInInches?: number
  heightInCentimeters?: number
  heightFormatted?: string     // Formatted "6'2\""
  weightInPounds?: number
  weightInKilograms?: number
  shootsCatches?: string       // "L" or "R"
  draftYear?: number
  draftRound?: number
  draftOverall?: number
  age?: number
  
  // Season-by-season stats (from NHL API seasonTotals)
  seasonTotals?: Array<{
    season: number               // e.g., 20222023
    leagueAbbrev: string        // e.g., "NHL"
    gameTypeId: number          // 2 = regular season, 3 = playoffs
    gamesPlayed: number
    goals: number
    assists: number
    points: number
    plusMinus: number
    pim: number
    shots?: number
    shootingPctg?: number
    powerPlayGoals?: number
    powerPlayPoints?: number
    shorthandedGoals?: number
    avgToi?: string
    teamAbbrev?: string
  }>
  
  // Last 5 games (from NHL API)
  last5Games?: Array<{
    gameId: number
    gameDate: string
    opponentAbbrev: string
    homeRoadFlag: string
    goals: number
    assists: number
    points: number
    plusMinus: number
    shots: number
    pim: number
    toi: string
  }>
}

export interface GameLog {
  // Enhanced with NHL API data
  gameId: string
  date: string
  opponent: string
  opponentName: string
  homeAway: 'home' | 'away'
  result: 'W' | 'L' | 'OTL'
  
  // Basic stats (from NHL API boxscore)
  goals: number
  assists: number
  points: number
  plusMinus: number
  pim: number
  shots: number
  hits: number
  blockedShots: number
  takeaways: number
  giveaways: number
  timeOnIce: string
  shifts: number
  
  // Special teams (from NHL API)
  powerPlayGoals?: number
  shortHandedGoals?: number
  gameWinningGoals?: number
  
  // Faceoffs (for centers)
  faceoffWins?: number
  faceoffLosses?: number
  faceoffWinPct?: number
  
  // Game context
  gameState: string            // "FINAL", "LIVE", etc.
  periodType?: string          // "REG", "OT", "SO"
}

export interface TeamPerformanceData {
  goalsPerGame: { date: string; value: number }[]
  xGoalsPerGame: { date: string; value: number }[]
  winLossPattern: { date: string; result: 'W' | 'L' | 'OTL' }[]
  homeAwaySplits: {
    home: { gf: number; ga: number; record: string }
    away: { gf: number; ga: number; record: string }
  }
}

// Advanced team metrics (aggregated from extractor outputs)
export interface TeamAdvancedGame {
  gameId: number
  gameDate?: string
  team?: string
  opponent?: string
  homeAway?: 'home' | 'away'
  zone_time?: { oz?: number; nz?: number; dz?: number }
  possession_time?: number
  entries?: { controlled_attempts?: number; controlled_success?: number; dump_attempts?: number }
  exits?: { controlled_attempts?: number; controlled_success?: number; dump_attempts?: number }
  shots_for?: { on?: number; missed?: number; blocked?: number; total?: number }
  shots_against_total?: number
  passes?: number
  lpr_recoveries?: number
  pressure_events?: number
  turnovers?: number
  // Opponent side per-game counts (when available in data)
  opponent_passes?: number
  opponent_lpr_recoveries?: number
  opponent_pressure_events?: number
  opponent_turnovers?: number
  // Final score
  goals_for?: number
  goals_against?: number
  derived?: {
    corsi_for?: number
    corsi_against?: number
    corsi_for_pct?: number | null
    offensive_zone_share?: number | null
    neutral_zone_share?: number | null
    defensive_zone_share?: number | null
    possession_share?: number | null
    entry_controlled_success_rate?: number | null
    exit_controlled_success_rate?: number | null
  }
  strength_splits?: Record<string, {
    cf?: number
    ca?: number
    cf_pct?: number | null
    oz_share?: number | null
    possession_time?: number | null
    entry_ctrl_rate?: number | null
    exit_ctrl_rate?: number | null
  }>
}

export interface TeamAdvancedMetrics {
  team: string
  season: string
  gameType: string
  lastUpdated?: string | null
  totals: {
    zone_time: { oz: number; nz: number; dz: number }
    possession_time: number
    entries: { controlled_attempts: number; controlled_success: number; dump_attempts: number }
    exits: { controlled_attempts: number; controlled_success: number; dump_attempts: number }
    shots_for: { on: number; missed: number; blocked: number; total: number }
    shots_against_total: number
    passes: number
    lpr_recoveries: number
    pressure_events: number
    turnovers: number
    // Opponent season totals (optional, for summaries)
    opponent_passes?: number
    opponent_lpr_recoveries?: number
    opponent_pressure_events?: number
    opponent_turnovers?: number
    derived: {
      corsi_for: number
      corsi_against: number
      corsi_for_pct: number | null
      offensive_zone_share: number | null
      possession_share: number | null
      entry_controlled_success_rate: number | null
      exit_controlled_success_rate: number | null
    }
    strength_splits: Record<string, {
      cf?: number
      ca?: number
      cf_pct?: number | null
      oz_share?: number | null
      entry_ctrl_rate?: number | null
      exit_ctrl_rate?: number | null
    }>
    deployments: {
      by_zone: Record<string, number>
      by_strength: Record<string, number>
    }
    pass_network_avg?: { nodes?: number | null; edges?: number | null; avg_degree?: number | null }
  }
  games: TeamAdvancedGame[]
}

// Team rotation analytics (line changes and transitions)
export interface TeamRotationEvent {
  team: string
  opponent: string
  season?: string
  game_id?: number | string
  event_index?: number | null
  sequence_index?: number | null
  period?: number | null
  period_time?: number | null
  game_time?: number | null
  timecode?: number | null
  stoppage_type?: string | null
  strength_state?: string | null // e.g., 5v5
  score_differential?: number | null // from team perspective
  from_forwards?: string | null // pipe-separated ids: "id1|id2|id3"
  from_defense?: string | null // pipe-separated ids: "id1|id2"
  to_forwards?: string | null
  to_defense?: string | null
  time_between_real?: number | null
  time_between_game?: number | null
  replacements_f?: Array<{ out: string | null; in: string | null }> | null
  replacements_d?: Array<{ out: string | null; in: string | null }> | null
}

export interface TeamRotationTransitionAgg {
  team: string
  strength_state?: string | null
  from_line: string // e.g., "F:ID|ID|ID_D:ID|ID"
  to_line: string
  season?: string | null
  opponent?: string | null
  game_date?: string | null
  game_id?: number | string
  result?: string | null
  count: number
}

export async function fetchTeamRotations(params: {
  team: string
  season?: string
  opponent?: string
  strength?: string
  limit?: number
}): Promise<{ team: string; count: number; events: TeamRotationEvent[] }> {
  const { team, season, opponent, strength, limit } = params
  const url = new URL(`${API_BASE_URL}/api/v1/team/${team}/rotations`)
  if (season) url.searchParams.set('season', season)
  if (opponent) url.searchParams.set('opponent', opponent)
  if (strength) url.searchParams.set('strength', strength)
  if (limit) url.searchParams.set('limit', String(limit))

  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch team rotations: ${res.status}`)
  const data = await res.json()
  // Normalize replacements JSON into arrays if backend returned strings
  const events: TeamRotationEvent[] = (data?.events || []).map((e: any) => ({
    ...e,
    replacements_f: Array.isArray(e?.replacements_f)
      ? e.replacements_f
      : safeJson(e?.replacements_f),
    replacements_d: Array.isArray(e?.replacements_d)
      ? e.replacements_d
      : safeJson(e?.replacements_d),
  }))
  return { team: data?.team || team, count: events.length, events }
}

export async function fetchTeamRotationTransitions(params: {
  team: string
  season?: string
  opponent?: string
  strength?: string
  limit?: number
  groupBy?: 'game'
}): Promise<{ team: string; count: number; transitions: TeamRotationTransitionAgg[] }> {
  const { team, season, opponent, strength, limit } = params
  const url = new URL(`${API_BASE_URL}/api/v1/team/${team}/rotations`)
  url.searchParams.set('aggregate', 'true')
  if (season) url.searchParams.set('season', season)
  if (opponent) url.searchParams.set('opponent', opponent)
  if (strength) url.searchParams.set('strength', strength)
  if (limit) url.searchParams.set('limit', String(limit))
  if (params.groupBy) url.searchParams.set('groupBy', params.groupBy)

  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Failed to fetch rotation transitions: ${res.status}`)
  const data = await res.json()
  return {
    team: data?.team || team,
    count: data?.count || 0,
    transitions: (data?.transitions || []) as TeamRotationTransitionAgg[],
  }
}

function safeJson(value: any) {
  try {
    return typeof value === 'string' ? JSON.parse(value) : value
  } catch {
    return null
  }
}

// Advanced player metrics (aggregated from extractor outputs)
export interface AdvancedPlayerMetrics {
  playerId: string
  season: string
  gameType: string
  lastUpdated?: string | null
  totals: {
    shift_count: number
    toi_game_sec: number
    avg_shift_game_sec: number | null
    avg_rest_game_sec: number | null
    lpr_recoveries: number
    pressure_events: number
    turnovers: number
    entries: {
      controlled_attempts: number
      controlled_success: number
      dump_attempts: number
      controlled_success_rate: number | null
    }
    exits: {
      controlled_attempts: number
      controlled_success: number
      dump_attempts: number
      controlled_success_rate: number | null
    }
    actions: Record<string, number>
    success_by_action: Record<string, { success: number; total: number }>
    success_rate_by_action: Record<string, number | null>
    preferred_zones: Record<string, number>
    preferred_shot_location: Record<string, number>
    top_opponents_by_time: Array<{ opponent_id: string; total_time_sec: number }>
  }
  games: Array<{
    gameId: number
    homeTeam?: string
    awayTeam?: string
    shift_count: number
    toi_game_sec: number
    avg_shift_game_sec: number | null
    avg_rest_game_sec: number | null
    lpr_recoveries: number
    pressure_events: number
    turnovers: number
    entries: { controlled_attempts: number; controlled_success: number; dump_attempts: number }
    exits: { controlled_attempts: number; controlled_success: number; dump_attempts: number }
    actions: Record<string, number>
    success_by_action: Record<string, { success: number; total: number }>
    preferred_zones: Record<string, number>
    preferred_shot_location: Record<string, number>
    momentum?: { final?: number; peak?: number; low?: number }
    top_opponents_by_time: Array<{ opponent_id: string; total_time_sec: number }>
    opponent_appearances?: Record<string, number>
    line_vs_pair_appearances?: Record<string, number>
    line_vs_pair_time_sec?: Record<string, number>
    trio_time_sec?: Record<string, number>
    deployments?: {
      by_zone?: Record<string, number>
      by_strength?: Record<string, number>
    }
    events?: Array<{
      x?: number | null
      y?: number | null
      x_adj?: number | null
      y_adj?: number | null
      zone?: string | null
      playSection?: string | null
      shorthand?: string | null
      outcome?: string | null
      period?: number | null
      gameTime?: number | null
    }>
  }>
}

export interface TeamMatchupHistory {
  opponent: string
  gamesPlayed: number
  wins: number
  losses: number
  otLosses: number
  goalsFor: number
  goalsAgainst: number
  lastGame: string
}

export interface PlayerNameEntry {
  lastName: string
  firstName?: string | null
  teamAbbrev?: string | null
}

// NHL API Integration Functions
async function fetchNHLTeamData(teamId: string): Promise<Partial<TeamProfile> | null> {
  try {
    const teamInfo = TEAM_INFO_MAP[teamId]
    if (!teamInfo) return null

    // Fetch team summary (record/stats) via backend standings proxy
    const summaryRes = await fetch(`${NHL_API_BASE}/team/${teamId}/summary`)
    let summary: any | null = null
    if (summaryRes.ok) {
      summary = await summaryRes.json()
    } else {
      console.log(`⚠️ Team summary call failed for ${teamId}: ${summaryRes.status}`)
    }

    return {
      id: getTeamIdFromAbbrev(teamId),
      name: getTeamNameFromAbbrev(teamId),
      city: teamInfo.city,
      division: teamInfo.division,
      conference: teamInfo.conference,
      logoUrl: `https://assets.nhle.com/logos/nhl/svg/${teamId}_light.svg`,
      darkLogoUrl: `https://assets.nhle.com/logos/nhl/svg/${teamId}_dark.svg`,
      ...(summary?.record ? { record: summary.record } : {}),
      ...(summary?.stats ? { stats: summary.stats } : {}),
    }
  } catch (error) {
    console.error('Error fetching NHL team data:', error)
    return null
  }
}

async function fetchNHLPlayerData(playerId: string | number): Promise<Partial<PlayerProfile> | null> {
  try {
    // Direct player lookup via backend proxy -> NHL /player/{id}/landing
    console.log(`📡 Fetching NHL player landing for ${playerId}`)
    const res = await fetch(`${NHL_API_BASE}/player/${playerId}/landing`)
    
    if (!res.ok) {
      console.log(`⚠️ Player landing call failed for ${playerId}: ${res.status}`)
      return null
    }
    
    const data = await res.json()
    console.log(`📊 NHL API player data for ${playerId}:`, data)

    // Parse NHL API response format
    const firstName = data?.firstName?.default || 'Unknown'
    const lastName = data?.lastName?.default || `Player ${playerId}`
    const position = data?.position || 'C'
    const jersey = data?.sweaterNumber || 0
    const teamAbbrev = data?.currentTeamAbbrev || ''
    const teamInfo = TEAM_INFO_MAP[teamAbbrev] || TEAM_INFO_MAP.MTL

    // Extract season stats from featuredStats.regularSeason.subSeason
    const seasonStats = data?.featuredStats?.regularSeason?.subSeason
    
    // Extract career stats from featuredStats.regularSeason.career
    const careerStats = data?.featuredStats?.regularSeason?.career
    
    // Calculate age from birthDate
    let age: number | undefined
    if (data?.birthDate) {
      const birthDate = new Date(data.birthDate)
      const today = new Date()
      age = today.getFullYear() - birthDate.getFullYear()
      const monthDiff = today.getMonth() - birthDate.getMonth()
      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age--
      }
    }
    
    // Format height (NHL API provides heightInInches)
    let heightFormatted: string | undefined
    if (data?.heightInInches) {
      const feet = Math.floor(data.heightInInches / 12)
      const inches = data.heightInInches % 12
      heightFormatted = `${feet}'${inches}"`
    }
    
    // Format birthplace - birthCity and birthStateProvince are objects with default property
    const birthCity = data?.birthCity?.default
    const birthStateProvince = data?.birthStateProvince?.default
    const birthCountry = data?.birthCountry
    
    let birthplace: string | undefined
    if (birthCity && birthStateProvince && birthCountry) {
      birthplace = `${birthCity}, ${birthStateProvince}, ${birthCountry}`
    } else if (birthCity && birthCountry) {
      birthplace = `${birthCity}, ${birthCountry}`
    } else if (birthCity) {
      birthplace = birthCity
    }
    
    return {
      // Ensure both id (number) and playerId (string|number) are available to the UI
      id: data?.playerId || parseInt(playerId as string) || 0,
      playerId: data?.playerId || playerId,
      name: `${firstName} ${lastName}`.trim(),
      firstName,
      lastName,
      position,
      jerseyNumber: jersey,
      teamId: teamAbbrev,
      teamName: getTeamNameFromAbbrev(teamAbbrev),
      teamFullName: `${teamInfo.city} ${getTeamNameFromAbbrev(teamAbbrev)}`,
      
      // Bio data
      birthDate: data?.birthDate,
      birthCity,
      birthStateProvince,
      birthCountry,
      birthplace,
      heightInInches: data?.heightInInches,
      heightInCentimeters: data?.heightInCentimeters,
      heightFormatted,
      weightInPounds: data?.weightInPounds,
      weightInKilograms: data?.weightInKilograms,
      shootsCatches: data?.shootsCatches,
      draftYear: data?.draftDetails?.year,
      draftRound: data?.draftDetails?.round,
      draftOverall: data?.draftDetails?.overallPick,
      age,
      
      // Career stats
      ...(careerStats && {
        careerStats: {
          gamesPlayed: careerStats.gamesPlayed || 0,
          goals: careerStats.goals || 0,
          assists: careerStats.assists || 0,
          points: careerStats.points || 0,
          plusMinus: careerStats.plusMinus || 0,
          pim: careerStats.pim || 0,
          shots: careerStats.shots || 0,
          shootingPct: (careerStats.shootingPctg || 0) * 100,
          powerPlayGoals: careerStats.powerPlayGoals || 0,
          powerPlayPoints: careerStats.powerPlayPoints || 0,
          shortHandedGoals: careerStats.shorthandedGoals || 0,
          shortHandedPoints: careerStats.shorthandedPoints || 0,
          gameWinningGoals: careerStats.gameWinningGoals || 0,
          otGoals: careerStats.otGoals || 0,
        }
      }),
      
      // Season totals (from seasonTotals array - filter for NHL regular season only)
      seasonTotals: data?.seasonTotals?.filter((s: any) => 
        s.leagueAbbrev === 'NHL' && s.gameTypeId === 2
      ).map((s: any) => ({
        season: s.season,
        leagueAbbrev: s.leagueAbbrev,
        gameTypeId: s.gameTypeId,
        gamesPlayed: s.gamesPlayed || 0,
        goals: s.goals || 0,
        assists: s.assists || 0,
        points: s.points || 0,
        plusMinus: s.plusMinus || 0,
        pim: s.pim || 0,
        shots: s.shots,
        shootingPctg: s.shootingPctg,
        powerPlayGoals: s.powerPlayGoals,
        powerPlayPoints: s.powerPlayPoints,
        shorthandedGoals: s.shorthandedGoals,
        avgToi: s.avgToi,
        teamAbbrev: s.teamCommonName?.default,
      })),
      
      // Last 5 games
      last5Games: data?.last5Games?.map((g: any) => ({
        gameId: g.gameId,
        gameDate: g.gameDate,
        opponentAbbrev: g.opponentAbbrev,
        homeRoadFlag: g.homeRoadFlag,
        goals: g.goals || 0,
        assists: g.assists || 0,
        points: g.points || 0,
        plusMinus: g.plusMinus || 0,
        shots: g.shots || 0,
        pim: g.pim || 0,
        toi: g.toi,
      })),
      
      ...(seasonStats && {
        seasonStats: {
          gamesPlayed: seasonStats.gamesPlayed || 0,
          goals: seasonStats.goals || 0,
          assists: seasonStats.assists || 0,
          points: seasonStats.points || 0,
          plusMinus: seasonStats.plusMinus || 0,
          pim: seasonStats.pim || 0,
          shots: seasonStats.shots || 0,
          shootingPct: (seasonStats.shootingPctg || 0) * 100,
          timeOnIce: '00:00', // Not in landing endpoint, will need game-by-game
          powerPlayGoals: seasonStats.powerPlayGoals || 0,
          powerPlayPoints: seasonStats.powerPlayPoints || 0,
          shortHandedGoals: seasonStats.shorthandedGoals || 0,
          hits: 0, // Not in landing endpoint
          blockedShots: 0, // Not in landing endpoint
          takeaways: 0, // Not in landing endpoint
          giveaways: 0, // Not in landing endpoint
        }
      })
    }
  } catch (error) {
    console.error('Error fetching NHL player data:', error)
    return null
  }
}

// Helper functions for team data mapping (using official NHL team IDs)
function getTeamIdFromAbbrev(abbrev: string): number {
  const teamIds: Record<string, number> = {
    // Eastern Conference - Atlantic Division
    MTL: 8,   // Montréal Canadiens
    TOR: 10,  // Toronto Maple Leafs
    BOS: 6,   // Boston Bruins
    BUF: 7,   // Buffalo Sabres
    OTT: 9,   // Ottawa Senators
    DET: 17,  // Detroit Red Wings
    FLA: 13,  // Florida Panthers
    TBL: 14,  // Tampa Bay Lightning
    
    // Eastern Conference - Metropolitan Division
    NYR: 3,   // New York Rangers
    NYI: 2,   // New York Islanders
    PHI: 4,   // Philadelphia Flyers
    WSH: 15,  // Washington Capitals
    CAR: 12,  // Carolina Hurricanes
    NJD: 1,   // New Jersey Devils
    CBJ: 29,  // Columbus Blue Jackets
    PIT: 5,   // Pittsburgh Penguins
    
    // Western Conference - Central Division
    COL: 21,  // Colorado Avalanche
    DAL: 25,  // Dallas Stars
    MIN: 30,  // Minnesota Wild
    NSH: 18,  // Nashville Predators
    STL: 19,  // St. Louis Blues
    WPG: 52,  // Winnipeg Jets
    CHI: 16,  // Chicago Blackhawks
    UTA: 59,  // Utah Hockey Club (formerly Arizona Coyotes)
    
    // Western Conference - Pacific Division
    VGK: 54,  // Vegas Golden Knights
    SEA: 55,  // Seattle Kraken
    LAK: 26,  // Los Angeles Kings
    SJS: 28,  // San Jose Sharks
    ANA: 24,  // Anaheim Ducks
    VAN: 23,  // Vancouver Canucks
    CGY: 20,  // Calgary Flames
    EDM: 22,  // Edmonton Oilers
    
    // Legacy mapping for Arizona (now Utah)
    ARI: 59,  // Maps to Utah Hockey Club
  }
  return teamIds[abbrev] || 8  // Default to Montreal Canadiens if not found
}

function getTeamNameFromAbbrev(abbrev: string): string {
  const teamNames: Record<string, string> = {
    // Eastern Conference - Atlantic Division
    MTL: 'Canadiens',
    TOR: 'Maple Leafs', 
    BOS: 'Bruins',
    BUF: 'Sabres',
    OTT: 'Senators',
    DET: 'Red Wings',
    FLA: 'Panthers',
    TBL: 'Lightning',
    
    // Eastern Conference - Metropolitan Division
    NYR: 'Rangers',
    NYI: 'Islanders',
    PHI: 'Flyers',
    WSH: 'Capitals',
    CAR: 'Hurricanes',
    NJD: 'Devils',
    CBJ: 'Blue Jackets',
    PIT: 'Penguins',
    
    // Western Conference - Central Division
    COL: 'Avalanche',
    DAL: 'Stars',
    MIN: 'Wild',
    NSH: 'Predators',
    STL: 'Blues',
    WPG: 'Jets',
    CHI: 'Blackhawks',
    UTA: 'Mammoth',  // Utah Hockey Club
    
    // Western Conference - Pacific Division
    VGK: 'Golden Knights',
    SEA: 'Kraken',
    LAK: 'Kings',
    SJS: 'Sharks',
    ANA: 'Ducks',
    VAN: 'Canucks',
    CGY: 'Flames',
    EDM: 'Oilers',
    
    // Legacy mapping
    ARI: 'Hockey Club',  // Arizona -> Utah Hockey Club
  }
  return teamNames[abbrev] || 'Team'
}

function getTeamAbbrevFromId(id: number): string | undefined {
  const map: Record<number, string> = {
    8: 'MTL', 10: 'TOR', 6: 'BOS', 7: 'BUF', 9: 'OTT', 17: 'DET', 13: 'FLA', 14: 'TBL',
    3: 'NYR', 2: 'NYI', 4: 'PHI', 15: 'WSH', 12: 'CAR', 1: 'NJD', 29: 'CBJ', 5: 'PIT',
    21: 'COL', 25: 'DAL', 30: 'MIN', 18: 'NSH', 19: 'STL', 52: 'WPG', 16: 'CHI', 59: 'UTA',
    54: 'VGK', 55: 'SEA', 26: 'LAK', 28: 'SJS', 24: 'ANA', 23: 'VAN', 20: 'CGY', 22: 'EDM',
  }
  return map[id]
}

// API functions with NHL API integration
export async function getTeamProfile(teamId: string): Promise<TeamProfile> {
  console.log(`🏒 Fetching team profile for: ${teamId}`)
  
  const nhlData = await fetchNHLTeamData(teamId)
  
  if (!nhlData) {
    throw new Error(`Failed to fetch team data for ${teamId}`)
  }
  
  return nhlData as TeamProfile
}

export async function getPlayerProfile(playerId: string | number): Promise<PlayerProfile> {
  console.log(`🏒 Fetching player profile for: ${playerId}`)
  
  const nhlData = await fetchNHLPlayerData(playerId)
  
  if (!nhlData) {
    throw new Error(`Failed to fetch player data for ${playerId}`)
  }
  
  // TODO: Fetch contract data from your parquet files
  // For now, contract data is not available from NHL API
  return nhlData as PlayerProfile
}

export async function getPlayerGameLogs(
  playerId: string | number,
  opts?: { season?: string; gameType?: 'regular' | 'playoffs' }
): Promise<GameLog[]> {
  try {
    // Get current season if not provided
    const season = opts?.season || getCurrentSeason()
    const gameType = opts?.gameType || 'regular'
    const gameTypeId = gameType === 'regular' ? '2' : '3'
    
    console.log(`Fetching game logs for player ${playerId} - ${season} ${gameType}`)
    
    const res = await fetch(`${NHL_API_BASE}/player/${playerId}/game-log/${season}/${gameTypeId}`)
    
    if (!res.ok) {
      console.log(`Game log not available for player ${playerId}: ${res.status}`)
      return []
    }
    
    const data = await res.json()
    const gameLog = data.gameLog || []
    
    console.log(`Fetched ${gameLog.length} games for player ${playerId}`)
    
    // Transform NHL API format to our GameLog interface
    const gameLogs: GameLog[] = gameLog.map((game: any) => {
      // Determine home/away and opponent
      const homeTeamAbbrev = game.homeRoadFlag === 'H' ? game.teamAbbrev : game.opponentAbbrev
      const awayTeamAbbrev = game.homeRoadFlag === 'R' ? game.teamAbbrev : game.opponentAbbrev
      const isHome = game.homeRoadFlag === 'H'
      
      // Determine game result (W/L/OTL)
      let result: 'W' | 'L' | 'OTL' = 'L'
      if (game.gameOutcome) {
        if (game.gameOutcome.lastPeriodType === 'OT' || game.gameOutcome.lastPeriodType === 'SO') {
          // Overtime or shootout
          if ((isHome && game.homeRoadFlag === 'H') || (!isHome && game.homeRoadFlag === 'R')) {
            // Player's team won or lost
            result = game.teamAbbrev === (game.gameOutcome.homeTeamWon ? homeTeamAbbrev : awayTeamAbbrev) ? 'W' : 'OTL'
          }
        } else {
          // Regulation
          result = game.gameOutcome.homeTeamWon === isHome ? 'W' : 'L'
        }
      }
      
      return {
        gameId: String(game.gameId),
        date: game.gameDate,
        opponent: game.opponentAbbrev || '',
        opponentName: getTeamNameFromAbbrev(game.opponentAbbrev || ''),
        homeAway: isHome ? 'home' : 'away',
        result,
        
        // Basic stats
        goals: game.goals || 0,
        assists: game.assists || 0,
        points: game.points || 0,
        plusMinus: game.plusMinus || 0,
        pim: game.pim || 0,
        shots: game.shots || 0,
        hits: game.hits || 0,
        blockedShots: game.blockedShots || 0,
        takeaways: 0, // Not available in game-log endpoint
        giveaways: 0, // Not available in game-log endpoint
        timeOnIce: game.toi || '00:00',
        shifts: game.shifts || 0,
        
        // Special teams
        powerPlayGoals: game.powerPlayGoals || 0,
        shortHandedGoals: game.shorthandedGoals || 0,
        gameWinningGoals: game.gameWinningGoals || 0,
        
        // Faceoffs (for centers)
        faceoffWins: game.faceoffWins,
        faceoffLosses: game.faceoffLosses,
        faceoffWinPct: game.faceoffWinningPctg ? game.faceoffWinningPctg * 100 : undefined,
        
        // Game context
        gameState: 'FINAL',
        periodType: game.gameOutcome?.lastPeriodType,
      }
    })
    
    return gameLogs
  } catch (error) {
    console.error('Error fetching game logs:', error)
    return []
  }
}

// Helper function to get current season in YYYYYYYY format
function getCurrentSeason(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1 // 0-indexed
  
  // NHL season typically starts in October
  // If we're in Jan-Sep, we're in the season that started last year
  if (month < 10) {
    return `${year - 1}${year}`
  } else {
    return `${year}${year + 1}`
  }
}

export async function getPlayerAdvancedMetrics(
  playerId: string | number,
  opts?: { season?: string; gameType?: 'regular' | 'playoffs' }
): Promise<AdvancedPlayerMetrics | null> {
  try {
    const params = new URLSearchParams()
    if (opts?.season) params.set('season', opts.season)
    if (opts?.gameType) params.set('game_type', opts.gameType)
    const url = `${API_BASE_URL}/api/v1/player/${playerId}/advanced${params.toString() ? `?${params.toString()}` : ''}`
    const res = await fetch(url)
    if (!res.ok) {
      console.log(`⚠️ Advanced metrics not available for ${playerId}: ${res.status}`)
      return null
    }
    const data = (await res.json()) as AdvancedPlayerMetrics
    return data
  } catch (err) {
    console.error('Error fetching advanced metrics:', err)
    return null
  }
}

export async function resolvePlayerNames(ids: Array<string | number>): Promise<Record<string, PlayerNameEntry>> {
  if (!ids || ids.length === 0) return {}
  // De-duplicate and sort for stable cache key
  const uniq = Array.from(new Set(ids.map(x => String(x))))
  uniq.sort((a,b) => a.localeCompare(b))
  const key = uniq.join(',')
  // In-memory request cache to prevent duplicate calls across components
  const g = (globalThis as any)
  g.__resolveCache = g.__resolveCache || new Map<string, Promise<Record<string, PlayerNameEntry>>>()
  const cache: Map<string, Promise<Record<string, PlayerNameEntry>>> = g.__resolveCache
  if (cache.has(key)) {
    return await cache.get(key)!
  }
  const promise = (async () => {
    const params = new URLSearchParams()
    params.set('ids', uniq.join(','))
    const url = `${API_BASE_URL}/api/v1/player/resolve?${params.toString()}`
    const res = await fetch(url)
    if (!res.ok) return {}
    const data = (await res.json()) as Record<string, PlayerNameEntry>
    return data
  })()
  cache.set(key, promise)
  try {
    const result = await promise
    return result
  } finally {
    // optionally keep cache; do not delete to allow reuse
  }
}

export interface PlayerEvent {
  x?: number | null
  y?: number | null
  x_adj?: number | null
  y_adj?: number | null
  zone?: string | null
  playSection?: string | null
  shorthand?: string | null
  outcome?: string | null
  period?: number | null
  gameTime?: number | null
}

export interface PlayerShift {
  start_game_time: number | null
  end_game_time: number | null
  start_period?: number | null
  end_period?: number | null
  start_period_time?: number | null
  end_period_time?: number | null
  shift_game_length?: number | null
  shift_real_length?: number | null
  rest_game_next?: number | null
  rest_real_next?: number | null
  strength_start?: string | null
  manpower_start?: string | null
  sequence_ids?: number[]
  deployment_ids?: number[]
  index?: number
}

export async function getPlayerGameEvents(
  playerId: string | number,
  gameId: number,
  opts?: { season?: string; teamAbbrev?: string }
): Promise<{ events: PlayerEvent[]; shifts: PlayerShift[] }> {
  const params = new URLSearchParams()
  if (opts?.season) params.set('season', opts.season)
  if (opts?.teamAbbrev) params.set('team_abbrev', opts.teamAbbrev)
  const url = `${API_BASE_URL}/api/v1/player/${playerId}/events/${gameId}${params.toString() ? `?${params.toString()}` : ''}`
  const res = await fetch(url)
  if (!res.ok) return { events: [], shifts: [] }
  const data = await res.json()
  const events = Array.isArray(data?.events) ? (data.events as PlayerEvent[]) : []
  const shifts = Array.isArray(data?.shifts) ? (data.shifts as PlayerShift[]) : []
  return { events, shifts }
}

// Game-level deployments (whistle/period starts) enriched with score
export interface GameDeployment {
  deployment_id?: number
  whistle_time?: number
  whistle_event_index?: number
  period?: number
  home_forwards?: string[]
  home_defense?: string[]
  away_forwards?: string[]
  away_defense?: string[]
  strength?: string
  manpowerSituation?: string | null
  home_skaters?: number | null
  away_skaters?: number | null
  home_zone?: string | null
  away_zone?: string | null
  faceoff_zone?: string | null
  faceoff_winner_team?: string | null
  home_score?: number | null
  away_score?: number | null
  score_diff?: number | null
}

export async function getGameDeployments(
  gameId: number | string
): Promise<{
  game_id: number
  home_team_code?: string
  away_team_code?: string
  deployments: GameDeployment[]
  period_openers: GameDeployment[]
}> {
  const url = `${API_BASE_URL}/api/v1/team/game/${gameId}/deployments`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Failed to fetch game deployments: ${res.status}`)
  }
  const data = await res.json()
  return {
    game_id: data?.game_id ?? Number(gameId),
    home_team_code: data?.home_team_code,
    away_team_code: data?.away_team_code,
    deployments: Array.isArray(data?.deployments) ? (data.deployments as GameDeployment[]) : [],
    period_openers: Array.isArray(data?.period_openers) ? (data.period_openers as GameDeployment[]) : [],
  }
}

// Build matchup table from a TeamAdvancedMetrics object
export function buildTeamMatchupsFromAdvanced(adv: TeamAdvancedMetrics | null | undefined): TeamMatchupHistory[] {
  if (!adv) return []
  const opps: Record<string, any> | undefined = (adv as any)?.totals?.opponents
  if (opps && typeof opps === 'object') {
    return Object.entries(opps).map(([opponent, row]) => ({
      opponent,
      gamesPlayed: Number((row as any).gamesPlayed || 0),
      wins: Number((row as any).wins || 0),
      losses: Number((row as any).losses || 0),
      otLosses: Number((row as any).otLosses || 0),
      goalsFor: Number((row as any).goalsFor || 0),
      goalsAgainst: Number((row as any).goalsAgainst || 0),
      lastGame: String((row as any).lastGame || ''),
    }))
  }
  // Fallback from per-game list
  const byOpp: Record<string, TeamMatchupHistory> = {}
  for (const g of (adv.games || [])) {
    const opp = String((g as any).opponent || '?')
    const gf = Number((g as any).goals_for || 0)
    const ga = Number((g as any).goals_against || 0)
    const wentToOT = Boolean((g as any).went_to_ot)
    if (!byOpp[opp]) {
      byOpp[opp] = {
        opponent: opp,
        gamesPlayed: 0,
        wins: 0,
        losses: 0,
        otLosses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        lastGame: '',
      }
    }
    const row = byOpp[opp]
    row.gamesPlayed += 1
    row.goalsFor += gf
    row.goalsAgainst += ga
    if (gf > ga) row.wins += 1
    else if (gf < ga) row[wentToOT ? 'otLosses' : 'losses'] += 1
    const d = (g as any).gameDate
    if (d && (!row.lastGame || String(d) > row.lastGame)) row.lastGame = String(d)
  }
  return Object.values(byOpp)
}

export async function getTeamPerformance(teamId: string): Promise<TeamPerformanceData> {
  // TODO: Implement NHL API integration for team performance
  console.log(`⚠️ Team performance not yet implemented for ${teamId}`)
  return {
    goalsPerGame: [],
    xGoalsPerGame: [],
    winLossPattern: [],
    homeAwaySplits: {
      home: { gf: 0, ga: 0, record: '0-0-0' },
      away: { gf: 0, ga: 0, record: '0-0-0' },
    },
  }
}

export async function getTeamAdvancedMetrics(
  teamId: string,
  opts?: { season?: string }
): Promise<TeamAdvancedMetrics | null> {
  try {
    const params = new URLSearchParams()
    if (opts?.season) params.set('season', opts.season)
    const url = `${API_BASE_URL}/api/v1/team/${teamId}/advanced${params.toString() ? `?${params.toString()}` : ''}`
    const res = await fetch(url)
    if (!res.ok) {
      console.log(`⚠️ Team advanced metrics not available for ${teamId}: ${res.status}`)
      return null
    }
    const data = (await res.json()) as TeamAdvancedMetrics
    return data
  } catch (err) {
    console.error('Error fetching team advanced metrics:', err)
    return null
  }
}

export async function getTeamMatchups(teamId: string): Promise<TeamMatchupHistory[]> {
  try {
    const adv = await getTeamAdvancedMetrics(teamId)
    if (!adv) return []

    // Prefer pre-aggregated opponents summary if present
    const opps: Record<string, any> | undefined = (adv as any)?.totals?.opponents
    if (opps && typeof opps === 'object') {
      return Object.entries(opps).map(([opponent, row]) => ({
        opponent,
        gamesPlayed: Number((row as any).gamesPlayed || 0),
        wins: Number((row as any).wins || 0),
        losses: Number((row as any).losses || 0),
        otLosses: Number((row as any).otLosses || 0),
        goalsFor: Number((row as any).goalsFor || 0),
        goalsAgainst: Number((row as any).goalsAgainst || 0),
        lastGame: String((row as any).lastGame || ''),
      }))
    }

    // Fallback: compute from per-game list
    const byOpp: Record<string, TeamMatchupHistory> = {}
    for (const g of (adv.games || [])) {
      const opp = String((g as any).opponent || '?')
      const gf = Number((g as any).goals_for || 0)
      const ga = Number((g as any).goals_against || 0)
      const wentToOT = Boolean((g as any).went_to_ot)
      if (!byOpp[opp]) {
        byOpp[opp] = {
          opponent: opp,
          gamesPlayed: 0,
          wins: 0,
          losses: 0,
          otLosses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          lastGame: '',
        }
      }
      const row = byOpp[opp]
      row.gamesPlayed += 1
      row.goalsFor += gf
      row.goalsAgainst += ga
      if (gf > ga) row.wins += 1
      else if (gf < ga) row[wentToOT ? 'otLosses' : 'losses'] += 1
      const d = (g as any).gameDate
      if (d && (!row.lastGame || String(d) > row.lastGame)) row.lastGame = String(d)
    }
    return Object.values(byOpp)
  } catch (e) {
    console.error('getTeamMatchups failed:', e)
    return []
  }
}

// Test function to check NHL API connectivity via backend proxy
export async function testNHLAPI(): Promise<void> {
  console.log('🧪 Testing NHL API connectivity via backend proxy...')
  
  try {
    // Test 1: Check backend NHL API test endpoint
    console.log('📡 Testing backend proxy health...')
    const testResponse = await fetch(`${NHL_API_BASE}/test`)
    console.log(`Backend proxy status: ${testResponse.status}`)
    
    if (testResponse.ok) {
      const testData = await testResponse.json()
      console.log('Backend NHL API proxy working!', testData)
    } else {
      console.log(`Backend proxy failed with status: ${testResponse.status}`)
      const errorText = await testResponse.text()
      console.log('Backend proxy error:', errorText)
    }
    
    // Test 2: Actual roster call through proxy
    console.log('📡 Testing roster endpoint via proxy...')
    const rosterResponse = await fetch(`${NHL_API_BASE}/roster/MTL/current`)
    console.log(`Roster call status: ${rosterResponse.status}`)
    
    if (rosterResponse.ok) {
      const rosterData = await rosterResponse.json()
      console.log('✅ NHL API roster call successful!')
      console.log('Sample roster data:', rosterData)
    } else {
      console.log(` Roster call failed with status: ${rosterResponse.status}`)
      const errorText = await rosterResponse.text()
      console.log('Roster error:', errorText)
    }
    
  } catch (error) {
    console.error('❌ NHL API test failed:', error)
    
    if (error instanceof TypeError && error.message.includes('fetch')) {
      console.log('🚫 This might be a connectivity issue.')
      console.log('💡 Check:')
      console.log('1. Is your FastAPI backend running on port 8000?')
      console.log('2. Is the NHL proxy route properly configured?')
      console.log('3. Does the backend have httpx dependency installed?')
    }
  }
}

// Add this to window for easy testing
if (typeof window !== 'undefined') {
  (window as any).testNHLAPI = testNHLAPI
}
