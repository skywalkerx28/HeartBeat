'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { TeamMatchupHistory as MatchupData } from '../../lib/profileApi'
import { TeamLink } from '../navigation/TeamLink'

interface TeamMatchupHistoryProps {
  matchups: MatchupData[]
}

export function TeamMatchupHistory({ matchups }: TeamMatchupHistoryProps) {
  const [sortBy, setSortBy] = useState<'opponent' | 'gp' | 'wins' | 'pts'>('opponent')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortDir('asc')
    }
  }

  const sortedMatchups = [...matchups].sort((a, b) => {
    let aVal: number | string = 0
    let bVal: number | string = 0

    switch (sortBy) {
      case 'opponent':
        aVal = a.opponent
        bVal = b.opponent
        break
      case 'gp':
        aVal = a.gamesPlayed
        bVal = b.gamesPlayed
        break
      case 'wins':
        aVal = a.wins
        bVal = b.wins
        break
      case 'pts':
        aVal = (a.wins * 2) + a.otLosses
        bVal = (b.wins * 2) + b.otLosses
        break
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }

    return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-lg"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            Head-to-Head Matchups
          </h3>
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-[1.5fr_0.8fr_1fr_1fr_1fr_1fr_1.2fr] gap-3 px-3 pb-3 border-b border-white/10 mb-2">
          <button
            onClick={() => handleSort('opponent')}
            className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider hover:text-white transition-colors"
          >
            Opponent {sortBy === 'opponent' && (sortDir === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('gp')}
            className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider hover:text-white transition-colors"
          >
            GP {sortBy === 'gp' && (sortDir === 'asc' ? '↑' : '↓')}
          </button>
          <button
            onClick={() => handleSort('wins')}
            className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider hover:text-white transition-colors"
          >
            W {sortBy === 'wins' && (sortDir === 'asc' ? '↑' : '↓')}
          </button>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">L</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">OTL</div>
          <button
            onClick={() => handleSort('pts')}
            className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider hover:text-white transition-colors"
          >
            PTS {sortBy === 'pts' && (sortDir === 'asc' ? '↑' : '↓')}
          </button>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">GF/GA</div>
        </div>

        {/* Table Rows */}
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {sortedMatchups.map((matchup, idx) => {
            const points = (matchup.wins * 2) + matchup.otLosses
            const winPct = matchup.gamesPlayed > 0 
              ? ((matchup.wins / matchup.gamesPlayed) * 100).toFixed(0) 
              : '0'

            return (
              <motion.div
                key={matchup.opponent}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.02 }}
                className="grid grid-cols-[1.5fr_0.8fr_1fr_1fr_1fr_1fr_1.2fr] gap-3 items-center p-3 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
              >
                <TeamLink teamId={matchup.opponent} className="text-xs font-military-display text-white">
                  {matchup.opponent}
                </TeamLink>

                <div className="text-[11px] font-military-display text-gray-400 text-center tabular-nums">
                  {matchup.gamesPlayed}
                </div>

                <div className="text-[11px] font-military-display text-green-400 text-center tabular-nums">
                  {matchup.wins}
                </div>

                <div className="text-[11px] font-military-display text-red-400 text-center tabular-nums">
                  {matchup.losses}
                </div>

                <div className="text-[11px] font-military-display text-amber-400 text-center tabular-nums">
                  {matchup.otLosses}
                </div>

                <div className="text-[11px] font-military-display text-blue-400 text-center tabular-nums">
                  {points}
                </div>

                <div className="text-[11px] font-military-display text-white text-center tabular-nums">
                  {matchup.goalsFor}/{matchup.goalsAgainst}
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
            2025-26 Season Head-to-Head Records
          </div>
        </div>
      </div>
    </motion.div>
  )
}

