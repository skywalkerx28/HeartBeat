'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ShieldExclamationIcon, FireIcon } from '@heroicons/react/24/outline'

interface RivalTeamData {
  team: string
  rti_score: number
  xgf_pct: number
  points_pct: number
  special_teams_net: number
  goal_share_5v5: number
  recent_record: string
}

interface RivalIndexTableProps {
  rivals: RivalTeamData[]
  isLoading?: boolean
}

export function RivalIndexTable({ rivals, isLoading }: RivalIndexTableProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-400">
            ANALYZING DIVISION RIVALS...
          </div>
        </div>
      </div>
    )
  }

  if (!rivals || rivals.length === 0) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-400">
            NO RIVAL DATA AVAILABLE
          </div>
        </div>
      </div>
    )
  }

  const getThreatLevel = (rti: number) => {
    if (rti >= 60) return { label: 'HIGH', color: 'text-red-400 border-red-600/40 bg-red-600/10' }
    if (rti >= 50) return { label: 'MODERATE', color: 'text-yellow-400 border-yellow-600/40 bg-yellow-600/10' }
    return { label: 'LOW', color: 'text-green-400 border-green-600/40 bg-green-600/10' }
  }

  const sortedRivals = [...rivals].sort((a, b) => b.rti_score - a.rti_score)
  const topRivals = sortedRivals.filter(r => r.team !== 'MTL').slice(0, 5)

  return (
    <div className="relative group overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      
      <div className="relative p-6">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-red-600 to-transparent" />
          <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
            Rival Threat Index
          </h4>
          <ShieldExclamationIcon className="w-4 h-4 text-red-600" />
        </div>

        <div className="space-y-3">
          {topRivals.map((rival, index) => {
            const threat = getThreatLevel(rival.rti_score)
            
            return (
              <motion.div
                key={rival.team}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + index * 0.05 }}
                className="bg-white/5 border border-white/10 rounded p-3 hover:bg-white/10 transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="text-sm font-military-display text-white tracking-wider">
                      {rival.team}
                    </div>
                    <span className={`
                      px-2 py-0.5 rounded text-xs font-military-display border
                      ${threat.color}
                    `}>
                      {threat.label}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <div className="text-xl font-military-display text-red-400">
                      {rival.rti_score.toFixed(1)}
                    </div>
                    {rival.rti_score >= 60 && (
                      <FireIcon className="w-4 h-4 text-red-600 animate-pulse" />
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 pt-2 border-t border-white/5">
                  <div className="text-center">
                    <div className="text-xs font-military-display text-gray-500 mb-1">xGF%</div>
                    <div className="text-xs font-military-display text-white">
                      {rival.xgf_pct.toFixed(1)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-military-display text-gray-500 mb-1">PTS%</div>
                    <div className="text-xs font-military-display text-white">
                      {rival.points_pct.toFixed(1)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-military-display text-gray-500 mb-1">ST NET</div>
                    <div className="text-xs font-military-display text-white">
                      {rival.special_teams_net > 0 ? '+' : ''}{rival.special_teams_net.toFixed(1)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-military-display text-gray-500 mb-1">REC</div>
                    <div className="text-xs font-military-display text-white">
                      {rival.recent_record}
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

