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

interface PulseOnIceFormationProps {
  homeRoster: Roster
  awayRoster: Roster
  homeTeam: string
  awayTeam: string
  period?: number
  periodTime?: number
}

export function PulseOnIceFormation({
  homeRoster,
  awayRoster,
  homeTeam,
  awayTeam,
  period = 2,
  periodTime = 8.34
}: PulseOnIceFormationProps) {
  
  // Format time in MM:SS (periodTime is in minutes with decimal seconds)
  const formatTime = (minutes: number) => {
    const mins = Math.floor(minutes)
    const secs = Math.floor((minutes - mins) * 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  const PlayerNode = ({ player, isHome }: { player: Player, isHome: boolean }) => {
    const fatigueLevel = calculateFatigueLevel(player)
    const energyLevel = 100 - fatigueLevel
    
    const getEnergyColor = () => {
      if (energyLevel >= 70) return isHome ? '#ef4444' : '#9ca3af'
      if (energyLevel >= 40) return '#fbbf24'
      return '#dc2626'
    }

    return (
      <div className="relative group cursor-pointer">
        {/* Outer glow ring - static */}
        <div 
          className="absolute inset-0 rounded-full blur-lg opacity-30"
          style={{
            background: `radial-gradient(circle, ${getEnergyColor()} 0%, transparent 70%)`
          }}
        />
        
        {/* Player circle */}
        <div className="relative w-16 h-16 rounded-full border-2 bg-black/60 backdrop-blur-sm flex items-center justify-center"
          style={{ borderColor: getEnergyColor() }}
        >
          {/* Energy ring - static */}
          <svg className="absolute inset-0 w-full h-full -rotate-90">
              <circle
              cx="32"
              cy="32"
              r="30"
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="1"
                fill="none"
              />
              <circle
              cx="32"
              cy="32"
              r="30"
                stroke={getEnergyColor()}
                strokeWidth="2"
                fill="none"
              strokeDasharray={`${energyLevel * 1.88} 188`}
                strokeLinecap="round"
                style={{
                  filter: `drop-shadow(0 0 3px ${getEnergyColor()})`
                }}
              />
            </svg>
            
          {/* Player info */}
          <div className="text-center z-10">
            <div className="text-lg font-military-display text-white font-bold">
                  {player.number}
                </div>
            <div className="text-[8px] font-military-display text-gray-400">
                  {player.position}
                </div>
              </div>
            </div>
            
        {/* Hover tooltip */}
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
          <div className="bg-black/90 backdrop-blur-xl border border-white/20 rounded px-3 py-2 whitespace-nowrap">
            <div className="text-xs font-military-display text-white font-bold">
              {player.name}
          </div>
            <div className="text-[10px] font-military-display text-gray-400">
              Rest: {Math.floor(player.restGameTime || 0)}s • Energy: {Math.round(energyLevel)}%
            </div>
          </div>
        </div>

        {/* Status indicators - only pulse for overused players */}
        {player.isOverused && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-600 rounded-full animate-pulse border border-black" />
        )}
      </div>
    )
  }

  const calculateFatigueLevel = (player: Player): number => {
    const restTime = player.restGameTime || 90
    const maxRestTime = 120
    const baseFatigue = Math.max(0, Math.min(100, ((maxRestTime - restTime) / maxRestTime) * 100))
    
    if (player.isOverused) return Math.min(100, baseFatigue + 20)
    if (player.isWellRested) return Math.max(0, baseFatigue - 30)
    
    return baseFatigue
  }

  // Sort forwards by position
  const sortHomeForwards = [...homeRoster.onIce.forwards].sort((a, b) => {
    const order = { 'LW': 0, 'C': 1, 'RW': 2 }
    return (order[a.position as keyof typeof order] || 3) - (order[b.position as keyof typeof order] || 3)
  })

  const sortAwayForwards = [...awayRoster.onIce.forwards].sort((a, b) => {
      const order = { 'LW': 0, 'C': 1, 'RW': 2 }
      return (order[a.position as keyof typeof order] || 3) - (order[b.position as keyof typeof order] || 3)
    })

    return (
    <div className="relative">
      {/* Single Horizontal Rink - floating directly on background */}
      <div className="relative">
        <div className="perspective-container" style={{ perspective: '1200px', perspectiveOrigin: 'center center' }}>
          <div 
            className="relative w-full aspect-[2/1] max-w-6xl mx-auto transform-3d"
            style={{ 
              transform: 'rotateX(25deg) rotateZ(0deg)',
              transformStyle: 'preserve-3d',
              transition: 'transform 0.3s ease-out'
            }}
          >
          {/* SVG Horizontal Rink Outline */}
          <svg 
            viewBox="0 0 800 400" 
            className="absolute inset-0 w-full h-full"
            style={{ 
              filter: 'drop-shadow(0 8px 16px rgba(0, 0, 0, 0.6)) drop-shadow(0 0 2px rgba(156, 163, 175, 0.3))',
              transformStyle: 'preserve-3d'
            }}
          >
            {/* Rink boards - horizontal orientation */}
            <rect 
              x="20" 
              y="80" 
              width="760" 
              height="240" 
              rx="30"
              fill="none"
              stroke="rgba(156, 163, 175, 0.3)"
              strokeWidth="1.5"
            />

            {/* Blue lines - vertical */}
            <line 
              x1="220" 
              y1="80" 
              x2="220" 
              y2="320" 
              stroke="rgba(156, 163, 175, 0.3)"
              strokeWidth="2"
            />
            <line 
              x1="580" 
              y1="80" 
              x2="580" 
              y2="320" 
              stroke="rgba(156, 163, 175, 0.3)"
              strokeWidth="2"
            />

            {/* Red center line - vertical */}
            <line 
              x1="400" 
              y1="80" 
              x2="400" 
              y2="320" 
              stroke="rgba(239, 68, 68, 0.4)"
              strokeWidth="2"
            />

            {/* Center face-off circle */}
            <circle 
              cx="400" 
              cy="200" 
              r="40" 
              fill="none"
              stroke="rgba(156, 163, 175, 0.2)"
              strokeWidth="1"
            />
            <circle 
              cx="400" 
              cy="200" 
              r="3" 
              fill="rgba(239, 68, 68, 0.6)"
            />

            {/* Goal lines */}
            <line 
              x1="60" 
              y1="80" 
              x2="60" 
              y2="320" 
              stroke="rgba(239, 68, 68, 0.3)"
              strokeWidth="1.5"
            />
            <line 
              x1="740" 
              y1="80" 
              x2="740" 
              y2="320" 
              stroke="rgba(239, 68, 68, 0.3)"
              strokeWidth="1.5"
            />

            {/* Goal creases - left (away) */}
            <path
              d="M 60 160 Q 75 200 60 240"
              fill="none"
              stroke="rgba(156, 163, 175, 0.3)"
              strokeWidth="1.5"
            />
            <rect
              x="20"
              y="185"
              width="15"
              height="30"
              fill="none"
              stroke="rgba(156, 163, 175, 0.3)"
              strokeWidth="1"
            />
            <rect
              x="20"
              y="185"
              width="15"
              height="30"
              fill="rgba(156, 163, 175, 0.05)"
            />

            {/* Goal creases - right (home) */}
            <path
              d="M 740 160 Q 725 200 740 240"
              fill="none"
              stroke="rgba(239, 68, 68, 0.3)"
              strokeWidth="1.5"
            />
            <rect
              x="765"
              y="185"
              width="15"
              height="30"
              fill="none"
              stroke="rgba(239, 68, 68, 0.3)"
              strokeWidth="1"
            />
            <rect
              x="765"
              y="185"
              width="15"
              height="30"
              fill="rgba(239, 68, 68, 0.05)"
            />

            {/* Face-off dots - left zone */}
            <circle cx="140" cy="140" r="3" fill="rgba(156, 163, 175, 0.4)" />
            <circle cx="140" cy="260" r="3" fill="rgba(156, 163, 175, 0.4)" />
            
            {/* Face-off dots - right zone */}
            <circle cx="660" cy="140" r="3" fill="rgba(239, 68, 68, 0.4)" />
            <circle cx="660" cy="260" r="3" fill="rgba(239, 68, 68, 0.4)" />

            {/* Neutral zone face-off dots */}
            <circle cx="300" cy="140" r="2" fill="rgba(156, 163, 175, 0.3)" />
            <circle cx="300" cy="260" r="2" fill="rgba(156, 163, 175, 0.3)" />
            <circle cx="500" cy="140" r="2" fill="rgba(156, 163, 175, 0.3)" />
            <circle cx="500" cy="260" r="2" fill="rgba(156, 163, 175, 0.3)" />
          </svg>

          {/* Player Positions - Both teams on same rink */}
          <div 
            className="absolute inset-0"
            style={{ transformStyle: 'preserve-3d' }}
          >
            {/* AWAY TEAM (Left side - defending left goal) */}
            {/* Away Goalie */}
            <div className="absolute" style={{ left: '6%', top: '50%', transform: 'translateY(-50%)' }}>
              <PlayerNode player={awayRoster.onIce.goalie} isHome={false} />
            </div>

            {/* Away Defense */}
            <div className="absolute flex flex-col gap-16" style={{ left: '15%', top: '50%', transform: 'translateY(-50%)' }}>
              {awayRoster.onIce.defense.slice(0, 2).map((player) => (
                <PlayerNode key={player.id} player={player} isHome={false} />
              ))}
            </div>

            {/* Away Forwards */}
            <div className="absolute flex flex-col gap-12" style={{ left: '32%', top: '50%', transform: 'translateY(-50%)' }}>
              {sortAwayForwards.map((player) => (
                <PlayerNode key={player.id} player={player} isHome={false} />
              ))}
          </div>

            {/* HOME TEAM (Right side - defending right goal) */}
            {/* Home Goalie */}
            <div className="absolute" style={{ right: '6%', top: '50%', transform: 'translateY(-50%)' }}>
              <PlayerNode player={homeRoster.onIce.goalie} isHome={true} />
          </div>

            {/* Home Defense */}
            <div className="absolute flex flex-col gap-16" style={{ right: '15%', top: '50%', transform: 'translateY(-50%)' }}>
              {homeRoster.onIce.defense.slice(0, 2).map((player) => (
                <PlayerNode key={player.id} player={player} isHome={true} />
            ))}
          </div>

            {/* Home Forwards */}
            <div className="absolute flex flex-col gap-12" style={{ right: '32%', top: '50%', transform: 'translateY(-50%)' }}>
              {sortHomeForwards.map((player) => (
                <PlayerNode key={player.id} player={player} isHome={true} />
              ))}
            </div>
          </div>

          </div>
        </div>

        {/* Zone labels and team headers - 2D overlay (not tilted) */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="relative w-full aspect-[2/1] max-w-6xl mx-auto">
            {/* Away Team (Left defensive zone) */}
            <div className="absolute left-12 top-3">
              <div className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full shadow-lg shadow-gray-400/50"></div>
                <span className="text-xs font-military-display text-gray-300 tracking-widest uppercase font-bold drop-shadow-lg">
                  {awayTeam}
                </span>
              </div>
              <div className="text-[8px] font-military-display text-gray-500 tracking-wider uppercase mt-1">
                Defensive Zone
              </div>
            </div>
            
            {/* Neutral Zone (Center) */}
            <div className="absolute left-1/2 -translate-x-1/2 top-3">
              <div className="text-center">
                <div className="text-xs font-military-display text-gray-400 tracking-widest uppercase font-bold drop-shadow-lg">
                  On-Ice Formation
                </div>
                <div className="text-[8px] font-military-display text-gray-600 tracking-wider uppercase mt-1">
                  Neutral Zone
                </div>
              </div>
            </div>
            
            {/* Game Clock - positioned between text and rink */}
            <div className="absolute left-1/2 -translate-x-1/2 top-16">
              <div className="text-4xl font-military-display text-white tabular-nums tracking-wider">
                {formatTime(periodTime)}
              </div>
            </div>
            
            {/* Home Team (Right defensive zone) */}
            <div className="absolute right-12 top-3">
              <div className="flex items-center space-x-2 justify-end">
                <span className="text-xs font-military-display text-white tracking-widest uppercase font-bold drop-shadow-lg">
                  {homeTeam}
                </span>
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse shadow-lg shadow-red-600/50"></div>
              </div>
              <div className="text-[8px] font-military-display text-gray-500 tracking-wider uppercase mt-1 text-right">
                Defensive Zone
              </div>
          </div>
          </div>
        </div>
      </div>

    </div>
  )
}