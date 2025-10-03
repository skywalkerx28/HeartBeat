'use client'

import { UserGroupIcon } from '@heroicons/react/24/outline'

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

interface PulseOnIceFormationProps {
  homeRoster: Roster
  awayRoster: Roster
  homeTeam: string
  awayTeam: string
}

export function PulseOnIceFormation({
  homeRoster,
  awayRoster,
  homeTeam,
  awayTeam
}: PulseOnIceFormationProps) {
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

  const getRestStatusColor = (isWellRested?: boolean, isOverused?: boolean) => {
    if (isOverused) return 'text-red-400'
    if (isWellRested) return 'text-gray-300'
    return 'text-gray-500'
  }

  const PlayerCard = ({ player, isHome }: { player: Player, isHome: boolean }) => (
    <div className={`
      bg-gray-800/60 border border-gray-700/50 rounded-lg p-1.5 min-w-[100px] max-w-[110px] text-center
      ${isHome ? 'bg-red-900/20 border-red-700/30' : 'bg-gray-900/20'}
      hover:bg-gray-700/40 transition-colors
    `}>
      <div className={`
        w-6 h-6 rounded-full flex items-center justify-center text-xs font-military-display font-bold mx-auto mb-1
        ${isHome ? 'bg-red-600 text-white border border-red-600' : 'bg-gray-700 text-white border border-gray-600'}
      `}>
        {player.number}
      </div>
      <div className="text-xs font-military-chat text-white truncate mb-0.5">
        {player.name.split(' ')[1] || player.name}
      </div>
      <div className={`text-xs font-military-display ${getPositionColor(player.position)} mb-0.5`}>
        {player.position}
      </div>
      <div className={`text-xs font-military-display ${getRestStatusColor(player.isWellRested, player.isOverused)} text-[10px]`}>
        {(player.restGameTime || 0).toFixed(1)}s
      </div>
    </div>
  )

  const FormationSection = ({
    title,
    roster,
    isHome
  }: {
    title: string,
    roster: Roster,
    isHome: boolean
  }) => {
    // Sort forwards by position (LW, C, RW)
    const sortedForwards = [...roster.onIce.forwards].sort((a, b) => {
      const order = { 'LW': 0, 'C': 1, 'RW': 2 }
      return (order[a.position as keyof typeof order] || 3) - (order[b.position as keyof typeof order] || 3)
    })

    return (
      <div className="flex-1">
        <h3 className="text-center text-sm font-military-display text-gray-300 mb-4 tracking-wider">
          {title}
        </h3>

        {/* Hockey Rink Formation */}
        <div className="relative bg-gradient-to-b from-gray-950 to-gray-900 rounded-lg p-4 border border-gray-700/30 min-h-[450px]">

          {/* Center Line */}
          <div className="absolute top-1/2 left-0 right-0 h-px bg-gray-600/50"></div>

          {/* Blue Lines */}
          <div className="absolute top-8 left-0 right-0 h-px bg-gray-500/30"></div>
          <div className="absolute bottom-8 left-0 right-0 h-px bg-gray-500/30"></div>

          {/* Net Areas - Bottom Layer */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 w-16 h-8 border-2 border-red-500/50 rounded-full bg-red-900/10"></div>

          {/* Goalie - On Net */}
          <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2">
            <PlayerCard player={roster.onIce.goalie} isHome={isHome} />
          </div>

          {/* Forwards - Behind Defense */}
          <div className="absolute top-24 left-1/2 transform -translate-x-1/2 flex space-x-8">
            {sortedForwards.map((player) => (
              <PlayerCard key={player.id} player={player} isHome={isHome} />
            ))}
          </div>

          {/* Defense - Top Layer at Center */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex space-x-12">
            {roster.onIce.defense.slice(0, 2).map((player) => (
              <PlayerCard key={player.id} player={player} isHome={isHome} />
            ))}
          </div>

          {/* Formation Labels */}
          <div className="absolute top-1/2 left-4 transform -translate-y-1/2 text-xs text-gray-500 font-military-display">
            DEFENSE
          </div>
          <div className="absolute top-28 left-4 text-xs text-gray-500 font-military-display">
            FORWARDS
          </div>
          <div className="absolute bottom-16 left-4 text-xs text-gray-500 font-military-display">
            GOALTENDER
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-gray-950/95 via-gray-900/90 to-gray-950/95 border border-gray-700/30 rounded-xl backdrop-blur-2xl shadow-2xl shadow-black/50 relative overflow-hidden">
      {/* Futuristic Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-red-500/3 via-transparent to-blue-500/3"></div>
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-red-400/20 to-transparent"></div>
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/20 to-transparent"></div>
      <div className="absolute top-0 bottom-0 left-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>
      <div className="absolute top-0 bottom-0 right-0 w-px bg-gradient-to-b from-transparent via-gray-500/15 to-transparent"></div>
      {/* Header */}
      <div className="relative p-6 border-b border-gray-700/30">
        <div className="flex items-center justify-center space-x-3">
          <UserGroupIcon className="w-5 h-5 text-gray-400" />
          <div className="text-center">
            <h3 className="text-lg font-military-display text-white tracking-wider">
              ON-ICE FORMATION
            </h3>
            <p className="text-xs font-military-display text-gray-400">
              CURRENT PLAYERS ON ICE
            </p>
          </div>
        </div>
      </div>

      {/* Formation Display */}
      <div className="relative p-6">
        <div className="flex justify-center space-x-8">
              <FormationSection
                title={homeTeam}
                roster={homeRoster}
                isHome={true}
              />
              <FormationSection
                title={awayTeam}
                roster={awayRoster}
                isHome={false}
              />
            </div>
          </div>

      {/* Footer */}
      <div className="relative px-6 py-3 bg-gray-800/30 border-t border-gray-700/30">
        <div className="flex items-center justify-center space-x-6 text-xs font-military-display text-gray-500">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>Overused</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
            <span>Well Rested</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <span>Normal</span>
          </div>
        </div>
      </div>
    </div>
  )
}
