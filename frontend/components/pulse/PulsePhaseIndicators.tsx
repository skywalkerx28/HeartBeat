'use client'

import { motion } from 'framer-motion'
import { FireIcon, ClockIcon, ShieldExclamationIcon, BoltIcon } from '@heroicons/react/24/outline'

interface GameData {
  scoreDifferential: number
  hasLastChange: boolean
  isPeriodLate: boolean
  isGameLate: boolean
  isLatePk: boolean
  isLatePp: boolean
  isCloseAndLate: boolean
  lastStoppageType: string
  lastStoppageDuration: number
  lastStoppageTime: string
  decisionRole: number
}

interface PulsePhaseIndicatorsProps {
  gameData: GameData
}

export function PulsePhaseIndicators({ gameData }: PulsePhaseIndicatorsProps) {
  const indicators = [
    {
      id: 'lastChange',
      label: 'LAST CHANGE',
      value: gameData.hasLastChange ? 'MTL ADVANTAGE' : 'OPP ADVANTAGE',
      color: gameData.hasLastChange ? 'text-red-400 bg-red-600/10 border-red-600/30' : 'text-gray-400 bg-gray-600/10 border-gray-600/30',
      icon: ShieldExclamationIcon,
      active: true
    },
    {
      id: 'periodPhase',
      label: 'PERIOD PHASE',
      value: gameData.isPeriodLate ? 'LATE PERIOD' : 'EARLY PERIOD',
      color: gameData.isPeriodLate ? 'text-red-400 bg-red-600/10 border-red-600/30' : 'text-gray-400 bg-gray-600/10 border-gray-600/30',
      icon: ClockIcon,
      active: gameData.isPeriodLate
    },
    {
      id: 'gamePhase',
      label: 'GAME PHASE',
      value: gameData.isGameLate ? 'LATE GAME' : 'EARLY GAME',
      color: gameData.isGameLate ? 'text-red-400 bg-red-600/10 border-red-600/30' : 'text-gray-400 bg-gray-600/10 border-gray-600/30',
      icon: FireIcon,
      active: gameData.isGameLate
    },
    {
      id: 'specialTeams',
      label: 'SPECIAL TEAMS',
      value: gameData.isLatePk ? 'LATE PK' : gameData.isLatePp ? 'LATE PP' : 'EVEN STRENGTH',
      color: gameData.isLatePk || gameData.isLatePp ? 'text-red-400 bg-red-600/10 border-red-600/30' : 'text-gray-400 bg-gray-600/10 border-gray-600/30',
      icon: BoltIcon,
      active: gameData.isLatePk || gameData.isLatePp
    }
  ]

  const getScoreContext = () => {
    const diff = Math.abs(gameData.scoreDifferential)
    if (diff === 0) return { text: 'TIED GAME', color: 'text-gray-400' }
    if (diff === 1) return { text: 'CLOSE GAME', color: 'text-red-400' }
    if (diff >= 2) return { text: 'DECISIVE LEAD', color: gameData.scoreDifferential > 0 ? 'text-gray-400' : 'text-red-400' }
    return { text: 'SCORE DIFFERENTIAL', color: 'text-gray-400' }
  }

  const scoreContext = getScoreContext()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-gray-950/95 via-gray-900/90 to-gray-950/95 border border-gray-700/30 rounded-xl p-6 backdrop-blur-2xl h-full shadow-2xl shadow-black/50 relative overflow-hidden"
    >
      {/* Futuristic Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-red-500/3 via-transparent to-blue-500/3"></div>
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-red-400/20 to-transparent"></div>
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/20 to-transparent"></div>
      <div className="absolute top-0 bottom-0 left-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>
      <div className="absolute top-0 bottom-0 right-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>
      {/* Header */}
      <div className="relative flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <FireIcon className="w-5 h-5 text-red-400" />
          <h3 className="text-lg font-military-display text-white">
            PHASE INDICATORS
          </h3>
        </div>

        {/* Score Context */}
        <div className="text-right">
          <div className={`text-sm font-military-display ${scoreContext.color}`}>
            {scoreContext.text}
          </div>
          <div className="text-xs font-military-display text-gray-500">
            {gameData.scoreDifferential > 0 ? '+' : ''}{gameData.scoreDifferential} GOALS
          </div>
        </div>
      </div>

      {/* Indicators Grid */}
      <div className="relative grid grid-cols-2 md:grid-cols-4 gap-4">
        {indicators.map((indicator, index) => {
          const IconComponent = indicator.icon

          return (
            <motion.div
              key={indicator.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className={`
                bg-gradient-to-br from-gray-900/70 to-gray-950/70 border border-gray-700/30 rounded-lg p-4 backdrop-blur-md transition-all
                ${indicator.color}
                ${indicator.active ? 'shadow-lg' : 'opacity-60'}
              `}
              whileHover={{ scale: 1.02 }}
            >
              <div className="flex items-center space-x-2 mb-3">
                <IconComponent className={`w-5 h-5 ${indicator.active ? 'animate-pulse' : ''}`} />
                <div className="text-xs font-military-display text-gray-200 tracking-wider">
                  {indicator.label}
                </div>
              </div>

              <div className="text-sm font-military-display text-white drop-shadow-sm">
                {indicator.value}
              </div>

              {indicator.active && (
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="mt-1 w-full h-0.5 bg-current rounded-full"
                />
              )}
            </motion.div>
          )
        })}
      </div>

      {/* Stoppage Context */}
      <div className="relative mt-6 pt-6 border-t border-gray-700/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <span className="text-sm font-military-display text-gray-400">
              LAST STOPPAGE
            </span>
          </div>
          <div className="text-right">
            <div className="text-sm font-military-display text-white">
              {gameData.lastStoppageType?.toUpperCase() || 'UNKNOWN'}
            </div>
            <div className="text-xs font-military-display text-gray-500">
              {gameData.lastStoppageDuration?.toFixed(1) || '0.0'}s • {gameData.lastStoppageTime || 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Decision Context */}
      <div className="mt-3 flex items-center justify-between text-xs font-military-display">
        <span className="text-gray-500">DECISION CONTEXT</span>
        <span className={`font-bold ${gameData.decisionRole === 1 ? 'text-red-400' : 'text-gray-400'}`}>
          {gameData.decisionRole === 1 ? 'TACTICAL ADVANTAGE' : 'TACTICAL DISADVANTAGE'}
        </span>
      </div>

      {/* High Leverage Alert */}
      {gameData.isCloseAndLate && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mt-4 p-3 bg-red-600/20 border border-red-600/50 rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
            <div>
              <div className="text-sm font-military-display text-red-400">
                HIGH-LEVERAGE SITUATION
              </div>
              <div className="text-xs font-military-display text-gray-400">
                Close game in late stages - maximum decision impact
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
