'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { API_BASE_URL } from '@/lib/api'

type MetricType = 
  | 'points' | 'goals' | 'assists' | 'plusMinus'
  | 'powerPlayGoals' | 'powerPlayPoints' 
  | 'gameWinningGoals' | 'otGoals'
  | 'shots' | 'avgShifts'
  | 'shorthandedGoals' | 'shorthandedPoints'
  | 'pim' | 'avgToi'
  | 'salaryAccrued'

interface SeasonData {
  season: number
  gamesPlayed: number
  [key: string]: any
}

interface CumulativeGameData {
  gameId: number
  gameDate: string
  opponent: string
  homeRoadFlag: string
  gamesPlayed: number
  
  assists: number
  goals: number
  points: number
  plusMinus: number
  powerPlayGoals: number
  powerPlayPoints: number
  gameWinningGoals: number
  otGoals: number
  shots: number
  shifts: number
  shorthandedGoals: number
  shorthandedPoints: number
  pim: number
  
  avgToi: number
  avgShots: number
  avgShifts: number
  
  gameStats: {
    assists: number
    goals: number
    points: number
    shots: number
    toi: string
    plusMinus: number
  }
  [key: string]: any
}

interface CumulativeSeasonData {
  playerId: string
  season: string
  gameType: string
  games: CumulativeGameData[]
}

interface PlayerProductionChartProps {
  playerId: string | number
  seasonTotals: SeasonData[]
}

// Professional color palette for season overlays (Bloomberg-style)
const SEASON_COLORS = [
  '#3b82f6', // Blue
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#a855f7', // Purple
  '#ec4899', // Pink
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#8b5cf6', // Violet
  '#14b8a6', // Teal
  '#f43f5e', // Rose
  '#84cc16', // Lime
  '#6366f1', // Indigo
]

export function PlayerProductionChart({ playerId, seasonTotals }: PlayerProductionChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('points')
  const [selectedSeasons, setSelectedSeasons] = useState<number[]>([]) // Multi-select
  const [seasonDropdownOpen, setSeasonDropdownOpen] = useState(false)
  const [metricDropdownOpen, setMetricDropdownOpen] = useState(false)
  const [cumulativeDataMap, setCumulativeDataMap] = useState<Map<number, CumulativeSeasonData>>(new Map())
  const [loading, setLoading] = useState(true)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [forecast, setForecast] = useState<{
    steps: number[]
    p10: number[]
    p50: number[]
    p90: number[]
    currentTotal: number
  } | null>(null)
  
  // Auto-detect comparison mode based on number of selected seasons
  const comparisonMode = selectedSeasons.length > 1

  const metrics = [
    { id: 'points' as MetricType, label: 'Points', shortLabel: 'PTS' },
    { id: 'goals' as MetricType, label: 'Goals', shortLabel: 'G' },
    { id: 'assists' as MetricType, label: 'Assists', shortLabel: 'A' },
    { id: 'plusMinus' as MetricType, label: 'Plus/Minus', shortLabel: '+/-' },
    { id: 'powerPlayGoals' as MetricType, label: 'PP Goals', shortLabel: 'PPG' },
    { id: 'powerPlayPoints' as MetricType, label: 'PP Points', shortLabel: 'PPP' },
    { id: 'gameWinningGoals' as MetricType, label: 'GW Goals', shortLabel: 'GWG' },
    { id: 'otGoals' as MetricType, label: 'OT Goals', shortLabel: 'OTG' },
    { id: 'shots' as MetricType, label: 'Shots', shortLabel: 'SOG' },
    { id: 'avgShifts' as MetricType, label: 'Shifts/Game', shortLabel: 'SFT/G' },
    { id: 'shorthandedGoals' as MetricType, label: 'SH Goals', shortLabel: 'SHG' },
    { id: 'shorthandedPoints' as MetricType, label: 'SH Points', shortLabel: 'SHP' },
    { id: 'pim' as MetricType, label: 'Penalties', shortLabel: 'PIM' },
    { id: 'avgToi' as MetricType, label: 'TOI/Game', shortLabel: 'TOI/G' },
    { id: 'salaryAccrued' as MetricType, label: 'Salary Accrued', shortLabel: 'SAL' },
  ]

  const formatSeason = (season: number) => {
    const seasonStr = season.toString()
    const yearStart = seasonStr.slice(0, 4)
    const yearEnd = seasonStr.slice(4, 8)
    return `${yearStart}-${yearEnd.slice(-2)}`
  }

  // De-duplicate and sort available seasons
  const availableSeasons = useMemo(() => {
    const bySeason = new Map<number, SeasonData>()
    for (const s of seasonTotals || []) {
      if (!s || typeof s.season !== 'number') continue
      if (s.season < 20032004 || (s.gamesPlayed ?? 0) <= 0) continue
      const existing = bySeason.get(s.season)
      if (!existing || (s.gamesPlayed ?? 0) > (existing.gamesPlayed ?? 0)) {
        bySeason.set(s.season, s)
      }
    }

    return Array.from(bySeason.values())
      .sort((a, b) => b.season - a.season)
      .map((s, idx) => ({
        season: s.season,
        label: formatSeason(s.season),
        gamesPlayed: s.gamesPlayed,
        index: idx,
      }))
  }, [seasonTotals])

  // Initialize with most recent season
  useEffect(() => {
    if (availableSeasons.length > 0 && selectedSeasons.length === 0) {
      setSelectedSeasons([availableSeasons[0].season])
    }
  }, [availableSeasons])

  // Fetch cumulative data for selected seasons
  useEffect(() => {
    if (!playerId || selectedSeasons.length === 0) return

    const fetchMultipleSeasons = async () => {
      setLoading(true)
      const newDataMap = new Map(cumulativeDataMap)
      
      for (const season of selectedSeasons) {
        // Skip if already loaded
        if (newDataMap.has(season)) continue
        
        try {
          const seasonStr = season.toString()
          if (selectedMetric === 'salaryAccrued') {
            const dashed = `${seasonStr.slice(0,4)}-${seasonStr.slice(4,8)}`
            const response = await fetch(`${API_BASE_URL}/api/v1/market/salary/progression/${playerId}?season=${encodeURIComponent(dashed)}`)
            if (response.ok) {
              const data = await response.json()
              if (data && Array.isArray(data.games) && data.games.length > 0) {
                newDataMap.set(season, data)
              }
            }
          } else {
            const response = await fetch(`${API_BASE_URL}/api/nhl/player/${playerId}/cumulative/${seasonStr}/regular`)
            if (response.ok) {
              const data = await response.json()
              if (data && Array.isArray(data.games) && data.games.length > 0) {
                newDataMap.set(season, data)
              }
            }
          }
        } catch (error) {
          console.error(`Error loading ${season}:`, error)
        }
      }
      
      setCumulativeDataMap(newDataMap)
      setLoading(false)
    }

    fetchMultipleSeasons()
  }, [selectedSeasons, playerId, selectedMetric])

  // Reset cached season data when switching metric family (ensures correct fields)
  useEffect(() => {
    setCumulativeDataMap(new Map())
  }, [selectedMetric])

  // Toggle season selection (always multi-select enabled)
  const toggleSeason = (season: number) => {
    if (selectedSeasons.includes(season)) {
      // Deselect - keep at least one season selected
      if (selectedSeasons.length > 1) {
        setSelectedSeasons(selectedSeasons.filter(s => s !== season))
      }
    } else {
      // Select - add to list
      setSelectedSeasons([...selectedSeasons, season])
    }
  }

  // Prepare chart data (merge all selected seasons)
  const chartData = useMemo(() => {
    if (selectedSeasons.length === 0 || cumulativeDataMap.size === 0) return []

    if (comparisonMode) {
      // Multi-season overlay: normalize to game number (1-82)
      const maxGames = 82
      const normalized: any[] = []
      
      for (let gameNum = 1; gameNum <= maxGames; gameNum++) {
        const point: any = { gameNumber: gameNum }
        
        selectedSeasons.forEach((season) => {
          const data = cumulativeDataMap.get(season)
          if (data && data.games[gameNum - 1]) {
            const game = data.games[gameNum - 1]
            point[`season_${season}`] = game[selectedMetric] || 0
          }
        })
        
        normalized.push(point)
      }
      
      return normalized
    } else {
      // Single season: use actual dates
      const season = selectedSeasons[0]
      const data = cumulativeDataMap.get(season)
      
      if (!data || !data.games) return []
      
      return data.games.map((game) => {
        const date = new Date(game.gameDate)
        const month = date.toLocaleString('en-US', { month: 'short' })
        const day = date.getDate()
        
        return {
          ...game,
          dateLabel: `${month} ${day}`,
          month: month,
          value: game[selectedMetric] || 0,
        }
      })
    }
  }, [selectedSeasons, cumulativeDataMap, selectedMetric, comparisonMode])

  // Fetch forecast when single season selected and metric supported
  useEffect(() => {
    const supportedMetrics: MetricType[] = ['points', 'goals', 'assists']
    if (comparisonMode || selectedSeasons.length !== 1 || !supportedMetrics.includes(selectedMetric)) {
      setForecast(null)
      return
    }
    const season = selectedSeasons[0]
    const seasonDash = `${season.toString().slice(0,4)}-${season.toString().slice(4,8)}`
    const fetchForecast = async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/predictions/player/${playerId}/${seasonDash}?metric=${selectedMetric}`)
        if (!resp.ok) {
          setForecast(null)
          return
        }
        const data = await resp.json()
        setForecast({
          steps: data.steps || [],
          p10: data.p10 || [],
          p50: data.p50 || [],
          p90: data.p90 || [],
          currentTotal: data.currentTotal ?? 0,
        })
      } catch (e) {
        console.error('Forecast fetch error', e)
        setForecast(null)
      }
    }
    fetchForecast()
  }, [comparisonMode, selectedSeasons, selectedMetric, playerId])

  // Append forecast points to chart data for single-season view
  const chartDataWithForecast = useMemo(() => {
    if (comparisonMode || selectedSeasons.length !== 1) return chartData
    if (!forecast || !chartData || chartData.length === 0) return chartData
    const extended = [...chartData]
    const lastIdx = chartData.length
    // Build synthetic future x labels as +1, +2, ... to avoid relying on schedule
    forecast.steps.forEach((step, i) => {
      const p50 = forecast.p50[i] ?? 0
      const p10 = forecast.p10[i] ?? 0
      const p90 = forecast.p90[i] ?? 0
      extended.push({
        dateLabel: `+${step}`,
        value: null,
        forecast_p50: forecast.currentTotal + p50,
        forecast_p10: forecast.currentTotal + p10,
        forecast_p90: forecast.currentTotal + p90,
      })
    })
    return extended
  }, [chartData, forecast, comparisonMode, selectedSeasons])

  const selectedMetricData = metrics.find((m) => m.id === selectedMetric)

  // Calculate stats
  const stats = useMemo(() => {
    if (selectedSeasons.length === 0 || cumulativeDataMap.size === 0) return []
    
    return selectedSeasons.map((season, idx) => {
      const data = cumulativeDataMap.get(season)
      if (!data || !data.games || data.games.length === 0) return null
      
      const lastGame = data.games[data.games.length - 1]
      const total = lastGame[selectedMetric] || 0
      const gamesPlayed = lastGame.gamesPlayed
      const perGame = gamesPlayed > 0 ? (total / gamesPlayed).toFixed(2) : '0.00'
      
      return {
        season,
        label: formatSeason(season),
        total,
        gamesPlayed,
        perGame,
        color: SEASON_COLORS[idx % SEASON_COLORS.length],
      }
    }).filter(Boolean)
  }, [selectedSeasons, cumulativeDataMap, selectedMetric])

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null
    
    const data = payload[0].payload
    
    if (comparisonMode) {
      // Multi-season tooltip
      return (
        <div className="bg-gray-900/95 backdrop-blur-sm border border-gray-800 rounded-lg p-3 shadow-xl">
          <div className="text-xs font-military-display text-gray-400 mb-2">
            Game {data.gameNumber}
          </div>
          <div className="space-y-1">
            {selectedSeasons.map((season, idx) => {
              const value = data[`season_${season}`]
              if (value === undefined) return null
              
              return (
                <div key={season} className="flex items-center justify-between space-x-4">
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-2 h-2 rounded-full" 
                      style={{ backgroundColor: SEASON_COLORS[idx % SEASON_COLORS.length] }}
                    />
                    <span className="text-xs font-military-display text-gray-400">
                      {formatSeason(season)}
                    </span>
                  </div>
                  <span className="text-sm font-military-display text-white tabular-nums">
                    {selectedMetric === 'salaryAccrued' ? `$${Math.round(value).toLocaleString()}` : value}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )
    } else {
      // Single season tooltip
      return (
        <div className="bg-gray-900/95 backdrop-blur-sm border border-gray-800 rounded-lg p-3 shadow-xl">
          <div className="text-xs font-military-display text-gray-400 mb-2">
            {data.dateLabel}
            {data.opponent ? ` vs ${data.opponent} (${data.homeRoadFlag === 'H' ? 'HOME' : 'AWAY'})` : ''}
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-gray-500">
                Cumulative {selectedMetricData?.shortLabel}
              </span>
              <span className="text-sm font-military-display text-white tabular-nums">
                {selectedMetric === 'salaryAccrued' ? `$${Math.round(data.value).toLocaleString()}` : data.value}
              </span>
            </div>
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-gray-500">
                This Game
              </span>
              <span className="text-sm font-military-display text-white tabular-nums">
                {selectedMetric === 'salaryAccrued' 
                  ? `$${Math.round((data as any).salaryPerGame || 0).toLocaleString()}`
                  : (data.gameStats?.[selectedMetric] ?? 'N/A')}
              </span>
            </div>
            <div className="flex items-center justify-between space-x-4 pt-2 border-t border-gray-800">
              <span className="text-xs font-military-display text-gray-500">
                Game {data.gamesPlayed}
              </span>
              <span className="text-xs font-military-display text-gray-400">
                {data.gameStats ? `${data.gameStats?.goals}G ${data.gameStats?.assists}A` : ''}
              </span>
            </div>
          </div>
        </div>
      )
    }
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setSeasonDropdownOpen(false)
        setMetricDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (loading && cumulativeDataMap.size === 0) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6 flex items-center justify-center h-96">
          <div className="text-gray-500 text-xs font-military-display">LOADING SEASON DATA...</div>
        </div>
      </div>
    )
  }

  if (availableSeasons.length === 0) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Season Production
            </h3>
          </div>
          <div className="flex items-center justify-center h-48 text-gray-500 text-xs font-military-display">
            NO GAME DATA AVAILABLE
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-lg" ref={dropdownRef}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        {/* Header */}
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            {comparisonMode ? 'Season Comparison' : 'Season Production'}
          </h3>
          {comparisonMode && (
            <span className="text-xs font-military-display text-gray-500">
              ({selectedSeasons.length} Seasons)
            </span>
          )}
        </div>

        {/* Controls Row */}
        <div className="flex items-start space-x-3 mb-4">
          {/* Season Selector Dropdown */}
          <div className="relative flex-1">
            <button
              onClick={() => setSeasonDropdownOpen(!seasonDropdownOpen)}
              className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500">SEASON{selectedSeasons.length > 1 ? 'S' : ''}:</span>
                <span className="text-white">
                  {selectedSeasons.length === 1 
                    ? formatSeason(selectedSeasons[0])
                    : `${selectedSeasons.length} Selected`
                  }
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
                  className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
                >
                  {availableSeasons.map((seasonOption) => {
                    const isSelected = selectedSeasons.includes(seasonOption.season)
                    const colorIdx = selectedSeasons.indexOf(seasonOption.season)
                    const color = colorIdx >= 0 ? SEASON_COLORS[colorIdx % SEASON_COLORS.length] : null
                    
                    return (
                      <button
                        key={seasonOption.season}
                        onClick={() => toggleSeason(seasonOption.season)}
                        className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                          isSelected 
                            ? 'bg-white/5 text-white' 
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div 
                            className={`w-2 h-2 rounded-full ${isSelected ? '' : 'border border-gray-700'}`}
                            style={{ backgroundColor: isSelected && color ? color : 'transparent' }}
                          />
                          <span>{seasonOption.label}</span>
                        </div>
                        <span className="text-gray-600 text-xs">{seasonOption.gamesPlayed} GP</span>
                      </button>
                    )
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Metric Selector Dropdown */}
          <div className="relative flex-1">
            <button
              onClick={() => setMetricDropdownOpen(!metricDropdownOpen)}
              className="w-full flex items-center justify-between px-3 py-2 bg-black/40 border border-white/10 rounded text-xs font-military-display text-white hover:border-white/20 transition-all"
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500">METRIC:</span>
                <span className="text-white">{selectedMetricData?.label}</span>
              </div>
              <ChevronDownIcon className={`w-3.5 h-3.5 transition-transform ${metricDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {metricDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 w-full mt-2 bg-gray-900/95 backdrop-blur-xl border border-gray-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
                >
                  {metrics.map((metric) => (
                    <button
                      key={metric.id}
                      onClick={() => {
                        setSelectedMetric(metric.id)
                        setMetricDropdownOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-xs font-military-display transition-all border-b border-gray-800/50 last:border-0 ${
                        selectedMetric === metric.id 
                          ? 'bg-white/5 text-white' 
                          : 'text-gray-400 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span>{metric.label}</span>
                      <span className="text-gray-600 text-xs">{metric.shortLabel}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Selected Seasons Pills (when comparing) */}
        {comparisonMode && selectedSeasons.length > 1 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {selectedSeasons.map((season, idx) => {
              const data = cumulativeDataMap.get(season)
              const stat = stats.find(s => s?.season === season)
              
              return (
                <motion.div
                  key={season}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="flex items-center space-x-2 px-3 py-1.5 bg-black/40 border border-white/10 rounded-full"
                >
                  <div 
                    className="w-2 h-2 rounded-full" 
                    style={{ backgroundColor: SEASON_COLORS[idx % SEASON_COLORS.length] }}
                  />
                  <span className="text-xs font-military-display text-white">
                    {formatSeason(season)}
                  </span>
                  {stat && (
                    <span className="text-xs font-military-display text-gray-500 tabular-nums">
                      {stat.total}
                    </span>
                  )}
                  {selectedSeasons.length > 1 && (
                    <button
                      onClick={() => toggleSeason(season)}
                      className="ml-1 text-gray-500 hover:text-white transition-colors"
                    >
                      <XMarkIcon className="w-3 h-3" />
                    </button>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}

        {/* Chart */}
        <div className="h-80 -mr-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartDataWithForecast} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
              <defs>
                {selectedSeasons.map((season, idx) => (
                  <linearGradient key={`gradient-${season}`} id={`gradient-${season}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={SEASON_COLORS[idx % SEASON_COLORS.length]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={SEASON_COLORS[idx % SEASON_COLORS.length]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} vertical={false} />
              <XAxis
                dataKey={comparisonMode ? "gameNumber" : "dateLabel"}
                stroke="#6b7280"
                style={{ fontSize: '10px', fontFamily: 'monospace' }}
                tick={{ fill: '#6b7280' }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
                interval={comparisonMode ? 9 : Math.floor((chartData.length || 1) / 10)}
                height={40}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: '11px', fontFamily: 'monospace' }}
                tick={{ fill: '#6b7280' }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
                tickFormatter={selectedMetric === 'salaryAccrued' ? (v: number) => `$${Math.round(v).toLocaleString()}` : undefined}
                width={40}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '3 3' }} />
              
              {comparisonMode ? (
                // Multi-season overlay
                selectedSeasons.map((season, idx) => (
                  <Line
                    key={season}
                    type="monotone"
                    dataKey={`season_${season}`}
                    stroke={SEASON_COLORS[idx % SEASON_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: SEASON_COLORS[idx % SEASON_COLORS.length], stroke: '#fff', strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                ))
              ) : (
                // Single season
                <>
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={SEASON_COLORS[0]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: SEASON_COLORS[0], stroke: '#fff', strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                  {forecast && forecast.steps.length > 0 && (
                    <>
                      {/* Forecast band */}
                      <Line
                        type="monotone"
                        dataKey="forecast_p10"
                        stroke="#6b7280"
                        strokeDasharray="3 3"
                        dot={false}
                        isAnimationActive={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="forecast_p90"
                        stroke="#6b7280"
                        strokeDasharray="3 3"
                        dot={false}
                        isAnimationActive={false}
                      />
                      {/* Forecast median */}
                      <Line
                        type="monotone"
                        dataKey="forecast_p50"
                        stroke={SEASON_COLORS[0]}
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        dot={false}
                        isAnimationActive={false}
                      />
                    </>
                  )}
                </>
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Footer */}
        <div className="mt-4 pt-4 border-t border-white/10">
          {comparisonMode ? (
            // Multi-season stats grid
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {stats.map((stat) => stat && (
                <div key={stat.season} className="flex items-center space-x-2">
                  <div 
                    className="w-2 h-2 rounded-full flex-shrink-0" 
                    style={{ backgroundColor: stat.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-military-display text-gray-500">{stat.label}</div>
                    <div className="flex items-center space-x-2 text-xs font-military-display">
                      <span className="text-white tabular-nums">
                        {selectedMetric === 'salaryAccrued' ? `$${Math.round(stat.total as number).toLocaleString()}` : stat.total}
                      </span>
                      <span className="text-gray-600">
                        ({selectedMetric === 'salaryAccrued' ? `$${Math.round(parseFloat(stat.perGame as string || '0')).toLocaleString()}` : stat.perGame}/G)
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // Single season stats
            stats[0] && (
              <div className="flex items-center justify-between text-xs font-military-display">
                <div className="flex items-center space-x-6">
                  <div>
                    <span className="text-gray-500">Season Total: </span>
                    <span className="text-white tabular-nums">{selectedMetric === 'salaryAccrued' ? `$${Math.round(stats[0].total as number).toLocaleString()}` : stats[0].total}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Games: </span>
                    <span className="text-white tabular-nums">{stats[0].gamesPlayed}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Per Game: </span>
                    <span className="text-white tabular-nums">{selectedMetric === 'salaryAccrued' ? `$${Math.round(parseFloat(stats[0].perGame as string || '0')).toLocaleString()}` : stats[0].perGame}</span>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  )
}
