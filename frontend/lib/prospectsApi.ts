/**
 * Prospects API Client
 * Functions for fetching prospect data from the HeartBeat Engine
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Prospect {
  name: string
  age: number
  position: string
  shot_catches?: string
  height?: string
  weight?: string
  draft_round?: number
  draft_pick?: number
  draft_year?: number
  birthdate?: string
  birthplace?: string
  nationality?: string
  sign_by_date?: string
  ufa_year?: number
  waivers_eligibility?: string
  est_career_earnings?: string
}

export interface ProspectsResponse {
  prospects: Prospect[]
  total: number
  team: string
  season: string
}

/**
 * Fetch prospects for a specific team
 */
export async function getTeamProspects(
  teamId: string,
  season: string = '20252026',
  position?: string
): Promise<ProspectsResponse> {
  try {
    const params = new URLSearchParams()
    params.append('season', season)
    if (position) {
      params.append('position', position)
    }

    const url = `${API_BASE_URL}/api/prospects/team/${teamId.toUpperCase()}?${params.toString()}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Don't cache prospect data
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch prospects: ${response.statusText}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('Error fetching prospects:', error)
    throw error
  }
}

/**
 * Fetch prospects filtered by position
 */
export async function getTeamProspectsByPosition(
  teamId: string,
  position: 'F' | 'D' | 'G',
  season: string = '20252026'
): Promise<ProspectsResponse> {
  try {
    const url = `${API_BASE_URL}/api/prospects/team/${teamId.toUpperCase()}/position/${position}?season=${season}`
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch prospects: ${response.statusText}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('Error fetching prospects by position:', error)
    throw error
  }
}

/**
 * Get primary position from position string
 * Handles combined positions like "C,RW" or "C,W"
 */
export function getPrimaryPosition(position: string): string {
  if (!position) return ''
  const positions = position.split(',').map(p => p.trim())
  return positions[0] || ''
}

/**
 * Determine if position is forward
 */
export function isForward(position: string): boolean {
  const pos = getPrimaryPosition(position).toUpperCase()
  return ['C', 'LW', 'RW', 'W', 'F'].includes(pos)
}

/**
 * Determine if position is defense
 */
export function isDefense(position: string): boolean {
  const pos = getPrimaryPosition(position).toUpperCase()
  return pos === 'D'
}

/**
 * Determine if position is goalie
 */
export function isGoalie(position: string): boolean {
  const pos = getPrimaryPosition(position).toUpperCase()
  return pos === 'G'
}

