'use client'

import { useState, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'

type MetricType = 'points' | 'goals' | 'assists' | 'plusMinus'

interface SeasonData {
  season: number
  leagueAbbrev: string
  gameTypeId: number
  gamesPlayed: number
  goals: number
  assists: number
  points: number
  plusMinus: number
  pim: number
  shots?: number
  shootingPctg?: number
  powerPlayGoals?: number
  powerPlayPoints?: number
  shorthandedGoals?: number
  avgToi?: string
  teamAbbrev?: string
}

interface PlayerProductionChartProps {
  seasonTotals: SeasonData[]
  last5Games?: Array<{
    gameId: number
    gameDate: string
    opponentAbbrev: string
    homeRoadFlag: string
    goals: number
    assists: number
    points: number
    plusMinus: number
    shots: number
    pim: number
    toi: string
  }>
}

export function PlayerProductionChart({ seasonTotals, last5Games }: PlayerProductionChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('points')
  const [selectedSeasonIndex, setSelectedSeasonIndex] = useState(0)

  const metrics = [
    { id: 'points' as MetricType, label: 'Points', color: '#3b82f6' },
    { id: 'goals' as MetricType, label: 'Goals', color: '#22c55e' },
    { id: 'assists' as MetricType, label: 'Assists', color: '#a855f7' },
    { id: 'plusMinus' as MetricType, label: '+/-', color: '#f59e0b' },
  ]

  const formatSeason = (season: number) => {
    const yearStart = Math.floor(season / 10000)
    const yearEnd = yearStart + 1
    return `${yearStart.toString().slice(-2)}-${yearEnd.toString().slice(-2)}`
  }

  // Get available seasons (sorted newest first)
  const availableSeasons = useMemo(() => {
    return [...seasonTotals]
      .sort((a, b) => b.season - a.season)
      .map((s, idx) => ({
        season: s.season,
        label: formatSeason(s.season),
        index: idx,
      }))
  }, [seasonTotals])

  const selectedSeason = availableSeasons[selectedSeasonIndex]?.season || seasonTotals[0]?.season
  const selectedSeasonData = seasonTotals.find((s) => s.season === selectedSeason)

  // For now, we'll simulate monthly progression
  // TODO: Replace with actual game-by-game data aggregated by month
  const chartData = useMemo(() => {
    if (!selectedSeasonData) return []
    
    const months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr']
    const gamesPerMonth = Math.ceil(selectedSeasonData.gamesPlayed / 7)
    
    return months.map((month, idx) => {
      const progress = (idx + 1) / months.length
      return {
        month,
        points: Math.round(selectedSeasonData.points * progress),
        goals: Math.round(selectedSeasonData.goals * progress),
        assists: Math.round(selectedSeasonData.assists * progress),
        plusMinus: Math.round(selectedSeasonData.plusMinus * progress),
      }
    })
  }, [selectedSeasonData])

  const selectedMetricData = metrics.find((m) => m.id === selectedMetric)
  
  // Calculate current value and change
  const currentValue = chartData.length > 0 ? chartData[chartData.length - 1][selectedMetric] : 0
  const startValue = chartData.length > 0 ? chartData[0][selectedMetric] : 0
  const change = currentValue - startValue
  const changePercent = startValue !== 0 ? ((change / Math.abs(startValue)) * 100).toFixed(2) : '0.00'

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 shadow-xl">
          <div className="text-xs font-military-display text-gray-400 mb-2">
            {data.month}
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between space-x-4">
              <span className="text-xs font-military-display text-gray-500">
                {selectedMetricData?.label}
              </span>
              <span className="text-sm font-military-display text-white tabular-nums">
                {data[selectedMetric]}
              </span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="relative overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        {/* Header with Season Selector */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Season Production
            </h3>
          </div>

          {/* Value and Change Display */}
          <div className="flex items-center space-x-2 text-sm font-military-display">
            <span className="text-white tabular-nums">
              {currentValue}
            </span>
            <span className={`tabular-nums ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {change >= 0 ? '+' : ''}{change} {change >= 0 ? '↗' : '↘'} {Math.abs(parseFloat(changePercent))}%
            </span>
          </div>
        </div>

        {/* Season Selector Buttons - Perplexity style */}
        <div className="flex items-center space-x-2 mb-4">
          <div className="flex space-x-1 bg-black/40 rounded-lg p-1 border border-white/5">
            {availableSeasons.slice(0, 6).map((seasonOption) => (
              <button
                key={seasonOption.season}
                onClick={() => setSelectedSeasonIndex(seasonOption.index)}
                className={`px-3 py-1 text-xs font-military-display transition-all duration-200 rounded ${
                  selectedSeasonIndex === seasonOption.index
                    ? 'bg-white/10 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {seasonOption.label}
              </button>
            ))}
          </div>

          {/* Metric Selector */}
          <div className="flex space-x-1 bg-black/40 rounded-lg p-1 border border-white/5">
            {metrics.map((metric) => (
              <button
                key={metric.id}
                onClick={() => setSelectedMetric(metric.id)}
                className={`px-3 py-1 text-xs font-military-display transition-all duration-200 rounded ${
                  selectedMetric === metric.id
                    ? 'bg-white/10 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={selectedMetricData?.color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={selectedMetricData?.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} vertical={false} />
              <XAxis
                dataKey="month"
                stroke="#6b7280"
                style={{
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}
                tick={{ fill: '#6b7280' }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
              />
              <YAxis
                stroke="#6b7280"
                style={{
                  fontSize: '11px',
                  fontFamily: 'monospace',
                }}
                tick={{ fill: '#6b7280' }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '3 3' }} />
              <Area
                type="monotone"
                dataKey={selectedMetric}
                stroke={selectedMetricData?.color}
                strokeWidth={2}
                fill={`url(#gradient-${selectedMetric})`}
                dot={false}
                activeDot={{
                  r: 4,
                  fill: selectedMetricData?.color,
                  stroke: '#fff',
                  strokeWidth: 2,
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Season Stats Summary */}
        {selectedSeasonData && (
          <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between text-xs font-military-display">
            <div className="flex items-center space-x-6">
              <div>
                <span className="text-gray-500">Season Total: </span>
                <span className="text-white tabular-nums">{selectedSeasonData[selectedMetric]}</span>
              </div>
              <div>
                <span className="text-gray-500">GP: </span>
                <span className="text-white tabular-nums">{selectedSeasonData.gamesPlayed}</span>
              </div>
              <div>
                <span className="text-gray-500">Avg/Game: </span>
                <span className="text-white tabular-nums">
                  {(selectedSeasonData[selectedMetric] / selectedSeasonData.gamesPlayed).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

