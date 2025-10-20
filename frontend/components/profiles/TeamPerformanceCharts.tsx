'use client'

import { motion } from 'framer-motion'
import { TeamPerformanceData } from '../../lib/profileApi'

interface TeamPerformanceChartsProps {
  data: TeamPerformanceData
  teamId: string
}

export function TeamPerformanceCharts({ data, teamId }: TeamPerformanceChartsProps) {
  return (
    <div className="space-y-6">
      {/* Goals Per Game Trend */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Goals Per Game Trend (Last 30 Days)
            </h3>
          </div>

          <div className="h-48 flex items-end space-x-1">
            {data.goalsPerGame.slice(-15).map((point, idx) => {
              const height = (point.value / 5) * 100
              return (
                <div key={idx} className="flex-1 flex flex-col items-center">
                  <div 
                    className="w-full bg-blue-500/30 hover:bg-blue-500/50 transition-colors rounded-t"
                    style={{ height: `${height}%` }}
                    title={`${point.date}: ${point.value.toFixed(2)} G/GP`}
                  />
                </div>
              )
            })}
          </div>

          <div className="mt-3 flex items-center justify-between text-xs font-military-display text-gray-500">
            <span>15 Games Ago</span>
            <span>Recent</span>
          </div>
        </div>
      </motion.div>

      {/* Home/Away Splits */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Home/Away Splits
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="text-sm font-military-display text-blue-400 uppercase tracking-wider">
                Home
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs font-military-display text-gray-500">Record</span>
                  <span className="text-sm font-military-display text-white">{data.homeAwaySplits.home.record}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs font-military-display text-gray-500">GF/GA</span>
                  <span className="text-sm font-military-display text-white">
                    {data.homeAwaySplits.home.gf}/{data.homeAwaySplits.home.ga}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-sm font-military-display text-gray-400 uppercase tracking-wider">
                Away
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs font-military-display text-gray-500">Record</span>
                  <span className="text-sm font-military-display text-white">{data.homeAwaySplits.away.record}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs font-military-display text-gray-500">GF/GA</span>
                  <span className="text-sm font-military-display text-white">
                    {data.homeAwaySplits.away.gf}/{data.homeAwaySplits.away.ga}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Win/Loss Pattern */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Recent Form (Last 15 Games)
            </h3>
          </div>

          <div className="flex items-center space-x-1">
            {data.winLossPattern.slice(-15).map((game, idx) => (
              <div
                key={idx}
                className={`flex-1 h-8 rounded ${
                  game.result === 'W' ? 'bg-green-500/30' : 
                  game.result === 'OTL' ? 'bg-amber-500/30' : 
                  'bg-red-500/30'
                }`}
                title={`${game.date}: ${game.result}`}
              />
            ))}
          </div>

          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center space-x-4 text-xs font-military-display">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500/30 rounded" />
                <span className="text-gray-500">Win</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500/30 rounded" />
                <span className="text-gray-500">Loss</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-amber-500/30 rounded" />
                <span className="text-gray-500">OTL</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

