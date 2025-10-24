'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { TrophyIcon } from '@heroicons/react/24/outline'

interface LeaderData {
  firstName?: { default?: string }
  lastName?: { default?: string }
  teamAbbrev?: string
  value?: number
  position?: string
}

interface LeagueLeadersProps {
  leaders: LeaderData[]
  category: string
  isLoading?: boolean
}

export function LeagueLeaders({ leaders, category, isLoading }: LeagueLeadersProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            LOADING LEAGUE LEADERS...
          </div>
        </div>
      </div>
    )
  }

  if (!leaders || leaders.length === 0) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-600 dark:text-gray-400">
            NO DATA AVAILABLE
          </div>
        </div>
      </div>
    )
  }

  const categoryLabel = category.charAt(0).toUpperCase() + category.slice(1)

  return (
    <div className="relative group overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 group-hover:border-gray-300/80 shadow-sm transition-colors duration-300 dark:bg-black/40 dark:border-white/10 dark:group-hover:border-white/20" />
      
      <div className="relative p-5">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
          <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
            League Leaders
          </h4>
        </div>

        <div className="space-y-2">
          {leaders.slice(0, 5).map((leader, index) => {
            const firstName = leader.firstName?.default || ''
            const lastName = leader.lastName?.default || ''
            const fullName = `${firstName} ${lastName}`.trim()
            const team = leader.teamAbbrev || 'N/A'
            const value = leader.value || 0
            
            return (
              <motion.div
                key={`${fullName}-${team}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 + index * 0.03 }}
                className="flex items-center justify-between p-2 rounded border bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300 transition-all duration-200 dark:bg-white/[0.02] dark:border-white/5 dark:hover:bg-white/5 dark:hover:border-white/10"
              >
                <div className="flex items-center space-x-2">
                  <div className="flex items-center justify-center w-5 h-5 rounded bg-gray-100 border border-gray-200 dark:bg-white/5 dark:border-white/10">
                    <span className="text-[10px] font-military-display text-gray-600 dark:text-gray-400">
                      {index + 1}
                    </span>
                  </div>
                  
                  <div>
                    <div className="text-xs font-military-display text-gray-900 dark:text-white">
                      {fullName}
                    </div>
                    <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider dark:text-gray-500">
                      {team}
                    </div>
                  </div>
                </div>

                <div className="text-sm font-military-display text-gray-900 dark:text-white">
                  {value}
                </div>
              </motion.div>
            )
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-white/5">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center dark:text-gray-500">
            {categoryLabel} Leaders
          </div>
        </div>
      </div>
    </div>
  )
}
