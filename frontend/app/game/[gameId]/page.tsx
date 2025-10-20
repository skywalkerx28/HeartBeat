'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { 
  ArrowLeftIcon, 
  ClockIcon, 
  TrophyIcon,
  UserGroupIcon,
  ChartBarIcon,
  PlayIcon
} from '@heroicons/react/24/outline'
import { api } from '../../../lib/api'

export default function GameAnalyticsPage() {
  const params = useParams()
  const router = useRouter()
  const gameId = params?.gameId as string

  const [boxscore, setBoxscore] = useState<any>(null)
  const [playByPlay, setPlayByPlay] = useState<any>(null)
  const [landing, setLanding] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'boxscore' | 'plays' | 'ice'>('overview')

  useEffect(() => {
    const fetchGameData = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const [boxscoreData, playByPlayData, landingData] = await Promise.all([
          api.getGameBoxscore(Number(gameId)),
          api.getGamePlayByPlay(Number(gameId)),
          api.getGameLanding(Number(gameId))
        ])

        setBoxscore(boxscoreData)
        setPlayByPlay(playByPlayData)
        setLanding(landingData)
      } catch (err) {
        console.error('Error fetching game data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load game data')
      } finally {
        setIsLoading(false)
      }
    }

    if (gameId) {
      fetchGameData()
    }
  }, [gameId])

  const formatTime = (toi: string) => {
    if (!toi) return '0:00'
    return toi
  }

  // Create a player lookup map from roster
  const getPlayerName = (playerId: number) => {
    if (!playByPlay?.rosterSpots) return 'Unknown'
    const player = playByPlay.rosterSpots.find((p: any) => p.playerId === playerId)
    if (!player) return 'Unknown'
    return `${player.firstName?.default || ''} ${player.lastName?.default || ''}`.trim()
  }

  // Get team abbreviation from team ID
  const getTeamAbbrev = (teamId: number) => {
    if (!playByPlay) return ''
    if (teamId === playByPlay.awayTeam?.id) return playByPlay.awayTeam?.abbrev || ''
    if (teamId === playByPlay.homeTeam?.id) return playByPlay.homeTeam?.abbrev || ''
    return ''
  }

  // Get team logo from team ID
  const getTeamLogo = (teamId: number) => {
    if (!playByPlay) return ''
    if (teamId === playByPlay.awayTeam?.id) return playByPlay.awayTeam?.logo || ''
    if (teamId === playByPlay.homeTeam?.id) return playByPlay.homeTeam?.logo || ''
    return ''
  }

  // Determine strength from situation code and scoring team
  const getStrength = (situationCode: string, scoringTeamId?: number): 'ev' | 'pp' | 'sh' => {
    if (!situationCode || situationCode.length < 4) return 'ev'
    const awayPlayers = parseInt(situationCode[0])
    const homePlayers = parseInt(situationCode[1])
    
    // Even strength
    if (awayPlayers === homePlayers) return 'ev'
    
    // Need to know which team scored to determine PP vs SH
    if (!scoringTeamId) return 'ev'
    
    const isAwayTeam = scoringTeamId === playByPlay?.awayTeam?.id
    const isHomeTeam = scoringTeamId === playByPlay?.homeTeam?.id
    
    // Away team scored
    if (isAwayTeam) {
      if (awayPlayers > homePlayers) return 'pp'  // Away has more players = PP
      if (awayPlayers < homePlayers) return 'sh'  // Away has fewer players = SH
    }
    
    // Home team scored
    if (isHomeTeam) {
      if (homePlayers > awayPlayers) return 'pp'  // Home has more players = PP
      if (homePlayers < awayPlayers) return 'sh'  // Home has fewer players = SH
    }
    
    return 'ev'
  }

  if (isLoading) {
    return (
      <BasePage loadingMessage="LOADING GAME ANALYTICS...">
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <div className="text-white font-military-display text-lg">ANALYZING GAME DATA...</div>
          </div>
        </div>
      </BasePage>
    )
  }

  if (error || !boxscore || !playByPlay) {
    return (
      <BasePage loadingMessage="ERROR...">
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-center">
            <div className="text-red-400 font-military-display text-xl mb-4">ERROR LOADING GAME</div>
            <div className="text-gray-400 font-military-chat mb-6">{error || 'Game data not available'}</div>
            <button
              onClick={() => router.push('/scores')}
              className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-military-display rounded-lg transition-colors"
            >
              RETURN TO SCORES
            </button>
          </div>
        </div>
      </BasePage>
    )
  }

  const { awayTeam, homeTeam, clock, period, periodDescriptor, gameState } = boxscore

  return (
    <BasePage loadingMessage="GAME ANALYTICS">
      <div className="min-h-screen bg-gray-950 relative overflow-hidden">
        {/* Matrix background */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="matrix-rain"></div>
        </div>

        {/* Main content */}
        <div className="relative z-10 mx-auto max-w-7xl px-6 pt-4 pb-20 lg:px-12">
          {/* Page Header */}
          <div className="mb-6 py-2 text-center">
            <h1 className="text-3xl font-military-display text-white tracking-wider">
              HeartBeat
            </h1>
          </div>

          {/* Back Button */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="mb-8"
          >
            <button
              onClick={() => router.push('/scores')}
              className="flex items-center space-x-2 text-gray-400 hover:text-white transition-colors group"
            >
              <ArrowLeftIcon className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
              <span className="font-military-display text-sm uppercase tracking-wider">Back to Scores</span>
            </button>
          </motion.div>

          {/* Game Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <div className="bg-black/40 backdrop-blur-xl border border-cyan-600/30 rounded-lg p-6 shadow-xl shadow-cyan-500/10">
              {/* Teams Display */}
              <div className="flex items-center justify-between mb-6">
                {/* Away Team */}
                <div className="flex items-center space-x-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-lg flex items-center justify-center border border-gray-600/50 shadow-lg overflow-hidden">
                    {awayTeam.logo && (
                      <img src={awayTeam.logo} alt={awayTeam.abbrev} className={`w-14 h-14 object-contain ${awayTeam.abbrev !== 'MTL' ? 'grayscale opacity-60' : ''}`} />
                    )}
                  </div>
                  <div>
                    <div className="text-2xl font-military-display text-white">{awayTeam.commonName.default}</div>
                    <div className="text-sm font-military-display text-gray-400">{awayTeam.placeName.default}</div>
                  </div>
                </div>

                {/* Score */}
                <div className="flex items-center space-x-6">
                  <div className="text-5xl font-military-display text-white font-bold tabular-nums">
                    {awayTeam.score}
                  </div>
                  <div className="text-3xl font-military-display text-gray-500">-</div>
                  <div className="text-5xl font-military-display text-white font-bold tabular-nums">
                    {homeTeam.score}
                  </div>
                </div>

                {/* Home Team */}
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-2xl font-military-display text-white">{homeTeam.commonName.default}</div>
                    <div className="text-sm font-military-display text-gray-400">{homeTeam.placeName.default}</div>
                  </div>
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-lg flex items-center justify-center border border-gray-600/50 shadow-lg overflow-hidden">
                    {homeTeam.logo && (
                      <img src={homeTeam.logo} alt={homeTeam.abbrev} className={`w-14 h-14 object-contain ${homeTeam.abbrev !== 'MTL' ? 'grayscale opacity-60' : ''}`} />
                    )}
                  </div>
                </div>
              </div>

              {/* Game Status */}
              <div className="flex items-center justify-center space-x-6 pt-4 border-t border-white/10">
                <div className="flex items-center space-x-2">
                  {gameState === 'LIVE' ? (
                    <>
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      <span className="text-sm font-military-display text-red-400 uppercase tracking-wider">
                        LIVE - Period {period} ({clock?.timeRemaining || '00:00'})
                      </span>
                    </>
                  ) : gameState === 'FINAL' ? (
                    <>
                      <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                      <span className="text-sm font-military-display text-gray-400 uppercase tracking-wider">
                        FINAL
                        {periodDescriptor?.periodType !== 'REG' && ` - ${periodDescriptor?.periodType}`}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm font-military-display text-cyan-400 uppercase tracking-wider">
                      {boxscore.startTimeUTC && new Date(boxscore.startTimeUTC).toLocaleTimeString()}
                    </span>
                  )}
                </div>
                <div className="w-px h-4 bg-gray-600"></div>
                {/* Shots on Goal */}
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-military-display text-gray-500 uppercase">SOG</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-base font-military-display text-white font-bold tabular-nums">{awayTeam.sog}</span>
                    <span className="text-sm text-gray-500">-</span>
                    <span className="text-base font-military-display text-white font-bold tabular-nums">{homeTeam.sog}</span>
                  </div>
                </div>
                <div className="w-px h-4 bg-gray-600"></div>
                <div className="text-sm font-military-display text-gray-400">
                  {boxscore.venue?.default}
                </div>
                <div className="w-px h-4 bg-gray-600"></div>
                <div className="text-sm font-military-display text-gray-400">
                  {boxscore.gameDate}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Tab Navigation */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-8"
          >
            <div className="relative inline-flex space-x-8 border-b border-white/10 pb-2">
              <button
                onClick={() => setActiveTab('overview')}
                className="relative px-4 py-2 font-military-display text-sm uppercase tracking-wider transition-all group"
              >
                <span className={`transition-colors ${
                  activeTab === 'overview' ? 'text-cyan-400' : 'text-gray-400 group-hover:text-white'
                }`}>
                  Overview
                </span>
                {activeTab === 'overview' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
              
              <button
                onClick={() => setActiveTab('boxscore')}
                className="relative px-4 py-2 font-military-display text-sm uppercase tracking-wider transition-all group"
              >
                <span className={`transition-colors ${
                  activeTab === 'boxscore' ? 'text-cyan-400' : 'text-gray-400 group-hover:text-white'
                }`}>
                  Boxscore
                </span>
                {activeTab === 'boxscore' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
              
              <button
                onClick={() => setActiveTab('plays')}
                className="relative px-4 py-2 font-military-display text-sm uppercase tracking-wider transition-all group"
              >
                <span className={`transition-colors ${
                  activeTab === 'plays' ? 'text-cyan-400' : 'text-gray-400 group-hover:text-white'
                }`}>
                  Play-by-Play
                </span>
                {activeTab === 'plays' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
              
              <button
                onClick={() => setActiveTab('ice')}
                className="relative px-4 py-2 font-military-display text-sm uppercase tracking-wider transition-all group"
              >
                <span className={`transition-colors ${
                  activeTab === 'ice' ? 'text-cyan-400' : 'text-gray-400 group-hover:text-white'
                }`}>
                  Ice Analysis
                </span>
                {activeTab === 'ice' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </button>
            </div>
          </motion.div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Official Game Reports (PDF) */}
                {(() => {
                  // Game reports are directly at landing.gameReports according to NHL API
                  const reports = landing?.gameReports
                  
                  if (!reports || typeof reports !== 'object') {
                    return (
                      <div className="bg-black/40 backdrop-blur-xl border border-red-600/20 rounded-lg p-6 shadow-xl shadow-red-600/10">
                        <div className="flex items-center justify-between mb-4 pb-3 border-b border-red-600/20">
                          <div className="flex items-center space-x-3">
                            <ChartBarIcon className="w-5 h-5 text-red-400" />
                            <h3 className="text-sm font-military-display text-white uppercase tracking-wider">Official Game Reports</h3>
                          </div>
                          <span className="text-xs font-military-display text-gray-500">PDF</span>
                        </div>
                        <div className="text-center py-8">
                          <div className="text-sm font-military-display text-gray-400 mb-2">
                            Game reports not yet available
                          </div>
                          <div className="text-xs font-military-display text-gray-600">
                            PDF reports are generated 30-60 minutes after the game ends
                          </div>
                        </div>
                      </div>
                    )
                  }

                  const titleMap: Record<string, string> = {
                    gameSummary: 'Game Summary',
                    eventSummary: 'Event Summary',
                    playByPlay: 'Play-by-Play',
                    faceoffSummary: 'Faceoff Summary',
                    faceoffComparison: 'Faceoff Comparison',
                    rosters: 'Rosters',
                    shotSummary: 'Shot Summary',
                    shiftChart: 'Shift Chart',
                    toiAway: 'TOI (Away)',
                    toiHome: 'TOI (Home)'
                  }

                  const keys = Object.keys(titleMap)
                  const items: Array<{ key: string; label: string; url?: string }> = keys.map(k => ({ key: k, label: titleMap[k], url: (reports as any)?.[k] }))
                  // Also include any extra detected PDFs not in our known keys
                  for (const [k, v] of Object.entries(reports)) {
                    if (typeof v === 'string' && v.includes('.pdf') && !keys.includes(k)) {
                      items.push({ key: k, label: k.replace(/([A-Z])/g, ' $1').trim(), url: v })
                    }
                  }

                  const anyUrl = items.some(i => typeof i.url === 'string' && i.url.length > 0)
                  if (!anyUrl) return null

                  return (
                    <div className="bg-black/40 backdrop-blur-xl border border-red-600/20 rounded-lg p-6 shadow-xl shadow-red-600/10">
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-red-600/20">
                        <div className="flex items-center space-x-3">
                          <ChartBarIcon className="w-5 h-5 text-red-400" />
                          <h3 className="text-sm font-military-display text-white uppercase tracking-wider">Official Game Reports</h3>
                        </div>
                        <span className="text-xs font-military-display text-gray-500">PDF</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {items.map((it, idx) => (
                          <a
                            key={`${it.key}-${idx}`}
                            href={it.url || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`flex items-center justify-between px-3 py-2 rounded border transition ${
                              it.url ? 'border-red-600/20 bg-red-600/5 hover:bg-red-600/10 hover:border-red-600/30' : 'border-white/5 bg-black/20 cursor-not-allowed opacity-50'
                            }`}
                          >
                            <span className="text-xs font-military-display text-white">{it.label}</span>
                            {it.url ? (
                              <span className="text-[10px] text-red-400">Open</span>
                            ) : (
                              <span className="text-[10px] text-gray-500">Unavailable</span>
                            )}
                          </a>
                        ))}
                      </div>
                    </div>
                  )
                })()}

                {/* Game Timeline - All Events */}
                {playByPlay?.plays && landing?.summary?.scoring && (() => {
                  // Create a map of goals with their strength from landing data
                  const goalStrengthMap = new Map()
                  landing.summary.scoring.forEach((period: any) => {
                    period.goals?.forEach((goal: any) => {
                      goalStrengthMap.set(goal.eventId, goal)
                    })
                  })

                  // Get all timeline events (goals, penalties, fights)
                  const timelineEvents = playByPlay.plays
                    .filter((play: any) => ['goal', 'penalty', 'fight'].includes(play.typeDescKey))
                    .map((play: any) => {
                      if (play.typeDescKey === 'goal' && goalStrengthMap.has(play.eventId)) {
                        // Merge play-by-play data with landing data for goals
                        return { ...play, goalData: goalStrengthMap.get(play.eventId) }
                      }
                      return play
                    })

                  return (
                    <div className="bg-black/40 backdrop-blur-xl border border-cyan-600/30 rounded-lg p-6 shadow-xl shadow-cyan-500/10">
                      <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-cyan-600/20">
                        <ClockIcon className="w-6 h-6 text-cyan-400" />
                        <h2 className="text-xl font-military-display text-white uppercase tracking-wider">
                          Game Timeline
                        </h2>
                        <div className="flex-1"></div>
                        <div className="text-sm font-military-display text-gray-400">
                          {timelineEvents.length} Key Events
                        </div>
                      </div>
                      
                      <div className="relative">
                        {/* Timeline line */}
                        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyan-600 via-cyan-600/50 to-transparent"></div>
                        
                        <div className="space-y-4">
                          {timelineEvents.map((play: any, index: number) => {
                            const isGoal = play.typeDescKey === 'goal'
                            const isPenalty = play.typeDescKey === 'penalty'
                            const isFight = play.typeDescKey === 'fight'
                            
                            return (
                              <motion.div
                                key={`${play.eventId}-${index}`}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.03 }}
                                className="relative pl-20"
                              >
                                {/* Timeline dot */}
                                <div className={`absolute left-6 top-4 w-4 h-4 rounded-full border-2 ${
                                  isGoal ? 'bg-cyan-500 border-cyan-400 shadow-lg shadow-cyan-500/50' :
                                  isPenalty ? 'bg-red-500 border-red-400 shadow-lg shadow-red-500/50' :
                                  isFight ? 'bg-red-600 border-red-500 shadow-lg shadow-red-600/50' :
                                  'bg-gray-500 border-gray-400'
                                }`}></div>

                                <div className={`bg-white/5 backdrop-blur-sm rounded-lg p-4 border ${
                                  isGoal ? 'border-cyan-600/30 hover:border-cyan-600/50' :
                                  isPenalty ? 'border-red-600/30 hover:border-red-600/50' :
                                  isFight ? 'border-red-700/30 hover:border-red-700/50' :
                                  'border-white/10 hover:border-white/20'
                                } transition-colors`}>
                                  
                                  <div className="flex items-start justify-between mb-2">
                                    <div className="flex items-center space-x-3">
                                      <span className={`text-xs font-military-display uppercase font-bold ${
                                        isGoal ? 'text-cyan-400' :
                                        isPenalty ? 'text-red-400' :
                                        isFight ? 'text-red-400' :
                                        'text-gray-400'
                                      }`}>
                                        {isGoal ? 'GOAL' : 
                                         isPenalty ? 'PENALTY' : 
                                         isFight ? 'FIGHT' : 
                                         play.typeDescKey.toUpperCase()}
                                      </span>
                                      <span className="text-sm font-military-display text-gray-400">
                                        {play.periodDescriptor?.number && `P${play.periodDescriptor.number}`} • {play.timeInPeriod || play.timeRemaining}
                                      </span>
                                    </div>
                                    
                                    {isGoal && play.goalData && (
                                      <div className="text-lg font-military-display text-white tabular-nums">
                                        {play.goalData.awayScore} - {play.goalData.homeScore}
                                      </div>
                                    )}
                                  </div>

                                  {/* Event Details */}
                                  <div className="space-y-3">
                                    {isGoal && play.goalData && (
                                      <>
                                        {/* Scorer */}
                                        <div className="flex items-center justify-between">
                                          <div className="flex items-center space-x-3">
                                            <img 
                                              src={play.goalData.teamAbbrev.default === awayTeam.abbrev ? awayTeam.logo : homeTeam.logo} 
                                              alt="Team" 
                                              className="w-8 h-8"
                                            />
                                            <div>
                                              <div className="flex items-center space-x-2">
                                                <span className="text-lg font-military-display text-white font-bold">
                                                  {play.goalData.name.default}
                                                </span>
                                                {play.goalData.goalsToDate && (
                                                  <span className="text-sm font-military-display text-gray-500">
                                                    ({play.goalData.goalsToDate})
                                                  </span>
                                                )}
                                              </div>
                                              <div className="text-xs font-military-display text-gray-400 uppercase">
                                                Scorer
                                              </div>
                                            </div>
                                          </div>
                                          
                                          {/* Situation Text - Use API's strength field */}
                                          <div className="flex items-center space-x-2">
                                            {play.goalData.strength && play.goalData.strength !== 'ev' && (
                                              <span className={`text-sm font-military-display font-bold ${
                                                play.goalData.strength === 'pp' ? 'text-cyan-400' :
                                                play.goalData.strength === 'sh' ? 'text-red-400' :
                                                'text-gray-400'
                                              }`}>
                                                {play.goalData.strength === 'pp' ? 'POWER PLAY' :
                                                 play.goalData.strength === 'sh' ? 'SHORT HANDED' :
                                                 'EVEN STRENGTH'}
                                              </span>
                                            )}
                                          </div>
                                        </div>

                                        {/* Assists */}
                                        {play.goalData.assists && play.goalData.assists.length > 0 && (
                                          <div className="bg-black/30 rounded-lg p-3 border border-white/5">
                                            <div className="text-xs font-military-display text-gray-500 uppercase mb-2">Assists</div>
                                            <div className="flex flex-wrap gap-3">
                                              {play.goalData.assists.map((assist: any, idx: number) => (
                                                <div key={idx} className="flex items-center space-x-2">
                                                  <span className="text-sm font-military-display text-white">
                                                    {assist.name.default}
                                                  </span>
                                                  {assist.assistsToDate && (
                                                    <span className="text-xs font-military-display text-gray-500">
                                                      ({assist.assistsToDate})
                                                    </span>
                                                  )}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                        {/* Shot Type & Team */}
                                        <div className="flex items-center justify-between text-sm">
                                          <div className="flex items-center space-x-3 text-gray-400 font-military-display">
                                            <span>{play.goalData.teamAbbrev.default}</span>
                                            {play.goalData.shotType && (
                                              <>
                                                <span>•</span>
                                                <span className="uppercase">{play.goalData.shotType}</span>
                                              </>
                                            )}
                                          </div>
                                        </div>
                                      </>
                                    )}

                                    {isPenalty && play.details && (
                                      <>
                                        {/* Penalized Player & Team */}
                                        <div className="flex items-center space-x-3">
                                          <img 
                                            src={getTeamLogo(play.details.eventOwnerTeamId)} 
                                            alt="Team" 
                                            className="w-8 h-8"
                                          />
                                          <div>
                                            <div className="text-lg font-military-display text-white font-bold">
                                              {getPlayerName(play.details.committedByPlayerId)}
                                            </div>
                                            <div className="text-xs font-military-display text-gray-400 uppercase">
                                              {getTeamAbbrev(play.details.eventOwnerTeamId)} - Penalized
                                            </div>
                                          </div>
                                        </div>

                                        {/* Penalty Type */}
                                        <div className="bg-black/30 rounded-lg p-3 border border-white/5">
                                          <div className="text-xs font-military-display text-gray-500 uppercase mb-1">Infraction</div>
                                          <div className="flex items-center space-x-2">
                                            <div className="text-base font-military-display text-red-400 uppercase tracking-wide">
                                              {play.details.descKey?.replace(/-/g, ' ') || play.details.typeCode}
                                            </div>
                                            <span className="text-sm font-military-display text-gray-400">
                                              - {play.details.duration || 2} min
                                            </span>
                                          </div>
                                        </div>

                                        {/* Drawn By */}
                                        {play.details.drawnByPlayerId && (
                                          <div className="flex items-center space-x-3 text-sm">
                                            <span className="text-gray-500 font-military-display">Drawn by:</span>
                                            <span className="text-white font-military-display">
                                              {getPlayerName(play.details.drawnByPlayerId)}
                                            </span>
                                          </div>
                                        )}
                                      </>
                                    )}

                                    {isFight && play.details && (
                                      <>
                                        <div className="text-base font-military-display text-white">
                                          {play.details.player1 || 'Player 1'} vs {play.details.player2 || 'Player 2'}
                                        </div>
                                        <div className="text-sm font-military-display text-gray-400">
                                          Fight - Both players assessed fighting majors
                                        </div>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </motion.div>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  )
                })()}

                {/* Goals Section */}
                {playByPlay.summary?.scoring && playByPlay.summary.scoring.length > 0 && (
                  <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg p-6 shadow-xl">
                    <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-white/10">
                      <TrophyIcon className="w-6 h-6 text-cyan-400" />
                      <h2 className="text-xl font-military-display text-white uppercase tracking-wider">
                        Scoring Summary
                      </h2>
                    </div>
                    <div className="space-y-4">
                      {playByPlay.summary.scoring.flatMap((period: any) =>
                        period.goals?.map((goal: any, index: number) => (
                          <motion.div
                            key={`${period.period}-${index}`}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center space-x-3 mb-2">
                                  <span className="text-lg font-military-display text-white font-bold">
                                    {goal.name.default}
                                  </span>
                                  <span className="text-xs font-military-display text-gray-500">
                                    ({goal.goalsToDate})
                                  </span>
                                </div>
                                {goal.assists && goal.assists.length > 0 && (
                                  <div className="text-sm font-military-display text-gray-400 mb-3">
                                    Assists: {goal.assists.map((a: any) => a.name.default).join(', ')}
                                  </div>
                                )}
                                <div className="flex items-center space-x-3">
                                  <span className="text-sm font-military-display text-gray-400">
                                    Period {goal.period} • {goal.timeInPeriod}
                                  </span>
                                  {goal.strength !== 'ev' && (
                                    <span className={`text-xs font-military-display px-2 py-1 rounded ${
                                      goal.strength === 'pp' ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-600/30' :
                                      goal.strength === 'sh' ? 'bg-red-600/20 text-red-400 border border-red-600/30' :
                                      'bg-gray-600/20 text-gray-400 border border-gray-600/30'
                                    }`}>
                                      {goal.strength.toUpperCase()}
                                    </span>
                                  )}
                                  {goal.goalModifier === 'empty-net' && (
                                    <span className="text-xs font-military-display px-2 py-1 rounded bg-gray-600/20 text-gray-400 border border-gray-600/30">
                                      EN
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-2xl font-military-display text-white font-bold tabular-nums">
                                  {goal.awayScore}-{goal.homeScore}
                                </div>
                                <div className="text-sm font-military-display text-cyan-400 mt-1">
                                  {goal.teamAbbrev.default}
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )) || []
                      )}
                    </div>
                  </div>
                )}

              </motion.div>
            )}

            {activeTab === 'boxscore' && (
              <motion.div
                key="boxscore"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Player Stats Tables */}
                {['awayTeam', 'homeTeam'].map((teamKey) => {
                  const team = teamKey === 'awayTeam' ? awayTeam : homeTeam
                  const playerStats = boxscore.playerByGameStats[teamKey]

                  return (
                    <div key={teamKey} className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg p-6 shadow-xl">
                      {/* Team Header */}
                      <div className="flex items-center space-x-4 mb-6 pb-4 border-b border-white/10">
                        <div className="w-12 h-12 bg-gradient-to-br from-gray-700 to-gray-800 rounded-lg flex items-center justify-center border border-gray-600/50 overflow-hidden">
                          {team.logo && (
                            <img src={team.logo} alt={team.abbrev} className={`w-10 h-10 object-contain ${team.abbrev !== 'MTL' ? 'grayscale opacity-60' : ''}`} />
                          )}
                        </div>
                        <div>
                          <h2 className="text-xl font-military-display text-white uppercase tracking-wider">
                            {team.commonName.default}
                          </h2>
                          <div className="text-sm font-military-display text-gray-400">Player Statistics</div>
                        </div>
                      </div>

                      {/* Forwards */}
                      {playerStats.forwards && playerStats.forwards.length > 0 && (
                        <div className="mb-6">
                          <div className="text-xs font-military-display text-cyan-400 uppercase tracking-wider mb-3 pl-2">
                            Forwards
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="border-b border-white/10">
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">#</th>
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Player</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">G</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">A</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">P</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">+/-</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">SOG</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Hits</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">TOI</th>
                                </tr>
                              </thead>
                              <tbody>
                                {playerStats.forwards.map((player: any) => (
                                  <tr key={player.playerId} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                    <td className="py-3 px-3 text-sm font-military-display text-gray-400">{player.sweaterNumber}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-white">{player.name.default}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-white font-bold">{player.goals}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-white font-bold">{player.assists}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-cyan-400 font-bold">{player.points}</td>
                                    <td className={`py-3 px-3 text-sm font-military-display text-center font-bold ${
                                      player.plusMinus > 0 ? 'text-cyan-400' : player.plusMinus < 0 ? 'text-red-400' : 'text-gray-400'
                                    }`}>
                                      {player.plusMinus > 0 ? '+' : ''}{player.plusMinus}
                                    </td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.sog}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.hits}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.toi}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Defense */}
                      {playerStats.defense && playerStats.defense.length > 0 && (
                        <div className="mb-6">
                          <div className="text-xs font-military-display text-cyan-400 uppercase tracking-wider mb-3 pl-2">
                            Defense
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="border-b border-white/10">
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">#</th>
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Player</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">G</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">A</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">P</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">+/-</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">SOG</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Blocks</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">TOI</th>
                                </tr>
                              </thead>
                              <tbody>
                                {playerStats.defense.map((player: any) => (
                                  <tr key={player.playerId} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                    <td className="py-3 px-3 text-sm font-military-display text-gray-400">{player.sweaterNumber}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-white">{player.name.default}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-white font-bold">{player.goals}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-white font-bold">{player.assists}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-cyan-400 font-bold">{player.points}</td>
                                    <td className={`py-3 px-3 text-sm font-military-display text-center font-bold ${
                                      player.plusMinus > 0 ? 'text-cyan-400' : player.plusMinus < 0 ? 'text-red-400' : 'text-gray-400'
                                    }`}>
                                      {player.plusMinus > 0 ? '+' : ''}{player.plusMinus}
                                    </td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.sog}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.blockedShots}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.toi}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Goalies */}
                      {playerStats.goalies && playerStats.goalies.length > 0 && (
                        <div>
                          <div className="text-xs font-military-display text-cyan-400 uppercase tracking-wider mb-3 pl-2">
                            Goalies
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="border-b border-white/10">
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">#</th>
                                  <th className="text-left py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Player</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">SA</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">Saves</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">GA</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">SV%</th>
                                  <th className="text-center py-2 px-3 text-xs font-military-display text-gray-500 uppercase">TOI</th>
                                </tr>
                              </thead>
                              <tbody>
                                {playerStats.goalies.map((player: any) => (
                                  <tr key={player.playerId} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                    <td className="py-3 px-3 text-sm font-military-display text-gray-400">{player.sweaterNumber}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-white">{player.name.default}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-white">{player.saveShotsAgainst}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-cyan-400 font-bold">{player.saves}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-red-400 font-bold">{player.goalsAgainst}</td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-cyan-400 font-bold">
                                      {(player.savePctg * 100).toFixed(1)}%
                                    </td>
                                    <td className="py-3 px-3 text-sm font-military-display text-center text-gray-300">{player.toi}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </motion.div>
            )}

            {activeTab === 'plays' && (
              <motion.div
                key="plays"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg p-6 shadow-xl">
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-white/10">
                    <PlayIcon className="w-6 h-6 text-cyan-400" />
                    <h2 className="text-xl font-military-display text-white uppercase tracking-wider">
                      Play-by-Play
                    </h2>
                    <div className="text-sm font-military-display text-gray-500">
                      {playByPlay.plays?.length || 0} Events
                    </div>
                  </div>
                  
                  <div className="space-y-2 max-h-[600px] overflow-y-auto">
                    {playByPlay.plays?.slice().reverse().map((play: any, index: number) => (
                      <motion.div
                        key={play.eventId}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: Math.min(index * 0.02, 0.5) }}
                        className="bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10 hover:bg-white/10 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-1">
                              <span className={`text-xs font-military-display px-2 py-1 rounded ${
                                play.typeDescKey === 'goal' ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-600/30' :
                                play.typeDescKey === 'shot-on-goal' ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-600/30' :
                                play.typeDescKey === 'hit' ? 'bg-red-600/20 text-red-400 border border-red-600/30' :
                                play.typeDescKey === 'penalty' ? 'bg-red-700/20 text-red-400 border border-red-700/30' :
                                'bg-gray-600/20 text-gray-400 border border-gray-600/30'
                              }`}>
                                {play.typeDescKey?.replace(/-/g, ' ').toUpperCase() || 'EVENT'}
                              </span>
                              <span className="text-xs font-military-display text-gray-400">
                                P{play.period} • {play.timeInPeriod}
                              </span>
                              {play.details?.zoneCode && (
                                <span className="text-xs font-military-display text-cyan-400">
                                  {play.details.zoneCode === 'O' ? 'OFF' : play.details.zoneCode === 'D' ? 'DEF' : 'NEU'} Zone
                                </span>
                              )}
                            </div>
                            <div className="text-sm font-military-display text-white">
                              {play.details?.eventOwnerTeamId && (
                                <span className="text-cyan-400">
                                  {play.details.eventOwnerTeamId === awayTeam.id ? awayTeam.abbrev : homeTeam.abbrev}
                                </span>
                              )}
                              {' '}
                              {play.typeDescKey}
                              {play.details?.shotType && (
                                <span className="text-gray-400"> ({play.details.shotType})</span>
                              )}
                            </div>
                            {(play.details?.xCoord !== undefined && play.details?.yCoord !== undefined) && (
                              <div className="text-xs font-military-display text-gray-500 mt-1">
                                Coordinates: ({play.details.xCoord}, {play.details.yCoord})
                              </div>
                            )}
                          </div>
                          <div className="text-right text-xs font-military-display text-gray-500 tabular-nums">
                            #{play.eventId}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'ice' && (
              <motion.div
                key="ice"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg p-6 shadow-xl">
                  <div className="flex items-center space-x-3 mb-6 pb-4 border-b border-white/10">
                    <ChartBarIcon className="w-6 h-6 text-cyan-400" />
                    <h2 className="text-xl font-military-display text-white uppercase tracking-wider">
                      Ice Surface Analysis
                    </h2>
                  </div>
                  
                  {/* Ice Rink Visualization */}
                  <div className="relative w-full aspect-[2/1] bg-gradient-to-br from-gray-900/20 to-black/40 rounded-lg border border-cyan-600/30 overflow-hidden">
                    {/* Ice surface with coordinate grid */}
                    <svg viewBox="0 0 200 100" className="w-full h-full">
                      {/* Ice surface background */}
                      <rect width="200" height="100" fill="rgba(59, 130, 246, 0.05)" />
                      
                      {/* Center ice */}
                      <circle cx="100" cy="50" r="15" fill="none" stroke="rgba(6, 182, 212, 0.3)" strokeWidth="0.5" />
                      <line x1="100" y1="0" x2="100" y2="100" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="0.8" />
                      
                      {/* Blue lines */}
                      <line x1="75" y1="0" x2="75" y2="100" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="0.8" />
                      <line x1="125" y1="0" x2="125" y2="100" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="0.8" />
                      
                      {/* Goal lines */}
                      <line x1="11" y1="0" x2="11" y2="100" stroke="rgba(239, 68, 68, 0.4)" strokeWidth="0.5" />
                      <line x1="189" y1="0" x2="189" y2="100" stroke="rgba(239, 68, 68, 0.4)" strokeWidth="0.5" />
                      
                      {/* Goals */}
                      <rect x="8" y="42" width="3" height="16" fill="none" stroke="rgba(239, 68, 68, 0.5)" strokeWidth="0.5" />
                      <rect x="189" y="42" width="3" height="16" fill="none" stroke="rgba(239, 68, 68, 0.5)" strokeWidth="0.5" />
                      
                      {/* Faceoff circles */}
                      <circle cx="31" cy="30" r="8" fill="none" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="0.5" />
                      <circle cx="31" cy="70" r="8" fill="none" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="0.5" />
                      <circle cx="169" cy="30" r="8" fill="none" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="0.5" />
                      <circle cx="169" cy="70" r="8" fill="none" stroke="rgba(239, 68, 68, 0.3)" strokeWidth="0.5" />
                      
                      {/* Plot events with coordinates */}
                      {playByPlay.plays?.filter((play: any) => 
                        play.details?.xCoord !== undefined && 
                        play.details?.yCoord !== undefined &&
                        (play.typeDescKey === 'shot-on-goal' || play.typeDescKey === 'goal')
                      ).map((play: any, index: number) => {
                        // NHL coordinates: x ranges from -100 to 100, y ranges from -42.5 to 42.5
                        // Convert to SVG coordinates (0-200 x, 0-100 y)
                        const svgX = ((play.details.xCoord + 100) / 200) * 200
                        const svgY = ((play.details.yCoord + 42.5) / 85) * 100
                        
                        const isGoal = play.typeDescKey === 'goal'
                        const isHomeTeam = play.details?.eventOwnerTeamId === homeTeam.id
                        
                        return (
                          <g key={play.eventId}>
                            <circle
                              cx={svgX}
                              cy={svgY}
                              r={isGoal ? 3 : 2}
                              fill={isGoal ? 'rgba(239, 68, 68, 0.8)' : 'rgba(6, 182, 212, 0.6)'}
                              stroke={isGoal ? 'rgba(239, 68, 68, 1)' : 'rgba(6, 182, 212, 0.8)'}
                              strokeWidth="0.5"
                              className={isGoal ? 'animate-pulse' : ''}
                            />
                            {isGoal && (
                              <circle
                                cx={svgX}
                                cy={svgY}
                                r="6"
                                fill="none"
                                stroke="rgba(239, 68, 68, 0.4)"
                                strokeWidth="0.5"
                              />
                            )}
                          </g>
                        )
                      })}
                    </svg>
                    
                    {/* Legend */}
                    <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-sm rounded-lg p-3 border border-white/10">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <div className="w-3 h-3 rounded-full bg-red-500"></div>
                          <span className="text-xs font-military-display text-white">Goals</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 rounded-full bg-cyan-500"></div>
                          <span className="text-xs font-military-display text-white">Shots</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Shot Statistics */}
                  <div className="mt-6 grid grid-cols-2 gap-4">
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                      <div className="text-xs font-military-display text-gray-400 uppercase tracking-wider mb-2">
                        {awayTeam.abbrev} Shot Locations
                      </div>
                      <div className="text-2xl font-military-display text-white font-bold">
                        {playByPlay.plays?.filter((p: any) => 
                          p.details?.eventOwnerTeamId === awayTeam.id && 
                          (p.typeDescKey === 'shot-on-goal' || p.typeDescKey === 'goal')
                        ).length || 0}
                      </div>
                    </div>
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                      <div className="text-xs font-military-display text-gray-400 uppercase tracking-wider mb-2">
                        {homeTeam.abbrev} Shot Locations
                      </div>
                      <div className="text-2xl font-military-display text-white font-bold">
                        {playByPlay.plays?.filter((p: any) => 
                          p.details?.eventOwnerTeamId === homeTeam.id && 
                          (p.typeDescKey === 'shot-on-goal' || p.typeDescKey === 'goal')
                        ).length || 0}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
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
