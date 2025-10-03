'use client'

import { UserGroupIcon, ShieldCheckIcon, ClockIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

interface Player {
  id: string
  name: string
  position: string
  number: number
  restGameTime?: number
  restRealTime?: number
  intermissionFlag?: number
  shiftsThisPeriod?: number
  shiftsTotalGame?: number
  toiPast20min?: number
  toiCumulativeGame?: number
  ewmaShiftLength?: number
  ewmaRestLength?: number
  isWellRested?: boolean
  isOverused?: boolean
  isHeavyToi?: boolean
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

interface PulseUnifiedRosterProps {
  title: string
  subtitle: string
  roster: Roster
  isHome: boolean
}

export function PulseUnifiedRoster({ title, subtitle, roster, isHome }: PulseUnifiedRosterProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getRestStatusColor = (isWellRested: boolean, isOverused: boolean) => {
    if (isOverused) return 'text-red-400'
    if (isWellRested) return 'text-gray-300'
    return 'text-gray-500'
  }

  const getRestStatusIcon = (isWellRested: boolean, isOverused: boolean) => {
    if (isOverused) return <ExclamationTriangleIcon className="w-3 h-3 text-red-400" />
    if (isWellRested) return <CheckCircleIcon className="w-3 h-3 text-gray-300" />
    return <ClockIcon className="w-3 h-3 text-gray-500" />
  }

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'G': return 'text-red-400'
      case 'D': return 'text-gray-400'
      case 'C': return 'text-gray-300'
      case 'LW': return 'text-gray-300'
      case 'RW': return 'text-gray-300'
      default: return 'text-gray-400'
    }
  }

  const PlayerRow = ({ player }: { player: Player }) => (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-10 gap-1 md:gap-2 p-2 md:p-3 border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors bg-gray-900/20">
      {/* Number */}
      <div className="col-span-1 md:col-span-1 lg:col-span-1 xl:col-span-1 flex items-center">
        <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-military-display font-bold bg-gray-700 text-white border border-gray-600">
          {player.number}
        </div>
      </div>

      {/* Name & Position */}
      <div className="col-span-2 md:col-span-2 lg:col-span-3 xl:col-span-3">
        <div className="text-xs md:text-sm font-military-chat text-white truncate">
          {player.name}
        </div>
        <div className={`text-xs font-military-display ${getPositionColor(player.position)}`}>
          {player.position}
        </div>
      </div>

      {/* Rest Status */}
      <div className="col-span-1 md:col-span-1 lg:col-span-2 xl:col-span-2 text-center hidden sm:block">
        <div className={`text-xs font-military-display ${getRestStatusColor(player.isWellRested ?? false, player.isOverused ?? false)}`}>
          {formatTime(player.restGameTime ?? 90.0)}
        </div>
      </div>

      {/* Availability Status */}
      <div className="col-span-1 md:col-span-1 lg:col-span-2 xl:col-span-2 text-center hidden md:block">
        <div className="flex items-center justify-center space-x-1">
          {getRestStatusIcon(player.isWellRested ?? false, player.isOverused ?? false)}
          <span className={`text-xs font-military-display ${getRestStatusColor(player.isWellRested ?? false, player.isOverused ?? false)}`}>
            {player.isWellRested ? 'READY' : player.isOverused ? 'TIRED' : 'RESTED'}
          </span>
        </div>
      </div>

      {/* Games Played */}
      <div className="col-span-1 md:col-span-1 lg:col-span-1 xl:col-span-1 text-center hidden lg:block">
        <div className="text-xs font-military-display text-gray-300">
          GP: {player.shiftsTotalGame ?? 0}
        </div>
      </div>

      {/* Status Indicators */}
      <div className="col-span-0 md:col-span-1 lg:col-span-1 xl:col-span-1 flex flex-col items-center space-y-1 hidden md:flex">
        {player.isHeavyToi && (
          <span className="px-1 py-0.5 text-xs bg-red-600/20 text-red-400 rounded border border-red-600/30">
            HT
          </span>
        )}
        {(player.intermissionFlag ?? 0) === 1 && (
          <span className="px-1 py-0.5 text-xs bg-gray-600/20 text-gray-400 rounded border border-gray-600/30">
            INT
          </span>
        )}
      </div>
    </div>
  )

  const SectionHeader = ({ title, count, icon: Icon }: { title: string, count: number, icon: any }) => (
    <div className="flex items-center justify-between p-2 md:p-3 bg-gray-800/50 border-b border-gray-700/50">
      <div className="flex items-center space-x-2 md:space-x-3">
        <Icon className="w-3 h-3 md:w-4 md:h-4 text-gray-400" />
        <span className="text-xs md:text-sm font-military-display text-gray-300 tracking-wider">
          {title}
        </span>
      </div>
      <div className="text-xs font-military-display text-gray-500 bg-gray-700/50 px-1.5 md:px-2 py-0.5 md:py-1 rounded">
        {count}
      </div>
    </div>
  )

  return (
    <div className="bg-gray-900/80 border border-gray-700 rounded-lg backdrop-blur-sm overflow-hidden w-full min-h-fit">
      {/* Header */}
      <div className="p-2 md:p-4 border-b border-gray-700/50">
        <div className="text-center">
          <h3 className="text-lg font-military-display text-white mb-1 tracking-wider">
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs font-military-display text-gray-400 tracking-wider">
              {subtitle}
            </p>
          )}
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-10 gap-1 md:gap-2 mt-4 p-2 bg-gray-800/30 rounded border border-gray-700/30">
          <div className="col-span-1 md:col-span-1 lg:col-span-1 xl:col-span-1 text-xs font-military-display text-gray-500 tracking-wider">#</div>
          <div className="col-span-2 md:col-span-2 lg:col-span-3 xl:col-span-3 text-xs font-military-display text-gray-500 tracking-wider">PLAYER</div>
          <div className="col-span-1 md:col-span-1 lg:col-span-2 xl:col-span-2 text-xs font-military-display text-gray-500 tracking-wider text-center hidden sm:block">REST</div>
          <div className="col-span-1 md:col-span-1 lg:col-span-2 xl:col-span-2 text-xs font-military-display text-gray-500 tracking-wider text-center hidden md:block">STATUS</div>
          <div className="col-span-1 md:col-span-1 lg:col-span-1 xl:col-span-1 text-xs font-military-display text-gray-500 tracking-wider text-center hidden lg:block">GAMES</div>
          <div className="col-span-0 md:col-span-1 lg:col-span-1 xl:col-span-1 text-xs font-military-display text-gray-500 tracking-wider text-center hidden md:block">FLAGS</div>
        </div>
      </div>


      {/* Bench Forwards */}
      {roster.bench.forwards.length > 0 && (
        <>
          <SectionHeader
            title="BENCH FORWARDS"
            count={roster.bench.forwards.length}
            icon={UserGroupIcon}
          />
          <div className="divide-y divide-gray-800/30">
            {roster.bench.forwards.map((player) => (
              <PlayerRow key={player.id} player={player} />
            ))}
          </div>
        </>
      )}

      {/* Bench Defense */}
      {roster.bench.defense.length > 0 && (
        <>
          <SectionHeader
            title="BENCH DEFENSE"
            count={roster.bench.defense.length}
            icon={ShieldCheckIcon}
          />
          <div className="divide-y divide-gray-800/30">
            {roster.bench.defense.map((player) => (
              <PlayerRow key={player.id} player={player} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
