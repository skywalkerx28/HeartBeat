'use client'

import { motion } from 'framer-motion'
import { TeamProfile } from '../../lib/profileApi'

interface TeamProfileHeaderProps {
  team: TeamProfile
}

export function TeamProfileHeader({ team }: TeamProfileHeaderProps) {
  const totalGames = team.record.wins + team.record.losses + team.record.otLosses
  const pointsPercentage = totalGames > 0 ? (team.record.points / (totalGames * 2) * 100).toFixed(1) : '0.0'

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="space-y-4"
    >
      {/* Team Logo and Identity */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-4">
            <div className="flex items-center space-x-4 mb-6">
              <img 
                src={team.logoUrl} 
                alt={team.name}
                className="w-16 h-16 object-contain"
              />
              <div>
                <div className="text-xs font-military-display text-gray-500 uppercase tracking-widest mb-1">
                  TEAM ID
                </div>
                <div className="text-2xl font-military-display text-white tracking-wider">
                  {team.abbreviation}
                </div>
                <div className="text-xs font-military-display text-gray-500 mt-1">
                  #{team.id}
                </div>
              </div>
            </div>
            
            <h1 className="text-xl font-military-display text-white uppercase tracking-wider mb-3">
              {team.city} {team.name}
            </h1>
            
            <div className="space-y-2 text-sm font-military-display">
              <div className="flex justify-between">
                <span className="text-gray-500">Division:</span>
                <span className="text-white">{team.division}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Conference:</span>
                <span className="text-white">{team.conference}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Games Played:</span>
                <span className="text-white">{team.record.gamesPlayed}</span>
              </div>
            </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-4">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Season Stats
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Record
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {team.record.wins}-{team.record.losses}-{team.record.otLosses}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Points
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {team.record.points}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Points %
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {pointsPercentage}%
              </span>
            </div>

            <div className="pt-3 border-t border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  GF/GA
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {team.stats.goalsFor}/{team.stats.goalsAgainst}
                </span>
              </div>

              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  PP%
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {team.stats.ppPercent.toFixed(1)}%
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  PK%
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {team.stats.pkPercent.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Indicator */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-3">
          <div className="flex items-center space-x-2">
            <div className="relative flex-shrink-0">
              <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
              <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
            </div>
            <span className="text-xs font-military-display text-gray-400 uppercase tracking-wider">
              Live Data Feed
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
