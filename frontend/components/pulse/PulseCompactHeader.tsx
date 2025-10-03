'use client'

import { motion } from 'framer-motion'
import { ClockIcon } from '@heroicons/react/24/outline'

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

interface PulseCompactHeaderProps {
  gameData: GameData
}

export function PulseCompactHeader({ gameData }: PulseCompactHeaderProps) {
  const formatTime = (minutes: number) => {
    const mins = Math.floor(minutes)
    const secs = Math.floor((minutes - mins) * 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getZoneColor = (zone: string) => {
    switch (zone.toLowerCase()) {
      case 'oz': return 'text-red-400'
      case 'dz': return 'text-gray-400'
      case 'nz': return 'text-white'
      default: return 'text-gray-400'
    }
  }

  const getStrengthColor = (strength: string) => {
    if (strength.includes('5v4') || strength.includes('powerPlay')) return 'text-red-400'
    if (strength.includes('4v5') || strength.includes('penaltyKill')) return 'text-gray-400'
    return 'text-white'
  }

  const getScoreContext = () => {
    const diff = Math.abs(gameData.scoreDifferential)
    if (diff === 0) return { text: 'TIED', color: 'text-gray-400' }
    if (diff === 1) return { text: 'CLOSE', color: 'text-red-400' }
    if (diff >= 2) return { text: gameData.scoreDifferential > 0 ? 'LEADING' : 'TRAILING', color: gameData.scoreDifferential > 0 ? 'text-white' : 'text-red-400' }
    return { text: 'LIVE', color: 'text-gray-400' }
  }

  const scoreContext = getScoreContext()

  return (
    <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg shadow-xl shadow-white/5">
      {/* Top Row - Game Info & Score */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        {/* Left - Game Status */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
            <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
          </div>
          <div>
            <div className="text-sm font-military-display text-white tracking-wider">
              {gameData.awayTeam} @ {gameData.homeTeam}
            </div>
            <div className="text-xs font-military-display text-gray-400">
              {gameData.status} • {scoreContext.text}
            </div>
          </div>
        </div>

        {/* Center - Score */}
        <div className="flex items-center space-x-6">
          <div className="text-center">
            <div className="text-3xl font-military-display text-gray-300">
              {gameData.awayScore}
            </div>
            <div className="text-xs font-military-display text-gray-500">
              {gameData.awayTeam}
            </div>
          </div>
          <div className="text-xl font-military-display text-gray-600">-</div>
          <div className="text-center">
            <div className="text-3xl font-military-display text-white">
              {gameData.homeScore}
            </div>
            <div className="text-xs font-military-display text-gray-400">
              {gameData.homeTeam}
            </div>
          </div>
        </div>

        {/* Right - Period & Time */}
        <div className="text-right">
          <div className="text-2xl font-military-display text-white">
            {formatTime(gameData.periodTime)}
          </div>
          <div className="text-xs font-military-display text-gray-400">
            PERIOD {gameData.period}
          </div>
        </div>
      </div>

      {/* Bottom Row - Game Stats */}
      <div className="grid grid-cols-6 gap-4 px-6 py-3">
        {/* Zone */}
        <div className="text-center">
          <div className={`text-lg font-military-display ${getZoneColor(gameData.zone)}`}>
            {gameData.zone.toUpperCase()}
          </div>
          <div className="text-xs font-military-display text-gray-500">ZONE</div>
        </div>

        {/* Strength */}
        <div className="text-center">
          <div className={`text-lg font-military-display ${getStrengthColor(gameData.strength)}`}>
            {gameData.strength}
          </div>
          <div className="text-xs font-military-display text-gray-500">STRENGTH</div>
        </div>

        {/* Last Change */}
        <div className="text-center">
          <div className={`text-sm font-military-display ${gameData.hasLastChange ? 'text-white' : 'text-gray-400'}`}>
            {gameData.hasLastChange ? 'MTL' : 'OPP'}
          </div>
          <div className="text-xs font-military-display text-gray-500">LAST CHANGE</div>
        </div>

        {/* Phase */}
        <div className="text-center">
          <div className={`text-sm font-military-display ${gameData.isPeriodLate ? 'text-red-400' : 'text-gray-400'}`}>
            {gameData.isPeriodLate ? 'LATE' : 'EARLY'}
          </div>
          <div className="text-xs font-military-display text-gray-500">PERIOD</div>
        </div>

        {/* Special Teams */}
        <div className="text-center">
          <div className={`text-sm font-military-display ${gameData.isLatePk || gameData.isLatePp ? 'text-red-400' : 'text-gray-400'}`}>
            {gameData.isLatePk ? 'PK' : gameData.isLatePp ? 'PP' : 'ES'}
          </div>
          <div className="text-xs font-military-display text-gray-500">SITUATION</div>
        </div>

        {/* Last Event */}
        <div className="text-center">
          <div className="text-sm font-military-display text-white truncate">
            {gameData.lastEvent}
          </div>
          <div className="text-xs font-military-display text-gray-500">{gameData.lastEventTime}</div>
        </div>
      </div>

      {/* High Leverage Alert */}
      {gameData.isCloseAndLate && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="border-t border-red-600/30 bg-red-600/10 px-6 py-2"
        >
          <div className="flex items-center justify-center space-x-2">
            <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
            <span className="text-xs font-military-display text-red-400 tracking-wider uppercase">
              High-Leverage Situation
            </span>
          </div>
        </motion.div>
      )}
    </div>
  )
}
