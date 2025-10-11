'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { PlayerProfileHeader } from '../../../components/profiles/PlayerProfileHeader'
import { PlayerGameLogsTable } from '../../../components/profiles/PlayerGameLogsTable'
import { ProfileInfoCard, InfoField } from '../../../components/profiles/ProfileInfoCard'
import { PlayerProductionChart } from '../../../components/profiles/PlayerProductionChart'
import {
  getPlayerProfile,
  getPlayerGameLogs,
  PlayerProfile,
  GameLog,
} from '../../../lib/profileApi'
import { ClockIcon, ChartBarIcon } from '@heroicons/react/24/outline'

export default function PlayerProfilePage() {
  const params = useParams() as Record<string, string>
  const playerId = params?.playerId as string
  
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [player, setPlayer] = useState<PlayerProfile | null>(null)
  const [gameLogs, setGameLogs] = useState<GameLog[]>([])
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
        const [playerData, logsData] = await Promise.all([
          getPlayerProfile(playerId),
          getPlayerGameLogs(playerId),
        ])
        setPlayer(playerData)
        setGameLogs(logsData)
        setLastUpdated(new Date())
      } catch (error) {
        console.error('Error loading player data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [playerId])

  const getInfoCardFields = (): InfoField[] => {
    if (!player) return []
    
    const formatCurrency = (amount: number): string => {
      if (amount >= 1000000) {
        return `$${(amount / 1000000).toFixed(2)}M`
      }
      return `$${(amount / 1000).toFixed(0)}K`
    }

    const fields: InfoField[] = []
    
    // Bio information
    if (player.birthplace) {
      fields.push({ label: 'Birthplace', value: player.birthplace })
    }
    if (player.age) {
      fields.push({ label: 'Age', value: player.age })
    }
    if (player.heightFormatted) {
      fields.push({ label: 'Height', value: player.heightFormatted })
    }
    if (player.weightInPounds) {
      fields.push({ label: 'Weight', value: `${player.weightInPounds} lbs` })
    }
    if (player.shootsCatches) {
      fields.push({ label: 'Shoots', value: player.shootsCatches })
    }
    
    // Draft information
    if (player.draftYear && player.draftRound && player.draftOverall) {
      fields.push({ 
        label: 'Draft', 
        value: `${player.draftYear} Rd ${player.draftRound}, #${player.draftOverall}` 
      })
    }

    // Contract information
    if (player.contract) {
      fields.push(
        { label: 'Cap Hit', value: formatCurrency(player.contract.aav) },
        { label: 'Years Left', value: player.contract.yearsRemaining }
      )
    }

    return fields
  }

  if (loading || !player) {
    return (
      <BasePage loadingMessage="LOADING PLAYER PROFILE...">
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-white font-military-display">Loading...</div>
        </div>
      </BasePage>
    )
  }

  return (
    <BasePage loadingMessage="LOADING PLAYER PROFILE...">
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
            {/* Header: Profile label left, HEARTBEAT centered, clock right */}
            <div className="mb-6 py-2 grid grid-cols-3 items-center">
            {/* Left: Player Profile label */}
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
                PLAYER PROFILE
              </h2>
              <div className="text-xs font-mono text-gray-500 tracking-wider">
                ID:{playerId}
              </div>
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

          {/* Three-Column Layout: Left (identity), Middle (logs), Right (metrics) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 xl:gap-6">
            {/* Left Sidebar - Player Info (compact, sticky) */}
            <div className="lg:col-span-2 xl:col-span-2 lg:sticky top-4 self-start">
              <PlayerProfileHeader player={player} />
            </div>

            {/* Middle - Production Chart + Game Logs */}
            <div className="lg:col-span-7 xl:col-span-7 space-y-6">
              {/* Career Production Chart */}
              {player.seasonTotals && player.seasonTotals.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <PlayerProductionChart 
                    seasonTotals={player.seasonTotals} 
                    last5Games={player.last5Games}
                  />
                </motion.div>
              )}

              <PlayerGameLogsTable gameLogs={gameLogs} />
            </div>

            {/* Right - Info Card + Advanced Metrics & Trends */}
            <div className="lg:col-span-3 xl:col-span-3 space-y-6">
              {/* Profile Info Card */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <ProfileInfoCard
                  title={player.lastName}
                  subtitle={`${player.firstName} ${player.lastName}`}
                  description={`${player.position === 'L' ? 'Left Wing' : player.position === 'R' ? 'Right Wing' : player.position === 'C' ? 'Center' : player.position === 'D' ? 'Defense' : player.position} for the ${player.teamFullName}. Currently in his ${player.seasonStats.gamesPlayed > 0 ? 'active' : 'rookie'} season with ${player.seasonStats.points} points (${player.seasonStats.goals}G, ${player.seasonStats.assists}A) in ${player.seasonStats.gamesPlayed} games played.`}
                  fields={getInfoCardFields()}
                />
              </motion.div>
              {/* Advanced Metrics Preview */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-lg"
              >
                <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                <div className="relative p-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <ChartBarIcon className="w-4 h-4 text-gray-500" />
                    <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                      Advanced Metrics
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        PP Points
                      </div>
                      <div className="text-xl font-military-display text-blue-400 tabular-nums">
                        {player.seasonStats.powerPlayPoints}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        PP Goals
                      </div>
                      <div className="text-xl font-military-display text-blue-400 tabular-nums">
                        {player.seasonStats.powerPlayGoals}
                      </div>
                    </div>
                  </div>

                  {/* Enhanced NHL API stats */}
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        Hits
                      </div>
                      <div className="text-base font-military-display text-white tabular-nums">
                        {player.seasonStats.hits}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        Blocks
                      </div>
                      <div className="text-base font-military-display text-white tabular-nums">
                        {player.seasonStats.blockedShots}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        Takeaways
                      </div>
                      <div className="text-base font-military-display text-green-400 tabular-nums">
                        {player.seasonStats.takeaways}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                        Giveaways
                      </div>
                      <div className="text-base font-military-display text-red-400 tabular-nums">
                        {player.seasonStats.giveaways}
                      </div>
                    </div>
                  </div>

                  {/* Faceoff stats for centers */}
                  {player.position === 'C' && player.seasonStats.faceoffWinPct && (
                    <div className="mt-4 pt-3 border-t border-white/10">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Faceoff Statistics
                      </div>
                      <div className="text-lg font-military-display text-blue-400 tabular-nums">
                        {player.seasonStats.faceoffWinPct.toFixed(1)}%
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Faceoff Win Percentage
                      </div>
                    </div>
                  )}

                  <div className="mt-4 pt-3 border-t border-white/5">
                    <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
                      Extended analytics with xG, zone entries, and defensive metrics coming soon
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Last 5 Games Metrics */}
              {player.last5Games && player.last5Games.length > 0 && (
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
                        Last 5 Games
                      </h3>
                    </div>

                    {(() => {
                      const totals = player.last5Games!.reduce((acc, game) => ({
                        goals: acc.goals + game.goals,
                        assists: acc.assists + game.assists,
                        points: acc.points + game.points,
                        shots: acc.shots + game.shots,
                        plusMinus: acc.plusMinus + game.plusMinus,
                      }), { goals: 0, assists: 0, points: 0, shots: 0, plusMinus: 0 })

                      return (
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                              Points
                            </div>
                            <div className="text-xl font-military-display text-blue-400 tabular-nums">
                              {totals.points}
                            </div>
                          </div>

                          <div>
                            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                              Goals
                            </div>
                            <div className="text-xl font-military-display text-white tabular-nums">
                              {totals.goals}
                            </div>
                          </div>

                          <div>
                            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                              Assists
                            </div>
                            <div className="text-base font-military-display text-white tabular-nums">
                              {totals.assists}
                            </div>
                          </div>

                          <div>
                            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                              Shots
                            </div>
                            <div className="text-base font-military-display text-white tabular-nums">
                              {totals.shots}
                            </div>
                          </div>

                          <div className="col-span-2">
                            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                              +/-
                            </div>
                            <div className={`text-base font-military-display tabular-nums ${
                              totals.plusMinus > 0 ? 'text-green-400' : 
                              totals.plusMinus < 0 ? 'text-red-400' : 'text-white'
                            }`}>
                              {totals.plusMinus > 0 ? '+' : ''}{totals.plusMinus}
                            </div>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                </motion.div>
              )}

              {/* Career Totals */}
              {player.careerStats && (
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
                        Career Totals
                      </h3>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          GP
                        </div>
                        <div className="text-xl font-military-display text-white tabular-nums">
                          {player.careerStats.gamesPlayed}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Points
                        </div>
                        <div className="text-xl font-military-display text-blue-400 tabular-nums">
                          {player.careerStats.points}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Goals
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {player.careerStats.goals}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Assists
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {player.careerStats.assists}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          +/-
                        </div>
                        <div className={`text-base font-military-display tabular-nums ${
                          player.careerStats.plusMinus > 0 ? 'text-green-400' : 
                          player.careerStats.plusMinus < 0 ? 'text-red-400' : 'text-white'
                        }`}>
                          {player.careerStats.plusMinus > 0 ? '+' : ''}{player.careerStats.plusMinus}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          GWG
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {player.careerStats.gameWinningGoals}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/10 grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          PP Goals
                        </div>
                        <div className="text-sm font-military-display text-blue-400 tabular-nums">
                          {player.careerStats.powerPlayGoals}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          SH Goals
                        </div>
                        <div className="text-sm font-military-display text-blue-400 tabular-nums">
                          {player.careerStats.shortHandedGoals}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Shooting %
                        </div>
                        <div className="text-sm font-military-display text-white tabular-nums">
                          {player.careerStats.shootingPct.toFixed(1)}%
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          OT Goals
                        </div>
                        <div className="text-sm font-military-display text-white tabular-nums">
                          {player.careerStats.otGoals}
                        </div>
                      </div>
                  </div>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>
    </BasePage>
  )
}
