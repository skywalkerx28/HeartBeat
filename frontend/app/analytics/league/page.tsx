'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { AnalyticsNavigation } from '../../../components/analytics/AnalyticsNavigation'
import { ClockIcon } from '@heroicons/react/24/outline'

export default function LeaguePage() {
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

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

  useEffect(() => {
    setLastUpdated(new Date())
  }, [])

  return (
    <BasePage loadingMessage="LOADING LEAGUE ANALYTICS...">
      <div className="min-h-screen bg-gray-950 relative overflow-hidden">
        {/* Animated background grid */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>

        {/* Radial gradient overlay */}
        <div className="absolute inset-0 bg-gradient-radial from-cyan-500/5 via-transparent to-transparent opacity-30" />

        {/* Main Content Container (compact for consistency with Market/Analytics) */}
        <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-4 pb-20 lg:px-12 scale-[0.90] origin-top">
          
          {/* Top Header Row */}
          <div className="mb-8 py-2 grid grid-cols-3 items-center">
            {/* Left: Team Branding */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-4 justify-start"
            >
              <div className="relative">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
              </div>
              <h2 className="text-xl font-military-display text-white tracking-wider">
                MONTREAL CANADIENS
              </h2>
              <span className="text-xs font-military-display text-gray-400">2025-2026</span>
            </motion.div>

            {/* Center: HeartBeat Logo */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center"
            >
              <h1 className="text-2xl font-military-display text-white tracking-wider">
                HeartBeat
              </h1>
            </motion.div>

            {/* Right: System Info */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-6 text-gray-400 text-xs font-military-display justify-end"
            >
              <div className="flex items-center space-x-2">
                <ClockIcon className="w-3 h-3 text-white" />
                <span className="text-white">{currentTime}</span>
              </div>
              {lastUpdated && (
                <span className="text-xs">
                  SYNC {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </motion.div>
          </div>

          {/* Analytics Navigation */}
          <AnalyticsNavigation />

          {/* Content */}
          <div className="text-center py-20">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="text-sm font-military-display text-gray-400 uppercase tracking-widest">
                League Analytics Coming Soon
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </BasePage>
  )
}
