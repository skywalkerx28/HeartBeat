'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { AnalyticsNavigation } from '../../../components/analytics/AnalyticsNavigation'
import { 
  ClockIcon,
  UserGroupIcon,
  StarIcon,
  GlobeAltIcon,
  AcademicCapIcon,
  TrophyIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'
import { getTeamProspects, getPrimaryPosition } from '../../../lib/prospectsApi'
import type { Prospect as APIProspect } from '../../../lib/prospectsApi'

interface Prospect {
  playerId: string
  playerName: string
  position: string
  age: number
  draftYear: number
  draftRound: number
  draftPick: number
  currentLeague: string
  currentTeam: string
  gamesPlayed: number
  goals: number
  assists: number
  points: number
  plusMinus?: number
  status: 'rising' | 'steady' | 'declining'
  lastUpdate: string
  projectedNHLEta?: string
  potentialRating: 'Elite' | 'Top-6' | 'Top-4' | 'Middle-6' | 'Bottom-6' | 'Depth'
  nationality?: string
  birthplace?: string
}

type LeagueFilter = 'ALL' | 'AHL' | 'CHL' | 'NCAA' | 'EUROPE' | 'OTHER'
type PositionFilter = 'ALL' | 'F' | 'D' | 'G'
type StatusFilter = 'ALL' | 'rising' | 'steady' | 'declining'

export default function ProspectPage() {
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [leagueFilter, setLeagueFilter] = useState<LeagueFilter>('ALL')
  const [positionFilter, setPositionFilter] = useState<PositionFilter>('ALL')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [showBotStatus, setShowBotStatus] = useState(true)
  const [realProspects, setRealProspects] = useState<Prospect[]>([])
  const [loading, setLoading] = useState(true)

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

  // Load real prospect data from API
  useEffect(() => {
    const loadProspects = async () => {
      setLoading(true)
      try {
        const response = await getTeamProspects('MTL', '20252026')
        
        // Convert API prospects to UI format
        const converted: Prospect[] = response.prospects.map((p: APIProspect, idx: number) => {
          // Determine league based on nationality/location (placeholder logic)
          let league = 'OTHER'
          if (p.birthplace) {
            const birthplace = p.birthplace.toLowerCase()
            if (birthplace.includes('usa') || birthplace.includes('united states') || birthplace.includes(', michigan') || birthplace.includes(', massachusetts')) {
              league = 'NCAA'
            } else if (birthplace.includes('canada') || birthplace.includes('ontario') || birthplace.includes('quebec')) {
              league = 'CHL'
            } else {
              league = 'EUROPE'
            }
          }
          
          // Assign potential ratings based on draft position
          let potential: Prospect['potentialRating'] = 'Depth'
          if (p.draft_round) {
            if (p.draft_round === 1) potential = p.draft_pick && p.draft_pick <= 10 ? 'Elite' : 'Top-6'
            else if (p.draft_round === 2) potential = 'Top-6'
            else if (p.draft_round === 3) potential = 'Middle-6'
            else if (p.draft_round <= 5) potential = 'Bottom-6'
            else potential = 'Depth'
            
            // Adjust for defensemen
            if (p.position.toUpperCase() === 'D') {
              if (potential === 'Elite' || potential === 'Top-6') potential = 'Top-4'
              else if (potential === 'Middle-6' || potential === 'Bottom-6') potential = 'Top-4'
            }
          }
          
          return {
            playerId: `mtl-prospect-${idx}`,
            playerName: p.name,
            position: getPrimaryPosition(p.position),
            age: p.age,
            draftYear: p.draft_year || 0,
            draftRound: p.draft_round || 0,
            draftPick: p.draft_pick || 0,
            currentLeague: league,
            currentTeam: 'TBD',  // Will be populated by HeartBeat bot
            gamesPlayed: 0,  // Will be populated by HeartBeat bot
            goals: 0,  // Will be populated by HeartBeat bot
            assists: 0,  // Will be populated by HeartBeat bot
            points: 0,  // Will be populated by HeartBeat bot
            plusMinus: undefined,
            status: 'steady',  // Default to steady until bot provides updates
            lastUpdate: new Date().toISOString().split('T')[0],
            projectedNHLEta: p.draft_year ? `${(p.draft_year + 3)}-${(p.draft_year + 4).toString().slice(-2)}` : undefined,
            potentialRating: potential,
            nationality: p.nationality,
            birthplace: p.birthplace
          }
        })
        
        setRealProspects(converted)
        setLastUpdated(new Date())
      } catch (error) {
        console.error('Failed to load prospects:', error)
        // Keep mock data as fallback
      } finally {
        setLoading(false)
      }
    }
    
    loadProspects()
  }, [])

  const mockProspects: Prospect[] = [
    {
      playerId: '1001',
      playerName: 'Lane Hutson',
      position: 'D',
      age: 20,
      draftYear: 2022,
      draftRound: 2,
      draftPick: 62,
      currentLeague: 'AHL',
      currentTeam: 'Laval Rocket',
      gamesPlayed: 12,
      goals: 3,
      assists: 14,
      points: 17,
      plusMinus: 8,
      status: 'rising',
      lastUpdate: '2025-10-14',
      projectedNHLEta: '2025-26',
      potentialRating: 'Top-4'
    },
    {
      playerId: '1002',
      playerName: 'Owen Beck',
      position: 'C',
      age: 20,
      draftYear: 2022,
      draftRound: 2,
      draftPick: 33,
      currentLeague: 'AHL',
      currentTeam: 'Laval Rocket',
      gamesPlayed: 15,
      goals: 5,
      assists: 8,
      points: 13,
      plusMinus: 4,
      status: 'steady',
      lastUpdate: '2025-10-14',
      projectedNHLEta: '2025-26',
      potentialRating: 'Middle-6'
    },
    {
      playerId: '1003',
      playerName: 'Joshua Roy',
      position: 'LW',
      age: 21,
      draftYear: 2021,
      draftRound: 5,
      draftPick: 150,
      currentLeague: 'AHL',
      currentTeam: 'Laval Rocket',
      gamesPlayed: 18,
      goals: 9,
      assists: 11,
      points: 20,
      plusMinus: 6,
      status: 'rising',
      lastUpdate: '2025-10-14',
      projectedNHLEta: '2025-26',
      potentialRating: 'Top-6'
    },
    {
      playerId: '1004',
      playerName: 'Logan Mailloux',
      position: 'D',
      age: 21,
      draftYear: 2021,
      draftRound: 1,
      draftPick: 31,
      currentLeague: 'AHL',
      currentTeam: 'Laval Rocket',
      gamesPlayed: 14,
      goals: 2,
      assists: 7,
      points: 9,
      plusMinus: 2,
      status: 'steady',
      lastUpdate: '2025-10-14',
      projectedNHLEta: '2025-26',
      potentialRating: 'Top-4'
    },
    {
      playerId: '1005',
      playerName: 'Michael Hage',
      position: 'C',
      age: 19,
      draftYear: 2024,
      draftRound: 1,
      draftPick: 21,
      currentLeague: 'NCAA',
      currentTeam: 'University of Michigan',
      gamesPlayed: 8,
      goals: 4,
      assists: 6,
      points: 10,
      plusMinus: 3,
      status: 'rising',
      lastUpdate: '2025-10-13',
      projectedNHLEta: '2026-27',
      potentialRating: 'Top-6'
    },
    {
      playerId: '1006',
      playerName: 'Ivan Demidov',
      position: 'RW',
      age: 19,
      draftYear: 2024,
      draftRound: 1,
      draftPick: 5,
      currentLeague: 'EUROPE',
      currentTeam: 'SKA St. Petersburg (KHL)',
      gamesPlayed: 16,
      goals: 7,
      assists: 9,
      points: 16,
      plusMinus: 5,
      status: 'rising',
      lastUpdate: '2025-10-14',
      projectedNHLEta: '2025-26',
      potentialRating: 'Elite'
    },
    {
      playerId: '1007',
      playerName: 'Quentin Miller',
      position: 'D',
      age: 20,
      draftYear: 2023,
      draftRound: 3,
      draftPick: 78,
      currentLeague: 'CHL',
      currentTeam: 'Sudbury Wolves (OHL)',
      gamesPlayed: 10,
      goals: 3,
      assists: 12,
      points: 15,
      plusMinus: 7,
      status: 'rising',
      lastUpdate: '2025-10-13',
      projectedNHLEta: '2026-27',
      potentialRating: 'Top-4'
    },
  ]

  // Use real prospects if loaded, otherwise use mock data
  const allProspects = realProspects.length > 0 ? realProspects : mockProspects

  // Separate AHL (Laval) from other prospects
  const lavalRoster = useMemo(() => {
    return allProspects.filter(prospect => prospect.currentLeague === 'AHL')
  }, [allProspects])

  const otherProspects = useMemo(() => {
    return allProspects.filter(prospect => prospect.currentLeague !== 'AHL')
  }, [allProspects])

  // Apply filters to Laval roster
  const filteredLaval = useMemo(() => {
    return lavalRoster.filter(prospect => {
      const matchesPosition = positionFilter === 'ALL' || 
        (positionFilter === 'F' && ['C', 'LW', 'RW'].includes(prospect.position)) ||
        (positionFilter === 'D' && prospect.position === 'D') ||
        (positionFilter === 'G' && prospect.position === 'G')
      const matchesStatus = statusFilter === 'ALL' || prospect.status === statusFilter
      const matchesSearch = searchQuery === '' || 
        prospect.playerName.toLowerCase().includes(searchQuery.toLowerCase())
      
      return matchesPosition && matchesStatus && matchesSearch
    })
  }, [lavalRoster, positionFilter, statusFilter, searchQuery])

  // Apply filters to other prospects
  const filteredOthers = useMemo(() => {
    return otherProspects.filter(prospect => {
      const matchesLeague = leagueFilter === 'ALL' || prospect.currentLeague === leagueFilter
      const matchesPosition = positionFilter === 'ALL' || 
        (positionFilter === 'F' && ['C', 'LW', 'RW'].includes(prospect.position)) ||
        (positionFilter === 'D' && prospect.position === 'D') ||
        (positionFilter === 'G' && prospect.position === 'G')
      const matchesStatus = statusFilter === 'ALL' || prospect.status === statusFilter
      const matchesSearch = searchQuery === '' || 
        prospect.playerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        prospect.currentTeam.toLowerCase().includes(searchQuery.toLowerCase())
      
      return matchesLeague && matchesPosition && matchesStatus && matchesSearch
    })
  }, [otherProspects, leagueFilter, positionFilter, statusFilter, searchQuery])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'rising': return <ArrowTrendingUpIcon className="w-3 h-3 text-white" />
      case 'declining': return <ArrowTrendingDownIcon className="w-3 h-3 text-red-400" />
      default: return <div className="w-3 h-3" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'rising': return 'text-white'
      case 'declining': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'rising': return 'bg-white/10 border-white/30'
      case 'declining': return 'bg-red-600/10 border-red-600/30'
      default: return 'bg-white/5 border-white/10'
    }
  }

  const getPotentialColor = (rating: string) => {
    switch (rating) {
      case 'Elite': return 'text-red-400'
      case 'Top-6':
      case 'Top-4': return 'text-white'
      case 'Middle-6': return 'text-gray-300'
      case 'Bottom-6':
      case 'Depth': return 'text-gray-500'
      default: return 'text-gray-400'
    }
  }

  const getLeagueIcon = (league: string) => {
    switch (league) {
      case 'AHL': return <UserGroupIcon className="w-3 h-3" />
      case 'NCAA': return <AcademicCapIcon className="w-3 h-3" />
      case 'CHL': return <TrophyIcon className="w-3 h-3" />
      case 'EUROPE': return <GlobeAltIcon className="w-3 h-3" />
      default: return <StarIcon className="w-3 h-3" />
    }
  }

  const statsOverview = useMemo(() => ({
    totalProspects: allProspects.length,
    lavalRoster: lavalRoster.length,
    otherLeagues: otherProspects.length,
    risingStars: allProspects.filter(p => p.status === 'rising').length,
    eliteProspects: allProspects.filter(p => p.potentialRating === 'Elite' || p.potentialRating === 'Top-6' || p.potentialRating === 'Top-4').length,
    avgAge: allProspects.length > 0 ? Math.round(allProspects.reduce((sum, p) => sum + p.age, 0) / allProspects.length * 10) / 10 : 0,
    avgPoints: allProspects.length > 0 ? Math.round(allProspects.reduce((sum, p) => sum + p.points, 0) / allProspects.length * 10) / 10 : 0
  }), [allProspects, lavalRoster, otherProspects])

  return (
    <BasePage loadingMessage="LOADING PROSPECT ANALYTICS...">
      <div className="min-h-screen bg-gray-950 relative overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>

        <div className="absolute inset-0 bg-gradient-radial from-cyan-500/5 via-transparent to-transparent opacity-30" />

        <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-4 pb-20 lg:px-12 scale-[0.90] origin-top">
          
          <div className="mb-8 py-2 grid grid-cols-3 items-center">
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

            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center"
            >
              <h1 className="text-2xl font-military-display text-white tracking-wider">
                HEARTBEAT
              </h1>
            </motion.div>

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

          <AnalyticsNavigation />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <div className="lg:col-span-2 space-y-8">
              
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    System Overview
                  </h3>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Laval Rocket
                      </div>
                      <div className="text-2xl font-military-display text-white tabular-nums">
                        {statsOverview.lavalRoster}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        AHL Roster
                      </div>
                    </div>
                  </div>

                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Other Leagues
                      </div>
                      <div className="text-2xl font-military-display text-white tabular-nums">
                        {statsOverview.otherLeagues}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        NCAA/CHL/Europe
                      </div>
                    </div>
                  </div>

                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Rising Stars
                      </div>
                      <div className="text-2xl font-military-display text-white tabular-nums">
                        {statsOverview.risingStars}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Trending Up
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-2">
                    <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                    <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                      Filters & Search
                    </h3>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-lg mb-6">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  <div className="relative p-4">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <div>
                        <label className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mb-1 block">
                          League
                        </label>
                        <select
                          value={leagueFilter}
                          onChange={(e) => setLeagueFilter(e.target.value as LeagueFilter)}
                          className="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs font-military-display text-white focus:outline-none focus:border-white/30 transition-colors"
                        >
                          <option value="ALL">ALL LEAGUES</option>
                          <option value="AHL">AHL</option>
                          <option value="CHL">CHL</option>
                          <option value="NCAA">NCAA</option>
                          <option value="EUROPE">EUROPE</option>
                          <option value="OTHER">OTHER</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mb-1 block">
                          Position
                        </label>
                        <select
                          value={positionFilter}
                          onChange={(e) => setPositionFilter(e.target.value as PositionFilter)}
                          className="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs font-military-display text-white focus:outline-none focus:border-white/30 transition-colors"
                        >
                          <option value="ALL">ALL POSITIONS</option>
                          <option value="F">FORWARDS</option>
                          <option value="D">DEFENSE</option>
                          <option value="G">GOALIES</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mb-1 block">
                          Status
                        </label>
                        <select
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                          className="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-xs font-military-display text-white focus:outline-none focus:border-white/30 transition-colors"
                        >
                          <option value="ALL">ALL STATUS</option>
                          <option value="rising">RISING</option>
                          <option value="steady">STEADY</option>
                          <option value="declining">DECLINING</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mb-1 block">
                          Search
                        </label>
                        <div className="relative">
                          <MagnifyingGlassIcon className="w-3 h-3 text-gray-500 absolute left-2 top-1/2 -translate-y-1/2" />
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Name or team..."
                            className="w-full bg-white/5 border border-white/10 rounded pl-7 pr-2 py-1.5 text-xs font-military-display text-white placeholder-gray-600 focus:outline-none focus:border-white/30 transition-colors"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* LAVAL ROCKET ROSTER */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-red-600 to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    Laval Rocket
                  </h3>
                  <span className="text-xs font-military-display text-gray-500">
                    ({filteredLaval.length} Players)
                  </span>
                  <div className="flex items-center space-x-1 ml-2">
                    <UserGroupIcon className="w-3 h-3 text-red-400" />
                    <span className="text-[9px] font-military-display text-red-400 uppercase tracking-wider">AHL</span>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-red-600/20" />
                  
                  <div className="relative p-5">
                    <div className="grid grid-cols-[1fr_60px_50px_100px_80px_60px_70px_90px] gap-3 px-3 pb-3 border-b border-white/10 mb-2">
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Player</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Pos</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Age</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Draft</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Stats</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">+/-</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Status</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Potential</div>
                    </div>

                    <div className="space-y-1">
                      {filteredLaval.map((prospect, index) => (
                        <motion.div
                          key={prospect.playerId}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.05 + index * 0.03 }}
                          className="grid grid-cols-[1fr_60px_50px_100px_80px_60px_70px_90px] gap-3 items-center p-3 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
                        >
                          <div className="text-xs font-military-display text-white">
                            {prospect.playerName}
                          </div>

                          <div className="text-[10px] font-military-display text-gray-400 text-center uppercase">
                            {prospect.position}
                          </div>

                          <div className="text-[11px] font-military-display text-gray-400 text-center tabular-nums">
                            {prospect.age}
                          </div>

                          <div className="text-[10px] font-military-display text-gray-500 text-center tabular-nums">
                            {prospect.draftYear} R{prospect.draftRound} P{prospect.draftPick}
                          </div>

                          <div className="text-[11px] font-military-display text-white text-center tabular-nums">
                            {prospect.points}P ({prospect.goals}G {prospect.assists}A)
                          </div>

                          <div className={`text-[11px] font-military-display text-center tabular-nums ${
                            (prospect.plusMinus || 0) > 0 ? 'text-white' : 
                            (prospect.plusMinus || 0) < 0 ? 'text-red-400' : 
                            'text-gray-400'
                          }`}>
                            {prospect.plusMinus !== undefined ? (prospect.plusMinus > 0 ? '+' : '') + prospect.plusMinus : '—'}
                          </div>

                          <div className="flex justify-center">
                            <div className={`px-2 py-0.5 rounded border text-[9px] font-military-display uppercase tracking-wider flex items-center space-x-1 ${getStatusBg(prospect.status)}`}>
                              {getStatusIcon(prospect.status)}
                              <span className={getStatusColor(prospect.status)}>
                                {prospect.status === 'rising' ? 'Rise' : prospect.status === 'declining' ? 'Dec' : 'Hold'}
                              </span>
                            </div>
                          </div>

                          <div className="flex justify-center">
                            <div className={`text-[10px] font-military-display uppercase tracking-wider ${getPotentialColor(prospect.potentialRating)}`}>
                              {prospect.potentialRating}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {filteredLaval.length === 0 && (
                      <div className="text-center py-8 text-sm font-military-display text-gray-500">
                        NO LAVAL PLAYERS MATCH CURRENT FILTERS
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>

              {/* OTHER PROSPECTS (NCAA, CHL, EUROPE, ETC) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    Other Prospects
                  </h3>
                  <span className="text-xs font-military-display text-gray-500">
                    ({filteredOthers.length} Players)
                  </span>
                  <div className="flex items-center space-x-1 ml-2">
                    <GlobeAltIcon className="w-3 h-3 text-gray-400" />
                    <span className="text-[9px] font-military-display text-gray-400 uppercase tracking-wider">NCAA/CHL/Europe</span>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="grid grid-cols-[1fr_60px_50px_100px_200px_80px_60px_70px_90px] gap-3 px-3 pb-3 border-b border-white/10 mb-2">
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Player</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Pos</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Age</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Draft</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Current Team</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Stats</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">+/-</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Status</div>
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Potential</div>
                    </div>

                    <div className="space-y-1">
                      {filteredOthers.map((prospect, index) => (
                        <motion.div
                          key={prospect.playerId}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.05 + index * 0.03 }}
                          className="grid grid-cols-[1fr_60px_50px_100px_200px_80px_60px_70px_90px] gap-3 items-center p-3 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
                        >
                          <div className="text-xs font-military-display text-white">
                            {prospect.playerName}
                          </div>

                          <div className="text-[10px] font-military-display text-gray-400 text-center uppercase">
                            {prospect.position}
                          </div>

                          <div className="text-[11px] font-military-display text-gray-400 text-center tabular-nums">
                            {prospect.age}
                          </div>

                          <div className="text-[10px] font-military-display text-gray-500 text-center tabular-nums">
                            {prospect.draftYear} R{prospect.draftRound} P{prospect.draftPick}
                          </div>

                          <div className="flex items-center space-x-1.5">
                            {getLeagueIcon(prospect.currentLeague)}
                            <div className="text-[10px] font-military-display text-white truncate">
                              {prospect.currentTeam}
                            </div>
                            <div className="text-[9px] font-military-display text-gray-600">
                              ({prospect.currentLeague})
                            </div>
                          </div>

                          <div className="text-[11px] font-military-display text-white text-center tabular-nums">
                            {prospect.points}P ({prospect.goals}G {prospect.assists}A)
                          </div>

                          <div className={`text-[11px] font-military-display text-center tabular-nums ${
                            (prospect.plusMinus || 0) > 0 ? 'text-white' : 
                            (prospect.plusMinus || 0) < 0 ? 'text-red-400' : 
                            'text-gray-400'
                          }`}>
                            {prospect.plusMinus !== undefined ? (prospect.plusMinus > 0 ? '+' : '') + prospect.plusMinus : '—'}
                          </div>

                          <div className="flex justify-center">
                            <div className={`px-2 py-0.5 rounded border text-[9px] font-military-display uppercase tracking-wider flex items-center space-x-1 ${getStatusBg(prospect.status)}`}>
                              {getStatusIcon(prospect.status)}
                              <span className={getStatusColor(prospect.status)}>
                                {prospect.status === 'rising' ? 'Rise' : prospect.status === 'declining' ? 'Dec' : 'Hold'}
                              </span>
                            </div>
                          </div>

                          <div className="flex justify-center">
                            <div className={`text-[10px] font-military-display uppercase tracking-wider ${getPotentialColor(prospect.potentialRating)}`}>
                              {prospect.potentialRating}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {filteredOthers.length === 0 && (
                      <div className="text-center py-8 text-sm font-military-display text-gray-500">
                        NO OTHER PROSPECTS MATCH CURRENT FILTERS
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>

            </div>

            <div className="lg:col-span-1 space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="sticky top-6 space-y-6"
              >
                
                {showBotStatus && (
                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-red-600/30" />
                    
                    <div className="relative p-5">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                          <div className="relative">
                            <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                            <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
                          </div>
                          <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                            HeartBeat Bot
                          </h4>
                        </div>
                        <button
                          onClick={() => setShowBotStatus(false)}
                          className="text-gray-500 hover:text-white text-xs"
                        >
                          ×
                        </button>
                      </div>

                      <div className="space-y-3">
                        <div className="text-[10px] font-military-display text-gray-400 leading-relaxed">
                          Automated prospect monitoring system will scan news sources, league websites, and social media for updates on your prospects.
                        </div>

                        <div className="p-3 rounded bg-red-600/10 border border-red-600/20">
                          <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                            Status
                          </div>
                          <div className="text-xs font-military-display text-red-400">
                            COMING SOON
                          </div>
                        </div>

                        <div className="space-y-2 text-[10px] font-military-display text-gray-500">
                          <div className="flex items-center space-x-2">
                            <div className="w-1 h-1 bg-gray-700 rounded-full" />
                            <span>Auto-update player stats</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-1 h-1 bg-gray-700 rounded-full" />
                            <span>Track injuries & transactions</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-1 h-1 bg-gray-700 rounded-full" />
                            <span>Monitor performance trends</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-1 h-1 bg-gray-700 rounded-full" />
                            <span>Alert on significant events</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        Distribution
                      </h4>
                    </div>

                    <div className="space-y-3">
                      {/* Laval Rocket */}
                      <div className="p-3 rounded bg-red-600/5 border border-red-600/20">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <UserGroupIcon className="w-3 h-3 text-red-400" />
                            <span className="text-xs font-military-display text-red-400">LAVAL AHL</span>
                          </div>
                          <span className="text-sm font-military-display text-white tabular-nums">{lavalRoster.length}</span>
                        </div>
                        <div className="relative w-full h-1 bg-white/5 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${allProspects.length > 0 ? (lavalRoster.length / allProspects.length) * 100 : 0}%` }}
                            transition={{ delay: 0.3, duration: 0.5 }}
                            className="h-full bg-red-600/50"
                          />
                        </div>
                      </div>

                      {/* Other Leagues */}
                      {['NCAA', 'CHL', 'EUROPE'].map((league) => {
                        const count = otherProspects.filter(p => p.currentLeague === league).length
                        const percentage = allProspects.length > 0 ? (count / allProspects.length) * 100 : 0
                        
                        return count > 0 ? (
                          <div key={league} className="p-2 rounded bg-white/[0.02] border border-white/5">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                {getLeagueIcon(league)}
                                <span className="text-xs font-military-display text-white">{league}</span>
                              </div>
                              <span className="text-xs font-military-display text-gray-400 tabular-nums">{count}</span>
                            </div>
                            <div className="relative w-full h-1 bg-white/5 rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${percentage}%` }}
                                transition={{ delay: 0.3, duration: 0.5 }}
                                className="h-full bg-white/30"
                              />
                            </div>
                          </div>
                        ) : null
                      })}
                    </div>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        Top Performers
                      </h4>
                    </div>

                    <div className="space-y-2">
                      {allProspects
                        .sort((a, b) => b.points - a.points)
                        .slice(0, 5)
                        .map((prospect, idx) => (
                          <div
                            key={prospect.playerId}
                            className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5"
                          >
                            <div>
                              <div className="text-xs font-military-display text-white">
                                {prospect.playerName}
                              </div>
                              <div className="text-[10px] font-military-display text-gray-500">
                                {prospect.currentLeague}
                              </div>
                            </div>
                            <div className="text-xs font-military-display text-white tabular-nums">
                              {prospect.points}P
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        NHL Ready
                      </h4>
                    </div>

                    <div className="space-y-2">
                      {allProspects
                        .filter(p => p.projectedNHLEta === '2025-26')
                        .map((prospect) => (
                          <div
                            key={prospect.playerId}
                            className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5"
                          >
                            <div>
                              <div className="text-xs font-military-display text-white">
                                {prospect.playerName}
                              </div>
                              <div className="text-[10px] font-military-display text-gray-500">
                                {prospect.position} - {prospect.currentLeague}
                              </div>
                            </div>
                            <div className={`text-[10px] font-military-display uppercase ${getPotentialColor(prospect.potentialRating)}`}>
                              {prospect.potentialRating}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

              </motion.div>
            </div>

          </div>
        </div>
      </div>
    </BasePage>
  )
}

