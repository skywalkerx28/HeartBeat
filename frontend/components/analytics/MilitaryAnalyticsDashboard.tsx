'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import BackgroundPulse from '@/components/global/BackgroundPulse'
import { useRouter } from 'next/navigation'
import {
  CalendarIcon,
  ChartBarIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { api, NHLGame } from '../../lib/api'
import { PlayerFormLeaders } from './PlayerFormLeaders'
import { TeamTrendGauges } from './TeamTrendGauges'
import { DivisionWatch } from './DivisionWatch'
import { RivalIndexTable } from './RivalIndexTable'
import { SentimentDial } from './SentimentDial'
import { LeagueLeaders } from './LeagueLeaders'
import { LeagueSummary } from './LeagueSummary'
import { LeagueTrendIndex } from './LeagueTrendIndex'
import { TransactionsFeed } from './TransactionsFeed'
import { CompactStandings } from './CompactStandings'
import { AnalyticsNavigation } from './AnalyticsNavigation'

export function MilitaryAnalyticsDashboard() {
  const router = useRouter()
  const [currentTime, setCurrentTime] = useState('')
  const [upcomingGames, setUpcomingGames] = useState<NHLGame[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  
  const [advancedAnalytics, setAdvancedAnalytics] = useState<any>(null)
  const [standings, setStandings] = useState<any[]>([])
  const [leagueLeaders, setLeagueLeaders] = useState<any[]>([])
  const [analyticsLoading, setAnalyticsLoading] = useState(true)

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
    fetchAdvancedAnalytics()
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

  const fetchAdvancedAnalytics = async () => {
    try {
      setAnalyticsLoading(true)
      
      const [analyticsData, standingsData, leadersData] = await Promise.all([
        api.getMTLAdvancedAnalytics(10, '2024-2025'),
        api.getNHLStandings(),
        api.getNHLLeaders('points', 10)
      ])
      
      setAdvancedAnalytics(analyticsData)
      setStandings(standingsData.standings || [])
      setLeagueLeaders(leadersData.leaders || [])
      
      console.log('Advanced Analytics loaded:', analyticsData)
    } catch (err) {
      console.error('Error fetching advanced analytics:', err)
    } finally {
      setAnalyticsLoading(false)
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
      console.log('Found game for date:', targetDateStr, 'Game:', game.awayTeam.abbrev, '@', game.homeTeam.abbrev)
    }
    
    return game
  }

  const weekSchedule = getWeekSchedule()

  return (
      <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100/50 dark:bg-none dark:bg-gray-950">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-30 dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(156, 163, 175, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(156, 163, 175, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>
      
      {/* Dark mode grid overlay */}
      <div className="absolute inset-0 opacity-0 dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Radial gradient overlay */}
      <div className="absolute inset-0 bg-gradient-radial from-red-500/5 via-transparent to-transparent opacity-20 dark:from-cyan-500/5 dark:opacity-30" />

      {/* Heartbeat Pulse Animation */}
      {/* Single pulse component ensures one-at-a-time rendering */}
      <BackgroundPulse />

      {/* Main Content Container (compact for denser layout) */}
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
            <h2 className="text-xl font-military-display text-gray-900 tracking-wider dark:text-white">
              MONTREAL CANADIENS
            </h2>
            <span className="text-xs font-military-display text-gray-500 dark:text-gray-400">2025-2026</span>
          </motion.div>

          {/* Center: HeartBeat Logo */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center"
          >
            <h1 className="text-2xl font-military-display text-gray-900 tracking-wider dark:text-white">
              HeartBeat
            </h1>
          </motion.div>

          {/* Right: System Info */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center space-x-6 text-gray-500 text-xs font-military-display justify-end dark:text-gray-400"
          >
            <div className="flex items-center space-x-2">
              <ClockIcon className="w-3 h-3 text-gray-900 dark:text-white" />
              <span className="text-gray-900 dark:text-white">{currentTime}</span>
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

        {/* Three-Column Layout: Main Content + Right Sidebar + Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1200px)_380px_80px] gap-8 max-w-screen-2xl mx-auto">
          
          {/* Main Content Area (Left) */}
          <div className="space-y-8">
            
            {/* Weekly Schedule Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
                <h3 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
                  Upcoming Week
                </h3>
              </div>
          
{isLoading ? (
            <div className="text-center py-8">
              <div className="text-sm font-military-display text-gray-500 dark:text-gray-400">Loading schedule...</div>
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
                    {/* Glassy background with red glowing border */}
                    <div className={`
                      absolute inset-0 bg-gradient-to-br from-gray-100 to-white backdrop-blur-md dark:from-white/5 dark:to-transparent
                      border transition-all duration-300
                      ${isToday ? 'border-red-600/60 shadow-lg shadow-red-600/30 dark:border-red-600/40 dark:shadow-red-600/20' : 'border-red-600/30 shadow-md shadow-red-600/15 dark:border-red-600/20 dark:shadow-red-600/10'}
                      ${game ? 'group-hover:border-red-600/80 group-hover:shadow-xl group-hover:shadow-red-600/40 dark:group-hover:border-red-600/60 dark:group-hover:shadow-red-600/30' : ''}
                    `} />
                    
                    {/* Corner accent for today */}
                    {isToday && (
                      <div className="absolute top-0 right-0 w-0 h-0 border-t-[20px] border-r-[20px] border-t-red-600/30 border-r-transparent" />
                    )}
                    
                    <div className="relative">
                      {/* Header with day and date */}
                      <div className={`
                        px-2 py-2 text-center border-b backdrop-blur-sm
                        ${isToday ? 'bg-red-600/15 border-red-600/40 dark:bg-red-600/10 dark:border-red-600/30' : 'bg-gray-50/50 border-gray-300/30 dark:bg-white/[0.02] dark:border-red-600/10'}
                      `}>
                        <div className={`text-[10px] font-military-display uppercase tracking-wider mb-0.5 ${isToday ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-500'}`}>
                          {date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()}
        </div>
                        <div className={`text-lg font-military-display ${isToday ? 'text-gray-900 dark:text-white' : 'text-gray-900 dark:text-white'}`}>
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
                              <span className="text-[10px] font-military-display text-gray-600 tracking-wider dark:text-gray-500">
                                {isMTLHome ? 'HOME' : 'AWAY'}
                              </span>
    </div>
                            
                            {/* Game time */}
          <div className="text-center">
                              <span className="text-[11px] font-military-display text-gray-900 tracking-wide dark:text-white">
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
                            <div className="w-8 h-8 mx-auto mb-2 border border-dashed border-gray-300 rounded-full flex items-center justify-center dark:border-gray-800">
                              <span className="text-[10px] font-military-display text-gray-400 dark:text-gray-700">--</span>
          </div>
                            <div className="text-[10px] font-military-display text-gray-400 tracking-wider dark:text-gray-700">
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

            {/* League Intelligence Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <LeagueSummary isLoading={analyticsLoading} />
            </motion.div>

            {/* Advanced Analytics Grid */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
                <h3 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
                  Advanced Metrics
                </h3>
              </div>

              <div className="space-y-6">
                {/* Player Form + Team Trends */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center space-x-2 mb-3">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
                      <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
                        Player Form Index
                      </h4>
                    </div>
                    <PlayerFormLeaders 
                      players={advancedAnalytics?.player_form || []} 
                      isLoading={analyticsLoading} 
                    />
                  </div>
                  <TeamTrendGauges 
                    trends={advancedAnalytics?.team_trends || {}} 
                    isLoading={analyticsLoading} 
                  />
                </div>

                {/* Rival Threat Index + Fan Sentiment */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <RivalIndexTable 
                    rivals={advancedAnalytics?.rival_threat_index || []} 
                    isLoading={analyticsLoading} 
                  />
                  <SentimentDial 
                    sentiment={advancedAnalytics?.fan_sentiment_proxy || {}} 
                    isLoading={analyticsLoading} 
                  />
                </div>
              </div>
            </motion.div>

          </div>

          {/* Right Sidebar (original position) */}
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="sticky top-6 space-y-6"
            >
              {/* Transaction Feed */}
              <TransactionsFeed hours={72} isLoading={analyticsLoading} />
              
              {/* Compact Standings */}
              <CompactStandings standings={standings} isLoading={analyticsLoading} />
              
              {/* League Trend Index */}
              <LeagueTrendIndex isLoading={analyticsLoading} />
              
              {/* League Leaders */}
              <LeagueLeaders 
                leaders={leagueLeaders} 
                category="points" 
                isLoading={analyticsLoading} 
              />
            </motion.div>
          </div>

          {/* Extreme Right: Minimal Timeline */}
          <div className="hidden lg:block relative">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="sticky top-6 ml-16"
            >
              <SeasonTimelineMinimal />
            </motion.div>
          </div>

        </div>
      </div>
    </div>
  )
}

// Minimal abstract timeline component
const SeasonTimelineMinimal = () => {
  const [currentDate, setCurrentDate] = useState(new Date())

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentDate(new Date())
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  const seasonStart = new Date('2025-10-07')
  const seasonEnd = new Date('2026-06-26')
  const totalDuration = seasonEnd.getTime() - seasonStart.getTime()
  const currentProgress = Math.max(0, Math.min(100, ((currentDate.getTime() - seasonStart.getTime()) / totalDuration) * 100))

  const keyDates = [
    { date: new Date('2025-10-07'), type: 'season', label: 'Season Opens' },
    { date: new Date('2025-11-14'), type: 'global', label: 'Global Series' },
    { date: new Date('2026-01-02'), type: 'classic', label: 'Winter Classic' },
    { date: new Date('2026-02-01'), type: 'stadium', label: 'Stadium Series' },
    { date: new Date('2026-02-06'), type: 'olympics', label: 'Olympics Start' },
    { date: new Date('2026-02-24'), type: 'olympics', label: 'Olympics End' },
    { date: new Date('2026-03-06'), type: 'trade', label: 'Trade Deadline' },
    { date: new Date('2026-04-16'), type: 'season', label: 'Season Ends' },
    { date: new Date('2026-04-20'), type: 'playoffs', label: 'Playoffs Begin' },
    { date: new Date('2026-06-01'), type: 'playoffs', label: 'Cup Finals' },
    { date: new Date('2026-06-26'), type: 'draft', label: 'NHL Draft' },
  ]

  const calculatePosition = (date: Date) => {
    const elapsed = date.getTime() - seasonStart.getTime()
    return Math.max(0, Math.min(100, (elapsed / totalDuration) * 100))
  }

  const isPast = (date: Date) => date.getTime() < currentDate.getTime()

  return (
    <div className="relative h-[800px] w-20 flex justify-center">
      {/* Vertical cord - very subtle */}
      <div className="absolute left-1/2 -ml-px top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-white/5" />
      
      {/* Progress indicator */}
      <motion.div
        className="absolute left-1/2 -ml-px top-0 w-0.5 bg-gradient-to-b from-red-600/30 via-red-600/15 to-transparent dark:from-red-600/20 dark:via-red-600/10"
        initial={{ height: 0 }}
        animate={{ height: `${currentProgress}%` }}
        transition={{ duration: 1.5, ease: 'easeOut' }}
      />

      {/* Current date marker */}
      <motion.div
        className="absolute left-1/2 -ml-1"
        style={{ top: `${currentProgress}%` }}
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, duration: 0.3 }}
      >
        <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse shadow-lg shadow-red-600/30" />
        
        {/* Current date text */}
        <div className="absolute left-4 top-1/2 -translate-y-1/2 whitespace-nowrap">
          <div className="text-[9px] font-military-display text-gray-500 tabular-nums dark:text-gray-400">
            {currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>
      </motion.div>

      {/* Key date nodes - minimal with hover */}
      {keyDates.map((kd, idx) => {
        const pos = calculatePosition(kd.date)
        const past = isPast(kd.date)
        const formatDate = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        
        return (
          <motion.div
            key={idx}
            className="absolute left-1/2 -ml-1 group cursor-pointer"
            style={{ top: `${pos}%` }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 + idx * 0.08 }}
          >
            <div 
              className={`w-2 h-2 rounded-full transition-all duration-200 ${
                kd.type === 'trade'
                  ? past
                    ? 'bg-gray-700/30 group-hover:bg-gray-600/50'
                    : 'bg-red-600/60 shadow-sm shadow-red-600/30 group-hover:bg-red-600 group-hover:shadow-md group-hover:shadow-red-600/50'
                  : past 
                    ? 'bg-gray-700/30 group-hover:bg-gray-600/50' 
                    : 'bg-gray-500/40 group-hover:bg-gray-400/60'
              }`}
            />
            
            {/* Tooltip on hover */}
            <div className="absolute left-6 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap">
              <div className="bg-white/95 backdrop-blur-xl border border-gray-200 rounded px-2 py-1 shadow-lg dark:bg-black/90 dark:border-white/20">
                <div className="text-[9px] font-military-display text-gray-900 uppercase tracking-wider dark:text-white">
                  {kd.label}
                </div>
                <div className="text-[8px] font-military-display text-gray-600 tabular-nums dark:text-gray-400">
                  {formatDate(kd.date)}
                </div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
