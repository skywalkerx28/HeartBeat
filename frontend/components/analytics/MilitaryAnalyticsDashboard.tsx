'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChartBarIcon,
  TableCellsIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  UserGroupIcon,
  ClockIcon,
  MapIcon,
  BoltIcon,
  ShieldCheckIcon,
  SignalIcon,
  CpuChipIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline'

interface DashboardWidget {
  id: string
  type: 'metric' | 'chart' | 'table' | 'map' | 'status'
  title: string
  category: string
  value?: string | number
  trend?: 'up' | 'down' | 'stable'
  data?: any
  status?: 'online' | 'offline' | 'warning'
  size?: 'small' | 'medium' | 'large'
}

export function MilitaryAnalyticsDashboard() {
  const [currentTime, setCurrentTime] = useState('')
  const [selectedSeason, setSelectedSeason] = useState('2025-2026')
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const seasons = [
    '2025-2026',
    '2024-2025', 
    '2023-2024',
    '2022-2023',
    '2021-2022'
  ]

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }))
    }
    
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  // Close dropdown when clicking outside or pressing escape
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (dropdownOpen && !target.closest('.season-dropdown')) {
        setDropdownOpen(false)
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dropdownOpen) {
        setDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [dropdownOpen])

  const widgets: DashboardWidget[] = [
    {
      id: 'team-performance',
      type: 'metric',
      title: 'TEAM PERFORMANCE INDEX',
      category: 'TACTICAL',
      value: '94.7',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'goals-for',
      type: 'metric',
      title: 'GOALS FOR',
      category: 'OFFENSE',
      value: '187',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'goals-against',
      type: 'metric',
      title: 'GOALS AGAINST',
      category: 'DEFENSE',
      value: '142',
      trend: 'down',
      size: 'small'
    },
    {
      id: 'win-rate',
      type: 'metric',
      title: 'WIN PERCENTAGE',
      category: 'OVERALL',
      value: '67.3%',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'xgf-percentage',
      type: 'metric',
      title: 'XGF%',
      category: 'ADVANCED',
      value: '52.8%',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'corsi-for',
      type: 'metric',
      title: 'CORSI FOR %',
      category: 'POSSESSION',
      value: '51.2%',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'power-play',
      type: 'chart',
      title: 'POWER PLAY EFFICIENCY',
      category: 'SPECIAL TEAMS',
      size: 'medium',
      data: { efficiency: 24.7, opportunities: 143, goals: 35, trend: [18.2, 21.5, 24.7, 26.1, 24.7] }
    },
    {
      id: 'penalty-kill',
      type: 'chart',
      title: 'PENALTY KILL SUCCESS',
      category: 'SPECIAL TEAMS',
      size: 'medium',
      data: { efficiency: 82.4, opportunities: 98, goals_against: 17, trend: [79.1, 80.5, 82.4, 83.2, 82.4] }
    },
    {
      id: 'player-stats',
      type: 'table',
      title: 'TOP PERFORMERS',
      category: 'PERSONNEL',
      size: 'medium',
      data: [
        { player: 'C. SUZUKI', goals: 23, assists: 34, points: 57, rating: '+12', xgf: '2.1', cf: '54.2' },
        { player: 'N. CAUFIELD', goals: 28, assists: 19, points: 47, rating: '+8', xgf: '1.8', cf: '52.1' },
        { player: 'J. SLAFKOVSKY', goals: 19, assists: 26, points: 45, rating: '+6', xgf: '1.6', cf: '51.8' },
        { player: 'K. DACH', goals: 14, assists: 28, points: 42, rating: '+4', xgf: '1.4', cf: '53.2' },
        { player: 'M. MATHESON', goals: 8, assists: 32, points: 40, rating: '+15', xgf: '1.2', cf: '56.8' }
      ]
    },
    {
      id: 'goalie-stats',
      type: 'table',
      title: 'GOALTENDING METRICS',
      category: 'PERSONNEL',
      size: 'medium',
      data: [
        { goalie: 'S. MONTEMBEAULT', gp: 45, sv_pct: '.912', gaa: '2.84', gsaa: '+8.2', hdsv: '.885' },
        { goalie: 'J. PRIMEAU', gp: 25, sv_pct: '.908', gaa: '2.91', gsaa: '+3.1', hdsv: '.878' }
      ]
    },
    {
      id: 'zone-control',
      type: 'map',
      title: 'ZONE CONTROL ANALYSIS',
      category: 'TACTICAL',
      size: 'small',
      data: { offensive: 52.3, neutral: 48.7, defensive: 54.1 }
    },
    {
      id: 'line-combinations',
      type: 'chart',
      title: 'TOP LINE COMBINATIONS',
      category: 'TACTICAL',
      size: 'medium',
      data: {
        lines: [
          { line: 'SUZUKI-CAUFIELD-SLAF', toi: '18:24', xgf: '65.2%', cf: '58.1%', gf: 8, ga: 3 },
          { line: 'DACH-NEWHOOK-GALLAGHER', toi: '16:12', xgf: '48.3%', cf: '52.4%', gf: 5, ga: 6 },
          { line: 'DVORAK-ANDERSON-ARMIA', toi: '14:35', xgf: '42.1%', cf: '46.8%', gf: 3, ga: 4 }
        ]
      }
    },
    {
      id: 'shot-metrics',
      type: 'chart',
      title: 'SHOT ATTEMPT TRENDS',
      category: 'ANALYTICS',
      size: 'medium',
      data: {
        last_10: [32, 28, 35, 31, 29, 33, 36, 30, 34, 32],
        opponent_last_10: [28, 30, 26, 29, 32, 28, 25, 31, 27, 29],
        cf_percentage: [53.3, 48.3, 57.4, 51.7, 47.5, 54.1, 59.0, 49.2, 55.7, 52.5]
      }
    },
    {
      id: 'faceoff-analysis',
      type: 'metric',
      title: 'FACEOFF WIN %',
      category: 'SPECIAL',
      value: '48.2%',
      trend: 'down',
      size: 'small'
    },
    {
      id: 'hits-blocks',
      type: 'metric',
      title: 'HITS PER GAME',
      category: 'PHYSICAL',
      value: '21.4',
      trend: 'up',
      size: 'small'
    },
    {
      id: 'pdo-metric',
      type: 'metric',
      title: 'PDO',
      category: 'LUCK',
      value: '101.2',
      trend: 'stable',
      size: 'small'
    },
    {
      id: 'shot-suppression',
      type: 'metric',
      title: 'SHOTS AGAINST/60',
      category: 'DEFENSE',
      value: '28.9',
      trend: 'down',
      size: 'small'
    },
    {
      id: 'recent-form',
      type: 'chart',
      title: 'LAST 10 GAMES FORM',
      category: 'PERFORMANCE',
      size: 'medium',
      data: {
        games: ['W', 'L', 'W', 'W', 'OTL', 'W', 'L', 'W', 'W', 'L'],
        goals_for: [4, 1, 3, 5, 2, 3, 2, 4, 3, 1],
        goals_against: [2, 3, 1, 2, 3, 1, 4, 2, 1, 3]
      }
    },
    {
      id: 'system-status',
      type: 'status',
      title: 'SYSTEM STATUS',
      category: 'OPERATIONS',
      size: 'small',
      status: 'online'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      {/* Floating title */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center px-6 py-6 pointer-events-none">
        <h1 className="text-xl font-bold text-white tracking-wider text-shadow-military font-military-display">
          HEARTBEAT
        </h1>
      </div>

      {/* Command Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse" />
            
            {/* Season Selector */}
            <div className="season-dropdown">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center space-x-2 text-2xl font-military-display text-white hover:text-gray-300 transition-colors"
              >
                <span>MTL {selectedSeason}</span>
                <ChevronDownIcon className={`w-5 h-5 transition-transform duration-200 ${
                  dropdownOpen ? 'rotate-180' : ''
                }`} />
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-6 text-gray-400">
            <div className="flex items-center space-x-2">
              <ClockIcon className="w-4 h-4" />
              <span className="font-military-chat text-sm">{currentTime}</span>
            </div>
            <div className="flex items-center space-x-2">
              <MapIcon className="w-4 h-4" />
              <span className="font-military-chat text-sm">MTL-HQ</span>
            </div>
            <div className="flex items-center space-x-2">
              <SignalIcon className="w-4 h-4" />
              <span className="font-military-chat text-sm">SECURE</span>
            </div>
          </div>
        </div>

        {/* Season Selection List */}
        <AnimatePresence>
          {dropdownOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="overflow-hidden mb-4"
            >
              <div className="bg-gray-900/50 border border-gray-800 rounded-lg backdrop-blur-sm p-2">
                <div className="grid gap-1">
                  {seasons.filter(season => season !== selectedSeason).map((season) => (
                    <button
                      key={season}
                      onClick={() => {
                        setSelectedSeason(season)
                        setDropdownOpen(false)
                      }}
                      className="w-full text-left px-3 py-2 text-sm font-military-chat text-gray-300 hover:bg-gray-800 hover:text-white rounded transition-colors"
                    >
                      MTL {season}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mission Status Bar */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'DATA SOURCES', value: '14/14', status: 'online' },
            { label: 'LAST SYNC', value: '00:12', status: 'online' },
            { label: 'ALERTS', value: '0', status: 'online' },
            { label: 'CPU LOAD', value: '23%', status: 'online' }
          ].map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className="bg-gray-900/50 border border-gray-800 rounded-lg p-3 backdrop-blur-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-military-display text-gray-400">{item.label}</span>
                <div className={`w-2 h-2 rounded-full ${
                  item.status === 'online' ? 'bg-gray-400' : 'bg-red-500'
                } animate-pulse`} />
              </div>
              <div className="text-lg font-military-chat text-white mt-1">{item.value}</div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-12 gap-4">
        {widgets.map((widget, index) => (
          <motion.div
            key={widget.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
            className={`
              ${widget.size === 'small' ? 'col-span-2' : 
                widget.size === 'large' ? 'col-span-6' : 'col-span-4'}
              bg-gray-900/50 border border-gray-800 rounded-lg backdrop-blur-sm overflow-hidden
              hover:border-gray-700 transition-all duration-200
            `}
          >
            <AnalyticsWidget widget={widget} />
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function AnalyticsWidget({ widget }: { widget: DashboardWidget }) {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <ArrowTrendingUpIcon className="w-4 h-4 text-white" />
      case 'down':
        return <ArrowTrendingDownIcon className="w-4 h-4 text-red-500" />
      default:
        return <div className="w-4 h-4" />
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'chart':
        return <ChartBarIcon className="w-4 h-4 text-gray-400" />
      case 'table':
        return <TableCellsIcon className="w-4 h-4 text-gray-400" />
      case 'map':
        return <MapIcon className="w-4 h-4 text-gray-400" />
      case 'status':
        return <CpuChipIcon className="w-4 h-4 text-gray-400" />
      default:
        return <BoltIcon className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <div className="p-3 h-full flex flex-col min-h-[140px]">
      {/* Widget Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {getTypeIcon(widget.type)}
          <h3 className="text-xs font-military-display text-gray-300">
            {widget.title}
          </h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-military-display text-gray-500">
            {widget.category}
          </span>
          {widget.trend && getTrendIcon(widget.trend)}
        </div>
      </div>

      {/* Widget Content */}
      <div className="flex-1">
        {widget.type === 'metric' && (
          <MetricWidget value={widget.value!} trend={widget.trend} />
        )}
        
        {widget.type === 'chart' && (
          <ChartWidget data={widget.data} />
        )}
        
        {widget.type === 'table' && (
          <TableWidget data={widget.data} />
        )}
        
        {widget.type === 'map' && (
          <MapWidget data={widget.data} />
        )}
        
        {widget.type === 'status' && (
          <StatusWidget status={widget.status} />
        )}
      </div>
    </div>
  )
}

function MetricWidget({ value, trend }: { value: string | number, trend?: string }) {
  return (
    <div className="flex flex-col justify-center h-full text-center">
      <div className={`text-2xl font-military-chat mb-1 ${
        trend === 'up' ? 'text-white' :
        trend === 'down' ? 'text-red-400' : 'text-white'
      }`}>
        {value}
      </div>
      <div className="text-xs font-military-display text-gray-500">
        CURRENT
      </div>
    </div>
  )
}

function ChartWidget({ data }: { data: any }) {
  if (data?.lines) {
    // Line combinations chart
    return (
      <div className="h-full flex flex-col">
        <div className="space-y-2">
          {data.lines.map((line: any, index: number) => (
            <div key={index} className="bg-gray-800/30 rounded p-2 border border-gray-800/50">
              <div className="text-xs font-military-chat text-white mb-1">{line.line}</div>
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div>
                  <span className="text-gray-400">TOI:</span>
                  <span className="text-white ml-1">{line.toi}</span>
                </div>
                <div>
                  <span className="text-gray-400">XGF%:</span>
                  <span className="text-white ml-1">{line.xgf}</span>
                </div>
                <div>
                  <span className="text-gray-400">GF:</span>
                  <span className="text-white ml-1">{line.gf}</span>
                </div>
                <div>
                  <span className="text-gray-400">GA:</span>
                  <span className="text-red-400 ml-1">{line.ga}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  if (data?.games) {
    // Recent form chart
    return (
      <div className="h-full flex flex-col">
        <div className="mb-2 grid grid-cols-2 gap-2 text-xs">
          <div className="text-center">
            <div className="text-white font-military-chat">GF AVG</div>
            <div className="text-gray-400">{(data.goals_for.reduce((a: number, b: number) => a + b, 0) / data.goals_for.length).toFixed(1)}</div>
          </div>
          <div className="text-center">
            <div className="text-white font-military-chat">GA AVG</div>
            <div className="text-gray-400">{(data.goals_against.reduce((a: number, b: number) => a + b, 0) / data.goals_against.length).toFixed(1)}</div>
          </div>
        </div>
        <div className="flex-1 bg-gray-800/30 rounded border border-gray-800/50 p-2">
          <div className="grid grid-cols-10 gap-1 h-full">
            {data.games.map((result: string, index: number) => (
              <div key={index} className="flex flex-col items-center justify-end">
                <div className="text-xs text-gray-400 mb-1">{data.goals_for[index]}-{data.goals_against[index]}</div>
                <div className={`w-full h-6 rounded flex items-center justify-center text-xs font-military-display ${
                  result === 'W' ? 'bg-white text-gray-900' :
                  result === 'L' ? 'bg-red-500 text-white' :
                  'bg-gray-600 text-white'
                }`}>
                  {result}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  
  if (data?.last_10) {
    // Shot trends chart
    return (
      <div className="h-full flex flex-col">
        <div className="mb-2 grid grid-cols-2 gap-2 text-xs">
          <div className="text-center">
            <div className="text-white font-military-chat">MTL AVG</div>
            <div className="text-gray-400">{(data.last_10.reduce((a: number, b: number) => a + b, 0) / data.last_10.length).toFixed(1)}</div>
          </div>
          <div className="text-center">
            <div className="text-white font-military-chat">OPP AVG</div>
            <div className="text-gray-400">{(data.opponent_last_10.reduce((a: number, b: number) => a + b, 0) / data.opponent_last_10.length).toFixed(1)}</div>
          </div>
        </div>
        <div className="flex-1 bg-gray-800/30 rounded border border-gray-800/50 p-2">
          <div className="h-full flex items-end justify-between gap-1">
            {data.cf_percentage.slice(-8).map((value: number, index: number) => (
              <div key={index} className="flex-1 flex flex-col items-center">
                <div 
                  className={`w-full rounded-t ${
                    value > 50 ? 'bg-white' : 'bg-red-400'
                  }`}
                  style={{ height: `${Math.max(value - 30, 10)}%` }}
                />
                <div className="text-xs text-gray-500 mt-1">{value.toFixed(0)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  
  // Default efficiency chart
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 bg-gray-800/30 rounded border border-gray-800/50 p-3 flex flex-col justify-center">
        <div className="text-center mb-2">
          <div className="text-2xl font-military-chat text-white mb-1">
            {data?.efficiency}%
          </div>
          <div className="text-xs font-military-display text-gray-400">
            EFFICIENCY RATE
          </div>
        </div>
        {data?.trend && (
          <div className="flex justify-between items-end h-8 gap-1">
            {data.trend.map((value: number, index: number) => (
              <div key={index} className="flex-1 flex flex-col items-center">
                <div 
                  className="w-full bg-white rounded-t"
                  style={{ height: `${(value / Math.max(...data.trend)) * 100}%` }}
                />
              </div>
            ))}
          </div>
        )}
        <div className="text-center mt-2">
          <div className="text-xs font-military-chat text-gray-500">
            {data?.opportunities || data?.goals || 0} total
          </div>
        </div>
      </div>
    </div>
  )
}

function TableWidget({ data }: { data: any[] }) {
  if (!data || data.length === 0) return null
  
  // Check if this is goalie data
  if (data[0]?.goalie && !data[0]?.opponent) {
    return (
      <div className="h-full">
        <div className="space-y-1">
          {/* Goalie Header */}
          <div className="grid grid-cols-6 gap-1 pb-1 border-b border-gray-800/50 text-xs font-military-display text-gray-400">
            <div>GOALIE</div>
            <div>GP</div>
            <div>SV%</div>
            <div>GAA</div>
            <div>GSAA</div>
            <div>HDSV%</div>
          </div>
          
          {/* Goalie Rows */}
          {data.map((goalie, index) => (
            <div key={goalie.goalie} className="grid grid-cols-6 gap-1 py-1 hover:bg-gray-800/30 rounded text-xs">
              <div className="font-military-chat text-white">{goalie.goalie}</div>
              <div className="font-military-chat text-white">{goalie.gp}</div>
              <div className="font-military-chat text-white">{goalie.sv_pct}</div>
              <div className="font-military-chat text-white">{goalie.gaa}</div>
              <div className={`font-military-chat ${
                parseFloat(goalie.gsaa) > 0 ? 'text-gray-300' : 'text-red-400'
              }`}>
                {goalie.gsaa}
              </div>
              <div className="font-military-chat text-white">{goalie.hdsv}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  
  // Regular player stats table with advanced metrics
  return (
    <div className="h-full">
      <div className="space-y-1">
        {/* Player Header */}
        <div className="grid grid-cols-7 gap-1 pb-1 border-b border-gray-800/50 text-xs font-military-display text-gray-400">
          <div>PLAYER</div>
          <div>G</div>
          <div>A</div>
          <div>PTS</div>
          <div>+/-</div>
          <div>XGF</div>
          <div>CF%</div>
        </div>
        
        {/* Player Rows */}
        {data.map((player, index) => (
          <div key={player.player || index} className="grid grid-cols-7 gap-1 py-1 hover:bg-gray-800/30 rounded text-xs">
            <div className="font-military-chat text-white">{player.player}</div>
            <div className="font-military-chat text-white">{player.goals}</div>
            <div className="font-military-chat text-white">{player.assists}</div>
            <div className="font-military-chat text-white font-medium">{player.points}</div>
            <div className={`font-military-chat ${
              player.rating && player.rating.startsWith('+') ? 'text-gray-300' : 'text-red-400'
            }`}>
              {player.rating}
            </div>
            <div className="font-military-chat text-white">{player.xgf}</div>
            <div className="font-military-chat text-white">{player.cf}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MapWidget({ data }: { data: any }) {
  return (
    <div className="h-full flex flex-col space-y-3">
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2 bg-gray-700/30 rounded border border-gray-600/50">
          <div className="text-lg font-military-chat text-white">{data?.offensive}%</div>
          <div className="text-xs font-military-display text-gray-400">OFFENSIVE</div>
        </div>
        <div className="p-2 bg-gray-700/30 rounded border border-gray-600/50">
          <div className="text-lg font-military-chat text-gray-300">{data?.neutral}%</div>
          <div className="text-xs font-military-display text-gray-400">NEUTRAL</div>
        </div>
        <div className="p-2 bg-gray-700/30 rounded border border-gray-600/50">
          <div className="text-lg font-military-chat text-gray-300">{data?.defensive}%</div>
          <div className="text-xs font-military-display text-gray-400">DEFENSIVE</div>
        </div>
      </div>
    </div>
  )
}

function StatusWidget({ status }: { status?: string }) {
  const statusConfig = {
    online: { label: 'OPERATIONAL' },
    offline: { label: 'OFFLINE' },
    warning: { label: 'WARNING' }
  }
  
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.online

  return (
    <div className="h-full flex flex-col justify-center items-center space-y-2 text-center p-2">
      <div className="w-10 h-10 rounded-full bg-gray-600/20 border border-gray-600/50 flex items-center justify-center">
        <ShieldCheckIcon className={`w-6 h-6 ${status === 'offline' ? 'text-red-500' : status === 'warning' ? 'text-gray-400' : 'text-gray-500'}`} />
      </div>
      <div className={`text-xs font-military-display ${status === 'offline' ? 'text-red-500' : 'text-gray-400'}`}>
        {config.label}
      </div>
      <div className="text-xs font-military-chat text-gray-400 text-center">
        ALL SYSTEMS NOMINAL
      </div>
    </div>
  )
}
