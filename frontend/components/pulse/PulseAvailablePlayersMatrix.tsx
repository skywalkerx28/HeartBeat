'use client'

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

interface PulseAvailablePlayersMatrixProps {
  roster: Roster
  isHome: boolean
}

export function PulseAvailablePlayersMatrix({ roster, isHome }: PulseAvailablePlayersMatrixProps) {
  // Create full roster including on-ice and bench
  const allForwards = [...roster.onIce.forwards, ...roster.bench.forwards]
  const allDefense = [...roster.onIce.defense, ...roster.bench.defense]
  
  // Sort by position for consistent ordering
  const sortForwards = (a: Player, b: Player) => {
    const order = { 'LW': 0, 'C': 1, 'RW': 2 }
    return (order[a.position as keyof typeof order] || 3) - (order[b.position as keyof typeof order] || 3)
  }
  
  const sortedForwards = allForwards.sort(sortForwards)
  const sortedDefense = allDefense
  
  // Check if player is currently on ice
  const isOnIce = (playerId: string) => {
    return roster.onIce.forwards.some(p => p.id === playerId) || 
           roster.onIce.defense.some(p => p.id === playerId)
  }
  
  // Create 12 slots for forwards (4 rows x 3 cols)
  const forwardSlots = Array(12).fill(null).map((_, index) => sortedForwards[index] || null)
  
  // Create 6 slots for defense (3 rows x 2 cols)
  const defenseSlots = Array(6).fill(null).map((_, index) => sortedDefense[index] || null)
  
  const PlayerSlot = ({ player }: { player: Player | null }) => {
    if (!player) {
      // Empty slot
      return (
        <div className={`
          w-12 h-12 rounded-full flex items-center justify-center
          border border-white/10
          bg-black/20
          opacity-20
        `} />
      )
    }
    
    const onIce = isOnIce(player.id)
    
    if (onIce) {
      // On-ice player - empty pill slot
      return (
        <div className={`
          w-12 h-12 rounded-full flex items-center justify-center
          border-2 ${isHome ? 'border-red-600/50' : 'border-gray-400/50'}
          bg-transparent
          opacity-40
          relative
        `}
        title={`${player.name} - ON ICE`}
        >
          <div className="absolute inset-0 rounded-full border border-dashed border-white/20 animate-pulse" />
        </div>
      )
    }
    
    // Available player on bench
    return (
      <div
        className={`
          w-12 h-12 rounded-full flex items-center justify-center
          border ${isHome ? 'border-red-600/30 text-red-400' : 'border-gray-400/30 text-gray-400'}
          bg-black/60 backdrop-blur-sm
          text-sm font-military-display font-bold
          hover:scale-110 hover:border-opacity-100 transition-all cursor-pointer
          ${player.isWellRested ? 'shadow-lg shadow-white/20' : ''}
          ${player.isOverused ? 'opacity-50' : 'opacity-90'}
        `}
        title={player.name}
      >
        {player.number}
      </div>
    )
  }
  
  return (
    <div className="flex flex-col space-y-6">
      {/* Forwards Matrix - 4 rows x 3 cols */}
      <div>
        <div className="grid grid-cols-3 gap-4">
          {forwardSlots.map((player, index) => (
            <PlayerSlot key={`forward-${index}`} player={player} />
          ))}
        </div>
      </div>
      
      {/* Defense Matrix - 3 rows x 2 cols */}
      <div>
        <div className="grid grid-cols-2 gap-4 justify-items-center">
          {defenseSlots.map((player, index) => (
            <PlayerSlot key={`defense-${index}`} player={player} />
          ))}
        </div>
      </div>
    </div>
  )
}
