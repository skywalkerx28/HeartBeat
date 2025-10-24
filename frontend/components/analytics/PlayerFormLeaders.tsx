'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, MinusIcon } from '@heroicons/react/24/outline'
import { PlayerLink } from '../navigation/PlayerLink'

interface PlayerFormData {
  player_name: string
  pfi_score: number
  trend: 'up' | 'down' | 'stable'
  games_analyzed: number
  total_toi_minutes: number
  breakdown: {
    ev_points_per60: number
    ixg_per60: number
    shot_assists_per60: number
    entries_per60: number
    xgf_pct: number
  }
}

interface PlayerFormLeadersProps {
  players: PlayerFormData[]
  isLoading?: boolean
}

export function PlayerFormLeaders({ players, isLoading }: PlayerFormLeadersProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            CALCULATING PLAYER FORM INDEX...
          </div>
        </div>
      </div>
    )
  }

  if (!players || players.length === 0) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            NO PLAYER DATA AVAILABLE
          </div>
        </div>
      </div>
    )
  }

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return <ArrowTrendingUpIcon className="w-3 h-3 text-green-400" />
    if (trend === 'down') return <ArrowTrendingDownIcon className="w-3 h-3 text-red-400" />
    return <MinusIcon className="w-3 h-3 text-gray-500" />
  }

  const getPFIColor = (score: number) => {
    if (score >= 70) return 'text-green-400'
    if (score >= 55) return 'text-white'
    if (score >= 45) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="space-y-3">
      {players.slice(0, 5).map((player, index) => (
        <motion.div
          key={player.player_name}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 + index * 0.05 }}
          className="relative group overflow-hidden rounded-lg"
        >
          <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 group-hover:border-gray-300/80 shadow-sm group-hover:shadow transition-all duration-300 dark:bg-black/40 dark:border-white/10 dark:group-hover:border-white/30" />
          
          <div className="relative p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-6 h-6 rounded bg-gray-100 border border-gray-200 dark:bg-white/5 dark:border-white/10">
                  <span className="text-xs font-military-display text-gray-900 dark:text-white">{index + 1}</span>
                </div>
                <div>
                  <PlayerLink playerId={player.player_name} className="text-sm font-military-display text-gray-900 dark:text-white">
                    {player.player_name}
                  </PlayerLink>
                  <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">
                    {player.games_analyzed}G • {Math.round(player.total_toi_minutes)}m TOI
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                {getTrendIcon(player.trend)}
                <div className={`text-xl font-military-display ${getPFIColor(player.pfi_score)}`}>
                  {player.pfi_score}
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-5 gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-white/5">
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">EVP/60</div>
                <div className="text-xs font-military-display text-gray-900 dark:text-white">
                  {player.breakdown.ev_points_per60.toFixed(2)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">ixG/60</div>
                <div className="text-xs font-military-display text-gray-900 dark:text-white">
                  {player.breakdown.ixg_per60.toFixed(2)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">SA/60</div>
                <div className="text-xs font-military-display text-gray-900 dark:text-white">
                  {player.breakdown.shot_assists_per60.toFixed(2)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">ENT/60</div>
                <div className="text-xs font-military-display text-gray-900 dark:text-white">
                  {player.breakdown.entries_per60.toFixed(2)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">xGF%</div>
                <div className="text-xs font-military-display text-gray-900 dark:text-white">
                  {player.breakdown.xgf_pct.toFixed(1)}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

