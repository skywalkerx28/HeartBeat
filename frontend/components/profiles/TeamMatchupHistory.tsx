'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect, useMemo } from 'react'
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { 
  getTeamAdvancedMetrics, 
  getGameDeployments, 
  resolvePlayerNames,
  TeamAdvancedMetrics,
  PlayerNameEntry 
} from '../../lib/profileApi'
import { TeamLink } from '../navigation/TeamLink'

interface TeamMatchupHistoryProps {
  teamId: string
}

interface GameInfo {
  gameId: number
  gameDate: string
  opponent: string
  homeAway: 'home' | 'away'
  goalsFor: number
  goalsAgainst: number
  result: 'W' | 'L' | 'OTL'
}

function mmss(totalSec?: number | null): string {
  if (totalSec == null) return '--:--'
  const s = Math.max(0, Math.round(totalSec))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

export function TeamMatchupHistory({ teamId }: TeamMatchupHistoryProps) {
  const [loading, setLoading] = useState(true)
  const [games, setGames] = useState<GameInfo[]>([])
  const [expandedGame, setExpandedGame] = useState<number | null>(null)
  const [deployments, setDeployments] = useState<any[]>([])
  const [periodOpeners, setPeriodOpeners] = useState<any[]>([])
  const [homeName, setHomeName] = useState<string>('')
  const [awayName, setAwayName] = useState<string>('')
  const [loadingDeployments, setLoadingDeployments] = useState(false)
  const [names, setNames] = useState<Record<string, PlayerNameEntry>>({})
  const [periodFilter, setPeriodFilter] = useState<string>('ALL')
  const [strengthFilter, setStrengthFilter] = useState<string>('ALL')
  const [seasonLabel, setSeasonLabel] = useState<string>('')

  // Load all games for this team
  useEffect(() => {
    let cancelled = false
    const loadGames = async () => {
      setLoading(true)
      try {
        const advData = await getTeamAdvancedMetrics(teamId)
        if (!advData || cancelled) return

        // Season label like 2024-2025
        const sl = advData.season && advData.season.length === 8 
          ? `${advData.season.slice(0,4)}-${advData.season.slice(4,8)}` 
          : String(advData.season || '')
        setSeasonLabel(sl)

        const allGames = (advData.games || [])
          .map((g: any) => {
            const gf = Number(g.goals_for || 0)
            const ga = Number(g.goals_against || 0)
            const wentToOT = Boolean(g.went_to_ot)
            let result: 'W' | 'L' | 'OTL' = 'L'
            if (gf > ga) result = 'W'
            else if (gf < ga) result = wentToOT ? 'OTL' : 'L'

            return {
              gameId: Number(g.gameId),
              gameDate: String(g.gameDate || ''),
              opponent: String(g.opponent || ''),
              homeAway: (g.homeAway || 'home') as 'home' | 'away',
              goalsFor: gf,
              goalsAgainst: ga,
              result,
            }
          })
          .sort((a, b) => b.gameDate.localeCompare(a.gameDate)) // Most recent first

        setGames(allGames)
      } catch (error) {
        console.error('Error loading games:', error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadGames()
    return () => { cancelled = true }
  }, [teamId])

  // Load deployments for expanded game
  useEffect(() => {
    if (expandedGame === null) return

    let cancelled = false
    const loadDeployments = async () => {
      setLoadingDeployments(true)
      setPeriodFilter('ALL')
      setStrengthFilter('ALL')
      
      try {
        const gd = await getGameDeployments(expandedGame)
        if (cancelled) return

        setHomeName(gd.home_team_code || '')
        setAwayName(gd.away_team_code || '')
        setDeployments(gd.deployments || [])
        setPeriodOpeners(gd.period_openers || [])

        // Resolve player names
        const ids = new Set<string>()
        const gather = (arr?: any[]) => {
          for (const d of arr || []) {
            ;(d.home_forwards || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.home_defense || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.away_forwards || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.away_defense || []).forEach((x: any) => x && ids.add(String(x)))
          }
        }
        gather(gd.deployments)
        gather(gd.period_openers)
        if (ids.size) {
          const map = await resolvePlayerNames(Array.from(ids))
          if (!cancelled) setNames(map || {})
        }
      } catch (error) {
        console.error('Error loading deployments:', error)
      } finally {
        if (!cancelled) setLoadingDeployments(false)
      }
    }

    loadDeployments()
    return () => { cancelled = true }
  }, [expandedGame])

  const short = (id?: string) => {
    if (!id) return ''
    const e = names[String(id)]
    return e?.lastName || String(id)
  }

  const labelGroup = (arr?: string[]) => (arr || []).map(id => short(id)).join(' / ')

  // Filter deployments by period and strength
  const filteredDeployments = useMemo(() => {
    return deployments.filter(d => {
      const okP = periodFilter === 'ALL' || String(d.period || '') === periodFilter
      const okS = strengthFilter === 'ALL' || String(d.strength || '') === strengthFilter
      return okP && okS
    })
  }, [deployments, periodFilter, strengthFilter])

  // Get unique periods and strengths for filters
  const periods = useMemo(() => {
    const p = new Set<number>()
    deployments.forEach(d => { if (d.period) p.add(Number(d.period)) })
    return ['ALL', ...Array.from(p).sort((a, b) => a - b).map(n => String(n))]
  }, [deployments])

  const strengths = useMemo(() => {
    const s = new Set<string>()
    deployments.forEach(d => { if (d.strength) s.add(String(d.strength)) })
    return ['ALL', ...Array.from(s)]
  }, [deployments])

  // Calculate forward line vs forward line matchups (trio vs trio)
  const forwardMatchups = useMemo(() => {
    if (filteredDeployments.length === 0) return []

    const patterns: Record<string, {
      homeForwards: string[]
      awayForwards: string[]
      count: number
    }> = {}

    filteredDeployments.forEach(d => {
      const homeForwards = d.home_forwards || []
      const awayForwards = d.away_forwards || []
      
      const key = `${homeForwards.sort().join('-')}|${awayForwards.sort().join('-')}`
      
      if (!patterns[key]) {
        patterns[key] = {
          homeForwards,
          awayForwards,
          count: 0
        }
      }

      patterns[key].count++
    })

    return Object.values(patterns)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }, [filteredDeployments])

  // Calculate defense pair vs away forwards matchups
  const defenseMatchups = useMemo(() => {
    if (filteredDeployments.length === 0) return []

    const patterns: Record<string, {
      homeDefense: string[]
      awayForwards: string[]
      count: number
    }> = {}

    filteredDeployments.forEach(d => {
      const homeDefense = d.home_defense || []
      const awayForwards = d.away_forwards || []
      
      const key = `${homeDefense.sort().join('-')}|${awayForwards.sort().join('-')}`
      
      if (!patterns[key]) {
        patterns[key] = {
          homeDefense,
          awayForwards,
          count: 0
        }
      }

      patterns[key].count++
    })

    return Object.values(patterns)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }, [filteredDeployments])

  if (loading) {
    return (
      <div className="py-6">
        <div className="text-xs text-gray-400 font-military-display">
          Loading game logs...
        </div>
      </div>
    )
  }

  if (games.length === 0) {
    return (
      <div className="py-6">
        <div className="text-xs text-gray-400 font-military-display">
          No games found
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-2">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
          Game Logs & Matchup Deployments
          </h3>
        </div>

      {/* Game Log Table */}
      <div className="space-y-1">
        {/* Header */}
        <div className="grid grid-cols-[0.8fr_1.2fr_0.8fr_0.8fr_0.6fr] gap-3 px-3 pb-3 border-b border-white/10">
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Date</div>
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Opponent</div>
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Score</div>
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Result</div>
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Deploy</div>
        </div>

        {/* Game Rows */}
        {games.map((game, idx) => {
            const isExpanded = expandedGame === game.gameId
            const isHomeTeam = game.homeAway === 'home'

            return (
              <div key={game.gameId} className="space-y-2">
                {/* Game Row - Clickable */}
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.02 }}
                  className={`grid grid-cols-[0.8fr_1.2fr_0.8fr_0.8fr_0.6fr] gap-3 items-center px-3 py-3 transition-all ${
                    isExpanded 
                      ? 'border-b border-white/10' 
                      : 'border-b border-white/5 hover:border-white/10'
                  }`}
                >
                  {/* Date */}
                  <div className="text-xs font-military-display text-gray-400">
                    {new Date(game.gameDate).toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric'
                    })}
                </div>

                  {/* Opponent */}
                  <div className="flex items-center">
                    <TeamLink teamId={game.opponent} className="text-xs font-military-display text-white">
                      {isHomeTeam ? 'vs' : '@'} {game.opponent}
                    </TeamLink>
                </div>

                  {/* Score */}
                  <div className="text-sm font-military-display text-white text-center tabular-nums">
                    {game.goalsFor} - {game.goalsAgainst}
                </div>

                  {/* Result */}
                  <div className="flex justify-center">
                    <div className="text-xs font-military-display text-white uppercase tracking-wider">
                      {game.result}
                </div>
                </div>

                  {/* Expand Button */}
                  <div className="flex justify-center">
                    <button
                      onClick={() => setExpandedGame(isExpanded ? null : game.gameId)}
                      className="p-1 rounded hover:bg-white/10 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDownIcon className="w-4 h-4 text-red-400" />
                      ) : (
                        <ChevronRightIcon className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </div>
                </motion.div>

                {/* Expanded Deployment Details */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="pb-4 space-y-6"
                    >
                        {loadingDeployments ? (
                          <div className="text-xs text-gray-400 font-military-display">
                            Loading deployment data...
                          </div>
                        ) : (
                          <>
                            {/* Filters */}
                            <div className="flex items-center justify-end space-x-4 pb-4 border-b border-white/10">
                              <div className="flex items-center space-x-2">
                                <span className="text-[10px] text-gray-500 font-military-display uppercase tracking-wider">Period</span>
                                <select 
                                  value={periodFilter} 
                                  onChange={e => setPeriodFilter(e.target.value)}
                                  className="bg-black/40 border border-white/10 rounded-lg text-xs px-3 py-1.5 text-white font-military-display"
                                >
                                  {periods.map(p => <option key={p} value={p}>{p}</option>)}
                                </select>
                              </div>
                              <div className="flex items-center space-x-2">
                                <span className="text-[10px] text-gray-500 font-military-display uppercase tracking-wider">Strength</span>
                                <select 
                                  value={strengthFilter} 
                                  onChange={e => setStrengthFilter(e.target.value)}
                                  className="bg-black/40 border border-white/10 rounded-lg text-xs px-3 py-1.5 text-white font-military-display"
                                >
                                  {strengths.map(s => <option key={s} value={s}>{s}</option>)}
                                </select>
                              </div>
                            </div>

                            {/* Empty states for deployments */}
                            {deployments.length === 0 && (
                              <div className="py-3 text-[11px] text-gray-500 font-military-display">
                                No deployments available for this game.
                              </div>
                            )}
                            {deployments.length > 0 && filteredDeployments.length === 0 && (
                              <div className="py-3 text-[11px] text-gray-500 font-military-display">
                                No deployments match the selected filters.
                              </div>
                            )}

                            {/* Forward Line vs Forward Line Matchups */}
                            {forwardMatchups.length > 0 && (
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <div className="w-0.5 h-4 bg-gradient-to-b from-red-400 to-transparent" />
                                    <h5 className="text-xs font-military-display text-white uppercase tracking-widest">
                                      Forward Line Matchups
                                    </h5>
                                  </div>
                                  <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                                    {homeName} (LC) vs {awayName}
                                  </div>
                                </div>

                                <div className="overflow-x-auto">
                                  <table className="w-full">
                                    <thead>
                                      <tr className="border-b border-white/10">
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">Count</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{homeName} Forward Line</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2">vs {awayName} Forward Line</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {forwardMatchups.map((matchup, idx) => (
                                        <tr 
                                          key={idx}
                                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                                        >
                                          <td className="py-3 pr-3">
                                            <span className="text-xs font-military-display text-red-400 tabular-nums">
                                              {matchup.count}x
                                            </span>
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-white">
                                            {labelGroup(matchup.homeForwards)}
                                          </td>
                                          <td className="py-3 text-xs font-military-display text-gray-300">
                                            {labelGroup(matchup.awayForwards)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* Defense Pair vs Away Forwards Matchups */}
                            {defenseMatchups.length > 0 && (
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <div className="w-0.5 h-4 bg-gradient-to-b from-red-400 to-transparent" />
                                    <h5 className="text-xs font-military-display text-white uppercase tracking-widest">
                                      Defense vs Forward Matchups
                                    </h5>
                                  </div>
                                  <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                                    {homeName} D-Pair (LC) vs {awayName} Forwards
                                  </div>
                                </div>

                                <div className="overflow-x-auto">
                                  <table className="w-full">
                                    <thead>
                                      <tr className="border-b border-white/10">
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">Count</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{homeName} Defense Pair</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2">vs {awayName} Forward Line</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {defenseMatchups.map((matchup, idx) => (
                                        <tr 
                                          key={idx}
                                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                                        >
                                          <td className="py-3 pr-3">
                                            <span className="text-xs font-military-display text-red-400 tabular-nums">
                                              {matchup.count}x
                                            </span>
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-white">
                                            {labelGroup(matchup.homeDefense)}
                                          </td>
                                          <td className="py-3 text-xs font-military-display text-gray-300">
                                            {labelGroup(matchup.awayForwards)}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* Period Starters */}
                            {periodOpeners.length > 0 && (
                              <div className="space-y-3">
                                <div className="flex items-center space-x-2">
                                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                                  <h5 className="text-xs font-military-display text-white uppercase tracking-widest">
                                    Period Starters
                                  </h5>
                                </div>

                                <div className="overflow-x-auto">
                                  <table className="w-full">
                                    <thead>
                                      <tr className="border-b border-white/10">
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">Period</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{awayName} Forwards</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{awayName} Defense</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{homeName} Forwards (LC)</th>
                                        <th className="text-left text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2 pr-3">{homeName} Defense (LC)</th>
                                        <th className="text-center text-[9px] font-military-display text-gray-500 uppercase tracking-wider pb-2">Str</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {periodOpeners.map((d, i) => (
                                        <tr 
                                          key={`po-${i}`}
                                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                                        >
                                          <td className="py-3 pr-3 text-xs font-military-display text-gray-400">
                                            P{d.period}
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-gray-300">
                                            {labelGroup(d.away_forwards)}
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-gray-500">
                                            {labelGroup(d.away_defense)}
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-white">
                                            {labelGroup(d.home_forwards)}
                                          </td>
                                          <td className="py-3 pr-3 text-xs font-military-display text-gray-400">
                                            {labelGroup(d.home_defense)}
                                          </td>
                                          <td className="py-3 text-center text-xs font-military-display text-blue-400">
                                            {d.strength}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}
                          </>
                )}
              </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>

      <div className="mt-6 pt-4 border-t border-white/5">
          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
          Season {seasonLabel || '—'} Game Logs
        </div>
      </div>
    </div>
  )
}
