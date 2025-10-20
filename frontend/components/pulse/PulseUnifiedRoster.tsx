'use client'

import { PlayerLink } from '../navigation/PlayerLink'

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
    if (isWellRested) return 'text-white'
    return 'text-gray-400'
  }

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'G': return 'text-red-400'
      case 'D': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  // Check if player is currently on ice
  const isPlayerOnIce = (playerId: string): boolean => {
    const onIceIds = [
      ...roster.onIce.forwards.map(p => p.id),
      ...roster.onIce.defense.map(p => p.id),
      roster.onIce.goalie.id
    ]
    return onIceIds.includes(playerId)
  }

  const PlayerRow = ({ player }: { player: Player }) => {
    const onIce = isPlayerOnIce(player.id)
    
    return (
      <div className={`grid gap-2 py-3 px-4 border-b border-white/5 transition-colors text-xs font-military-display ${
        onIce 
          ? 'bg-red-600/10 border-l-2 border-red-600 hover:bg-red-600/15' 
          : 'hover:bg-white/[0.02]'
      }`}
        style={{ gridTemplateColumns: '0.5fr 2fr 0.5fr 1fr 1fr 0.7fr 1.2fr 0.8fr' }}
      >
      {/* Number */}
      <div className={onIce ? 'text-red-400 font-bold' : 'text-gray-500'}>
        {player.number}
      </div>

      {/* Name */}
      <div className={`truncate ${onIce ? 'text-white font-bold' : 'text-white'}`}>
        <PlayerLink playerId={player.id}>
          {player.name.split(' ').slice(-1)[0]}
        </PlayerLink>
      </div>

      {/* Position */}
      <div className={`${getPositionColor(player.position)}`}>
        {player.position}
      </div>

      {/* Game Rest (GR) */}
      <div className={`text-center ${getRestStatusColor(player.isWellRested ?? false, player.isOverused ?? false)}`}>
        {formatTime(player.restGameTime ?? 90.0)}
      </div>

      {/* Real Rest (RR) */}
      <div className="text-center text-gray-400">
        {formatTime(player.restRealTime ?? 120.0)}
      </div>

      {/* Shifts */}
      <div className="text-center text-gray-300">
        {player.shiftsThisPeriod ?? 0}
      </div>

      {/* TOI */}
      <div className="text-center text-gray-300">
        {formatTime(player.toiCumulativeGame ?? 0)}
      </div>

      {/* Status Indicators */}
      <div className="flex items-center justify-center space-x-1">
        {player.isOverused && (
          <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" title="Overused" />
        )}
        {player.isWellRested && (
          <div className="w-1.5 h-1.5 bg-white rounded-full" title="Well Rested" />
        )}
        {player.isHeavyToi && (
          <div className="w-1.5 h-1.5 bg-yellow-500 rounded-full" title="Heavy TOI" />
        )}
      </div>
    </div>
    )
  }

  // Merge on-ice and bench players for complete roster
  const allForwards = [...roster.onIce.forwards, ...roster.bench.forwards]
  const allDefense = [...roster.onIce.defense, ...roster.bench.defense]

  return (
    <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg shadow-xl shadow-white/5">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-military-display text-white tracking-wider uppercase">
            {title}
          </h3>
          <span className="text-xs font-military-display text-gray-400">
            {subtitle}
          </span>
        </div>
      </div>

      {/* Table Header */}
      <div className="grid gap-2 px-4 py-3 bg-white/[0.02] border-b border-white/5 text-[10px] font-military-display text-gray-500 uppercase tracking-wider"
        style={{ gridTemplateColumns: '0.5fr 2fr 0.5fr 1fr 1fr 0.7fr 1.2fr 0.8fr' }}
      >
        <div>#</div>
        <div>Player</div>
        <div>Pos</div>
        <div className="text-center">GR</div>
        <div className="text-center">RR</div>
        <div className="text-center">Shifts</div>
        <div className="text-center">TOI</div>
        <div className="text-center">Status</div>
      </div>

      {/* Forwards */}
      {allForwards.length > 0 && (
        <>
          <div className="px-4 py-3 bg-white/[0.02] border-b border-white/5">
            <span className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
              Forwards ({allForwards.length})
            </span>
          </div>
          {allForwards.map((player) => (
            <PlayerRow key={player.id} player={player} />
          ))}
        </>
      )}

      {/* Defense */}
      {allDefense.length > 0 && (
        <>
          <div className="px-4 py-3 bg-white/[0.02] border-b border-white/5 mt-4">
            <span className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
              Defense ({allDefense.length})
            </span>
          </div>
          {allDefense.map((player) => (
            <PlayerRow key={player.id} player={player} />
          ))}
        </>
      )}
    </div>
  )
}