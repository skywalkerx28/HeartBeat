'use client'

import React from 'react'
import { motion } from 'framer-motion'

interface TeamTrendsData {
  window_games: number
  xgf_pct_rolling: number
  special_teams_net: number
  pace: {
    cf_per60: number
    ca_per60: number
    cf_pct: number
  }
  pdo: {
    value: number
    shooting_pct: number
    save_pct: number
    status: 'sustainable' | 'hot' | 'cold'
  }
}

interface TeamTrendGaugesProps {
  trends: TeamTrendsData
  isLoading?: boolean
}

export function TeamTrendGauges({ trends, isLoading }: TeamTrendGaugesProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            ANALYZING TEAM TRENDS...
          </div>
        </div>
      </div>
    )
  }

  const getGaugeColor = (value: number, midpoint: number = 50) => {
    if (value >= midpoint + 5) return 'bg-green-600'
    if (value >= midpoint - 5) return 'bg-white'
    return 'bg-red-600'
  }

  const getGaugeWidth = (value: number, max: number = 100) => {
    return `${Math.max(0, Math.min(100, (value / max) * 100))}%`
  }

  const getPDOStatusColor = (status: string) => {
    if (status === 'hot') return 'text-red-400'
    if (status === 'cold') return 'text-blue-400'
    return 'text-white'
  }

  return (
    <div className="relative group overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
      
      <div className="relative p-6 space-y-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
            <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
              Team Trends
            </h4>
          </div>
          <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">
            LAST {trends.window_games}G
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-military-display text-gray-600 uppercase tracking-wide dark:text-gray-400">
                xGF%
              </span>
              <span className="text-sm font-military-display text-gray-900 dark:text-white">
                {trends.xgf_pct_rolling.toFixed(1)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden dark:bg-white/5">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: getGaugeWidth(trends.xgf_pct_rolling) }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className={`h-full ${getGaugeColor(trends.xgf_pct_rolling)} rounded-full`}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-military-display text-gray-600 uppercase tracking-wide dark:text-gray-400">
                Special Teams Net
              </span>
              <span className="text-sm font-military-display text-gray-900 dark:text-white">
                {trends.special_teams_net > 0 ? '+' : ''}{trends.special_teams_net.toFixed(1)}
              </span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden dark:bg-white/5">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: getGaugeWidth(Math.abs(trends.special_teams_net), 20) }}
                transition={{ duration: 0.8, delay: 0.3 }}
                className={`h-full ${getGaugeColor(trends.special_teams_net + 100, 100)} rounded-full`}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-military-display text-gray-600 uppercase tracking-wide dark:text-gray-400">
                Pace (CF%)
              </span>
              <span className="text-sm font-military-display text-gray-900 dark:text-white">
                {trends.pace.cf_pct.toFixed(1)}%
              </span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden dark:bg-white/5">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: getGaugeWidth(trends.pace.cf_pct) }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className={`h-full ${getGaugeColor(trends.pace.cf_pct)} rounded-full`}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-military-display text-gray-600 uppercase tracking-wide dark:text-gray-400">
                PDO
              </span>
              <div className="flex items-center space-x-2">
                <span className={`text-sm font-military-display ${getPDOStatusColor(trends.pdo.status)}`}>
                  {trends.pdo.value.toFixed(1)}
                </span>
                <span className="text-xs font-military-display text-gray-500 uppercase dark:text-gray-600">
                  ({trends.pdo.status})
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-2">
              <div className="text-center p-2 bg-gray-100 rounded border border-gray-200 dark:bg-white/5 dark:border-white/10">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">SH%</div>
                <div className="text-sm font-military-display text-gray-900 dark:text-white">
                  {trends.pdo.shooting_pct.toFixed(1)}%
                </div>
              </div>
              <div className="text-center p-2 bg-gray-100 rounded border border-gray-200 dark:bg-white/5 dark:border-white/10">
                <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">SV%</div>
                <div className="text-sm font-military-display text-gray-900 dark:text-white">
                  {trends.pdo.save_pct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

