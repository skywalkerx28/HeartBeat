'use client'

import { motion } from 'framer-motion'

interface GameData {
  gameId: string
  homeTeam: string
  awayTeam: string
  homeScore: number
  awayScore: number
  period: number
  periodTime: number
  gameTime: number
  status: string
  zone: string
  strength: string
  lastEvent: string
  lastEventTime: string
}

interface PulseGameDashboardProps {
  gameData: GameData
}

export function PulseGameDashboard({ gameData }: PulseGameDashboardProps) {
  const formatTime = (minutes: number) => {
    const mins = Math.floor(minutes)
    const secs = Math.floor((minutes - mins) * 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getZoneColor = (zone: string) => {
    switch (zone.toLowerCase()) {
      case 'oz': return 'text-red-400'
      case 'dz': return 'text-gray-400'
      case 'nz': return 'text-gray-300'
      default: return 'text-gray-400'
    }
  }

  const getStrengthColor = (strength: string) => {
    if (strength.includes('5v4') || strength.includes('powerPlay')) return 'text-red-400'
    if (strength.includes('4v5') || strength.includes('penaltyKill')) return 'text-gray-400'
    return 'text-white'
  }

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
      {/* Game Header */}
      <div className="relative text-center mb-6">
        <motion.div
          animate={{
            scale: [1, 1.02, 1],
            boxShadow: [
              '0 0 0 0 rgba(239, 68, 68, 0.4)',
              '0 0 0 4px rgba(239, 68, 68, 0)',
              '0 0 0 0 rgba(239, 68, 68, 0.4)'
            ]
          }}
          transition={{ duration: 2, repeat: Infinity }}
          className="inline-flex items-center space-x-2 bg-gradient-to-r from-red-600/20 to-red-500/20 border border-red-400/60 rounded-lg px-4 py-2 mb-6 backdrop-blur-md shadow-lg"
        >
          <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
          <span className="text-sm font-military-display text-red-400 tracking-wider">
            {gameData.status}
          </span>
          <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
        </motion.div>

        <h2 className="text-xl font-military-display text-white mb-2 drop-shadow-lg">
          {gameData.awayTeam} @ {gameData.homeTeam}
        </h2>
        <p className="text-xs font-military-display text-gray-300 tracking-wider">
          GAME ID: {gameData.gameId}
        </p>
      </div>

      {/* Score Display */}
      <div className="relative flex items-center justify-center space-x-8 mb-6">
        {/* Away Team */}
        <div className="text-center">
          <motion.div
            className="text-5xl font-military-display font-bold text-gray-200 mb-2 drop-shadow-lg"
            animate={{ textShadow: [
              '0 0 10px rgba(156, 163, 175, 0.5)',
              '0 0 20px rgba(156, 163, 175, 0.8)',
              '0 0 10px rgba(156, 163, 175, 0.5)'
            ]}}
            transition={{ duration: 3, repeat: Infinity }}
          >
            {gameData.awayScore}
          </motion.div>
          <div className="text-sm font-military-display text-gray-400 tracking-wider uppercase">
            {gameData.awayTeam}
          </div>
        </div>

        {/* VS Separator */}
        <div className="flex flex-col items-center space-y-2">
          <motion.div
            className="text-2xl font-military-display text-gray-400 tracking-wider"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            VS
          </motion.div>
          <div className="w-12 h-px bg-gradient-to-r from-transparent via-gray-500 to-transparent"></div>
        </div>

        {/* Home Team */}
        <div className="text-center">
          <motion.div
            className="text-5xl font-military-display font-bold text-red-300 mb-2 drop-shadow-lg"
            animate={{ textShadow: [
              '0 0 10px rgba(248, 113, 113, 0.5)',
              '0 0 20px rgba(248, 113, 113, 0.8)',
              '0 0 10px rgba(248, 113, 113, 0.5)'
            ]}}
            transition={{ duration: 3, repeat: Infinity }}
          >
            {gameData.homeScore}
          </motion.div>
          <div className="text-sm font-military-display text-red-300 tracking-wider uppercase">
            {gameData.homeTeam}
          </div>
        </div>
      </div>

      {/* Game Status Grid */}
      <div className="relative grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Period & Time */}
        <motion.div
          className="bg-gradient-to-br from-gray-900/70 to-gray-950/70 border border-gray-700/30 rounded-lg p-4 text-center backdrop-blur-md"
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.2 }}
        >
          <div className="text-2xl font-military-display text-white drop-shadow-sm">
            {formatTime(gameData.periodTime)}
          </div>
          <div className="text-xs text-gray-400 tracking-wider mt-2">PERIOD {gameData.period}</div>
        </motion.div>

        {/* Game Zone */}
        <motion.div
          className="bg-gradient-to-br from-gray-900/70 to-gray-950/70 border border-gray-700/30 rounded-lg p-4 text-center backdrop-blur-md"
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.2 }}
        >
          <div className={`text-2xl font-military-display drop-shadow-sm ${getZoneColor(gameData.zone)}`}>
            {gameData.zone.toUpperCase()}
          </div>
          <div className="text-xs text-gray-400 tracking-wider mt-2">ZONE</div>
        </motion.div>

        {/* Strength State */}
        <motion.div
          className="bg-gradient-to-br from-gray-900/70 to-gray-950/70 border border-gray-700/30 rounded-lg p-4 text-center backdrop-blur-md"
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.2 }}
        >
          <div className={`text-xl font-military-display drop-shadow-sm ${getStrengthColor(gameData.strength)}`}>
            {gameData.strength}
          </div>
          <div className="text-xs text-gray-400 tracking-wider mt-2">STRENGTH</div>
        </motion.div>

        {/* Last Event */}
        <motion.div
          className="bg-gradient-to-br from-gray-900/70 to-gray-950/70 border border-gray-700/30 rounded-lg p-4 text-center backdrop-blur-md"
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.2 }}
        >
          <div className="text-sm font-military-display text-white drop-shadow-sm leading-tight">
            {gameData.lastEvent}
          </div>
          <div className="text-xs text-gray-400 tracking-wider mt-2">
            {gameData.lastEventTime}
          </div>
        </motion.div>
      </div>

      {/* Progress Bar */}
      <div className="mt-3">
        <div className="flex justify-between text-xs font-military-display text-gray-500 mb-1">
          <span>PERIOD {gameData.period}</span>
          <span>{formatTime(gameData.gameTime)}</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2">
          <motion.div
            className="bg-red-600 h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${(gameData.gameTime / 60) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    </motion.div>
  )
}
