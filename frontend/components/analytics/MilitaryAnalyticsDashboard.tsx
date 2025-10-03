'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import {
  CalendarIcon,
  ChartBarIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { api, NHLGame } from '../../lib/api'

export function MilitaryAnalyticsDashboard() {
  const router = useRouter()
  const [currentTime, setCurrentTime] = useState('')
  const [upcomingGames, setUpcomingGames] = useState<NHLGame[]>([])
  const [isLoading, setIsLoading] = useState(true)
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
    fetchUpcomingGames()
  }, [])

  const fetchUpcomingGames = async () => {
    try {
      setIsLoading(true)
      
      // Fetch schedule for the current week (7 days from today)
      const today = new Date()
      const schedulePromises = []
      
      // Fetch 7 days starting from today for the week calendar
      for (let i = 0; i < 7; i++) {
        const date = new Date(today)
        date.setDate(today.getDate() + i)
        const dateStr = date.toISOString().split('T')[0]
        schedulePromises.push(api.getNHLSchedule(dateStr))
      }
      
      const schedules = await Promise.all(schedulePromises)
      
      // Combine all games and filter for MTL
      const allGames: NHLGame[] = []
      schedules.forEach(schedule => {
        if (schedule.games) {
          allGames.push(...schedule.games)
        }
      })
      
      const mtlGames = allGames.filter(
        game => game.awayTeam.abbrev === 'MTL' || game.homeTeam.abbrev === 'MTL'
      )
      
      // Sort by date
      const sortedGames = mtlGames.sort(
        (a, b) => new Date(a.startTimeUTC).getTime() - new Date(b.startTimeUTC).getTime()
      )
      
      console.log('MTL Games found for this week:', sortedGames.length)
      sortedGames.forEach(game => {
        console.log('Full Game Object:', game)
        console.log('Game Date field:', game.gameDate)
        console.log('Start Time UTC:', game.startTimeUTC)
      })
      
      setUpcomingGames(sortedGames)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Error fetching schedule:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getWeekSchedule = () => {
    const today = new Date()
    const weekDays = []
    
    for (let i = 0; i < 7; i++) {
      const date = new Date(today)
      date.setDate(today.getDate() + i)
      weekDays.push(date)
    }
    
    return weekDays
  }

  const getGameForDate = (date: Date) => {
    // Format the target date as YYYY-MM-DD
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const targetDateStr = `${year}-${month}-${day}`
    
    const game = upcomingGames.find(game => {
      // Extract date from startTimeUTC (ISO format: "2025-10-04T23:00:00Z")
      // OR use gameDate if available
      let gameDateStr: string
      
      if (game.gameDate) {
        gameDateStr = game.gameDate
      } else if (game.startTimeUTC) {
        // Extract YYYY-MM-DD from ISO string
        gameDateStr = game.startTimeUTC.split('T')[0]
      } else {
        return false
      }
      
      return gameDateStr === targetDateStr
    })
    
    if (game) {
      console.log('✅ Found game for date:', targetDateStr, 'Game:', game.awayTeam.abbrev, '@', game.homeTeam.abbrev)
    }
    
    return game
  }

  const weekSchedule = getWeekSchedule()

  return (
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

      {/* Main Content Container with max-width for readability */}
      <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-8 pb-20 lg:px-12">
        
        {/* Floating Header */}
        <div className="mb-6 py-2 text-center">
          <h1 className="text-3xl font-military-display text-white tracking-wider">
            HeartBeat
          </h1>
        </div>
        
        {/* Team Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
          className="mb-12"
      >
          <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
            </div>
              <h2 className="text-2xl font-military-display text-white tracking-wider">
                MONTREAL CANADIENS
              </h2>
              <span className="text-xs font-military-display text-gray-400">2025-2026</span>
            </div>
            
            <div className="flex items-center space-x-6 text-gray-400 text-xs font-military-display">
            <div className="flex items-center space-x-2">
                <ClockIcon className="w-3 h-3 text-white" />
                <span className="text-white">{currentTime}</span>
            </div>
              {lastUpdated && (
                <span className="text-xs">
                  SYNC {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        </motion.div>

        {/* Weekly Schedule Section */}
            <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-16"
        >
          <div className="flex items-center space-x-2 mb-6">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Upcoming Week
            </h3>
              </div>
          
{isLoading ? (
            <div className="text-center py-8">
              <div className="text-sm font-military-display text-gray-400">Loading schedule...</div>
              </div>
          ) : (
            <div className="grid grid-cols-7 gap-2">
              {weekSchedule.map((date, index) => {
                const game = getGameForDate(date)
                const isToday = date.toDateString() === new Date().toDateString()
                const isMTLHome = game ? game.homeTeam.abbrev === 'MTL' : false
                const opponent = game ? (isMTLHome ? game.awayTeam : game.homeTeam) : null
                
                return (
          <motion.div
                    key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + index * 0.05 }}
            className={`
                      relative group overflow-hidden rounded-lg
                      ${game ? 'cursor-pointer' : ''}
                    `}
                    onClick={() => game && router.push(`/game/${game.id}`)}
                  >
                    {/* Glassy background with border */}
                    <div className={`
                      absolute inset-0 bg-gradient-to-br from-white/5 to-transparent backdrop-blur-md
                      border transition-all duration-300
                      ${isToday ? 'border-white/30 shadow-lg shadow-white/10' : 'border-white/10'}
                      ${game ? 'group-hover:border-white/30 group-hover:shadow-lg group-hover:shadow-white/10' : ''}
                    `} />
                    
                    {/* Corner accent for today */}
                    {isToday && (
                      <div className="absolute top-0 right-0 w-0 h-0 border-t-[20px] border-r-[20px] border-t-white/20 border-r-transparent" />
                    )}
                    
                    <div className="relative">
                      {/* Header with day and date */}
                      <div className={`
                        px-2 py-2 text-center border-b backdrop-blur-sm
                        ${isToday ? 'bg-white/5 border-white/20' : 'bg-white/[0.02] border-white/5'}
                      `}>
                        <div className={`text-[10px] font-military-display uppercase tracking-wider mb-0.5 ${isToday ? 'text-white' : 'text-gray-500'}`}>
                          {date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()}
        </div>
                        <div className={`text-lg font-military-display ${isToday ? 'text-white' : 'text-white'}`}>
                          {date.getDate()}
        </div>
      </div>

                      {/* Game content */}
                      <div className="p-3 min-h-[120px] flex flex-col items-center justify-center">
                        {game && opponent ? (
                          <div className="space-y-2 w-full">
                          {/* Opponent logo with glow effect */}
                          <div className="flex justify-center">
                            <div className="relative">
                              {game && (
                                <div className="absolute inset-0 bg-white/10 blur-xl rounded-full" />
                              )}
                              <img 
                                src={opponent.logo} 
                                alt={opponent.abbrev}
                                className="relative w-14 h-14 object-contain drop-shadow-lg grayscale opacity-60"
                              />
      </div>
    </div>
                            
                            {/* Home/Away indicator */}
                            <div className="text-center">
                              <span className="text-[10px] font-military-display text-gray-500 tracking-wider">
                                {isMTLHome ? 'HOME' : 'AWAY'}
                              </span>
    </div>
                            
                            {/* Game time */}
          <div className="text-center">
                              <span className="text-[11px] font-military-display text-white tracking-wide">
                                {new Date(game.startTimeUTC).toLocaleTimeString('en-US', { 
                                  hour: 'numeric',
                                  minute: '2-digit',
                                  hour12: true
                                }).toUpperCase()}
                              </span>
        </div>
      </div>
                        ) : (
          <div className="text-center">
                            <div className="w-8 h-8 mx-auto mb-2 border border-dashed border-gray-800 rounded-full flex items-center justify-center">
                              <span className="text-[10px] font-military-display text-gray-700">--</span>
          </div>
                            <div className="text-[10px] font-military-display text-gray-700 tracking-wider">
                              STANDBY
          </div>
        </div>
                        )}
          </div>
        </div>
                  </motion.div>
                )
              })}
          </div>
        )}
        </motion.div>


        {/* Placeholder for Advanced Analytics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center space-x-2 mb-6">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Intelligence
            </h3>
          </div>
          
          <div className="relative group overflow-hidden rounded-lg">
            {/* Glassy background */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent backdrop-blur-md border border-white/10" />
            
            {/* Animated scan lines */}
            <div className="absolute inset-0 opacity-20">
              <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/10 to-transparent animate-pulse" />
            </div>
            
            <div className="relative p-16 text-center">
              <div className="max-w-lg mx-auto">
                {/* Holographic icon effect */}
                <div className="relative w-20 h-20 mx-auto mb-6">
                  <div className="absolute inset-0 bg-white/10 blur-2xl rounded-full animate-pulse" />
                  <div className="relative w-20 h-20 border border-white/30 rounded-lg flex items-center justify-center backdrop-blur-sm bg-white/5">
                    <ChartBarIcon className="w-10 h-10 text-white/60" />
        </div>
                  {/* Corner accents */}
                  <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-white/50" />
                  <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-white/50" />
                  <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-white/50" />
                  <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-white/50" />
      </div>
                
                <div className="inline-flex items-center space-x-2 mb-3">
                  <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                  <h4 className="text-sm font-military-display text-white uppercase tracking-wider">
                    System Initializing
                  </h4>
                  <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
        </div>
        
                <p className="text-xs font-military-display text-gray-500 leading-relaxed max-w-md mx-auto">
                  ADVANCED PERFORMANCE METRICS • PLAYER INTELLIGENCE • HEARTBEAT ALGORITHM ANALYSIS
                  <br />
                  <br />
                  Real-time tactical data integration from NHL API and custom analytics computed by the HeartBeat Engine.
                </p>
                
                {/* Progress indicator */}
                <div className="mt-6 w-48 h-0.5 mx-auto bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-white to-transparent animate-pulse" />
                </div>
              </div>
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  )
}