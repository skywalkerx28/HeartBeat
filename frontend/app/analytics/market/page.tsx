'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { motion } from 'framer-motion'
import { BasePage } from '../../../components/layout/BasePage'
import { AnalyticsNavigation } from '../../../components/analytics/AnalyticsNavigation'
import { 
  ClockIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { 
  getTeamContracts, 
  getTeamCapSummary,
  PlayerContract as APIPlayerContract,
  TeamCapSummary,
  peekTeamContractsCache,
  peekTeamCapSummaryCache
} from '../../../lib/marketApi'
import { PlayerLink } from '../../../components/navigation/PlayerLink'
import { CapSpaceChart } from '../../../components/market/CapSpaceChart'

interface PlayerContract {
  playerId: string
  playerName: string
  position: string
  age: number
  capHit: number  // AAV
  capHit_2025_26?: number  // Season-specific cap hit
  dailyCapHit?: number  // Daily cap hit (cap_hit_2025_26 / 192)
  yearsRemaining: number
  performanceIndex: number
  contractEfficiency: number
  marketValue: number
  status: 'overperforming' | 'fair' | 'underperforming'
  roster_status?: string  // 'NHL', 'IR', 'Minor', 'Unsigned'
}

interface CapProjection {
  season: string
  capSpace: number
  committed: number
  projected: number
  capFloor?: number
}

export default function MarketPage() {
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const selectedTeam = 'MTL'  // Fixed to MTL - use search bar to navigate to other teams
  const [contracts, setContracts] = useState<PlayerContract[]>([])
  const [capSummary, setCapSummary] = useState<TeamCapSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAllContracts, setShowAllContracts] = useState(false)

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


  // Transform API contract into UI contract shape
  const transformContracts = (apiContracts: APIPlayerContract[]): PlayerContract[] => {
    return (apiContracts || []).map((c: APIPlayerContract) => {
      const status = (c.status as 'overperforming' | 'fair' | 'underperforming') || 'fair'
      const seasonCapHit = (c as any).cap_hit_2025_26 || c.cap_hit
      const dailyCapHit = seasonCapHit / 192
      return {
        playerId: c.nhl_player_id ? c.nhl_player_id.toString() : '0',
        playerName: (c as any).full_name || c.player_name || `Player ${c.nhl_player_id || 'Unknown'}`,
        position: c.position,
        age: (c as any).age,
        capHit: c.cap_hit,
        capHit_2025_26: seasonCapHit,
        dailyCapHit,
        yearsRemaining: c.years_remaining,
        performanceIndex: (c as any).performance_index || 100,
        contractEfficiency: (c as any).contract_efficiency || 1.0,
        marketValue: (c as any).market_value || c.cap_hit,
        status,
        roster_status: (c as any).roster_status,
      }
    })
  }


  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const run = async () => {
      // Fast path: present cached data immediately if we have it
      const cachedContracts = peekTeamContractsCache(selectedTeam, '2025-2026')
      const cachedCap = peekTeamCapSummaryCache(selectedTeam, '2025-2026', true)

      if (cachedContracts?.success && cachedContracts.data) {
        setContracts(transformContracts(cachedContracts.data.contracts || []))
        setLoading(false)
      }
      if (cachedCap?.success && cachedCap.data) {
        setCapSummary(cachedCap.data)
        setLoading(false)
      }

      // Abort any in-flight request when switching teams rapidly
      if (abortRef.current) abortRef.current.abort()
      const controller = new AbortController()
      abortRef.current = controller

      try {
        // Fetch fresh data with cache + ETag and update UI
        const [contractsResponse, capResponse] = await Promise.all([
          getTeamContracts(selectedTeam, '2025-2026', undefined, { signal: controller.signal }),
          getTeamCapSummary(selectedTeam, '2025-2026', true, { signal: controller.signal })
        ])

        if (contractsResponse?.success && contractsResponse.data) {
          setContracts(transformContracts(contractsResponse.data.contracts || []))
        }
        if (capResponse?.success && capResponse.data) {
          setCapSummary(capResponse.data)
        }
        setLastUpdated(new Date())
        setError(null)
      } catch (err) {
        if ((err as any)?.name === 'AbortError') return
        console.error('Failed to fetch market data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load market data')
        if (!cachedContracts) {
          // Fallback only when no cached data
          setContracts(mockContractsFallback)
        }
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [selectedTeam])

  // Fallback mock contract data if API fails
  const mockContractsFallback: PlayerContract[] = [
    {
      playerId: '8480018',
      playerName: 'Cole Caufield',
      position: 'RW',
      age: 23,
      capHit: 7850000,
      yearsRemaining: 7,
      performanceIndex: 142.3,
      contractEfficiency: 1.42,
      marketValue: 11200000,
      status: 'overperforming'
    },
    {
      playerId: '8479318',
      playerName: 'Nick Suzuki',
      position: 'C',
      age: 25,
      capHit: 7875000,
      yearsRemaining: 6,
      performanceIndex: 118.7,
      contractEfficiency: 1.19,
      marketValue: 9350000,
      status: 'overperforming'
    },
    {
      playerId: '8476458',
      playerName: 'Juraj Slafkovsky',
      position: 'LW',
      age: 20,
      capHit: 925000,
      yearsRemaining: 2,
      performanceIndex: 156.8,
      contractEfficiency: 1.57,
      marketValue: 1450000,
      status: 'overperforming'
    },
    {
      playerId: '8479318',
      playerName: 'Kirby Dach',
      position: 'C',
      age: 23,
      capHit: 3362500,
      yearsRemaining: 3,
      performanceIndex: 87.4,
      contractEfficiency: 0.87,
      marketValue: 2940000,
      status: 'fair'
    },
    {
      playerId: '8477476',
      playerName: 'Josh Anderson',
      position: 'RW',
      age: 30,
      capHit: 5500000,
      yearsRemaining: 2,
      performanceIndex: 68.2,
      contractEfficiency: 0.68,
      marketValue: 3750000,
      status: 'underperforming'
    }
  ]

  const mockCapProjections: CapProjection[] = [
    { season: '2024-25', capSpace: 2450000, committed: 86050000, projected: 88500000 },
    // Updated NHL cap ceilings and floors based on latest guidance
    { season: '2025-26', capSpace: 12800000, committed: 69200000, projected: 95500000, capFloor: 70600000 },
    { season: '2026-27', capSpace: 18500000, committed: 55500000, projected: 104000000, capFloor: 76900000 },
    { season: '2027-28', capSpace: 24300000, committed: 48700000, projected: 113500000, capFloor: 83900000 }
  ]

  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  // Precise currency formatter for cap calculations (to the cent)
  const formatCurrencyPrecise = (amount: number): string => {
    return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'overperforming': return 'text-white'
      case 'underperforming': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'overperforming': return 'bg-white/10 border-white/30'
      case 'underperforming': return 'bg-red-600/10 border-red-600/30'
      default: return 'bg-white/5 border-white/10'
    }
  }

  // Roster status styles (roster, soir, minors, reserve list)
  const getRosterStatusBg = (status?: string) => {
    switch ((status || '').toLowerCase()) {
      case 'roster': return 'bg-white/10 border-white/30'
      case 'soir': return 'bg-red-600/10 border-red-600/30'
      case 'minors': return 'bg-gray-600/10 border-gray-600/30'
      case 'reserve':
      case 'injured_reserve':
      case 'ir': return 'bg-red-600/10 border-red-600/30'
      case 'ltir': return 'bg-red-600/10 border-red-600/30'
      default: return 'bg-white/5 border-white/10'
    }
  }

  const getRosterStatusColor = (status?: string) => {
    switch ((status || '').toLowerCase()) {
      case 'roster': return 'text-white'
      case 'soir': return 'text-red-400'
      case 'minors': return 'text-gray-300'
      case 'reserve':
      case 'injured_reserve':
      case 'ir': return 'text-red-400'
      case 'ltir': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  // Visible contracts: first 25 by default, all when expanded
  const VISIBLE_DEFAULT = 25
  const visibleContracts = useMemo(
    () => (showAllContracts ? contracts : contracts.slice(0, VISIBLE_DEFAULT)),
    [showAllContracts, contracts]
  )

  const formatRosterStatus = (status?: string) => {
    if (!status) return '—'
    const s = status.toUpperCase()
    if (s === 'INJURED_RESERVE') return 'RESERVE'
    return s
  }

  // Calculate team-level metrics
  // CRITICAL: Only NHL + IR players count towards NHL cap (not Minor league)
  // Use season-specific cap_hit_2025_26 (accounts for bonuses/structure), not AAV
  const totalCapHit = useMemo(() => (
    contracts.length > 0
      ? contracts
          .filter(p => p.roster_status === 'NHL' || p.roster_status === 'IR')
          .reduce((sum, p) => sum + (p.capHit_2025_26 || p.capHit), 0)
      : 0
  ), [contracts])
  
  // Real cap calculations for 2025-26 season
  const capCeiling = 95500000  // 2025-26 NHL salary cap
  const capSpace = useMemo(() => capCeiling - totalCapHit, [capCeiling, totalCapHit])
  const capUsedPercentage = useMemo(() => (totalCapHit / capCeiling) * 100, [totalCapHit, capCeiling])
  
  // NHL Season Dates (2025-2026)
  const seasonStartDate = new Date('2025-10-07')  // Oct 7, 2025
  const seasonEndDate = new Date('2026-04-16')    // Apr 16, 2026
  const tradeDeadline = new Date('2026-03-06')    // Mar 6, 2026
  const today = new Date()
  
  const daysInSeason = 192  // Oct 7 to Apr 16
  const daysElapsed = Math.max(0, Math.floor((today.getTime() - seasonStartDate.getTime()) / (1000 * 60 * 60 * 24)))
  const daysToDeadline = Math.floor((tradeDeadline.getTime() - seasonStartDate.getTime()) / (1000 * 60 * 60 * 24))  // 150 days (Oct 7 to Mar 6)
  const daysRemainingAfterDeadline = Math.floor((seasonEndDate.getTime() - tradeDeadline.getTime()) / (1000 * 60 * 60 * 24))  // 41 days (Mar 6 to Apr 16)
  
  // Daily Cap Accrual Formula
  // Daily Unused Cap Space = Cap Space / Season Days
  const dailyUnusedCapSpace = useMemo(() => capSpace / daysInSeason, [capSpace])
  
  // Total Accrued Cap Space So Far (since Oct 7)
  const accruedCapSpaceSoFar = useMemo(() => dailyUnusedCapSpace * daysElapsed, [dailyUnusedCapSpace, daysElapsed])
  
  // Total Accrued Cap Space at Deadline 
  const accruedCapSpaceAtDeadline = useMemo(() => dailyUnusedCapSpace * daysToDeadline, [dailyUnusedCapSpace, daysToDeadline])
  
  // Maximum AAV Acquirable at Deadline
  // Formula: (Accrued Cap / Days Remaining After Deadline) × Total Season Days
  // This accounts for pro-rated cap hit of acquired players
  const maxAAVAtDeadline = useMemo(() => (accruedCapSpaceAtDeadline / daysRemainingAfterDeadline) * daysInSeason, [accruedCapSpaceAtDeadline, daysRemainingAfterDeadline])
  
  // LTIR Pool: Set to 0 for MTL (no players on LTIR currently)
  const ltirPool = 0
  
  const avgEfficiency = useMemo(() => (
    contracts.length > 0 ? contracts.reduce((sum, p) => sum + p.contractEfficiency, 0) / contracts.length : 1.0
  ), [contracts])
  const overperformers = useMemo(() => contracts.filter(p => p.status === 'overperforming').length, [contracts])
  const underperformers = useMemo(() => contracts.filter(p => p.status === 'underperforming').length, [contracts])

  // Real Cap Space Trajectory (calculated from actual contracts)
  const realCapProjections: CapProjection[] = [
    {
      season: '2024-25',
      capSpace: 2450000,  // Historical - keep as reference
      committed: 86050000,
      projected: 88500000
    },
    {
      season: '2025-26',
      capSpace: capSpace,  // Real current cap space
      committed: totalCapHit,  // Real current cap hit
      projected: capCeiling,  // $95.5M
      capFloor: 70600000
    },
    {
      season: '2026-27',
      capSpace: 0,  // Will calculate below
      committed: 0,  // Will calculate below
      projected: 104000000,
      capFloor: 76900000
    },
    {
      season: '2027-28',
      capSpace: 0,  // Will calculate below
      committed: 0,  // Will calculate below
      projected: 113500000,
      capFloor: 83900000
    }
  ]

  // Calculate future season commitments from contract data
  // TODO: Sum cap_hit_2026_27, cap_hit_2027_28 columns when API returns them
  // For now, estimate based on contracts with years_remaining
  const committed_26_27 = useMemo(() => (
    contracts
      .filter(c => (c.roster_status === 'roster' || c.roster_status === 'soir') && c.yearsRemaining >= 1)
      .reduce((sum, c) => sum + (c.capHit_2025_26 || c.capHit), 0)
  ), [contracts])
  realCapProjections[2].committed = committed_26_27
  realCapProjections[2].capSpace = realCapProjections[2].projected - committed_26_27

  const committed_27_28 = useMemo(() => (
    contracts
      .filter(c => (c.roster_status === 'roster' || c.roster_status === 'soir') && c.yearsRemaining >= 2)
      .reduce((sum, c) => sum + (c.capHit_2025_26 || c.capHit), 0)
  ), [contracts])
  realCapProjections[3].committed = committed_27_28
  realCapProjections[3].capSpace = realCapProjections[3].projected - committed_27_28

  return (
    <BasePage loadingMessage="LOADING MARKET ANALYTICS...">
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

        {/* Main Content Container (slightly compacted for better density) */}
        <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-4 pb-20 lg:px-12 scale-[0.90] origin-top">
          
          {/* Top Header Row - All elements aligned horizontally */}
          <div className="mb-6 py-2 grid grid-cols-3 items-center">
            {/* Left: Team Display */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-3"
            >
              <div className="flex items-center space-x-3">
                <div className="relative flex-shrink-0">
                  <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                  <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
                </div>
                
                <div>
                  <h2 className="text-xl font-military-display text-white tracking-wider whitespace-nowrap">
                    MONTREAL CANADIENS
                  </h2>
                  <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">
                    MTL • ATLANTIC
                  </div>
                </div>
              </div>
              
              <span className="text-xs font-military-display text-gray-400 ml-4 self-start mt-1">2025-2026</span>
            </motion.div>

            {/* Center: HeartBeat Logo */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center"
            >
              <h1 className="text-2xl font-military-display text-white tracking-wider">
                HEARTBEAT
              </h1>
            </motion.div>

            {/* Right: Time */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center justify-end space-x-4"
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

          {/* Analytics Navigation */}
          <AnalyticsNavigation />

          {/* Two-Column Layout: Main Content + Right Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Main Content Area (Left - 2/3 width) */}
            <div className="lg:col-span-2 space-y-8">
              
              {/* Market Overview Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    Market Overview
                  </h3>
                </div>

                <div className="grid grid-cols-4 gap-4">
                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Total Cap Hit
                      </div>
                      <div className="text-2xl font-military-display text-white tabular-nums">
                        {formatCurrency(totalCapHit)}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Active Roster
                      </div>
                    </div>
                  </div>

                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Avg Efficiency
                      </div>
                      <div className={`text-2xl font-military-display tabular-nums ${
                        avgEfficiency > 1 ? 'text-white' : avgEfficiency < 0.9 ? 'text-red-400' : 'text-gray-400'
                      }`}>
                        {avgEfficiency.toFixed(2)}x
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Value Index
                      </div>
                    </div>
                  </div>

                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Overperforming
                      </div>
                      <div className="text-2xl font-military-display text-white tabular-nums">
                        {overperformers}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Contracts
                      </div>
                    </div>
                  </div>

                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-4">
                      <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                        Underperforming
                      </div>
                      <div className="text-2xl font-military-display text-red-400 tabular-nums">
                        {underperformers}
                      </div>
                      <div className="text-[10px] font-military-display text-gray-500 mt-1">
                        Contracts
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Floating Cap Space Trajectory Chart */}
              <CapSpaceChart 
                projections={realCapProjections}
                currentCapSpace={capSpace}
                accruedCapSpace={accruedCapSpaceSoFar}
                deadlineCapSpace={maxAAVAtDeadline}
              />

              {/* Contract Efficiency Table */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    Contract Efficiency Index
                  </h3>
                </div>

                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                    <div className="relative p-5">
                      {/* Table Header */}
                      <div className="grid grid-cols-[50px_1fr_60px_50px_80px_70px_70px_80px_80px] gap-3 px-3 pb-3 border-b border-white/10 mb-2">
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">ID</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Player</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Pos</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Age</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Cap Hit</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Daily</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Eff</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Status</div>
                        <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Perf</div>
                      </div>

                    {/* Table Rows */}
                    <div className="space-y-1">
                      {visibleContracts.map((contract, index) => (
                        <motion.div
                          key={`${contract.playerId}-${index}`}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.05 + index * 0.03 }}
                          className="grid grid-cols-[50px_1fr_60px_50px_80px_70px_70px_80px_80px] gap-3 items-center p-3 rounded border bg-white/[0.02] border-white/5 hover:bg-white/5 hover:border-white/10 transition-all duration-200"
                        >
                          {/* Player ID */}
                          <div className="text-[10px] font-military-display text-gray-500 tabular-nums">
                            {contract.playerId}
                          </div>

                          {/* Player Name */}
                          <div className="text-xs font-military-display text-white">
                            <PlayerLink playerId={contract.playerId}>
                              {contract.playerName}
                            </PlayerLink>
                          </div>

                          {/* Position */}
                          <div className="text-[10px] font-military-display text-gray-400 text-center uppercase">
                            {contract.position}
                          </div>

                          {/* Age */}
                          <div className="text-[11px] font-military-display text-gray-400 text-center tabular-nums">
                            {contract.age}
                          </div>

                          {/* Cap Hit (2025-26 season-specific) */}
                          <div className="text-[11px] font-military-display text-white text-right tabular-nums">
                            {formatCurrency(contract.capHit_2025_26 || contract.capHit)}
                          </div>

                          {/* Daily Cap Hit (only for NHL/IR players) */}
                          <div className="text-[10px] font-military-display text-gray-400 text-right tabular-nums">
                            {(contract.roster_status === 'NHL' || contract.roster_status === 'IR') 
                              ? `$${(contract.dailyCapHit || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                              : '—'}
                          </div>

                  {/* Efficiency */}
                  <div className={`text-[11px] font-military-display text-center tabular-nums ${
                    contract.contractEfficiency > 1 ? 'text-white' : 
                    contract.contractEfficiency < 0.9 ? 'text-red-400' : 
                    'text-gray-400'
                  }`}>
                    {contract.contractEfficiency.toFixed(2)}x
                  </div>

                          {/* Roster Status */}
                          <div className="flex justify-center">
                            <div className={`px-2 py-0.5 rounded border text-[9px] font-military-display uppercase tracking-wider ${getRosterStatusBg(contract.roster_status)}`}>
                              <span className={getRosterStatusColor(contract.roster_status)}>
                                {formatRosterStatus(contract.roster_status)}
                              </span>
                            </div>
                          </div>

                          {/* Performance */}
                          <div className="flex justify-center">
                            <div className={`px-2 py-0.5 rounded border text-[9px] font-military-display uppercase tracking-wider ${getStatusBg(contract.status)}`}>
                              <span className={getStatusColor(contract.status)}>
                                {contract.status === 'overperforming' ? 'Over' : 
                                 contract.status === 'underperforming' ? 'Under' : 
                                 'Fair'}
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {/* Expand/Collapse control */}
                    {contracts.length > VISIBLE_DEFAULT && (
                      <div className="mt-3 flex justify-center">
                        <button
                          onClick={() => setShowAllContracts(v => !v)}
                          className="px-2 py-1 text-[11px] font-military-display text-gray-300 hover:text-white focus:outline-none"
                        >
                          {showAllContracts ? 'Show Less' : `Show All (${contracts.length - VISIBLE_DEFAULT} more)`}
                        </button>
                      </div>
                    )}

                    <div className="mt-4 pt-3 border-t border-white/5">
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
                        Efficiency: Performance Value / Contract Value
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Performance vs Contract Analysis */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <div className="flex items-center space-x-2 mb-6">
                  <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                  <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                    Value Analysis Matrix
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Overperformers */}
                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-5">
                      <div className="flex items-center space-x-2 mb-4">
                        <ArrowTrendingUpIcon className="w-4 h-4 text-gray-500" />
                        <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                          High Value Assets
                        </h4>
                      </div>
                      <div className="space-y-2">
                        {contracts
                          .filter(p => p.status === 'overperforming')
                          .map((player, idx) => (
                            <div
                              key={`${player.playerId}-${idx}`}
                              className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5"
                            >
                              <PlayerLink playerId={player.playerId} className="text-xs font-military-display text-white">
                                {player.playerName}
                              </PlayerLink>
                              <span className="text-xs font-military-display text-gray-300 tabular-nums">
                                {player.contractEfficiency.toFixed(2)}x
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>

                  {/* Underperformers */}
                  <div className="relative overflow-hidden rounded-lg">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                    <div className="relative p-5">
                      <div className="flex items-center space-x-2 mb-4">
                        <ArrowTrendingDownIcon className="w-4 h-4 text-gray-500" />
                        <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                          Risk Watch
                        </h4>
                      </div>
                      <div className="space-y-2">
                        {contracts
                          .filter(p => p.status === 'underperforming')
                          .map((player, idx) => (
                            <div
                              key={`${player.playerId}-${idx}`}
                              className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5"
                            >
                              <PlayerLink playerId={player.playerId} className="text-xs font-military-display text-white">
                                {player.playerName}
                              </PlayerLink>
                              <span className="text-xs font-military-display text-gray-300 tabular-nums">
                                {player.contractEfficiency.toFixed(2)}x
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

            </div>

            {/* Right Sidebar (1/3 width) */}
            <div className="lg:col-span-1 space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="sticky top-6 space-y-6"
              >
                {/* Cap Space Summary */}
                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        Cap Status
                      </h4>
                    </div>

                    <div className="space-y-3">
                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Current Space
                        </div>
                        <div className="text-lg font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(capSpace)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">
                          {capUsedPercentage.toFixed(3)}% Used
                        </div>
                      </div>

                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Daily Accrual
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(dailyUnusedCapSpace)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">
                          Day {daysElapsed} of {daysInSeason}
                        </div>
                      </div>

                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Accrued So Far
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(accruedCapSpaceSoFar)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">
                          Since Oct 7
                        </div>
                      </div>

                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Deadline Accrual
                        </div>
                        <div className="text-base font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(accruedCapSpaceAtDeadline)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">Projection</div>
                      </div>

                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          Max AAV Acquirable
                        </div>
                        <div className="text-lg font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(maxAAVAtDeadline)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">
                          Deadline Trade Power
                        </div>
                      </div>

                      <div className="p-3 rounded bg-white/5 border border-white/10">
                        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">
                          LTIR Pool
                        </div>
                        <div className="text-lg font-military-display text-white tabular-nums">
                          {formatCurrencyPrecise(ltirPool)}
                        </div>
                        <div className="text-[9px] font-military-display text-gray-500 mt-1">
                          Available Relief
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/5">
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
                        Updated Live
                      </div>
                    </div>
                  </div>
                </div>

                {/* Contract Alerts */}
                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        Contract Alerts
                      </h4>
                    </div>

                    <div className="space-y-2">
                      <div className="p-2 rounded border border-white/5 bg-white/[0.02]">
                        <div className="flex items-center space-x-2 mb-1">
                          <div className="w-1 h-1 bg-gray-500 rounded-full" />
                          <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
                            Expiring Soon
                          </span>
                        </div>
                        <div className="text-xs font-military-display text-white">
                          3 contracts expire 2025-26
                        </div>
                      </div>

                      <div className="p-2 rounded border border-white/5 bg-white/[0.02]">
                        <div className="flex items-center space-x-2 mb-1">
                          <div className="w-1 h-1 bg-gray-500 rounded-full" />
                          <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
                            RFA Arbitration
                          </span>
                        </div>
                        <div className="text-xs font-military-display text-white">
                          2 players eligible summer 2026
                        </div>
                      </div>

                      <div className="p-2 rounded border border-white/5 bg-white/[0.02]">
                        <div className="flex items-center space-x-2 mb-1">
                          <div className="w-1 h-1 bg-gray-500 rounded-full" />
                          <span className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
                            UFA Pool
                          </span>
                        </div>
                        <div className="text-xs font-military-display text-white">
                          5 unrestricted free agents
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Market Comparables */}
                <div className="relative overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
                  
                  <div className="relative p-5">
                    <div className="flex items-center space-x-2 mb-4">
                      <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                      <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                        League Comparables
                      </h4>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5">
                        <div>
                          <div className="text-xs font-military-display text-white">Top 5 RW AAV</div>
                          <div className="text-[10px] font-military-display text-gray-500">Position Average</div>
                        </div>
                        <div className="text-sm font-military-display text-white tabular-nums">
                          $9.2M
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5">
                        <div>
                          <div className="text-xs font-military-display text-white">Top 10 C AAV</div>
                          <div className="text-[10px] font-military-display text-gray-500">Position Average</div>
                        </div>
                        <div className="text-sm font-military-display text-white tabular-nums">
                          $8.5M
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/5">
                        <div>
                          <div className="text-xs font-military-display text-white">League Avg Cap</div>
                          <div className="text-[10px] font-military-display text-gray-500">Per Team</div>
                        </div>
                        <div className="text-sm font-military-display text-white tabular-nums">
                          $82.5M
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/5">
                      <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">
                        2024-25 Season
                      </div>
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
