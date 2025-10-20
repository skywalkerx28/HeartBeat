'use client'

import { motion } from 'framer-motion'
import { ClockIcon, ArrowRightIcon, UserGroupIcon } from '@heroicons/react/24/outline'

interface PlayerChange {
  id: string
  period: number
  time: string
  type: 'forward_line' | 'defense_pairing'
  changeType: 'line_change' | 'power_play' | 'penalty_kill' | 'injury' | 'rest'
  oldLine: string
  newLine: string
  playersOut: string[]
  playersIn: string[]
  reason?: string
}

interface PulsePlayerChangeLogProps {
  changeHistory: PlayerChange[]
}

export function PulsePlayerChangeLog({ changeHistory }: PulsePlayerChangeLogProps) {
  const getChangeTypeColor = (type: string) => {
    switch (type) {
      case 'line_change': return 'text-gray-300'
      case 'power_play': return 'text-red-400'
      case 'penalty_kill': return 'text-blue-400'
      case 'injury': return 'text-yellow-400'
      case 'rest': return 'text-green-400'
      default: return 'text-gray-400'
    }
  }

  const getChangeTypeIcon = (type: string) => {
    switch (type) {
      case 'line_change': return '↗'
      case 'power_play': return '⚡'
      case 'penalty_kill': return '🛡️'
      case 'injury': return '🚑'
      case 'rest': return '⏸'
      default: return '↗'
    }
  }

  const formatPlayerList = (players: string[]) => {
    return players.map(player => player.split(' ').pop()).join(', ')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-gray-950/95 via-gray-900/90 to-gray-950/95 border border-gray-700/30 rounded-xl backdrop-blur-2xl shadow-2xl shadow-black/50 relative overflow-hidden h-full"
    >
      {/* Futuristic Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-red-500/3 via-transparent to-blue-500/3"></div>
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-red-400/20 to-transparent"></div>
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/20 to-transparent"></div>
      <div className="absolute top-0 bottom-0 left-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>
      <div className="absolute top-0 bottom-0 right-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>

      {/* Header */}
      <div className="relative p-6 border-b border-gray-700/30">
        <div className="flex items-center space-x-3">
          <UserGroupIcon className="w-6 h-6 text-red-400" />
          <div>
            <h3 className="text-xl font-military-display text-white tracking-wider">
              PLAYER CHANGE LOG
            </h3>
            <p className="text-sm font-military-display text-gray-400">
              LINE CHANGES & SUBSTITUTIONS
            </p>
          </div>
        </div>
      </div>

      {/* Change History */}
      <div className="relative p-6">
        <div className="space-y-4 max-h-[600px] overflow-y-auto">
          {changeHistory.map((change, index) => (
            <motion.div
              key={change.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-gray-900/40 border border-gray-700/30 rounded-lg p-4 hover:bg-gray-800/40 transition-colors"
            >
              {/* Header Row */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    <ClockIcon className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-military-display text-gray-300">
                      P{change.period} • {change.time}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{getChangeTypeIcon(change.changeType)}</span>
                    <span className={`text-sm font-military-display uppercase tracking-wider ${getChangeTypeColor(change.changeType)}`}>
                      {change.changeType.replace('_', ' ')}
                    </span>
                  </div>
                </div>
                <div className={`text-xs font-military-display px-2 py-1 rounded border ${
                  change.type === 'forward_line'
                    ? 'text-red-400 bg-red-600/10 border-red-600/30'
                    : 'text-blue-400 bg-blue-600/10 border-blue-600/30'
                }`}>
                  {change.type === 'forward_line' ? 'FORWARDS' : 'DEFENSE'}
                </div>
              </div>

              {/* Change Details */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-military-display text-gray-400 mb-1">OUT</div>
                    <div className="text-sm font-military-display text-white">
                      {change.oldLine}
                    </div>
                    <div className="text-xs font-military-display text-gray-500">
                      {formatPlayerList(change.playersOut)}
                    </div>
                  </div>

                  <ArrowRightIcon className="w-5 h-5 text-gray-500 mx-4" />

                  <div className="flex-1 text-right">
                    <div className="text-sm font-military-display text-gray-400 mb-1">IN</div>
                    <div className="text-sm font-military-display text-white">
                      {change.newLine}
                    </div>
                    <div className="text-xs font-military-display text-gray-500">
                      {formatPlayerList(change.playersIn)}
                    </div>
                  </div>
                </div>

                {change.reason && (
                  <div className="mt-3 pt-3 border-t border-gray-700/30">
                    <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                      REASON: {change.reason}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {changeHistory.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-500 text-sm font-military-display">
                NO CHANGES RECORDED YET
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="relative px-6 py-3 bg-gray-800/30 border-t border-gray-700/30">
        <div className="flex items-center justify-center space-x-6 text-xs font-military-display text-gray-500">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>Forward Changes</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span>Defense Changes</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <span>Special Teams</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
