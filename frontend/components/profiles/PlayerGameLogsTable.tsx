'use client'

import { motion } from 'framer-motion'
import { GameLog } from '../../lib/profileApi'
import { TeamLink } from '../navigation/TeamLink'

interface PlayerGameLogsTableProps {
  gameLogs: GameLog[]
}

export function PlayerGameLogsTable({ gameLogs }: PlayerGameLogsTableProps) {
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
            Game Log - 2025-26 Season
          </h3>
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-[1fr_1.5fr_0.8fr_0.5fr_0.5fr_0.5fr_0.5fr_0.5fr_0.6fr_0.6fr_0.6fr_0.8fr_0.8fr] gap-2 px-3 pb-3 border-b border-white/10 mb-2">
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Date</div>
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Opponent</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Result</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">G</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">A</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">PTS</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">+/-</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">SOG</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Hits</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Blk</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">PIM</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Shifts</div>
          <div className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider">TOI</div>
        </div>

        {/* Table Rows */}
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {gameLogs.map((game, idx) => {
            const resultColor = game.result === 'W' ? 'text-green-400' : 
                               game.result === 'OTL' ? 'text-amber-400' : 'text-red-400'

            return (
            <motion.div
              key={game.gameId}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03 }}
              className="grid grid-cols-[1fr_1.5fr_0.8fr_0.5fr_0.5fr_0.5fr_0.5fr_0.5fr_0.6fr_0.6fr_0.6fr_0.8fr_0.8fr] gap-2 items-center p-3 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
            >
                <div className="text-[10px] font-military-display text-gray-500 tabular-nums">
                  {new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>

                <div className="flex flex-col">
                  <div className="flex items-center space-x-2">
                    <span className="text-[9px] font-military-display text-gray-500 uppercase">
                      {game.homeAway === 'away' ? '@' : 'vs'}
                    </span>
                    <TeamLink teamId={game.opponent} className="text-xs font-military-display text-white">
                      {game.opponent}
                    </TeamLink>
                  </div>
                  <div className="text-[9px] font-military-display text-gray-600 mt-0.5">
                    {game.opponentName}
                  </div>
                </div>

                <div className={`text-[11px] font-military-display ${resultColor} text-center font-bold`}>
                  {game.result}
                </div>

                <div className="text-[11px] font-military-display text-white text-center tabular-nums">
                  {game.goals}
                </div>

                <div className="text-[11px] font-military-display text-white text-center tabular-nums">
                  {game.assists}
                </div>

                <div className="text-[11px] font-military-display text-blue-400 text-center tabular-nums font-bold">
                  {game.points}
                </div>

                <div className={`text-[11px] font-military-display text-center tabular-nums ${
                  game.plusMinus > 0 ? 'text-green-400' : 
                  game.plusMinus < 0 ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {game.plusMinus > 0 ? '+' : ''}{game.plusMinus}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.shots}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.hits}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.blockedShots}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.pim}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.shifts}
                </div>

                <div className="text-[11px] font-military-display text-gray-300 text-center tabular-nums">
                  {game.timeOnIce}
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
            Note: Full parquet-sourced game logs with 50+ metrics coming soon
          </div>
        </div>
      </div>
    </motion.div>
  )
}

