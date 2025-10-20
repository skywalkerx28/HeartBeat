'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { TeamProfileHeader } from '../../../components/profiles/TeamProfileHeader'
import { TeamPerformanceCharts } from '../../../components/profiles/TeamPerformanceCharts'
import { TeamAdvancedCharts } from '../../../components/profiles/TeamAdvancedCharts'
import { TeamMatchupHistory } from '../../../components/profiles/TeamMatchupHistory'
import { TeamRotationAnalytics } from '../../../components/profiles/TeamRotationAnalytics'
import { TeamRosterTable } from '../../../components/profiles/TeamRosterTable'
import { ProfileInfoCard, InfoField } from '../../../components/profiles/ProfileInfoCard'
import { TeamLatestNews } from '../../../components/profiles/TeamLatestNews'
import { TeamRecentTransactions } from '../../../components/profiles/TeamRecentTransactions'
import {
  getTeamProfile,
  getTeamPerformance,
  TeamProfile,
  TeamPerformanceData,
  getTeamAdvancedMetrics,
  TeamAdvancedMetrics,
} from '../../../lib/profileApi'
import { ClockIcon } from '@heroicons/react/24/outline'
import { TabNavigation } from '../../../components/ui'

type TabType = 'performance' | 'matchups' | 'roster' | 'cap'

export default function TeamProfilePage() {
  const params = useParams() as Record<string, string>
  const teamId = params?.teamId as string
  
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('performance')
  const [team, setTeam] = useState<TeamProfile | null>(null)
  const [performance, setPerformance] = useState<TeamPerformanceData | null>(null)
  const [advanced, setAdvanced] = useState<TeamAdvancedMetrics | null>(null)
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
    const loadData = async () => {
      setLoading(true)
      try {
        const [teamData, perfData, advData] = await Promise.all([
          getTeamProfile(teamId.toUpperCase()),
          getTeamPerformance(teamId.toUpperCase()),
          getTeamAdvancedMetrics(teamId.toUpperCase()).catch(() => null),
        ])
        setTeam(teamData)
        setPerformance(perfData)
        setAdvanced(advData)
        setLastUpdated(new Date())
      } catch (error) {
        console.error('Error loading team data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [teamId])

  const getInfoCardFields = (): InfoField[] => {
    if (!team) return []
    
    const totalGames = team.record.wins + team.record.losses + team.record.otLosses
    const pointsPercentage = totalGames > 0 ? (team.record.points / (totalGames * 2) * 100).toFixed(1) : '0.0'
    const goalDiff = team.stats.goalsFor - team.stats.goalsAgainst
    
    return [
      { label: 'Division', value: team.division },
      { label: 'Conference', value: team.conference },
      { label: 'Record', value: `${team.record.wins}-${team.record.losses}-${team.record.otLosses}` },
      { label: 'Points', value: team.record.points },
      { label: 'Points %', value: `${pointsPercentage}%` },
      { label: 'GF/GA', value: `${team.stats.goalsFor}/${team.stats.goalsAgainst}` },
      { label: 'Goal Diff', value: goalDiff > 0 ? `+${goalDiff}` : goalDiff },
      { label: 'PP%', value: `${team.stats.ppPercent.toFixed(1)}%` },
      { label: 'PK%', value: `${team.stats.pkPercent.toFixed(1)}%` },
    ]
  }

  if (loading || !team || !performance) {
    return (
      <BasePage loadingMessage="LOADING TEAM PROFILE...">
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-white font-military-display">Loading...</div>
        </div>
      </BasePage>
    )
  }

  const tabs = [
    { id: 'performance' as TabType, label: 'Performance' },
    { id: 'matchups' as TabType, label: 'Matchups' },
    { id: 'roster' as TabType, label: 'Roster' },
    { id: 'cap' as TabType, label: 'Cap Analytics' },
  ]

  return (
    <BasePage loadingMessage="LOADING TEAM PROFILE...">
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

        {/* Edge-to-edge container: use full available width */}
        <div className="relative z-10 w-full max-w-none px-4 pt-4 pb-20 lg:px-8">
          
          {/* Header container matches analytics page width so clock doesn't sit under STANLEY */}
          <div className="mx-auto max-w-screen-2xl px-6 lg:px-12">
            {/* Header: Team profile left, HEARTBEAT centered, clock right */}
            <div className="mb-6 py-2 grid grid-cols-3 items-center">
            {/* Left: Team Profile label */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-3"
            >
              <div className="relative flex-shrink-0">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
              </div>
              <h2 className="text-xl font-military-display text-white tracking-wider">
                TEAM PROFILE
              </h2>
            </motion.div>

            {/* Center: HEARTBEAT */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center"
            >
              <h1 className="text-2xl font-military-display text-white tracking-wider">
                HEARTBEAT
              </h1>
            </motion.div>

            {/* Right: Clock + SYNC */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center justify-end mr-24 md:mr-28"
            >
              <div className="flex items-center space-x-4 text-xs font-military-display">
                <div className="flex items-center space-x-2 text-gray-400">
                  <ClockIcon className="w-3.5 h-3.5" />
                  <span className="tabular-nums">{currentTime}</span>
                </div>
                <div className="flex items-center space-x-2 text-gray-500">
                  <span className="uppercase tracking-wider">SYNC</span>
                  <span className="tabular-nums">{lastUpdated?.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' }).toUpperCase()}</span>
                </div>
              </div>
            </motion.div>
            </div>
          </div>

          {/* Three-Column Layout: Left (identity), Middle (tabs/content), Right (side metrics) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 xl:gap-6">
            {/* Left Sidebar - Team Info (compact, sticky) */}
            <div className="lg:col-span-2 xl:col-span-2 lg:sticky top-4 self-start">
              <TeamProfileHeader team={team} />
            </div>

            {/* Middle - Tab Navigation + Content */}
            <div className="lg:col-span-7 xl:col-span-7 space-y-6">
              {/* Tab Navigation */}
              <TabNavigation
                tabs={tabs}
                activeTab={activeTab}
                onTabChange={(tabId) => setActiveTab(tabId as TabType)}
              />

              {/* Tab Content */}
              <div className="space-y-6">
                {activeTab === 'performance' && (
                  <>
                    <TeamPerformanceCharts data={performance} teamId={teamId} />
                    {advanced && (
                      <TeamAdvancedCharts data={advanced} teamId={teamId} />
                    )}
                  </>
                )}
                {activeTab === 'matchups' && (
                  <>
                    <TeamMatchupHistory teamId={teamId.toUpperCase()} />
                    <TeamRotationAnalytics teamId={teamId.toUpperCase()} />
                  </>
                )}
                {activeTab === 'roster' && (
                  <TeamRosterTable teamId={teamId} season="2025-2026" />
                )}
                {activeTab === 'cap' && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative overflow-hidden rounded-lg"
                  >
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-6 text-center">
                      <p className="text-sm font-military-display text-gray-400">
                        Cap analytics integration coming soon
                      </p>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>

            {/* Right - Info Card + Side Metrics/Graphs */}
            <div className="lg:col-span-3 xl:col-span-3 space-y-6">
              {/* Profile Info Card */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <ProfileInfoCard
                  title={team.abbreviation}
                  subtitle={`${team.city} ${team.name}`}
                  description={`The ${team.city} ${team.name} compete in the NHL's ${team.conference} Conference, ${team.division} Division. Currently holding a ${team.record.wins}-${team.record.losses}-${team.record.otLosses} record with ${team.record.points} points through ${team.record.gamesPlayed} games this season.`}
                  fields={getInfoCardFields()}
                  imageUrl={team.logoUrl}
                />
              </motion.div>

              {/* Key Indicators */}
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
                      Key Indicators
                    </h3>
                  </div>
                  <div className="space-y-3 text-sm font-military-display">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Points %</span>
                      <span className="text-white tabular-nums">{((team.record.points / ((team.record.wins + team.record.losses + team.record.otLosses) * 2)) * 100 || 0).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">GF/GA</span>
                      <span className="text-white tabular-nums">{team.stats.goalsFor}/{team.stats.goalsAgainst}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Special Teams</span>
                      <span className="text-white tabular-nums">PP {team.stats.ppPercent.toFixed(1)}% • PK {team.stats.pkPercent.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Latest News */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <TeamLatestNews teamCode={teamId.toUpperCase()} limit={5} />
              </motion.div>

              {/* Recent Transactions */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <TeamRecentTransactions teamCode={teamId.toUpperCase()} limit={6} />
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </BasePage>
  )
}
