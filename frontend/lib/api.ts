/**
 * HeartBeat Engine - API Client
 * Montreal Canadiens Advanced Analytics Assistant
 * 
 * API client for communicating with the FastAPI backend.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://192.168.6.45:8000'

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
}

// Export singleton instance
export const api = new HeartBeatAPI()
