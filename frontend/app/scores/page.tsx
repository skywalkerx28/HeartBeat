'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { BasePage } from '../../components/layout/BasePage'
import { TrophyIcon, ClockIcon, CheckCircleIcon, XCircleIcon, ChevronDownIcon, ChevronUpIcon, ChevronLeftIcon, ChevronRightIcon, CalendarIcon } from '@heroicons/react/24/outline'
import { api, NHLGame } from '../../lib/api'

interface GameCardProps {
  game: NHLGame
}

function GameCard({ game }: GameCardProps) {
  const router = useRouter()
  const [isExpanded, setIsExpanded] = useState(false)

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on the expand button
    if ((e.target as HTMLElement).closest('button')) {
      return
    }
    router.push(`/game/${game.id}`)
  }

  const formatTime = (timeString: string) => {
    if (!timeString) return 'TBD'
    try {
      const date = new Date(timeString)
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      })
    } catch {
      return timeString
    }
  }

  const normalizeGameState = (g: NHLGame): string => {
    const s = (g.gameState || '').toUpperCase()
    const hasScores = (g.homeTeam && g.homeTeam.score != null) || (g.awayTeam && g.awayTeam.score != null)
    // Treat CRIT as LIVE
    if (s === 'CRIT') return 'LIVE'
    // Some feeds mark finished games as OFF; if scores exist, treat as FINAL
    if (s === 'OFF' && hasScores) return 'FINAL'
    return s || 'TBD'
  }

  const getGameStatus = (game: NHLGame) => {
    const state = normalizeGameState(game)

    if (state === 'LIVE') {
      const period = game.periodDescriptor?.number || game.period || 1
      const periodType = game.periodDescriptor?.periodType || 'Period'
      const timeRemaining = game.clock?.timeRemaining || '00:00'
      return {
        text: `LIVE - P${period} ${timeRemaining}`,
        // Use red accents to match app design and avoid green
        color: 'text-red-400',
        bgColor: 'bg-red-600/10',
        borderColor: 'border-red-600/30',
        glowColor: 'shadow-white/10',
        icon: <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
      }
    } else if (state === 'FINAL') {
      return {
        text: 'FINAL',
        color: 'text-gray-400',
        bgColor: 'bg-gray-600/10',
        borderColor: 'border-gray-600/30',
        glowColor: 'shadow-gray-500/10',
        icon: <CheckCircleIcon className="w-4 h-4 text-gray-400" />
      }
    } else if (state === 'OFF' || state === 'FUT') {
      return {
        text: formatTime(game.startTimeUTC),
        color: 'text-white',
        bgColor: 'bg-white/5',
        borderColor: 'border-white/10',
        glowColor: 'shadow-white/5',
        icon: null
      }
    } else if (state === 'PRE') {
      return {
        text: 'PRE-GAME',
        color: 'text-white',
        bgColor: 'bg-white/5',
        borderColor: 'border-white/10',
        glowColor: 'shadow-white/5',
        icon: null
      }
    } else {
      return {
        text: state || 'TBD',
        color: 'text-gray-400',
        bgColor: 'bg-gray-600/10',
        borderColor: 'border-gray-600/30',
        glowColor: 'shadow-gray-500/10',
        icon: null
      }
    }
  }

  const status = getGameStatus(game)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      onClick={handleCardClick}
      className={`relative group bg-white/90 backdrop-blur-xl border ${status.borderColor} rounded-lg overflow-hidden hover:border-gray-300 transition-all duration-300 shadow-lg ${status.glowColor} hover:shadow-gray-300/30 hover:shadow-xl cursor-pointer dark:bg-black/40 dark:hover:border-white/30 dark:hover:shadow-white/20`}
    >
      {/* Glassy overlay effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-100/50 to-transparent pointer-events-none dark:from-white/10" />
      
      {/* Animated border glow for live games */}
      {normalizeGameState(game) === 'LIVE' && (
        <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="absolute inset-0 rounded-lg border border-red-600/50 animate-pulse" />
        </div>
      )}

      {/* Header with status - Glassy effect */}
      <div className={`relative px-4 py-3 ${status.bgColor} border-b border-gray-200 backdrop-blur-sm dark:border-white/10`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {status.icon}
            <span className={`text-xs font-military-display ${status.color} tracking-wider uppercase`}>
              {status.text}
            </span>
          </div>
          {/* Right-side LIVE badge removed to avoid duplication */}
        </div>
      </div>

      {/* Game content */}
      <div className="relative p-5">
        {/* Teams Layout - Enhanced */}
        <div className="flex items-center justify-center gap-5">
          {/* Away Team */}
          <div className="flex items-center space-x-4 flex-shrink-0">
            <div className="relative w-12 h-12 flex items-center justify-center flex-shrink-0">
              {game.awayTeam.logo ? (
                <img 
                  src={game.awayTeam.logo} 
                  alt={game.awayTeam.abbrev}
                  className={`w-12 h-12 object-contain ${game.awayTeam.abbrev !== 'MTL' ? 'grayscale opacity-60' : ''}`}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                    const fallback = target.nextElementSibling as HTMLElement
                    if (fallback) fallback.style.display = 'flex'
                  }}
                />
              ) : null}
              <span className={`text-xs font-military-display text-white font-bold ${game.awayTeam.logo ? 'hidden' : 'flex'}`}>
                {game.awayTeam.abbrev}
              </span>
            </div>
            <div className="max-w-[140px]">
              <div className="text-sm font-military-display text-white truncate">
                {game.awayTeam.name.default}
              </div>
              <div className="text-xs font-military-display text-gray-500">
                {game.awayTeam.sog ? `${game.awayTeam.sog} SOG` : ''}
              </div>
            </div>
          </div>

          {/* Score Display - Enhanced with glassy effect */}
          <div className="flex-shrink-0">
            {(normalizeGameState(game) === 'LIVE' || normalizeGameState(game) === 'FINAL') && (game.awayTeam.score != null || game.homeTeam.score != null) ? (
              <div className="flex items-center space-x-2 bg-white/5 backdrop-blur-xl px-4 py-2 rounded-lg border border-white/20 shadow-xl shadow-white/10">
                <div className="text-3xl font-military-display text-white font-bold tabular-nums">
                  {game.awayTeam.score || 0}
                </div>
                <div className="text-xl font-military-display text-gray-400">-</div>
                <div className="text-3xl font-military-display text-white font-bold tabular-nums">
                  {game.homeTeam.score || 0}
                </div>
              </div>
            ) : (
              <div className="text-lg font-military-display text-gray-500 bg-black/20 px-4 py-2 rounded-lg border border-white/5">
                VS
              </div>
            )}
          </div>

          {/* Home Team */}
          <div className="flex items-center space-x-4 flex-shrink-0">
            <div className="max-w-[140px] text-right">
              <div className="text-sm font-military-display text-white truncate">
                {game.homeTeam.name.default}
              </div>
              <div className="text-xs font-military-display text-gray-500">
                {game.homeTeam.sog ? `${game.homeTeam.sog} SOG` : ''}
              </div>
            </div>
            <div className="relative w-12 h-12 flex items-center justify-center flex-shrink-0">
              {game.homeTeam.logo ? (
                <img 
                  src={game.homeTeam.logo} 
                  alt={game.homeTeam.abbrev}
                  className={`w-12 h-12 object-contain ${game.homeTeam.abbrev !== 'MTL' ? 'grayscale opacity-60' : ''}`}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                    const fallback = target.nextElementSibling as HTMLElement
                    if (fallback) fallback.style.display = 'flex'
                  }}
                />
              ) : null}
              <span className={`text-xs font-military-display text-white font-bold ${game.homeTeam.logo ? 'hidden' : 'flex'}`}>
                {game.homeTeam.abbrev}
              </span>
            </div>
          </div>
        </div>

        {/* Game details - Enhanced with glassy panels */}
        {normalizeGameState(game) === 'LIVE' && game.periodDescriptor && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="bg-white/5 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10">
                  <span className="text-xs font-military-display text-white uppercase tracking-wider">
                    Period {game.periodDescriptor.number}
                  </span>
                </div>
                <div className="bg-white/5 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10">
                  <span className="text-xs font-military-display text-gray-300">
                    {game.periodDescriptor.periodType}
                  </span>
                </div>
              </div>
              {game.situation && (
                <div className="flex items-center space-x-2">
                  <div className="bg-blue-600/20 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-blue-600/30">
                    <span className="text-xs font-military-display text-blue-400">
                      {game.situation.awayTeam.strength}v{game.situation.homeTeam.strength}
                    </span>
                  </div>
                  {game.situation.awayTeam.situationDescriptions && game.situation.awayTeam.situationDescriptions.length > 0 && (
                    <div className="bg-yellow-600/20 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-yellow-600/30">
                      <span className="text-xs font-military-display text-yellow-400 uppercase">
                        {game.situation.awayTeam.situationDescriptions.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Venue info for scheduled games */}
        {(['OFF','FUT','PRE','TBD'].includes(normalizeGameState(game))) && game.venue && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <span className="text-xs font-military-display text-gray-400">
              {game.venue.default}
            </span>
          </div>
        )}
      </div>

      {/* Corner accent - Tony Stark style */}
      <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-red-600/10 to-transparent pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-20 h-20 bg-gradient-to-tr from-red-600/10 to-transparent pointer-events-none" />

      {/* Expandable Details Section */}
      {(normalizeGameState(game) === 'LIVE' || normalizeGameState(game) === 'FINAL') && (game.goals || game.awayTeam.score != null) && (
        <div className="relative border-t border-white/10">
          {/* Expand/Collapse Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-5 py-3 flex items-center justify-between hover:bg-white/5 transition-colors group"
          >
            <div className="flex items-center space-x-3">
              <div className={`w-1 h-1 rounded-full ${game.gameState === 'LIVE' ? 'bg-red-600 animate-pulse' : 'bg-gray-500'}`}></div>
              <span className="text-xs font-military-display text-gray-400 uppercase tracking-wider">
                Game Details
              </span>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDownIcon className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
            </motion.div>
          </button>

          {/* Expandable Content */}
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="px-5 pb-5 space-y-4">
                  {/* Goals Section */}
                  {game.goals && game.goals.length > 0 && (
                    <div className="space-y-3">
                      <div className="space-y-2">
                        {game.goals.map((goal, index) => (
                          <motion.div
                            key={index}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <span className={`text-sm font-military-display font-bold ${goal.teamAbbrev === game.homeTeam.abbrev ? 'text-white' : 'text-gray-300'}`}>
                                    {goal.name.default}
                                  </span>
                                  <span className="text-xs font-military-display text-gray-500">
                                    ({goal.goalsToDate})
                                  </span>
                                </div>
                                {goal.assists && goal.assists.length > 0 && (
                                  <div className="text-xs font-military-display text-gray-400">
                                    Assists: {goal.assists.map(a => a.name.default).join(', ')}
                                  </div>
                                )}
                                <div className="flex items-center space-x-2 mt-2">
                                  <span className="text-xs font-military-display text-gray-500">
                                    P{goal.period} • {goal.timeInPeriod}
                                  </span>
                                  {goal.strength !== 'ev' && (
                                    <span className={`text-xs font-military-display px-2 py-0.5 rounded ${
                                      goal.strength === 'pp' ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30' :
                                      goal.strength === 'sh' ? 'bg-red-600/20 text-red-400 border border-red-600/30' :
                                      'bg-gray-600/20 text-gray-400 border border-gray-600/30'
                                    }`}>
                                      {goal.strength.toUpperCase()}
                                    </span>
                                  )}
                                  {goal.goalModifier === 'empty-net' && (
                                    <span className="text-xs font-military-display px-2 py-0.5 rounded bg-yellow-600/20 text-yellow-400 border border-yellow-600/30">
                                      EN
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-military-display text-white font-bold tabular-nums">
                                  {goal.awayScore}-{goal.homeScore}
                                </div>
                                <div className="text-xs font-military-display text-gray-500">
                                  {goal.teamAbbrev}
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Game Stats */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                      <div className="text-xs font-military-display text-gray-400 uppercase tracking-wider mb-1">
                        Shots
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-military-display text-white font-bold">
                          {game.awayTeam.sog || 0}
                        </span>
                        <span className="text-xs text-gray-500">-</span>
                        <span className="text-sm font-military-display text-white font-bold">
                          {game.homeTeam.sog || 0}
                        </span>
                      </div>
                    </div>

                    {game.period && (
                      <div className="bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                        <div className="text-xs font-military-display text-gray-400 uppercase tracking-wider mb-1">
                          Period
                        </div>
                        <div className="text-sm font-military-display text-white font-bold">
                          {game.period}
                          {game.periodDescriptor?.periodType && game.periodDescriptor.periodType !== 'REG' && (
                            <span className="ml-1 text-xs text-white">
                              {game.periodDescriptor.periodType}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {game.venue && (
                      <div className="bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                        <div className="text-xs font-military-display text-gray-400 uppercase tracking-wider mb-1">
                          Venue
                        </div>
                        <div className="text-xs font-military-display text-white truncate">
                          {game.venue.default.split(' ').slice(0, 2).join(' ')}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Broadcast Info */}
                  {game.tvBroadcasts && game.tvBroadcasts.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 pb-2 border-b border-white/10">
                        <div className="w-1 h-1 bg-white rounded-full"></div>
                        <h3 className="text-xs font-military-display text-white uppercase tracking-wider">
                          Broadcasts
                        </h3>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {game.tvBroadcasts.slice(0, 4).map((broadcast, index) => (
                          <div
                            key={index}
                            className="bg-white/5 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10"
                          >
                            <span className="text-xs font-military-display text-white">
                              {broadcast.network}
                            </span>
                            <span className="text-xs font-military-display text-gray-500 ml-2">
                              ({broadcast.market})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  )
}

export default function ScoresPage() {
  const [games, setGames] = useState<NHLGame[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [showDatePicker, setShowDatePicker] = useState(false)

  const formatDateForAPI = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const fetchScores = async (date?: Date) => {
    try {
      setIsLoading(true)
      setError(null)

      const targetDate = date || selectedDate
      const dateString = formatDateForAPI(targetDate)
      const scheduleData = await api.getNHLLiveScores(dateString)
      setGames(scheduleData.games || [])
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Error fetching NHL scores:', err)
      setError(err instanceof Error ? err.message : 'Failed to load scores')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchScores()

    // Set up polling for live updates every 30 seconds only if viewing today
    const isToday = formatDateForAPI(selectedDate) === formatDateForAPI(new Date())
    if (!isToday) return

    const interval = setInterval(() => fetchScores(), 30000)
    return () => clearInterval(interval)
  }, [selectedDate])

  const navigateDay = (direction: 'prev' | 'next') => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1))
    setSelectedDate(newDate)
  }

  const goToToday = () => {
    setSelectedDate(new Date())
  }

  const isToday = formatDateForAPI(selectedDate) === formatDateForAPI(new Date())

  const normalizeGameState = (g: NHLGame): string => {
    const s = (g.gameState || '').toUpperCase()
    const hasScores = (g.homeTeam && g.homeTeam.score != null) || (g.awayTeam && g.awayTeam.score != null)
    if (s === 'CRIT') return 'LIVE'
    if (s === 'OFF' && hasScores) return 'FINAL'
    return s || 'TBD'
  }

  const liveGames = games.filter(game => normalizeGameState(game) === 'LIVE')
  const scheduledGames = games.filter(game => {
    const s = normalizeGameState(game)
    return s === 'OFF' || s === 'FUT' || s === 'PRE' || s === 'TBD'
  })
  const completedGames = games.filter(game => normalizeGameState(game) === 'FINAL')

  return (
    <BasePage loadingMessage="CONNECTING TO NHL DATA FEED...">
      <div className="min-h-screen bg-gray-50 relative overflow-hidden dark:bg-gray-950">
        {/* Matrix-style background animation */}
        <div className="absolute inset-0 opacity-5 dark:opacity-10">
          <div className="matrix-rain"></div>
        </div>

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
        <div className="absolute inset-0 bg-gradient-radial from-red-500/5 via-transparent to-transparent opacity-20 dark:from-red-600/5 dark:opacity-30" />

        {/* Pulse animation intentionally only on Analytics page */}

        {/* Main content (match analytics/market density) */}
        <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-4 pb-20 lg:px-12 scale-[0.90] origin-top">
          {/* Floating Header */}
          <div className="mb-6 py-2 text-center">
            <h1 className="text-2xl font-military-display text-gray-900 tracking-wider dark:text-white">
              HeartBeat
            </h1>
          </div>

          {/* Date Navigation - Military Style */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, type: "spring", damping: 20 }}
            className="mb-6 flex justify-center"
          >
            <div className="flex flex-col lg:flex-row gap-4 items-center">
              <div className="inline-flex items-center bg-white/90 backdrop-blur-xl border border-gray-200 rounded-lg shadow-xl shadow-gray-200/50 dark:bg-black/40 dark:border-white/10 dark:shadow-white/5">
                {/* Previous Day */}
                <button
                  onClick={() => navigateDay('prev')}
                  className="p-3 hover:bg-gray-100 rounded-l-lg transition-colors group border-r border-gray-200 dark:hover:bg-white/5 dark:border-white/10"
                  aria-label="Previous day"
                >
                  <ChevronLeftIcon className="w-4 h-4 text-gray-600 group-hover:text-gray-900 transition-colors dark:text-gray-400 dark:group-hover:text-white" />
                </button>

                {/* Date Display */}
                <div className="flex items-center space-x-2 px-6">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-military-display text-gray-900 tracking-wider whitespace-nowrap dark:text-white">
                      {selectedDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    {isToday && (
                      <span className="text-xs font-military-display text-gray-500 uppercase dark:text-gray-400">• Today</span>
                    )}
                  </div>
                </div>

                {/* Next Day */}
                <button
                  onClick={() => navigateDay('next')}
                  className="p-3 hover:bg-gray-100 rounded-r-lg transition-colors group border-l border-gray-200 dark:hover:bg-white/5 dark:border-white/10"
                  aria-label="Next day"
                >
                  <ChevronRightIcon className="w-4 h-4 text-gray-600 group-hover:text-gray-900 transition-colors dark:text-gray-400 dark:group-hover:text-white" />
                </button>
              </div>

              {!isToday && (
                <button
                  onClick={goToToday}
                  className="px-4 py-2.5 hover:bg-gray-100 rounded-lg transition-colors group dark:hover:bg-white/5"
                >
                  <span className="text-xs font-military-display text-gray-600 hover:text-gray-900 uppercase tracking-wider transition-colors dark:text-gray-400 dark:hover:text-white">
                    Jump to Today
                  </span>
                </button>
              )}
            </div>
          </motion.div>

          {/* Status Bar - Enhanced glassy military style */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, type: "spring", damping: 20 }}
            className="mb-12 flex justify-center"
          >
            <div className="flex flex-col lg:flex-row gap-4 items-center">
              <div className="inline-flex items-center space-x-6 bg-white/90 backdrop-blur-xl border border-gray-200 rounded-lg px-8 py-4 shadow-xl shadow-gray-200/50 dark:bg-black/40 dark:border-white/10 dark:shadow-white/5">
                {/* Status indicator */}
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-500 animate-pulse' : 'bg-red-600'}`}></div>
                    <div className={`absolute inset-0 rounded-full ${isLoading ? 'bg-yellow-500' : 'bg-red-600'} animate-ping opacity-75`}></div>
                  </div>
                  <span className="text-xs font-military-display text-gray-900 tracking-wider uppercase dark:text-white">
                    {isLoading ? 'Syncing...' : isToday ? 'Live Feed Active' : 'Archive Mode'}
                  </span>
                </div>
                
                <div className="w-px h-6 bg-gradient-to-b from-transparent via-gray-400 to-transparent dark:via-gray-500"></div>
                
                {/* Clock */}
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-military-display text-gray-600 tracking-wider tabular-nums dark:text-gray-400">
                    {lastUpdated ? lastUpdated.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Initializing...'}
                  </span>
                </div>
                
                <div className="w-px h-6 bg-gradient-to-b from-transparent via-gray-400 to-transparent dark:via-gray-500"></div>
                
                {/* Game count */}
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-military-display text-gray-600 tracking-wider dark:text-gray-400">
                    {games.length} {games.length === 1 ? 'Game' : 'Games'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Error State */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8 text-center"
            >
              <div className="inline-flex items-center space-x-3 bg-red-600/20 border border-red-600/30 rounded-lg px-6 py-3">
                <XCircleIcon className="w-5 h-5 text-red-400" />
                <span className="text-sm font-military-display text-red-400">
                  {error}
                </span>
              </div>
            </motion.div>
          )}

          {/* Games Grid */}
          <div className="space-y-8">
            {/* Live Games */}
            {liveGames.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="mb-12"
              >
                {/* Floating Header */}
                <div className="mb-6 flex items-center space-x-3">
                  <div className="relative">
                    <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
                    <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping"></div>
                  </div>
                  <h2 className="text-sm font-military-display text-red-500 tracking-wider uppercase dark:text-red-400">
                    Active
                  </h2>
                  <div className="text-xs font-military-display text-gray-500 dark:text-gray-600">
                    {liveGames.length} {liveGames.length !== 1 ? 'matches' : 'match'}
                  </div>
                </div>
                
                {/* Three-up grid on large screens */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {liveGames.map((game, index) => (
                    <motion.div
                      key={game.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                    >
                      <GameCard game={game} />
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Scheduled Games */}
            {scheduledGames.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="mb-12"
              >
                {/* Floating Header */}
                <div className="mb-6 flex items-center space-x-3">
                  <div className="w-1 h-1 bg-red-600 rounded-full"></div>
                  <h2 className="text-sm font-military-display text-red-500 tracking-wider uppercase dark:text-red-400">
                    Upcoming
                  </h2>
                  <div className="text-xs font-military-display text-gray-500 dark:text-gray-600">
                    {scheduledGames.length} {scheduledGames.length !== 1 ? 'matches' : 'match'}
                  </div>
                </div>
                
                {/* Three-up grid on large screens */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {scheduledGames.map((game, index) => (
                    <motion.div
                      key={game.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.6 + index * 0.1 }}
                    >
                      <GameCard game={game} />
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Completed Games */}
            {completedGames.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="mb-12"
              >
                {/* Floating Header */}
                <div className="mb-6 flex items-center space-x-3">
                  <div className="w-1 h-1 bg-gray-500 rounded-full"></div>
                  <h2 className="text-sm font-military-display text-gray-600 tracking-wider uppercase dark:text-gray-400">
                    Completed
                  </h2>
                  <div className="text-xs font-military-display text-gray-500 dark:text-gray-600">
                    {completedGames.length} {completedGames.length !== 1 ? 'matches' : 'match'}
                  </div>
                </div>
                
                {/* Three-up grid on large screens */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {completedGames.map((game, index) => (
                    <motion.div
                      key={game.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.7 + index * 0.1 }}
                    >
                      <GameCard game={game} />
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* No Games */}
            {!isLoading && games.length === 0 && !error && (
              <div className="text-center py-12">
                <TrophyIcon className="w-16 h-16 text-gray-500 mx-auto mb-4 dark:text-gray-600" />
                <h3 className="text-lg font-military-display text-gray-600 mb-2 dark:text-gray-400">
                  NO GAMES TODAY
                </h3>
                <p className="text-sm font-military-chat text-gray-600 dark:text-gray-500">
                  There are no NHL games scheduled for today.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .matrix-rain {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(180deg, #000 0%, #111 100%);
          overflow: hidden;
        }

        .matrix-rain::before {
          content: '0101001001010010010100100101001001010010';
          position: absolute;
          top: -100%;
          left: 0;
          width: 100%;
          height: 200%;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          color: #666666;
          opacity: 0.1;
          animation: matrix-fall 10s linear infinite;
          white-space: pre;
          line-height: 1.2;
        }

        @keyframes matrix-fall {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
      `}</style>
    </BasePage>
  )
}
