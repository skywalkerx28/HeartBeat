'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline'
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
}

interface DivisionWatchProps {
  standings: StandingsTeam[]
  isLoading?: boolean
}

export function DivisionWatch({ standings, isLoading }: DivisionWatchProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            LOADING DIVISION STANDINGS...
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

  return (
    <div className="relative group overflow-hidden rounded-lg">
      {/* Red glow accent matching calendar cards */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-gray-100 to-white backdrop-blur-md
                   border transition-all duration-300 rounded-lg
                   border-red-600/30 shadow-md shadow-red-600/15
                   group-hover:border-red-600/80 group-hover:shadow-xl group-hover:shadow-red-600/40
                   dark:from-white/5 dark:to-transparent dark:border-red-600/20 dark:shadow-red-600/10
                   dark:group-hover:border-red-600/60 dark:group-hover:shadow-red-600/30" />
      {/* Subtle scanlines */}
      <div className="pointer-events-none absolute inset-0 opacity-5 dark:opacity-10">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-gray-900/10 to-transparent animate-pulse dark:via-white/10" />
      </div>
      {/* Corner accents */}
      <div className="pointer-events-none absolute top-2 left-2 w-2 h-2 border-t border-l border-gray-300/40 rounded-sm dark:border-white/20" />
      <div className="pointer-events-none absolute top-2 right-2 w-2 h-2 border-t border-r border-gray-300/40 rounded-sm dark:border-white/20" />
      <div className="pointer-events-none absolute bottom-2 left-2 w-2 h-2 border-b border-l border-gray-300/40 rounded-sm dark:border-white/20" />
      <div className="pointer-events-none absolute bottom-2 right-2 w-2 h-2 border-b border-r border-gray-300/40 rounded-sm dark:border-white/20" />
      
      <div className="relative p-6">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
          <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
            Atlantic Division
          </h4>
        </div>

        <div className="space-y-2">
          {atlanticTeams.slice(0, 8).map((team, index) => {
            const teamAbbrev = team.teamAbbrev?.default || ''
            const isMTL = teamAbbrev === 'MTL'
            const teamName = team.teamName?.default || teamAbbrev
            const record = `${team.wins || 0}-${team.losses || 0}-${team.otLosses || 0}`
            const points = team.points || 0
            const gd = team.goalDifferential || 0
            
            return (
              <motion.div
                key={teamAbbrev}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 + index * 0.05 }}
                className={`relative group/item overflow-hidden
                  flex items-center justify-between p-3 rounded border
                  ${isMTL 
                    ? 'bg-red-600/25 border-red-600/50 dark:bg-red-600/20 dark:border-red-600/40' 
                    : 'bg-gray-100 border-gray-200 dark:bg-white/5 dark:border-white/10'}
                  hover:bg-gray-50 transition-all duration-300 dark:hover:bg-white/10`}
              >
                {/* Left neon accent on hover */}
                <div className="pointer-events-none absolute left-0 top-0 h-full w-0.5 bg-gradient-to-b from-red-600/0 via-red-600/50 to-red-600/0 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" />
                {/* Soft inner border on hover */}
                <div className="pointer-events-none absolute inset-0 rounded border border-red-500/20 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" />
                <div className="flex items-center space-x-3">
                  <div className={`
                    flex items-center justify-center w-8 h-8 rounded bg-gray-50 border
                    ${isMTL ? 'border-red-600/60 dark:border-red-600/50' : 'border-gray-200 dark:border-white/20'} overflow-hidden
                    dark:bg-white/5
                  `}>
                    <img
                      src={getTeamLogo(teamAbbrev)}
                      alt={teamAbbrev}
                      className={
                        `w-7 h-7 object-contain ` +
                        (teamAbbrev === 'MTL' 
                          ? '' 
                          : teamAbbrev === 'TBL' 
                            ? 'grayscale opacity-280'
                            : 'grayscale opacity-280')
                      }
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                    />
                    {/* Fallback abbrev if logo fails */}
                    <span className="sr-only">{teamAbbrev}</span>
                  </div>
                  
                  <div>
                    <div className={`text-sm font-military-display ${isMTL ? 'text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                      {teamAbbrev}
                    </div>
                    <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">
                      {record}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">PTS</div>
                    <div className={`text-sm font-military-display tracking-wide ${isMTL ? 'text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                      {points}
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">DIFF</div>
                    <div className={`text-sm font-military-display ${
                      gd > 0 ? 'text-green-400' : gd < 0 ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {gd > 0 ? '+' : ''}{gd}
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
