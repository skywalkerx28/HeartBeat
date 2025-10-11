'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { FireIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline'
import { PlayerLink } from '../navigation/PlayerLink'
import { TeamLink } from '../navigation/TeamLink'

interface TrendingPlayer {
  playerId: string
  playerName: string
  team: string
  category: 'hot' | 'cold' | 'emerging'
  stat: string
  value: number
  change: string
  gameStreak?: string
}

interface TrendingPlayersProps {
  players?: TrendingPlayer[]
  isLoading?: boolean
}

export function TrendingPlayers({ players = [], isLoading }: TrendingPlayersProps) {
  const mockPlayers: TrendingPlayer[] = players.length > 0 ? players : [
    {
      playerId: '1',
      playerName: 'C. Caufield',
      team: 'MTL',
      category: 'hot',
      stat: 'Goals',
      value: 28,
      change: '+9 in L10',
      gameStreak: '12 GP'
    },
    {
      playerId: '2',
      playerName: 'N. Suzuki',
      team: 'MTL',
      category: 'hot',
      stat: 'Points',
      value: 62,
      change: '+14 in L10',
      gameStreak: '8 GP'
    },
    {
      playerId: '3',
      playerName: 'S. Montembeault',
      team: 'MTL',
      category: 'hot',
      stat: 'SV%',
      value: 0.923,
      change: '+.015',
      gameStreak: '15 GS'
    },
    {
      playerId: '4',
      playerName: 'K. Dach',
      team: 'MTL',
      category: 'emerging',
      stat: 'Assists',
      value: 31,
      change: '+7 in L10',
      gameStreak: '5 GP'
    },
    {
      playerId: '5',
      playerName: 'J. Slafkovsky',
      team: 'MTL',
      category: 'hot',
      stat: 'Points',
      value: 48,
      change: '+11 in L10',
      gameStreak: '6 GP'
    }
  ]

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'hot':
        return <FireIcon className="w-3 h-3 text-red-600" />
      case 'emerging':
        return <ArrowTrendingUpIcon className="w-3 h-3 text-blue-800" />
      default:
        return <FireIcon className="w-3 h-3 text-gray-500" />
    }
  }

  if (isLoading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6 text-center">
          <div className="text-xs font-military-display text-gray-400">
            ANALYZING PLAYER TRENDS...
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
            Trending Players
          </h4>
        </div>

        <div className="space-y-2.5">
          {mockPlayers.map((player, index) => (
            <motion.div
              key={player.playerId}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.05 + index * 0.03 }}
              className="relative p-3 rounded border transition-all duration-200 bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    {getCategoryIcon(player.category)}
                    <PlayerLink playerId={player.playerId} className="text-sm font-military-display text-white">
                      {player.playerName}
                    </PlayerLink>
                  </div>
                  <div className="mt-1 text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                    <TeamLink teamId={player.team}>{player.team}</TeamLink> → {player.stat}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-military-display text-white">
                    {typeof player.value === 'number' && player.value < 1 
                      ? player.value.toFixed(3) 
                      : player.value}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="font-military-display text-blue-800">
                  {player.change}
                </span>
                {player.gameStreak && (
                  <span className="font-military-display text-gray-500">
                    {player.gameStreak}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider text-center">
            Last 10 Games Performance
          </div>
        </div>
      </div>
    </div>
  )
}

