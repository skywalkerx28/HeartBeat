/**
 * HeartBeat Engine - API Client
 * Montreal Canadiens Advanced Analytics Assistant
 * 
 * API client for communicating with the FastAPI backend.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  success: boolean
  access_token?: string
  user_info?: {
    username: string
    name: string
    role: string
    email: string
    team_access: string[]
  }
  message: string
  expires_in?: number
}

export interface QueryRequest {
  query: string
  context?: string
}

export interface QueryResponse {
  success: boolean
  response: string
  query_type?: string
  tool_results: Array<{
    tool: string
    success: boolean
    data?: any
    processing_time_ms: number
    citations: string[]
    error?: string
  }>
  processing_time_ms: number
  evidence: string[]
  citations: string[]
  analytics: Array<{
    type: string
    title: string
    data: any
    metadata?: any
  }>
  user_role: string
  timestamp: string
  errors: string[]
  warnings: string[]
}

export interface NHLGame {
  id: number
  season: number
  gameType: number
  gameDate: string
  venue: {
    default: string
  }
  startTimeUTC: string
  easternUTCOffset: string
  venueUTCOffset: string
  tvBroadcasts?: Array<{
    id: number
    market: string
    countryCode: string
    network: string
    sequenceNumber: number
  }>
  gameState: string
  gameScheduleState: string
  awayTeam: {
    id: number
    name: {
      default: string
    }
    abbrev: string
    score?: number
    sog?: number
    logo: string
  }
  homeTeam: {
    id: number
    name: {
      default: string
    }
    abbrev: string
    score?: number
    sog?: number
    logo: string
  }
  gameCenterLink: string
  clock?: {
    timeRemaining: string
    secondsRemaining: number
    running: boolean
    inIntermission: boolean
  }
  neutralSite: boolean
  venueTimezone: string
  period?: number
  periodDescriptor?: {
    number: number
    periodType: string
    maxRegulationPeriods: number
  }
  gameOutcome?: {
    lastPeriodType: string
  }
  situation?: {
    homeTeam: {
      abbrev: string
      strength: number
    }
    awayTeam: {
      abbrev: string
      situationDescriptions?: string[]
      strength: number
    }
    situationCode: string
    timeRemaining: string
    secondsRemaining: number
  }
  goals?: Array<{
    period: number
    periodDescriptor: {
      number: number
      periodType: string
      maxRegulationPeriods: number
    }
    timeInPeriod: string
    playerId: number
    name: {
      default: string
    }
    firstName: {
      default: string
    }
    lastName: {
      default: string
    }
    goalModifier: string
    assists?: Array<{
      playerId: number
      name: {
        default: string
      }
      assistsToDate: number
    }>
    mugshot: string
    teamAbbrev: string
    goalsToDate: number
    awayScore: number
    homeScore: number
    strength: string
    highlightClipSharingUrl?: string
    highlightClipSharingUrlFr?: string
    highlightClip?: number
    highlightClipFr?: number
    discreteClip?: number
    discreteClipFr?: number
  }>
}

export interface NHLScheduleResponse {
  games: NHLGame[]
  date: string
}

class HeartBeatAPI {
  private accessToken: string | null = null

  setAccessToken(token: string) {
    this.accessToken = token
  }

  clearAccessToken() {
    this.accessToken = null
  }

  // Expose base URL and token when UI needs to build absolute media URLs
  getBaseUrl(): string {
    return API_BASE_URL
  }

  getAccessToken(): string | null {
    return this.accessToken
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`
    }

    return headers
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(credentials),
    })

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`)
    }

    const data = await response.json()
    
    if (data.success && data.access_token) {
      this.setAccessToken(data.access_token)
    }

    return data
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: this.getHeaders(),
      })
    } finally {
      this.clearAccessToken()
    }
  }

  async sendQuery(query: QueryRequest): Promise<QueryResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/query/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(query),
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Authentication required')
      }
      throw new Error(`Query failed: ${response.statusText}`)
    }

    return await response.json()
  }

  async getHealthStatus(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`)
    }

    return await response.json()
  }

  async getPlayers(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analytics/players`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch players: ${response.statusText}`)
    }

    return await response.json()
  }

  async getTeams(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analytics/teams`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch teams: ${response.statusText}`)
    }

    return await response.json()
  }

  // NHL API Methods (proxied through our backend)
  async getNHLSchedule(date?: string): Promise<NHLScheduleResponse> {
    // Get local date instead of UTC to avoid timezone issues
    const getLocalDate = () => {
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    const targetDate = date || getLocalDate()

    try {
      const params = date ? `?date=${targetDate}` : ''
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/nhl/schedule${params}`, {
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch NHL schedule: ${response.statusText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.detail || 'Failed to fetch NHL schedule')
      }

      // Transform the response to match our interface
      return {
        games: data.games || [],
        date: data.date || targetDate
      }
    } catch (error) {
      console.error('Error fetching NHL schedule:', error)
      throw new Error(`Failed to fetch NHL schedule: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getNHLLiveScores(date?: string): Promise<NHLScheduleResponse> {
    // Get local date instead of UTC to avoid timezone issues
    const getLocalDate = () => {
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    const targetDate = date || getLocalDate()

    try {
      const params = `?date=${targetDate}`
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/nhl/scores${params}`, {
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch NHL live scores: ${response.statusText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.detail || 'Failed to fetch NHL scores')
      }

      // Transform the response to match our interface
      return {
        games: data.games || [],
        date: data.date || targetDate
      }
    } catch (error) {
      console.error('Error fetching NHL live scores:', error)
      throw new Error(`Failed to fetch NHL live scores: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getGameBoxscore(gameId: number): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/nhl/game/${gameId}/boxscore`, {
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch boxscore: ${response.statusText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.detail || 'Failed to fetch boxscore')
      }

      return data.data
    } catch (error) {
      console.error('Error fetching game boxscore:', error)
      throw new Error(`Failed to fetch game boxscore: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getGamePlayByPlay(gameId: number): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/nhl/game/${gameId}/play-by-play`, {
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch play-by-play: ${response.statusText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.detail || 'Failed to fetch play-by-play')
      }

      return data.data
    } catch (error) {
      console.error('Error fetching play-by-play:', error)
      throw new Error(`Failed to fetch play-by-play: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getGameLanding(gameId: number): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/nhl/game/${gameId}/landing`, {
        headers: this.getHeaders(),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch game landing: ${response.statusText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.detail || 'Failed to fetch game landing')
      }

      return data.data
    } catch (error) {
      console.error('Error fetching game landing:', error)
      throw new Error(`Failed to fetch game landing: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }
}

// Export singleton instance
export const api = new HeartBeatAPI()
