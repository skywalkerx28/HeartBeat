'use client'

import { motion } from 'framer-motion'
import { PlayerProfile } from '../../lib/profileApi'
import { TeamLink } from '../navigation/TeamLink'

interface PlayerProfileHeaderProps {
  player: PlayerProfile
}

export function PlayerProfileHeader({ player }: PlayerProfileHeaderProps) {
  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="space-y-4"
    >
      {/* Player Identity - Ticker Style */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-4">
            <div className="space-y-2">
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-widest">
                PLAYER ID
              </div>
              <div className="text-2xl font-mono text-white tracking-wider tabular-nums leading-none">
                {player.playerId}
              </div>
              <h1 className="text-3xl font-military-display text-white uppercase tracking-wider leading-none">
                {player.lastName}
              </h1>
              <div className="text-sm font-military-display text-gray-400 leading-snug">
                {player.firstName} {player.lastName}
              </div>
            </div>

            <div className="mt-4 space-y-2 text-sm font-military-display">
              <div className="flex justify-between">
                <span className="text-gray-500">Position:</span>
                <span className="text-white">{player.position === 'L' ? 'LW' : player.position === 'R' ? 'RW' : player.position}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Number:</span>
                <span className="text-white">#{player.jerseyNumber}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Team:</span>
                <TeamLink teamId={player.teamId} className="text-white">
                  {player.teamFullName}
                </TeamLink>
              </div>
            </div>
        </div>
      </div>

      {/* Season Stats */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-4">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              2025-26 Stats
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                GP
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {player.seasonStats.gamesPlayed}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                  Goals
                </div>
                <div className="text-xl font-military-display text-white tabular-nums">
                  {player.seasonStats.goals}
                </div>
              </div>
              <div>
                <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                  Assists
                </div>
                <div className="text-xl font-military-display text-white tabular-nums">
                  {player.seasonStats.assists}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-white/10">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Points
              </span>
              <span className="text-lg font-military-display text-white tabular-nums">
                {player.seasonStats.points}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                +/-
              </span>
              <span className={`text-base font-military-display tabular-nums ${
                player.seasonStats.plusMinus > 0 ? 'text-green-400' : 
                player.seasonStats.plusMinus < 0 ? 'text-red-400' : 'text-white'
              }`}>
                {player.seasonStats.plusMinus > 0 ? '+' : ''}{player.seasonStats.plusMinus}
              </span>
            </div>

            <div className="pt-3 border-t border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  Shots
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {player.seasonStats.shots}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  Sh%
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {player.seasonStats.shootingPct.toFixed(1)}%
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                  TOI/GP
                </span>
                <span className="text-sm font-military-display text-white tabular-nums">
                  {player.seasonStats.timeOnIce}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Career Totals (moved from right column) */}
      {player.careerStats && (
        <div className="relative overflow-hidden rounded-lg">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
          <div className="relative p-4">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
              <h3 className="text-xs font-military-display text-white uppercase tracking-widest">Career Totals</h3>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">GP</div>
                <div className="text-lg font-military-display text-white tabular-nums">{player.careerStats.gamesPlayed}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Points</div>
                <div className="text-lg font-military-display text-white tabular-nums">{player.careerStats.points}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Goals</div>
                <div className="text-sm font-military-display text-white tabular-nums">{player.careerStats.goals}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Assists</div>
                <div className="text-sm font-military-display text-white tabular-nums">{player.careerStats.assists}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">+/-</div>
                <div className={`text-sm font-military-display tabular-nums ${
                  player.careerStats.plusMinus > 0 ? 'text-green-400' : player.careerStats.plusMinus < 0 ? 'text-red-400' : 'text-white'
                }`}>
                  {player.careerStats.plusMinus > 0 ? '+' : ''}{player.careerStats.plusMinus}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">GWG</div>
                <div className="text-sm font-military-display text-white tabular-nums">{player.careerStats.gameWinningGoals}</div>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-white/10 grid grid-cols-2 gap-3">
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">PP Goals</div>
                <div className="text-xs font-military-display text-white tabular-nums">{player.careerStats.powerPlayGoals}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">SH Goals</div>
                <div className="text-xs font-military-display text-white tabular-nums">{player.careerStats.shortHandedGoals}</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Shooting %</div>
                <div className="text-xs font-military-display text-white tabular-nums">{(player.careerStats.shootingPct || 0).toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">OT Goals</div>
                <div className="text-xs font-military-display text-white tabular-nums">{player.careerStats.otGoals}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Contract Info */}
      {player.contract && (
        <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-4">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Contract
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                AAV
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {formatCurrency(player.contract.aav)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Years Left
              </span>
              <span className="text-base font-military-display text-white tabular-nums">
                {player.contract.yearsRemaining}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                Status
              </span>
              <span className="text-sm font-military-display text-white uppercase tracking-wider">
                {player.contract.status}
              </span>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Live Data Feed removed */}
    </motion.div>
  )
}
