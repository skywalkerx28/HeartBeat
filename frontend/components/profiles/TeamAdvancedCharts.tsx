'use client'

import { useMemo, useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart, ComposedChart, Legend } from 'recharts'
import { ChevronDownIcon } from '@heroicons/react/24/outline'
import type { TeamAdvancedMetrics, TeamAdvancedGame } from '../../lib/profileApi'
import { getTeamAdvancedMetrics } from '../../lib/profileApi'

interface TeamAdvancedChartsProps {
  data: TeamAdvancedMetrics
  teamId: string
}

type MetricKey = 
  | 'cf_pct' 
  | 'oz_share' 
  | 'possession_share' 
  | 'entry_ctrl_rate' 
  | 'shots_differential'
  | 'passes'
  | 'lpr_recoveries'
  | 'pressure_events'
  | 'turnovers'

interface Metric {
  id: MetricKey
  label: string
  shortLabel: string
  unit: '%' | 'count' | 'differential'
  description: string
  isPercentage: boolean
  isDifferential?: boolean
}

const METRICS: Metric[] = [
  { 
    id: 'cf_pct', 
    label: 'Corsi For %', 
    shortLabel: 'CF%',
    unit: '%',
    description: 'Shot attempts differential (Higher is better)',
    isPercentage: true 
  },
  { 
    id: 'oz_share', 
    label: 'Offensive Zone Share', 
    shortLabel: 'OZ%',
    unit: '%',
    description: 'Time spent in offensive zone vs defensive zone',
    isPercentage: true 
  },
  { 
    id: 'possession_share', 
    label: 'Possession Share', 
    shortLabel: 'POSS%',
    unit: '%',
    description: 'Team puck possession time percentage',
    isPercentage: true 
  },
  { 
    id: 'entry_ctrl_rate', 
    label: 'Entry Control Rate', 
    shortLabel: 'ENTRY%',
    unit: '%',
    description: 'Controlled zone entries success rate',
    isPercentage: true 
  },
  { 
    id: 'shots_differential', 
    label: 'Shots Differential', 
    shortLabel: 'SHOT +/-',
    unit: 'differential',
    description: 'Shots for minus shots against',
    isPercentage: false,
    isDifferential: true
  },
  { 
    id: 'passes', 
    label: 'Passes', 
    shortLabel: 'PASS',
    unit: 'count',
    description: 'Total successful passes per game',
    isPercentage: false 
  },
  { 
    id: 'lpr_recoveries', 
    label: 'LPR Recoveries', 
    shortLabel: 'LPR',
    unit: 'count',
    description: 'Loose puck recoveries per game',
    isPercentage: false 
  },
  { 
    id: 'pressure_events', 
    label: 'Pressure Events', 
    shortLabel: 'PRESS',
    unit: 'count',
    description: 'Forechecking pressure events per game',
    isPercentage: false 
  },
  { 
    id: 'turnovers', 
    label: 'Turnovers', 
    shortLabel: 'TO',
    unit: 'count',
    description: 'Turnovers per game (Lower is better)',
    isPercentage: false 
  },
]

export function TeamAdvancedCharts({ data: initialData, teamId }: TeamAdvancedChartsProps) {
  const [data, setData] = useState<TeamAdvancedMetrics>(initialData)
  const [metric, setMetric] = useState<MetricKey>('cf_pct')
  const [strength, setStrength] = useState<string>('ALL')
  const [season, setSeason] = useState<string>(initialData.season)
  const [metricDropdownOpen, setMetricDropdownOpen] = useState(false)
  const [strengthDropdownOpen, setStrengthDropdownOpen] = useState(false)
  const [seasonDropdownOpen, setSeasonDropdownOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Available seasons (hardcoded for now, could be dynamic)
  const availableSeasons = [
    { id: '20252026', label: '2025-26' },
    { id: '20242025', label: '2024-25' },
  ]

  // Fetch data when season changes
  useEffect(() => {
    if (season === initialData.season) {
      setData(initialData)
      return
    }

    const fetchSeasonData = async () => {
      setLoading(true)
      try {
        const seasonData = await getTeamAdvancedMetrics(teamId, { season })
        if (seasonData) {
          setData(seasonData)
        }
      } catch (error) {
        console.error('Error fetching season data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchSeasonData()
  }, [season, teamId, initialData])

  // Gather available strength keys from games
  const strengthKeys = useMemo(() => {
    const keys = new Set<string>()
    data.games?.forEach((g) => {
      Object.keys(g.strength_splits || {}).forEach((k) => keys.add(k))
    })
    const arr = Array.from(keys)
    arr.sort()
    return ['ALL', ...arr]
  }, [data])

  const selectedMetricData = METRICS.find(m => m.id === metric)

  // Extract value from game based on selected metric and strength
  const extractMetricValue = (game: TeamAdvancedGame, metricId: MetricKey, strengthFilter: string): number | null => {
    let value: number | null = null

    if (strengthFilter === 'ALL') {
      const d = game.derived || {}
      
      switch (metricId) {
        case 'cf_pct':
          value = d.corsi_for_pct ?? null
          break
        case 'oz_share':
          value = d.offensive_zone_share ?? null
          break
        case 'possession_share':
          value = d.possession_share ?? null
          break
        case 'entry_ctrl_rate':
          value = d.entry_controlled_success_rate ?? null
          break
        case 'shots_differential':
          const sf = game.shots_for?.total ?? 0
          const sa = game.shots_against_total ?? 0
          value = sf - sa
          break
        case 'passes':
          value = game.passes ?? null
          break
        case 'lpr_recoveries':
          value = game.lpr_recoveries ?? null
          break
        case 'pressure_events':
          value = game.pressure_events ?? null
          break
        case 'turnovers':
          value = game.turnovers ?? null
          break
      }
    } else {
      const s = (game.strength_splits || {})[strengthFilter] || {}
      
      switch (metricId) {
        case 'cf_pct':
          value = s.cf_pct ?? null
          break
        case 'oz_share':
          value = s.oz_share ?? null
          break
        case 'entry_ctrl_rate':
          value = s.entry_ctrl_rate ?? null
          break
        case 'possession_share':
        case 'shots_differential':
        case 'passes':
        case 'lpr_recoveries':
        case 'pressure_events':
        case 'turnovers':
          // Not available at strength split level, return null
          value = null
          break
      }
    }

    // Convert 0-1 ranges to percentages where applicable
    if (value !== null && selectedMetricData?.isPercentage && value <= 1) {
      value = value * 100
    }

    return value
  }

  // Extract opponent value for the same metric
  const extractOpponentMetricValue = (game: TeamAdvancedGame, metricId: MetricKey, strengthFilter: string): number | null => {
    let value: number | null = null

    if (strengthFilter === 'ALL') {
      const d = game.derived || {}

      switch (metricId) {
        case 'cf_pct': {
          const cfPct = d.corsi_for_pct
          if (cfPct == null) {
            const cf = d.corsi_for ?? game.shots_for?.total ?? 0
            const ca = d.corsi_against ?? game.shots_against_total ?? 0
            const total = (cf ?? 0) + (ca ?? 0)
            value = total > 0 ? ((ca ?? 0) / total) * 100 : null
          } else {
            value = cfPct <= 1 ? (1 - cfPct) * 100 : 100 - cfPct
          }
          break
        }
        case 'oz_share':
          // Opponent OZ share equals our DZ share
          value = d.defensive_zone_share ?? null
          if (value !== null && value <= 1) value = value * 100
          break
        case 'possession_share': {
          const ps = d.possession_share
          if (ps == null) value = null
          else value = ps <= 1 ? (1 - ps) * 100 : 100 - ps
          break
        }
        case 'entry_ctrl_rate':
          // Not available from single-team perspective without fetching opponent file
          value = null
          break
        case 'shots_differential': {
          const sf = game.shots_for?.total ?? 0
          const sa = game.shots_against_total ?? 0
          value = sa - sf
          break
        }
        case 'passes':
          value = (game as any).opponent_passes ?? null
          break
        case 'lpr_recoveries':
          value = (game as any).opponent_lpr_recoveries ?? null
          break
        case 'pressure_events':
          value = (game as any).opponent_pressure_events ?? null
          break
        case 'turnovers':
          value = (game as any).opponent_turnovers ?? null
          break
      }
    } else {
      // For strength filters, only CF% can be derived easily; others are team-only
      const s = (game.strength_splits || {})[strengthFilter] || {}
      switch (metricId) {
        case 'cf_pct': {
          const v = s.cf_pct
          value = v == null ? null : (v <= 1 ? (1 - v) * 100 : 100 - v)
          break
        }
        default:
          value = null
      }
    }

    return value
  }

  // Prepare chart data
  const chartData = useMemo(() => {
    const games: TeamAdvancedGame[] = data.games || []
    
    return games.map((g, idx) => {
      const label = (() => {
        if (g.gameDate) {
          try {
            const d = new Date(g.gameDate)
            return `${d.toLocaleString('en-US', { month: 'short' })} ${d.getDate()}`
          } catch {
            return g.gameDate
          }
        }
        return `G${idx + 1}`
      })()

      const value = extractMetricValue(g, metric, strength)
      const valueOpp = extractOpponentMetricValue(g, metric, strength)
      
      return { 
        idx: idx + 1, 
        label, 
        value,
        valueOpp,
        opponent: g.opponent || '?',
        homeAway: g.homeAway || 'home',
        gameDate: g.gameDate,
        gf: typeof (g as any).goals_for === 'number' ? (g as any).goals_for : undefined,
        ga: typeof (g as any).goals_against === 'number' ? (g as any).goals_against : undefined,
      }
    })
  }, [data.games, metric, strength, selectedMetricData])

  // Calculate statistics
  const stats = useMemo(() => {
    const validValues = chartData.filter(d => d.value !== null).map(d => d.value as number)
    
    if (validValues.length === 0) {
      return {
        average: null,
        best: null,
        worst: null,
        trend: null,
      }
    }

    const sum = validValues.reduce((acc, v) => acc + v, 0)
    const average = sum / validValues.length
    const best = Math.max(...validValues)
    const worst = Math.min(...validValues)

    // Calculate trend (last 5 games vs first 5 games)
    const firstFive = validValues.slice(0, Math.min(5, validValues.length))
    const lastFive = validValues.slice(-Math.min(5, validValues.length))
    const firstAvg = firstFive.reduce((a, b) => a + b, 0) / firstFive.length
    const lastAvg = lastFive.reduce((a, b) => a + b, 0) / lastFive.length
    const trend = lastAvg - firstAvg

    return { average, best, worst, trend }
  }, [chartData])

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setMetricDropdownOpen(false)
        setStrengthDropdownOpen(false)
        setSeasonDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const formatValue = (value: number | null): string => {
    if (value === null) return 'N/A'
    if (selectedMetricData?.unit === '%') {
      return `${value.toFixed(1)}%`
    }
    if (selectedMetricData?.isDifferential) {
      return value >= 0 ? `+${value.toFixed(0)}` : value.toFixed(0)
    }
    return value.toFixed(1)
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null
    
    const data = payload[0].payload
    const value = data.value
    const valueOpp = data.valueOpp
    const gf = data.gf as number | undefined
    const ga = data.ga as number | undefined
    
    if (value === null && valueOpp === null) return null

    return (
      <div className="bg-gray-900/95 backdrop-blur-sm border border-gray-800 rounded-lg p-3 shadow-xl">
        <div className="text-xs font-military-display text-gray-400 mb-2">
          {data.label}
          {data.opponent && (
            <span className="ml-2">
              vs {data.opponent} ({data.homeAway === 'home' ? 'HOME' : 'AWAY'})
            </span>
          )}
        </div>
        <div className="space-y-1">
          {gf != null && ga != null && (
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-gray-500">Score</span>
              <span className={`text-xs font-military-display tabular-nums ${gf > ga ? 'text-green-400' : gf < ga ? 'text-red-400' : 'text-gray-300'}`}>
                {teamId.toUpperCase()} {gf}-{ga} {data.opponent}
              </span>
            </div>
          )}
          {value !== null && (
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-gray-500">{selectedMetricData?.label}</span>
              <span className="text-sm font-military-display text-white tabular-nums font-bold">{formatValue(value)}</span>
            </div>
          )}
          {valueOpp !== null && (
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-red-400">Opponent</span>
              <span className="text-sm font-military-display text-red-400 tabular-nums font-bold">{formatValue(valueOpp)}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Determine if we should show area or line chart
  const isPercentageMetric = selectedMetricData?.isPercentage || false
  const isDifferentialMetric = selectedMetricData?.isDifferential || false

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-lg"
      ref={dropdownRef}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Advanced Performance (Season {data.season.slice(0,4)}-{data.season.slice(4,8)})
            </h3>
          </div>
        </div>

        {/* Metric Description */}
        {selectedMetricData && (
          <div className="text-xs font-military-display text-gray-500">
            {selectedMetricData.description}
          </div>
        )}

        {/* Controls Row */}
        <div className="flex items-start space-x-3">
          {/* Season Selector Dropdown */}
          <div className="relative flex-1">
            <button
              onClick={() => {
                setSeasonDropdownOpen(!seasonDropdownOpen)
                setStrengthDropdownOpen(false)
                setMetricDropdownOpen(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500 uppercase tracking-wider">SEASON:</span>
                <span className="text-white">
                  {availableSeasons.find(s => s.id === season)?.label || season}
                </span>
              </div>
              <ChevronDownIcon className={`w-3.5 h-3.5 transition-transform ${seasonDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {seasonDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
                >
                  {availableSeasons.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => {
                        setSeason(s.id)
                        setSeasonDropdownOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                        season === s.id
                          ? 'bg-white/5 text-white' 
                          : 'text-gray-400 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span className="uppercase tracking-wider">{s.label}</span>
                      {season === s.id && (
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                      )}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Strength Filter Dropdown */}
          <div className="relative flex-1">
            <button
              onClick={() => {
                setStrengthDropdownOpen(!strengthDropdownOpen)
                setMetricDropdownOpen(false)
                setSeasonDropdownOpen(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500 uppercase tracking-wider">SITUATION:</span>
                <span className="text-white">{strength}</span>
              </div>
              <ChevronDownIcon className={`w-3.5 h-3.5 transition-transform ${strengthDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {strengthDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto"
            >
              {strengthKeys.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setStrength(s)
                        setStrengthDropdownOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                        strength === s
                          ? 'bg-white/5 text-white' 
                          : 'text-gray-400 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span className="uppercase tracking-wider">{s}</span>
                      {strength === s && (
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                      )}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Metric Selector Dropdown */}
          <div className="relative flex-1">
            <button
              onClick={() => {
                setMetricDropdownOpen(!metricDropdownOpen)
                setStrengthDropdownOpen(false)
                setSeasonDropdownOpen(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500 uppercase tracking-wider">METRIC:</span>
                <span className="text-white truncate">{selectedMetricData?.label}</span>
              </div>
              <ChevronDownIcon className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${metricDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {metricDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
            >
              {METRICS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setMetric(m.id)
                        setMetricDropdownOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                        metric === m.id
                          ? 'bg-white/5 text-white' 
                          : 'text-gray-400 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span className="text-left">{m.label}</span>
                      <span className="text-gray-600 text-xs ml-2">{m.shortLabel}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="h-80 flex items-center justify-center">
            <div className="text-gray-500 text-xs font-military-display">LOADING SEASON DATA...</div>
          </div>
        )}

        {/* Chart */}
        {!loading && (
        <div className="h-80 -mr-2">
          <ResponsiveContainer width="100%" height="100%">
            {isPercentageMetric || isDifferentialMetric ? (
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <defs>
                  <linearGradient id="metricGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#60A5FA" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} vertical={false} />
                <XAxis 
                  dataKey="label" 
                  stroke="#6b7280"
                  style={{ fontSize: '10px', fontFamily: 'monospace' }}
                  tick={{ fill: '#6b7280' }} 
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                  interval={Math.floor((chartData?.length || 30) / 8)} 
                  height={40}
                />
                <YAxis 
                  stroke="#6b7280"
                  style={{ fontSize: '11px', fontFamily: 'monospace' }}
                  tick={{ fill: '#6b7280' }} 
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                  domain={isPercentageMetric ? [0, 100] : ['auto', 'auto']}
                  unit={selectedMetricData?.unit === '%' ? '%' : ''}
                  width={50}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '3 3' }} />
                {/* Opponent overlay line */}
                <Line 
                  type="monotone" 
                  dataKey="valueOpp" 
                  name="Opponent" 
                  stroke="#EF4444" 
                  strokeWidth={1.8}
                  dot={false}
                  isAnimationActive={false}
                />
                {/* Add reference line at 50% for percentage metrics */}
                {isPercentageMetric && (
                  <Line 
                    type="monotone" 
                    dataKey={() => 50} 
                    stroke="#6b7280" 
                    strokeWidth={1} 
                    strokeDasharray="5 5" 
                    dot={false}
                  />
                )}
                {/* Add reference line at 0 for differential metrics */}
                {isDifferentialMetric && (
                  <Line 
                    type="monotone" 
                    dataKey={() => 0} 
                    stroke="#6b7280" 
                    strokeWidth={1} 
                    strokeDasharray="5 5" 
                    dot={false}
                  />
                )}
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  fill="url(#metricGradient)" 
                  stroke="#60A5FA" 
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#60A5FA', stroke: '#fff', strokeWidth: 2 }}
                  isAnimationActive={false}
                />
              </ComposedChart>
            ) : (
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} vertical={false} />
                <XAxis 
                  dataKey="label" 
                  stroke="#6b7280"
                  style={{ fontSize: '10px', fontFamily: 'monospace' }}
                  tick={{ fill: '#6b7280' }} 
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                  interval={Math.floor((chartData?.length || 30) / 8)}
                  height={40}
                />
                <YAxis 
                  stroke="#6b7280"
                  style={{ fontSize: '11px', fontFamily: 'monospace' }}
                  tick={{ fill: '#6b7280' }} 
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                  width={50}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '3 3' }} />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  name={selectedMetricData?.label} 
                  stroke="#60A5FA" 
                  strokeWidth={2} 
                  dot={false} 
                  activeDot={{ r: 4, fill: '#60A5FA', stroke: '#fff', strokeWidth: 2 }}
                  isAnimationActive={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="valueOpp" 
                  name="Opponent" 
                  stroke="#EF4444" 
                  strokeWidth={1.8} 
                  dot={false} 
                  isAnimationActive={false}
                />
            </LineChart>
            )}
          </ResponsiveContainer>
        </div>
        )}

        {/* Stats Footer */}
        {!loading && (
        <div className="pt-4 border-t border-white/10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.average !== null && (
              <div>
                <div className="text-xs font-military-display text-gray-500 mb-1">AVERAGE</div>
                <div className="text-sm font-military-display text-white tabular-nums font-bold">
                  {formatValue(stats.average)}
                </div>
              </div>
            )}
            {stats.best !== null && (
              <div>
                <div className="text-xs font-military-display text-gray-500 mb-1">BEST</div>
                <div className="text-sm font-military-display text-green-400 tabular-nums font-bold">
                  {formatValue(stats.best)}
                </div>
              </div>
            )}
            {stats.worst !== null && (
              <div>
                <div className="text-xs font-military-display text-gray-500 mb-1">WORST</div>
                <div className="text-sm font-military-display text-red-400 tabular-nums font-bold">
                  {formatValue(stats.worst)}
                </div>
              </div>
            )}
            {stats.trend !== null && (
              <div>
                <div className="text-xs font-military-display text-gray-500 mb-1">TREND (L5 vs F5)</div>
                <div className={`text-sm font-military-display tabular-nums font-bold ${
                  stats.trend > 0 ? 'text-green-400' : stats.trend < 0 ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {stats.trend >= 0 ? '+' : ''}{formatValue(stats.trend)}
                </div>
              </div>
            )}
          </div>
        </div>
        )}
      </div>
    </motion.div>
  )
}
