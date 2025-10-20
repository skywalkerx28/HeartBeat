'use client'

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDownIcon } from '@heroicons/react/24/outline'

interface PlayerEvent {
  x?: number | null
  y?: number | null
  x_adj?: number | null
  y_adj?: number | null
  zone?: string | null
  playSection?: string | null
  shorthand?: string | null
  outcome?: string | null
  period?: number | null
  gameTime?: number | null
}

interface GameLogRinkVisualizationProps {
  deployments?: {
    by_zone?: Record<string, number>
    by_strength?: Record<string, number>
  }
  playerPosition?: string
  events?: PlayerEvent[]
  shifts?: PlayerShift[]
}

interface PlayerShift {
  start_game_time: number | null
  end_game_time: number | null
  start_period?: number | null
  end_period?: number | null
  start_period_time?: number | null
  end_period_time?: number | null
  strength_start?: string | null
  manpower_start?: string | null
  sequence_ids?: number[]
  deployment_ids?: number[]
  index?: number
}

export function GameLogRinkVisualization({ deployments, playerPosition, events = [], shifts = [] }: GameLogRinkVisualizationProps) {
  const [selectedZone, setSelectedZone] = useState<string>('ALL')
  const [selectedAction, setSelectedAction] = useState<string>('ALL')
  const [selectedShift, setSelectedShift] = useState<number | 'ALL'>('ALL')
  const [zoneDropdownOpen, setZoneDropdownOpen] = useState(false)
  const [actionDropdownOpen, setActionDropdownOpen] = useState(false)
  const [shiftDropdownOpen, setShiftDropdownOpen] = useState(false)
  const [hoveredEvent, setHoveredEvent] = useState<PlayerEvent | null>(null)
  const [hoveredPosition, setHoveredPosition] = useState<{ x: number; y: number } | null>(null)
  
  // Get unique zones from events
  const zones = useMemo(() => {
    const zoneSet = new Set<string>()
    events.forEach(e => {
      if (e.zone) zoneSet.add(e.zone)
    })
    return ['ALL', ...Array.from(zoneSet).sort()]
  }, [events])

  // Get unique action types from events
  const actionTypes = useMemo(() => {
    const types = new Set<string>()
    events.forEach(e => {
      if (e.shorthand) types.add(e.shorthand)
    })
    return ['ALL', ...Array.from(types).sort()]
  }, [events])

  // Filter events based on selected zone, action, and shift
  const filteredEvents = useMemo(() => {
    let shiftBounds: { start: number; end: number } | null = null
    if (selectedShift !== 'ALL') {
      const sh = shifts.find(s => s.index === selectedShift)
      if (sh && sh.start_game_time != null && sh.end_game_time != null) {
        shiftBounds = { start: Number(sh.start_game_time), end: Number(sh.end_game_time) }
      }
    }

    const filtered = events.filter(e => {
      const zoneMatch = selectedZone === 'ALL' || e.zone === selectedZone
      const actionMatch = selectedAction === 'ALL' || e.shorthand === selectedAction
      const time = e.gameTime == null ? null : Number(e.gameTime)
      const shiftMatch = !shiftBounds || (time != null && time >= shiftBounds.start && time <= shiftBounds.end)
      return zoneMatch && actionMatch && shiftMatch
    })
    // Sort by game time to prepare for sequence visualization
    return filtered.sort((a, b) => (Number(a.gameTime ?? 0) - Number(b.gameTime ?? 0)))
  }, [events, selectedZone, selectedAction, selectedShift, shifts])

  // Calculate zone percentages and success/attempts from filtered events
  const {
    ozPercent, nzPercent, dzPercent,
    ozCount, nzCount, dzCount,
    ozSucc, nzSucc, dzSucc,
  } = useMemo(() => {
    const byZone: Record<string, { count: number; succ: number }> = {
      OZ: { count: 0, succ: 0 },
      NZ: { count: 0, succ: 0 },
      DZ: { count: 0, succ: 0 },
    }
    for (const e of filteredEvents) {
      const z = (e.zone || '').toString().toUpperCase()
      if (!byZone[z]) continue
      byZone[z].count += 1
      if ((e.outcome || '').toString().toLowerCase() === 'successful') byZone[z].succ += 1
    }
    const total = (byZone.OZ.count + byZone.NZ.count + byZone.DZ.count) || 1
    return {
      ozPercent: (byZone.OZ.count / total) * 100,
      nzPercent: (byZone.NZ.count / total) * 100,
      dzPercent: (byZone.DZ.count / total) * 100,
      ozCount: byZone.OZ.count,
      nzCount: byZone.NZ.count,
      dzCount: byZone.DZ.count,
      ozSucc: byZone.OZ.succ,
      nzSucc: byZone.NZ.succ,
      dzSucc: byZone.DZ.succ,
    }
  }, [filteredEvents])

  // Calculate heat map intensities (0-1 scale)
  const ozIntensity = ozPercent / 100
  const nzIntensity = nzPercent / 100
  const dzIntensity = dzPercent / 100

  // Coordinate transform (NHL standard: x_adj in [-100,100], y_adj in [-42.5,42.5])
  const rink = { x: 20, y: 60, w: 760, h: 240 }
  const toSvg = (ex: number | null | undefined, ey: number | null | undefined) => {
    if (ex === null || ex === undefined || ey === null || ey === undefined) return null
    const xNorm = (ex + 100) / 200 // 0..1
    const yNorm = (-(ey) + 42.5) / 85 // 0..1 (invert so +y is up on rink)
    const sx = rink.x + xNorm * rink.w
    const sy = rink.y + yNorm * rink.h
    return { x: sx, y: sy }
  }
  // Helper for mapping just x (feet -> px) to keep rink markings consistent with event mapping
  const mapX = (ex: number) => rink.x + ((ex + 100) / 200) * rink.w
  // Blue line world coords at +/-25 ft from center; compute pixel positions
  const leftBlueX = mapX(-25)
  const rightBlueX = mapX(25)
  // Optional: goal line approx at +/-89 ft (standard NHL)
  const leftGoalX = mapX(-89)
  const rightGoalX = mapX(89)

  return (
    <div className="relative w-full">
      {/* Filter Controls */}
      {(zones.length > 1 || actionTypes.length > 1 || (shifts && shifts.length > 0)) && (
        <div className="mb-4 flex items-start space-x-3">
          {/* Zone Filter */}
          {zones.length > 1 && (
            <div className="relative flex-1">
              <button
                onClick={() => {
                  setZoneDropdownOpen(!zoneDropdownOpen)
                  setActionDropdownOpen(false)
                }}
                className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-gray-500 uppercase tracking-wider">ZONE:</span>
                  <span className="text-white">{selectedZone}</span>
                </div>
                <ChevronDownIcon className={`w-3.5 h-3.5 transition-transform ${zoneDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {zoneDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
                  >
                    {zones.map((zone) => (
                      <button
                        key={zone}
                        onClick={() => {
                          setSelectedZone(zone)
                          setZoneDropdownOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                          selectedZone === zone
                            ? 'bg-white/5 text-white' 
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        <span className="uppercase tracking-wider">{zone}</span>
                        {selectedZone === zone && (
                          <div className="w-1.5 h-1.5 rounded-full bg-red-600" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Action Filter */}
          {actionTypes.length > 1 && (
            <div className="relative flex-1">
              <button
                onClick={() => {
                  setActionDropdownOpen(!actionDropdownOpen)
                  setZoneDropdownOpen(false)
                  setShiftDropdownOpen(false)
                }}
                className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-gray-500 uppercase tracking-wider">ACTION:</span>
                  <span className="text-white truncate">{selectedAction}</span>
                </div>
                <ChevronDownIcon className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${actionDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {actionDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
                  >
                    {actionTypes.map((action) => (
                      <button
                        key={action}
                        onClick={() => {
                          setSelectedAction(action)
                          setActionDropdownOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                          selectedAction === action
                            ? 'bg-white/5 text-white' 
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        <span className="uppercase tracking-wider text-left">{action}</span>
                        {selectedAction === action && (
                          <div className="w-1.5 h-1.5 rounded-full bg-red-600 flex-shrink-0" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Shift Filter */}
          {shifts && shifts.length > 0 && (
            <div className="relative flex-1">
              <button
                onClick={() => {
                  setShiftDropdownOpen(!shiftDropdownOpen)
                  setZoneDropdownOpen(false)
                  setActionDropdownOpen(false)
                }}
                className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-gray-500 uppercase tracking-wider">SHIFT:</span>
                  <span className="text-white truncate">{selectedShift === 'ALL' ? 'ALL' : `#${selectedShift}`}</span>
                </div>
                <ChevronDownIcon className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${shiftDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {shiftDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
                  >
                    {[{ label: 'ALL', value: 'ALL' as const }, ...shifts.map(s => ({ label: `#${s.index ?? ''} P${s.start_period ?? ''} ${formatGameClock(s.start_period_time)}–${formatGameClock(s.end_period_time)}`, value: s.index as number }))].map(item => (
                      <button
                        key={String(item.value)}
                        onClick={() => {
                          setSelectedShift(item.value)
                          setShiftDropdownOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                          selectedShift === item.value
                            ? 'bg-white/5 text-white' 
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        <span className="uppercase tracking-wider text-left">{item.label}</span>
                        {selectedShift === item.value && (
                          <div className="w-1.5 h-1.5 rounded-full bg-red-600 flex-shrink-0" />
                        )}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Clear Filters */}
          {(selectedZone !== 'ALL' || selectedAction !== 'ALL' || selectedShift !== 'ALL') && (
            <button
              onClick={() => {
                setSelectedZone('ALL')
                setSelectedAction('ALL')
                setSelectedShift('ALL')
                setZoneDropdownOpen(false)
                setActionDropdownOpen(false)
                setShiftDropdownOpen(false)
              }}
              className="px-3 py-2 text-[10px] font-military-display text-red-400 hover:text-red-300 uppercase tracking-wider transition-colors border border-red-600/20 hover:border-red-600/40 rounded"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Zone Labels Above Rink */}
      <div className="relative w-full max-w-4xl mx-auto mt-6 mb-2">
        <div className="grid grid-cols-3 gap-4">
          {/* DZ Label */}
          <div className="text-center">
            <div className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider font-bold">
              DZ
            </div>
            <div className="text-lg font-military-display text-white font-bold tabular-nums mt-0.5">
              {dzPercent.toFixed(0)}%
              <span className="text-[10px] text-gray-500 ml-1">({dzCount})</span>
            </div>
            <div className="text-[10px] font-military-display text-gray-500 tabular-nums">
              {dzSucc}/{dzCount} {dzCount > 0 ? Math.round((dzSucc/dzCount)*100) : 0}%
            </div>
          </div>

          {/* NZ Label */}
          <div className="text-center">
            <div className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider font-bold">
              NZ
            </div>
            <div className="text-lg font-military-display text-white font-bold tabular-nums mt-0.5">
              {nzPercent.toFixed(0)}%
              <span className="text-[10px] text-gray-500 ml-1">({nzCount})</span>
            </div>
            <div className="text-[10px] font-military-display text-gray-500 tabular-nums">
              {nzSucc}/{nzCount} {nzCount > 0 ? Math.round((nzSucc/nzCount)*100) : 0}%
            </div>
          </div>

          {/* OZ Label */}
          <div className="text-center">
            <div className="text-[10px] font-military-display text-red-400 uppercase tracking-wider font-bold">
              OZ
            </div>
            <div className="text-lg font-military-display text-white font-bold tabular-nums mt-0.5">
              {ozPercent.toFixed(0)}%
              <span className="text-[10px] text-gray-500 ml-1">({ozCount})</span>
            </div>
            <div className="text-[10px] font-military-display text-gray-500 tabular-nums">
              {ozSucc}/{ozCount} {ozCount > 0 ? Math.round((ozSucc/ozCount)*100) : 0}%
            </div>
          </div>
        </div>
      </div>

      {/* Compact Horizontal Rink */}
      <div className="relative">
        <div className="perspective-container" style={{ perspective: '800px', perspectiveOrigin: 'center center' }}>
          <div 
            className="relative w-full aspect-[2.2/1] max-w-4xl mx-auto transform-3d"
            style={{ 
              transform: 'rotateX(20deg) rotateZ(0deg)',
              transformStyle: 'preserve-3d',
              transition: 'transform 0.3s ease-out'
            }}
          >
            {/* SVG Horizontal Rink Outline */}
            <svg 
              viewBox="0 0 800 360" 
              className="absolute inset-0 w-full h-full"
              style={{ 
                filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.6))',
                transformStyle: 'preserve-3d'
              }}
            >
              {/* Rink boards - horizontal orientation */}
              <rect 
                x="20" 
                y="60" 
                width="760" 
                height="240" 
                rx="30"
                fill="none"
                stroke="rgba(156, 163, 175, 0.3)"
                strokeWidth="1.5"
              />

              {/* Zone heat map overlays */}
              {/* DZ - Left Zone (Away - Gray) */}
              <rect 
                x={rink.x}
                y={rink.y}
                width={leftBlueX - rink.x}
                height={rink.h}
                rx={30}
                fill={`rgba(156, 163, 175, ${dzIntensity * 0.25})`}
              />

              {/* NZ - Middle Zone (Neutral - Subtle) */}
              <rect 
                x={leftBlueX}
                y={rink.y}
                width={rightBlueX - leftBlueX}
                height={rink.h}
                fill={`rgba(156, 163, 175, ${nzIntensity * 0.15})`}
              />

              {/* OZ - Right Zone (Home - Red) */}
              <rect 
                x={rightBlueX}
                y={rink.y}
                width={rink.x + rink.w - rightBlueX}
                height={rink.h}
                rx={30}
                fill={`rgba(239, 68, 68, ${ozIntensity * 0.3})`}
              />

              {/* Blue lines - vertical (mapped to +/-25 ft) */}
              <line 
                x1={leftBlueX}
                y1={rink.y}
                x2={leftBlueX}
                y2={rink.y + rink.h}
                stroke="rgba(156, 163, 175, 0.3)"
                strokeWidth={2}
              />
              <line 
                x1={rightBlueX}
                y1={rink.y}
                x2={rightBlueX}
                y2={rink.y + rink.h}
                stroke="rgba(156, 163, 175, 0.3)"
                strokeWidth={2}
              />

              {/* Red center line - vertical */}
              <line 
                x1="400" 
                y1="60" 
                x2="400" 
                y2="300" 
                stroke="rgba(239, 68, 68, 0.4)"
                strokeWidth="2"
              />

              {/* Center face-off circle */}
              <ellipse 
                cx="400" 
                cy="180" 
                rx="40" 
                ry="28" 
                fill="none"
                stroke="rgba(156, 163, 175, 0.2)"
                strokeWidth="1"
              />
              <circle 
                cx="400" 
                cy="180" 
                r="3" 
                fill="rgba(239, 68, 68, 0.6)"
              />

              {/* Goal lines (mapped approx to +/-89 ft) */}
              <line 
                x1={leftGoalX}
                y1={rink.y}
                x2={leftGoalX}
                y2={rink.y + rink.h}
                stroke="rgba(239, 68, 68, 0.3)"
                strokeWidth={1.5}
              />
              <line 
                x1={rightGoalX}
                y1={rink.y}
                x2={rightGoalX}
                y2={rink.y + rink.h}
                stroke="rgba(239, 68, 68, 0.3)"
                strokeWidth={1.5}
              />

              {/* Goal creases - left (DZ - Away) */}
              <path
                d="M 60 140 Q 75 180 60 220"
                fill="none"
                stroke="rgba(156, 163, 175, 0.3)"
                strokeWidth="1.5"
              />

              {/* Goal creases - right (OZ - Home) */}
              <path
                d="M 740 140 Q 725 180 740 220"
                fill="none"
                stroke="rgba(239, 68, 68, 0.3)"
                strokeWidth="1.5"
              />

              {/* Face-off circles and dots - DZ */}
              <ellipse cx="140" cy="120" rx="20" ry="14" fill="none" stroke="rgba(156, 163, 175, 0.3)" strokeWidth="1" />
              <circle cx="140" cy="120" r="3" fill="rgba(239, 68, 68, 0.6)" />
              <ellipse cx="140" cy="240" rx="20" ry="14" fill="none" stroke="rgba(156, 163, 175, 0.3)" strokeWidth="1" />
              <circle cx="140" cy="240" r="3" fill="rgba(239, 68, 68, 0.6)" />
              
              {/* Face-off circles and dots - OZ */}
              <ellipse cx="660" cy="120" rx="20" ry="14" fill="none" stroke="rgba(156, 163, 175, 0.3)" strokeWidth="1" />
              <circle cx="660" cy="120" r="3" fill="rgba(239, 68, 68, 0.6)" />
              <ellipse cx="660" cy="240" rx="20" ry="14" fill="none" stroke="rgba(156, 163, 175, 0.3)" strokeWidth="1" />
              <circle cx="660" cy="240" r="3" fill="rgba(239, 68, 68, 0.6)" />

              {/* Neutral zone face-off dots */}
              <circle cx="300" cy="120" r="2" fill="rgba(156, 163, 175, 0.3)" />
              <circle cx="300" cy="240" r="2" fill="rgba(156, 163, 175, 0.3)" />
              <circle cx="500" cy="120" r="2" fill="rgba(156, 163, 175, 0.3)" />
              <circle cx="500" cy="240" r="2" fill="rgba(156, 163, 175, 0.3)" />

              {/* Player event markers */}
              {filteredEvents.map((ev, idx) => {
                const pt = toSvg((ev.x_adj ?? ev.x) as number | null, (ev.y_adj ?? ev.y) as number | null)
                if (!pt) return null
                const zone = (ev.zone || '').toString().toUpperCase()
                const success = (ev.outcome || '').toString().toLowerCase() === 'successful'
                const fill = zone === 'OZ' ? 'rgba(239,68,68,0.9)' : zone === 'DZ' ? 'rgba(156,163,175,0.9)' : 'rgba(148,163,184,0.9)'
                const stroke = success ? 'rgba(34,197,94,0.9)' : 'rgba(239,68,68,0.8)'
                const r = hoveredEvent === ev ? 5 : 3
                return (
                  <circle 
                    key={idx} 
                    cx={pt.x} 
                    cy={pt.y} 
                    r={r}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={hoveredEvent === ev ? 2 : 1}
                    opacity={hoveredEvent === ev ? 1 : 0.85}
                    className="cursor-pointer transition-all duration-150"
                    onMouseEnter={(e) => {
                      setHoveredEvent(ev)
                      const rect = (e.target as SVGCircleElement).getBoundingClientRect()
                      setHoveredPosition({ x: rect.left + rect.width / 2, y: rect.top })
                    }}
                    onMouseLeave={() => {
                      setHoveredEvent(null)
                      setHoveredPosition(null)
                    }}
                  >
                  </circle>
                )
              })}
            </svg>

          </div>
        </div>

        {/* Hover Tooltip */}
        {hoveredEvent && hoveredPosition && (
          <div
            className="fixed z-50 pointer-events-none"
            style={{
              left: hoveredPosition.x,
              top: hoveredPosition.y - 10,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div className="bg-black/95 backdrop-blur-xl border border-white/20 rounded px-3 py-2 shadow-lg">
              <div className="text-xs font-military-display text-white font-bold mb-1">
                {hoveredEvent.shorthand || 'UNKNOWN ACTION'}
              </div>
              <div className="space-y-0.5">
                {hoveredEvent.outcome && (
                  <div className="text-[10px] font-military-display text-gray-400">
                    Result: <span className={hoveredEvent.outcome.toLowerCase() === 'successful' ? 'text-green-400' : 'text-red-400'}>
                      {hoveredEvent.outcome}
                    </span>
                  </div>
                )}
                {hoveredEvent.zone && (
                  <div className="text-[10px] font-military-display text-gray-400">
                    Zone: <span className="text-white">{hoveredEvent.zone}</span>
                  </div>
                )}
                {hoveredEvent.period && (
                  <div className="text-[10px] font-military-display text-gray-400">
                    Period: <span className="text-white">{hoveredEvent.period}</span>
                  </div>
                )}
                {(() => {
                  if (!hoveredEvent || hoveredEvent.gameTime == null) return null
                  const sh = shifts.find(s => s.start_game_time != null && s.end_game_time != null && Number(hoveredEvent.gameTime!) >= Number(s.start_game_time) && Number(hoveredEvent.gameTime!) <= Number(s.end_game_time))
                  if (!sh || !sh.index) return null
                  return (
                    <div className="text-[10px] font-military-display text-gray-400">
                      Shift: <span className="text-white">#{sh.index}</span>
                    </div>
                  )
                })()}
              </div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="mt-4 flex items-center justify-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-sm bg-gray-500/30 border border-gray-500/50" />
            <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
              Defensive Zone
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-sm bg-gray-400/20 border border-gray-400/40" />
            <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
              Neutral Zone
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-sm bg-red-600/30 border border-red-600/50" />
            <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
              Offensive Zone
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helpers
function formatClock(t: number | null | undefined): string {
  if (t == null || isNaN(Number(t))) return '--:--'
  const total = Math.max(0, Math.floor(Number(t)))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

// Convert period elapsed seconds to game clock (counting down from 20:00)
function formatGameClock(t: number | null | undefined, periodLengthSec = 1200): string {
  if (t == null || isNaN(Number(t))) return '--:--'
  const elapsed = Math.max(0, Math.floor(Number(t)))
  const remaining = Math.max(0, periodLengthSec - elapsed)
  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}
