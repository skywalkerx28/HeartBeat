'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { GameLog, AdvancedPlayerMetrics, resolvePlayerNames, PlayerNameEntry, PlayerEvent, PlayerShift } from '../../lib/profileApi'
import { TeamLink } from '../navigation/TeamLink'
import { GameLogRinkVisualization } from './GameLogRinkVisualization'
import { getPlayerGameEvents } from '../../lib/profileApi'

interface PlayerGameLogsTableProps {
  gameLogs: GameLog[]
  adv?: AdvancedPlayerMetrics | null
  seasons?: number[]
  selectedSeason?: number
  onSelectSeason?: (season: number) => void
  playerTeamId?: string
  playerPosition?: string
}

export function PlayerGameLogsTable({ gameLogs, adv, seasons = [], selectedSeason, onSelectSeason, playerTeamId, playerPosition }: PlayerGameLogsTableProps) {
  const [expandedGameIds, setExpandedGameIds] = React.useState<Set<string | number>>(new Set())
  const [nameMap, setNameMap] = React.useState<Record<string, PlayerNameEntry>>({})
  // Removed legacy action breakdown/faceoff expanders
  const [eventsByGame, setEventsByGame] = React.useState<Record<string, { events: PlayerEvent[]; shifts: PlayerShift[] }>>({})

  // Resolve opponent names used in tables (dedup; stable key)
  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!adv?.games?.length) return
      const ids = new Set<string>()
      adv.games.forEach(game => {
        Object.keys(game.opponent_appearances || {}).forEach(k => ids.add(String(k)))
        game.top_opponents_by_time?.forEach(row => ids.add(String(row.opponent_id)))
        Object.keys(game.line_vs_pair_appearances || {}).forEach(tupleStr => {
          const inner = tupleStr.replace(/^\(/,'').replace(/\)$/,'')
          inner.split(',').forEach(p => { const id = p.trim().replace(/['"]/g, ''); if (id) ids.add(id) })
        })
        // Include IDs from time-vs-pair metrics as well
        const timePairs: Record<string, number> = (game as any).line_vs_pair_time_sec || {}
        Object.keys(timePairs).forEach(tupleStr => {
          const inner = tupleStr.replace(/^\(/,'').replace(/\)$/,'')
          inner.split(',').forEach(p => { const id = p.trim().replace(/['"]/g, ''); if (id) ids.add(id) })
        })
        Object.keys(game.trio_time_sec || {}).forEach(tupleStr => {
          const inner = tupleStr.replace(/^\(/,'').replace(/\)$/,'')
          inner.split(',').forEach(p => { const id = p.trim().replace(/['"]/g, ''); if (id) ids.add(id) })
        })
      })
      const arr = Array.from(ids)
      if (arr.length === 0) return
      // Skip if we already have all
      const allHave = arr.every(id => nameMap[String(id)])
      if (allHave) return
      const resolved = await resolvePlayerNames(arr)
      if (!cancelled && resolved) setNameMap(prev => ({ ...prev, ...resolved }))
    })()
    return () => { cancelled = true }
  }, [adv])

  const shortName = (id: string | number) => {
    const key = String(id)
    return nameMap[key]?.lastName || key
  }

  const formatIdTuple = (tupleStr: string, sep = ' / ') => {
    const inner = tupleStr.replace(/^\(/,'').replace(/\)$/,'')
    const ids = inner.split(',').map(s => s.trim().replace(/['"]/g, '')).filter(Boolean)
    return ids.map(shortName).join(sep)
  }

  const toggleGameExpansion = (gameId: string | number, advShortId?: string | number) => {
    setExpandedGameIds(prev => {
      const next = new Set(prev)
      if (next.has(gameId)) {
        next.delete(gameId)
      } else {
        next.add(gameId)
      }
      return next
    })
    // Lazy-load events when expanding
    const key = String(gameId)
    if (!eventsByGame[key] && adv?.playerId) {
      const raw = String(gameId)
      const fallbackShort = raw.slice(-5)
      const shortId = String(advShortId ?? fallbackShort)
      getPlayerGameEvents(adv.playerId, Number(shortId), { season: adv.season, teamAbbrev: playerTeamId }).then(payload => {
        setEventsByGame(prev => ({ ...prev, [key]: payload }))
      }).catch(()=>{})
    }
  }

  // Removed legacy action breakdown/faceoff handlers

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-lg"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              {(() => {
                if (!selectedSeason) return 'Game Log'
                const s = String(selectedSeason)
                const start = s.slice(0, 4)
                const end = s.slice(4, 8).slice(-2)
                return `Game Log - ${start}-${end}`
              })()}
            </h3>
          </div>
          {seasons.length > 0 && onSelectSeason && (
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">Season</span>
              <select
                value={selectedSeason || ''}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => onSelectSeason(parseInt(e.target.value, 10))}
                className="bg-black/40 border border-white/10 text-xs font-military-display text-white rounded px-2 py-1"
              >
                {seasons.map(s => (
                  <option key={s} value={s}>{`${String(s).slice(0,4)}-${String(s).slice(6,8)}`}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Table Header */}
        <div className="grid grid-cols-[auto_1.2fr_1.8fr_1fr_0.7fr_0.7fr_0.7fr_0.7fr_0.7fr_0.8fr_0.8fr_0.8fr_0.9fr_0.9fr] gap-4 px-4 pb-3 border-b border-white/20 mb-2">
          <div className="w-6"></div>
          <div className="text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Date</div>
          <div className="text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Opponent</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Result</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">G</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">A</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">PTS</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">+/-</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">SOG</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Hits</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Blk</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">PIM</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">Shifts</div>
          <div className="text-center text-[10px] font-military-display text-gray-400 uppercase tracking-widest">TOI</div>
        </div>

        {/* Table Rows */}
        <div className="space-y-2">
          {(gameLogs.length > 0 ? gameLogs : (adv?.games || []).map(g => ({
            gameId: String(g.gameId),
            date: '-',
            opponent: (playerTeamId && (g.homeTeam === playerTeamId || g.awayTeam === playerTeamId))
              ? (g.homeTeam === playerTeamId ? (g.awayTeam || '') : (g.homeTeam || ''))
              : `${g.homeTeam || ''}`,
            opponentName: '',
            homeAway: (playerTeamId && (g.homeTeam === playerTeamId || g.awayTeam === playerTeamId))
              ? (g.homeTeam === playerTeamId ? 'home' : 'away')
              : 'home',
            result: '-', goals: 0, assists: 0, points: 0, plusMinus: 0,
            pim: 0, shots: 0, hits: 0, blockedShots: 0, shifts: 0, timeOnIce: '--:--'
          }) as unknown as GameLog)).map((game, idx) => {
            const resultColor = game.result === 'W' ? 'text-green-400' : 
                               game.result === 'OTL' ? 'text-amber-400' : 'text-red-400'
            const isExpanded = expandedGameIds.has(game.gameId)
            
            // Normalize game ID for matching with advanced metrics
            // NHL API uses full format (2025020004), our advanced metrics use short format (20004)
            const normalizedGameId = game.gameId.length > 5 ? game.gameId.slice(-5) : game.gameId
            const gameAdv = adv?.games?.find(g => {
              const advGameId = String(g.gameId).padStart(5, '0')
              const matches = advGameId === normalizedGameId
              if (idx === 0 && matches) {
                console.log(`Game ID match found: NHL=${game.gameId} (normalized=${normalizedGameId}) matches Advanced=${g.gameId} (padded=${advGameId})`)
              }
              return matches
            })
            
            if (idx === 0 && !gameAdv && adv?.games?.length) {
              console.log(`No match for game ${game.gameId} (normalized=${normalizedGameId}). Available advanced game IDs:`, adv.games.slice(0, 5).map(g => g.gameId))
            }

            return (
              <motion.div
                key={game.gameId}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.02 }}
                className="border border-white/10 rounded bg-black/20 hover:border-white/20 transition-all duration-200"
              >
                {/* Main Row */}
                <div className="grid grid-cols-[auto_1.2fr_1.8fr_1fr_0.7fr_0.7fr_0.7fr_0.7fr_0.7fr_0.8fr_0.8fr_0.8fr_0.9fr_0.9fr] gap-4 items-center px-4 py-4">
                  <button
                    onClick={() => gameAdv && toggleGameExpansion(game.gameId, gameAdv.gameId)}
                    className={`w-6 h-6 flex items-center justify-center hover:bg-white/10 rounded transition-colors ${gameAdv ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
                    title={gameAdv ? 'View advanced metrics' : 'Advanced metrics not available for this game'}
                  >
                    {isExpanded ? (
                      <ChevronDownIcon className="w-4 h-4 text-red-400" />
                    ) : (
                      <ChevronRightIcon className={`w-4 h-4 ${gameAdv ? 'text-red-400' : 'text-gray-700'}`} />
                    )}
                  </button>

                  <div className="text-[11px] font-military-display text-gray-300 tabular-nums">
                    {game.date && game.date !== '-' ? new Date(game.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '-'}
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                      {game.homeAway === 'away' ? '@' : 'vs'}
                    </span>
                    <TeamLink teamId={game.opponent} className="text-xs font-military-display text-white hover:text-red-400 transition-colors">
                      {game.opponent}
                    </TeamLink>
                  </div>

                  <div className={`text-xs font-military-display ${resultColor} text-center font-bold uppercase tracking-wider`}>
                    {game.result}
                  </div>

                  <div className="text-xs font-military-display text-white text-center tabular-nums">
                    {game.goals}
                  </div>

                  <div className="text-xs font-military-display text-white text-center tabular-nums">
                    {game.assists}
                  </div>

                  <div className="text-xs font-military-display text-white text-center tabular-nums font-bold">
                    {game.points}
                  </div>

                  <div className={`text-xs font-military-display text-center tabular-nums ${
                    game.plusMinus > 0 ? 'text-green-400' : 
                    game.plusMinus < 0 ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {game.plusMinus > 0 ? '+' : ''}{game.plusMinus}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.shots}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.hits}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.blockedShots}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.pim}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.shifts}
                  </div>

                  <div className="text-xs font-military-display text-gray-300 text-center tabular-nums">
                    {game.timeOnIce}
                  </div>
                </div>

                {/* Expanded Advanced Metrics */}
                <AnimatePresence>
                  {isExpanded && gameAdv && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden border-t border-white/10"
                    >
                      <div className="px-4 py-6 bg-black/40">
                        <div className="flex items-center space-x-2 mb-6">
                          <div className="w-0.5 h-3 bg-red-600" />
                          <h5 className="text-[10px] font-military-display text-red-400 uppercase tracking-widest">
                            Advanced Metrics
                          </h5>
                        </div>

                        <div className="grid grid-cols-[1fr_1fr_1.5fr_1.2fr] gap-6">
                          {/* Opponents by Time */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              Top Opponents by Time
                            </div>
                            <div className="space-y-2">
                              {(gameAdv.top_opponents_by_time || []).slice(0, 5).map((row, i) => (
                                <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/5">
                                  <span className="text-[11px] font-military-display text-gray-400">{shortName(row.opponent_id)}</span>
                                  <span className="text-[11px] font-military-display text-white tabular-nums">{(row.total_time_sec / 60).toFixed(1)}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Opponents by Appearances */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              Opponents by Appearances
                            </div>
                            <div className="space-y-2">
                              {Object.entries(gameAdv.opponent_appearances || {})
                                .sort((a, b) => Number(b[1]) - Number(a[1]))
                                .slice(0, 5)
                                .map(([pid, cnt]) => (
                                  <div key={pid} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/5">
                                    <span className="text-[11px] font-military-display text-gray-400">{shortName(pid)}</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">{Number(cnt)}</span>
                                  </div>
                                ))}
                            </div>
                          </div>

                          {/* Line Trios - For D, show opponent trios faced by time */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              {playerPosition === 'D' ? 'Top Trios Faced (min)' : 'Top Line Trios (min)'}
                            </div>
                            <div className="space-y-2">
                              {Object.entries((playerPosition === 'D' ? (gameAdv as any).pair_vs_line_time_sec || {} : gameAdv.trio_time_sec || {}))
                                .sort((a, b) => Number(b[1]) - Number(a[1]))
                                .slice(0, 5)
                                .map(([trio, secs]) => (
                                  <div key={trio} className="flex items-start justify-between gap-2 py-1.5 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400 leading-tight" style={{ letterSpacing: '-0.3px' }}>
                                      {formatIdTuple(trio, ' - ')}
                                    </span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums flex-shrink-0">{(Number(secs) / 60).toFixed(1)}</span>
                                  </div>
                                ))}
                            </div>
                          </div>

                          {/* Line vs Pair / Player vs Pairing */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              {playerPosition === 'D' ? 'Player vs Pairing' : 'Line vs D-Pair'}
                            </div>
                            <div className="space-y-2">
                              {Object.entries(gameAdv.line_vs_pair_appearances || {})
                                .sort((a, b) => Number(b[1]) - Number(a[1]))
                                .slice(0, 5)
                                .map(([pairKey, cnt]) => (
                                  <div key={pairKey} className="flex items-start justify-between gap-2 py-1.5 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400 leading-tight" style={{ letterSpacing: '-0.3px' }}>
                                      {formatIdTuple(pairKey, ' / ')}
                                    </span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums flex-shrink-0">{Number(cnt)}</span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>

                        {/* Additional row: Time vs D-Pairs (min) + Shift Summary */}
                        <div className="grid grid-cols-[1.5fr_1fr] gap-6 mt-6">
                          {/* Time vs D-Pairs */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              Time vs D-Pairs (min)
                            </div>
                            <div className="space-y-2">
                              {Object.entries((gameAdv as any).line_vs_pair_time_sec || {})
                                .sort((a, b) => Number(b[1]) - Number(a[1]))
                                .slice(0, 5)
                                .map(([pairKey, secs]) => (
                                  <div key={pairKey} className="flex items-start justify-between gap-2 py-1.5 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400 leading-tight" style={{ letterSpacing: '-0.3px' }}>
                                      {formatIdTuple(pairKey as string, ' / ')}
                                    </span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums flex-shrink-0">{(Number(secs) / 60).toFixed(1)}</span>
                                  </div>
                                ))}
                            </div>
                          </div>

                          {/* Shift Summary */}
                          <div className="space-y-3">
                            <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider border-b border-white/5 pb-2">
                              Shift Summary
                            </div>
                            {(() => {
                              const shiftsPayload = eventsByGame[String(game.gameId)]?.shifts || []
                              const avg = (arr: number[]) => arr.length ? (arr.reduce((a,b)=>a+b,0)/arr.length) : null
                              const toMMSS = (sec?: number | null) => {
                                if (sec == null || isNaN(Number(sec))) return '--:--'
                                const s = Math.max(0, Math.round(Number(sec)))
                                const m = Math.floor(s/60)
                                const r = s%60
                                return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`
                              }
                              const signCls = (delta: number) => delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : 'text-gray-400'
                              const fmtDeltaTime = (d: number | null) => {
                                if (d == null || isNaN(Number(d))) return null
                                const s = Math.round(Math.abs(Number(d)))
                                const m = Math.floor(s/60), r = s%60
                                const sym = d > 0 ? '+' : d < 0 ? '−' : '±'
                                return `${sym}${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`
                              }
                              const fmtDeltaInt = (d: number | null) => {
                                if (d == null || isNaN(Number(d)) || d === 0) return d === 0 ? '±0' : null
                                const sym = d > 0 ? '+' : '−'
                                return `${sym}${Math.abs(Math.round(Number(d)))}`
                              }
                              // From aggregated per-game
                              const shiftCount = (gameAdv.shift_count ?? 0) as number
                              const toiGame = Number(gameAdv.toi_game_sec ?? 0)
                              const avgShiftGame = gameAdv.avg_shift_game_sec as number | null | undefined
                              const avgRestGame = gameAdv.avg_rest_game_sec as number | null | undefined
                              // Compute season medians from adv.games
                              const gamesArr = (adv?.games || []) as any[]
                              const med = (xs: (number | null | undefined)[]) => {
                                const arr = xs.map(v => Number(v)).filter(v => !isNaN(v)).sort((a,b)=>a-b)
                                if (arr.length === 0) return null
                                const mid = Math.floor(arr.length/2)
                                return arr.length % 2 ? arr[mid] : (arr[mid-1]+arr[mid])/2
                              }
                              const medShiftCount = med(gamesArr.map(g => g.shift_count))
                              const medToi = med(gamesArr.map(g => g.toi_game_sec))
                              const medAvgShift = med(gamesArr.map(g => g.avg_shift_game_sec))
                              const medAvgRest = med(gamesArr.map(g => g.avg_rest_game_sec))
                              const deltaShift = (medShiftCount == null ? null : (shiftCount - medShiftCount))
                              const deltaToi = (medToi == null ? null : (toiGame - medToi))
                              const deltaAvgShift = (medAvgShift == null || avgShiftGame == null ? null : (avgShiftGame - medAvgShift))
                              const deltaAvgRest = (medAvgRest == null || avgRestGame == null ? null : (avgRestGame - medAvgRest))
                              // From per-shift payload if available
                              const realRests = shiftsPayload.map(s => Number(s.rest_real_next)).filter(v => !isNaN(v))
                              const realLens = shiftsPayload.map(s => Number(s.shift_real_length)).filter(v => !isNaN(v))
                              const avgRestReal = avg(realRests)
                              const avgShiftReal = avg(realLens)
                              return (
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400">Shifts</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">
                                      {shiftCount}
                                      {medShiftCount != null && (
                                        <span className={`ml-2 ${signCls(deltaShift || 0)} text-[10px]`}>{fmtDeltaInt(deltaShift)}</span>
                                      )}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400">TOI (game)</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">
                                      {toMMSS(toiGame)}
                                      {medToi != null && (
                                        <span className={`ml-2 ${signCls(deltaToi || 0)} text-[10px]`}>{fmtDeltaTime(deltaToi)}</span>
                                      )}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400">Avg shift (game)</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">
                                      {toMMSS(avgShiftGame ?? undefined)}
                                      {medAvgShift != null && avgShiftGame != null && (
                                        <span className={`ml-2 ${signCls(deltaAvgShift || 0)} text-[10px]`}>{fmtDeltaTime(deltaAvgShift)}</span>
                                      )}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400">Avg rest (game)</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">
                                      {toMMSS(avgRestGame ?? undefined)}
                                      {medAvgRest != null && avgRestGame != null && (
                                        <span className={`ml-2 ${signCls(deltaAvgRest || 0)} text-[10px]`}>{fmtDeltaTime(deltaAvgRest)}</span>
                                      )}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-white/5">
                                    <span className="text-[10px] font-military-display text-gray-400">Avg rest (real)</span>
                                    <span className="text-[11px] font-military-display text-white tabular-nums">{toMMSS(avgRestReal ?? undefined)}</span>
                                  </div>
                                </div>
                              )
                            })()}
                          </div>
                        
                        </div>

                        {/* Game Events Section */}
                        <div className="mt-6 pt-6 border-t border-white/10">
                          <div className="flex items-center space-x-2 mb-6">
                            <div className="w-0.5 h-3 bg-red-600" />
                            <h6 className="text-[10px] font-military-display text-red-400 uppercase tracking-widest">
                              Game Events
                            </h6>
                          </div>

                          {/* Rink Visualization */}
                          <div>
                            <GameLogRinkVisualization 
                              deployments={gameAdv.deployments}
                              events={eventsByGame[String(game.gameId)]?.events || []}
                              shifts={eventsByGame[String(game.gameId)]?.shifts || []}
                            />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </div>

      </div>
    </motion.div>
  )
}
