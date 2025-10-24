'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { TeamLink } from '../navigation/TeamLink'

interface StandingsTeam {
  teamName?: { default?: string }
  teamAbbrev?: { default?: string }
  wins?: number
  losses?: number
  otLosses?: number
  points?: number
  gamesPlayed?: number
  goalDifferential?: number
  divisionName?: string
  streakCode?: string
  l10Wins?: number
  l10Losses?: number
  l10OtLosses?: number
}

interface CompactStandingsProps {
  standings: StandingsTeam[]
  isLoading?: boolean
}

export function CompactStandings({ standings, isLoading }: CompactStandingsProps) {
  if (isLoading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/20 dark:border-white/5" />
        <div className="relative p-6 text-center">
          <div className="text-xs font-military-display text-gray-600 dark:text-gray-400">
            LOADING STANDINGS...
          </div>
        </div>
      </div>
    )
  }

  const atlanticTeams = standings.filter(team => 
    team.divisionName === 'Atlantic' || 
    ['MTL', 'TOR', 'BOS', 'TBL', 'FLA', 'OTT', 'DET', 'BUF'].includes(
      team.teamAbbrev?.default || ''
    )
  )

  const getTeamLogo = (abbrev?: string) => {
    if (!abbrev) return ''
    return `https://assets.nhle.com/logos/nhl/svg/${abbrev}_light.svg`
  }

  // Mock last 5 games for demonstration (would come from API)
  const getLastFive = (abbrev: string) => {
    const mockData: Record<string, string> = {
      'TOR': 'WWLWW',
      'BOS': 'WWWLW',
      'FLA': 'WLWWL',
      'BUF': 'LLLLL',
      'DET': 'WLWLL',
      'OTT': 'LLWLL',
      'TBL': 'WWWWL',
      'MTL': 'LWLLW'
    }
    return mockData[abbrev] || 'WWLWL'
  }

  // Mock Strain Index (would be calculated from travel/schedule data)
  const getStrainIndex = (abbrev: string): { value: number; status: 'low' | 'medium' | 'high' } => {
    const mockData: Record<string, number> = {
      'TOR': 42,
      'BOS': 38,
      'FLA': 71,
      'BUF': 29,
      'DET': 55,
      'OTT': 48,
      'TBL': 68,
      'MTL': 52
    }
    const value = mockData[abbrev] || 50
    const status = value < 40 ? 'low' : value < 60 ? 'medium' : 'high'
    return { value, status }
  }

  // SI column should not be color-coded; keep neutral gray like other metrics

  return (
    <div className="relative group overflow-hidden rounded-lg">
      {/* Subtle glow effect */}
      <div className="absolute inset-0 bg-gray-100/50 rounded-lg blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 dark:bg-white/[0.02]" />
      
      {/* Glass panel */}
      <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 group-hover:border-gray-300/80 group-hover:bg-gray-100/80 transition-all duration-300 shadow-sm dark:bg-black/20 dark:border-white/5 dark:group-hover:border-white/10 dark:group-hover:bg-black/25 dark:shadow-black/50" />
      
      <div className="relative p-5">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
          <h4 className="text-sm font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
            Atlantic Division
          </h4>
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-[30px_1fr_45px_70px_45px_50px] gap-3 px-2 pb-2 border-b border-gray-200 mb-2 dark:border-white/10">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider dark:text-gray-500">#</div>
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider dark:text-gray-500">Team</div>
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center dark:text-gray-500">GP</div>
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center dark:text-gray-500">Last 5</div>
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center dark:text-gray-500">SI</div>
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-right dark:text-gray-500">PTS</div>
        </div>

        <div className="space-y-1">
          {atlanticTeams.slice(0, 8).map((team, index) => {
            const teamAbbrev = team.teamAbbrev?.default || ''
            const isMTL = teamAbbrev === 'MTL'
            const gp = team.gamesPlayed || 0
            const points = team.points || 0
            const lastFive = getLastFive(teamAbbrev)
            const strainIndex = getStrainIndex(teamAbbrev)
            const wins = lastFive.split('').filter(r => r === 'W').length
            const losses = lastFive.split('').filter(r => r === 'L').length
            
            return (
              <motion.div
                key={teamAbbrev}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 + index * 0.03 }}
                className="grid grid-cols-[30px_1fr_45px_70px_45px_50px] gap-3 items-center p-2 rounded border transition-all duration-200 border-gray-100 hover:bg-gray-50 hover:backdrop-blur-sm hover:border-gray-200 dark:border-white/5 dark:hover:bg-white/[0.03] dark:hover:border-white/10"
              >
                {/* Rank */}
                <div className="text-[11px] font-military-display text-gray-600 dark:text-gray-500">
                  {index + 1}
                </div>

                {/* Team */}
                <TeamLink teamId={teamAbbrev || 'MTL'}>
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
                      <img
                        src={getTeamLogo(teamAbbrev)}
                        alt={teamAbbrev}
                        className={teamAbbrev === 'MTL' ? 'w-5 h-5' : 'w-5 h-5 grayscale opacity-60'}
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                      />
                    </div>
                    <span className={`text-sm font-military-display ${isMTL ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'}`}>
                      {teamAbbrev}
                    </span>
                  </div>
                </TeamLink>

                {/* GP */}
                <div className="text-xs font-military-display text-gray-600 text-center tabular-nums dark:text-gray-400">
                  {gp}
                </div>

                {/* Last 5 */}
                <div className="text-xs font-military-display text-gray-600 text-center tabular-nums dark:text-gray-400">
                  {wins}-{losses}
                </div>

                {/* Strain Index (neutral color) */}
                <div className={`text-xs font-military-display text-gray-600 text-center tabular-nums dark:text-gray-400`}>
                  {strainIndex.value}
                </div>

                {/* Points */}
                <div className={`text-base font-military-display ${isMTL ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'} text-right tabular-nums`}>
                  {points}
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-white/5">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center dark:text-gray-500">
            SI: Strain Index (Travel + Workload)
          </div>
        </div>
      </div>
    </div>
  )
}
