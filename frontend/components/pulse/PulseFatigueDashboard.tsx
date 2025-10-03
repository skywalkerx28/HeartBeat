'use client'

import { ClockIcon, BoltIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

interface Player {
  id: string
  name: string
  position: string
  number: number
  restGameTime: number
  restRealTime: number
  intermissionFlag: number
  shiftsThisPeriod: number
  shiftsTotalGame: number
  toiPast20min: number
  toiCumulativeGame: number
  ewmaShiftLength: number
  ewmaRestLength: number
  isWellRested: boolean
  isOverused: boolean
  isHeavyToi: boolean
}

interface Roster {
  onIce: {
    forwards: Player[]
    defense: Player[]
    goalie: Player
  }
  bench: {
    forwards: Player[]
    defense: Player[]
  }
}

interface PulseFatigueDashboardProps {
  roster: Roster
}

export function PulseFatigueDashboard({ roster }: PulseFatigueDashboardProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getRestStatusColor = (isWellRested: boolean, isOverused: boolean) => {
    if (isOverused) return 'text-red-400'
    if (isWellRested) return 'text-green-400'
    return 'text-yellow-400'
  }

  const getRestStatusIcon = (isWellRested: boolean, isOverused: boolean) => {
    if (isOverused) return <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />
    if (isWellRested) return <CheckCircleIcon className="w-4 h-4 text-green-400" />
    return <ClockIcon className="w-4 h-4 text-yellow-400" />
  }

  const PlayerFatigueCard = ({ player, isOnIce = false }: { player: Player, isOnIce?: boolean }) => (
    <div
      className={`
        p-3 rounded border
        ${isOnIce
          ? 'border-red-600/50 bg-red-600/10 shadow-lg shadow-red-600/20'
          : 'border-gray-700/50 bg-gray-800/30'
        }
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <div className={`
            w-6 h-6 rounded-full flex items-center justify-center text-xs font-military-display font-bold
            ${isOnIce ? 'bg-red-600 text-white' : 'bg-gray-700 text-white'}
          `}>
            {player.number}
          </div>
          <div>
            <div className="text-sm font-military-chat text-white">
              {player.name}
            </div>
            <div className="text-xs font-military-display text-gray-500">
              {player.position}
            </div>
          </div>
        </div>
        {getRestStatusIcon(player.isWellRested, player.isOverused)}
      </div>

      {/* Fatigue Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-gray-500">REST (GAME)</div>
          <div className={`font-military-display ${getRestStatusColor(player.isWellRested, player.isOverused)}`}>
            {formatTime(player.restGameTime || 90.0)}
          </div>
        </div>
        <div>
          <div className="text-gray-500">REST (REAL)</div>
          <div className={`font-military-display ${getRestStatusColor(player.isWellRested, player.isOverused)}`}>
            {formatTime(player.restRealTime || 110.0)}
          </div>
        </div>
        <div>
            <div className="text-gray-500">SHIFTS P{player.shiftsThisPeriod || 0}</div>
            <div className="font-military-display text-gray-300">
              G{player.shiftsTotalGame || 0}
            </div>
        </div>
        <div>
          <div className="text-gray-500">TOI 20M</div>
          <div className="font-military-display text-gray-300">
            {((player.toiPast20min || 0) / 60).toFixed(1)}M
          </div>
        </div>
      </div>

      {/* EWMA Patterns */}
      <div className="mt-2 pt-2 border-t border-gray-700">
        <div className="text-xs text-gray-500 mb-1">EWMA PATTERNS</div>
        <div className="grid grid-cols-2 gap-1 text-xs">
          <div className="text-gray-400">
            SHIFT: {(player.ewmaShiftLength || 45.0).toFixed(1)}s
          </div>
          <div className="text-gray-400">
            REST: {(player.ewmaRestLength || 90.0).toFixed(1)}s
          </div>
        </div>
      </div>

      {/* Status Indicators */}
      <div className="mt-2 flex items-center space-x-2">
        {player.isHeavyToi && (
          <span className="px-1.5 py-0.5 text-xs bg-red-600/20 text-red-400 rounded">
            HEAVY TOI
          </span>
        )}
        {player.intermissionFlag === 1 && (
          <span className="px-1.5 py-0.5 text-xs bg-blue-600/20 text-blue-400 rounded">
            POST-INT
          </span>
        )}
      </div>
    </div>
  )

  // Combine all players for fatigue overview
  const allPlayers = [
    ...roster.onIce.forwards,
    ...roster.onIce.defense,
    roster.onIce.goalie,
    ...roster.bench.forwards,
    ...roster.bench.defense
  ]

  const wellRestedCount = allPlayers.filter(p => p.isWellRested).length
  const overusedCount = allPlayers.filter(p => p.isOverused).length
  const heavyToiCount = allPlayers.filter(p => p.isHeavyToi).length

  return (
    <div
      className="bg-gray-900/80 border border-gray-700 rounded-lg p-4 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center space-x-3 mb-4">
        <BoltIcon className="w-5 h-5 text-red-400" />
        <div>
          <h3 className="text-lg font-military-display text-white">
            FATIGUE MATRIX
          </h3>
          <p className="text-xs font-military-display text-gray-400">
            REAL-TIME PLAYER WORKLOAD
          </p>
        </div>
      </div>

      {/* Fatigue Overview */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-green-600/10 border border-green-600/30 rounded p-2 text-center">
          <div className="text-lg font-military-display text-green-400">{wellRestedCount}</div>
          <div className="text-xs font-military-display text-gray-500">WELL RESTED</div>
        </div>
        <div className="bg-red-600/10 border border-red-600/30 rounded p-2 text-center">
          <div className="text-lg font-military-display text-red-400">{overusedCount}</div>
          <div className="text-xs font-military-display text-gray-500">OVERUSED</div>
        </div>
        <div className="bg-orange-600/10 border border-orange-600/30 rounded p-2 text-center">
          <div className="text-lg font-military-display text-orange-400">{heavyToiCount}</div>
          <div className="text-xs font-military-display text-gray-500">HEAVY TOI</div>
        </div>
      </div>

      {/* On-Ice Players */}
      <div className="mb-4">
        <div className="text-sm font-military-display text-red-400 mb-2 tracking-wider">
          ON ICE
        </div>
        <div className="grid grid-cols-1 gap-2">
          {[...roster.onIce.forwards, ...roster.onIce.defense].map((player) => (
            <PlayerFatigueCard key={player.id} player={player} isOnIce={true} />
          ))}
        </div>
      </div>

      {/* Bench Players */}
      <div>
        <div className="text-sm font-military-display text-gray-400 mb-2 tracking-wider">
          BENCH
        </div>
        <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto">
          {[...roster.bench.forwards, ...roster.bench.defense].map((player) => (
            <PlayerFatigueCard key={player.id} player={player} />
          ))}
        </div>
      </div>
    </div>
  )
}
