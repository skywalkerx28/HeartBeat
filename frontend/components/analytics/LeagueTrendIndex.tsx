'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, MinusIcon } from '@heroicons/react/24/outline'
import { TeamLink } from '../navigation/TeamLink'

interface TeamTrend {
  teamAbbrev: string
  teamName: string
  trendScore: number
  change: number
  direction: 'up' | 'down' | 'stable'
  playoffProb: number
}

interface LeagueTrendIndexProps {
  teams?: TeamTrend[]
  isLoading?: boolean
}

export function LeagueTrendIndex({ teams = [], isLoading }: LeagueTrendIndexProps) {
  const mockTeams: TeamTrend[] = teams.length > 0 ? teams : [
    { teamAbbrev: 'BOS', teamName: 'Boston', trendScore: 94.2, change: 2.3, direction: 'up', playoffProb: 98 },
    { teamAbbrev: 'TOR', teamName: 'Toronto', trendScore: 91.8, change: 1.7, direction: 'up', playoffProb: 96 },
    { teamAbbrev: 'FLA', teamName: 'Florida', trendScore: 89.5, change: -0.8, direction: 'down', playoffProb: 94 },
    { teamAbbrev: 'TBL', teamName: 'Tampa Bay', trendScore: 87.3, change: 3.1, direction: 'up', playoffProb: 91 },
    { teamAbbrev: 'MTL', teamName: 'Montreal', trendScore: 68.4, change: 5.2, direction: 'up', playoffProb: 42 },
    { teamAbbrev: 'OTT', teamName: 'Ottawa', trendScore: 65.1, change: -2.4, direction: 'down', playoffProb: 38 },
    { teamAbbrev: 'DET', teamName: 'Detroit', trendScore: 62.8, change: 0.3, direction: 'stable', playoffProb: 35 },
    { teamAbbrev: 'BUF', teamName: 'Buffalo', trendScore: 58.9, change: -1.9, direction: 'down', playoffProb: 28 }
  ]

  const getTrendIcon = (direction: string) => {
    // Subtle accent colors matching TrendingPlayers
    switch (direction) {
      case 'up':
        return <ArrowTrendingUpIcon className="w-3 h-3 text-blue-800" />
      case 'down':
        return <ArrowTrendingDownIcon className="w-3 h-3 text-red-600" />
      default:
        return <MinusIcon className="w-3 h-3 text-gray-500" />
    }
  }

  const getTeamLogo = (abbrev: string) => {
    return `https://assets.nhle.com/logos/nhl/svg/${abbrev}_light.svg`
  }

  if (isLoading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6 text-center">
          <div className="text-xs font-military-display text-gray-400">
            CALCULATING LEAGUE INDEX...
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative group overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10 group-hover:border-white/20 transition-colors duration-300" />
      
      <div className="relative p-5">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
            League Trend Index
          </h4>
        </div>

        <div className="space-y-2">
          {mockTeams.map((team, index) => {
            return (
              <motion.div
                key={team.teamAbbrev}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 + index * 0.03 }}
                className="flex items-center justify-between p-2 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
              >
                <TeamLink teamId={team.teamAbbrev}>
                  <div className="flex items-center space-x-2 flex-1">
                    <div className="w-6 h-6 flex items-center justify-center">
                      <img
                        src={getTeamLogo(team.teamAbbrev)}
                        alt={team.teamAbbrev}
                        className="w-5 h-5 grayscale opacity-60"
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                      />
                    </div>
                    <span className="text-xs font-military-display text-white">
                      {team.teamAbbrev}
                    </span>
                  </div>
                </TeamLink>

                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-1">
                    {getTrendIcon(team.direction)}
                    <span className={`text-xs font-military-display ${team.direction === 'up' ? 'text-blue-800' : team.direction === 'down' ? 'text-red-600' : 'text-gray-500'}`}>
                      {team.change > 0 ? '+' : ''}{team.change.toFixed(1)}
                    </span>
                  </div>
                  
                  <div className="text-right min-w-[48px]">
                    <span className="text-xs font-military-display text-white">
                      {team.playoffProb}%
                    </span>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider text-center">
            Playoff Probability Based on Current Form
          </div>
        </div>
      </div>
    </div>
  )
}
