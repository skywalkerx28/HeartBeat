'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { PlayerLink } from '../navigation/PlayerLink'
import {
  getTeamContracts,
  PlayerContract as APIPlayerContract,
  peekTeamContractsCache,
} from '../../lib/marketApi'

interface PlayerContract {
  playerId: string
  playerName: string
  position: string
  age: number
  capHit: number
  capHit_2025_26?: number
  dailyCapHit?: number
  yearsRemaining: number
  performanceIndex: number
  contractEfficiency: number
  marketValue: number
  status: 'overperforming' | 'fair' | 'underperforming'
  roster_status?: string
}

interface TeamRosterTableProps {
  teamId: string
  season?: string
}

export const TeamRosterTable: React.FC<TeamRosterTableProps> = ({
  teamId,
  season = '2025-2026',
}) => {
  const [contracts, setContracts] = useState<PlayerContract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAllContracts, setShowAllContracts] = useState(false)

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

  useEffect(() => {
    const run = async () => {
      const cachedContracts = peekTeamContractsCache(teamId.toUpperCase(), season)

      if (cachedContracts?.success && cachedContracts.data) {
        setContracts(transformContracts(cachedContracts.data.contracts || []))
        setLoading(false)
      }

      try {
        const contractsResponse = await getTeamContracts(teamId.toUpperCase(), season)

        if (contractsResponse?.success && contractsResponse.data) {
          setContracts(transformContracts(contractsResponse.data.contracts || []))
        }
        setError(null)
      } catch (err) {
        console.error('Failed to fetch team contracts:', err)
        setError(err instanceof Error ? err.message : 'Failed to load contracts')
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [teamId, season])

  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'overperforming': return 'text-blue-400'
      case 'underperforming': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'overperforming': return 'bg-blue-600/10 border-blue-600/30'
      case 'underperforming': return 'bg-red-600/10 border-red-600/30'
      default: return 'bg-white/5 border-white/10'
    }
  }

  const getRosterStatusBg = (status?: string) => {
    switch ((status || '').toLowerCase()) {
      case 'roster': return 'bg-blue-600/10 border-blue-600/30'
      case 'soir': return 'bg-red-600/10 border-red-600/30'
      case 'minors': return 'bg-gray-600/10 border-gray-600/30'
      case 'reserve':
      case 'injured_reserve':
      case 'ir': return 'bg-red-600/10 border-red-600/30'
      case 'ltir': return 'bg-purple-600/10 border-purple-600/30'
      default: return 'bg-white/5 border-white/10'
    }
  }

  const getRosterStatusColor = (status?: string) => {
    switch ((status || '').toLowerCase()) {
      case 'roster': return 'text-blue-400'
      case 'soir': return 'text-red-400'
      case 'minors': return 'text-gray-300'
      case 'reserve':
      case 'injured_reserve':
      case 'ir': return 'text-red-400'
      case 'ltir': return 'text-purple-400'
      default: return 'text-gray-400'
    }
  }

  const formatRosterStatus = (status?: string) => {
    if (!status) return '—'
    const s = status.toUpperCase()
    if (s === 'INJURED_RESERVE') return 'RESERVE'
    return s
  }

  const VISIBLE_DEFAULT = 25
  const visibleContracts = useMemo(
    () => (showAllContracts ? contracts : contracts.slice(0, VISIBLE_DEFAULT)),
    [showAllContracts, contracts]
  )

  // Calculate team-level metrics
  const totalCapHit = useMemo(() => (
    contracts.length > 0
      ? contracts
          .filter(p => p.roster_status === 'NHL' || p.roster_status === 'IR')
          .reduce((sum, p) => sum + (p.capHit_2025_26 || p.capHit), 0)
      : 0
  ), [contracts])

  const capCeiling = 95500000
  const capSpace = useMemo(() => capCeiling - totalCapHit, [totalCapHit])

  const avgEfficiency = useMemo(() => (
    contracts.length > 0 ? contracts.reduce((sum, p) => sum + p.contractEfficiency, 0) / contracts.length : 1.0
  ), [contracts])

  const overperformers = useMemo(() => contracts.filter(p => p.status === 'overperforming').length, [contracts])
  const underperformers = useMemo(() => contracts.filter(p => p.status === 'underperforming').length, [contracts])

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6 text-center">
          <p className="text-sm font-military-display text-gray-400">
            Loading roster data...
          </p>
        </div>
      </motion.div>
    )
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-red-600/20" />
        <div className="relative p-6 text-center">
          <p className="text-sm font-military-display text-red-400">
            {error}
          </p>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Team Overview Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
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
                Cap Space
              </div>
              <div className="text-2xl font-military-display text-white tabular-nums">
                {formatCurrency(capSpace)}
              </div>
              <div className="text-[10px] font-military-display text-gray-500 mt-1">
                Available
              </div>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-lg">
            <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
            <div className="relative p-4">
              <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
                Overperforming
              </div>
              <div className="text-2xl font-military-display text-blue-400 tabular-nums">
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

      {/* Contract Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex items-center space-x-2 mb-6">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            Organization Roster
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

                  {/* Cap Hit */}
                  <div className="text-[11px] font-military-display text-white text-right tabular-nums">
                    {formatCurrency(contract.capHit_2025_26 || contract.capHit)}
                  </div>

                  {/* Daily Cap Hit */}
                  <div className="text-[10px] font-military-display text-gray-400 text-right tabular-nums">
                    {(contract.roster_status === 'NHL' || contract.roster_status === 'IR') 
                      ? `$${(contract.dailyCapHit || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : '—'}
                  </div>

                  {/* Efficiency */}
                  <div className={`text-[11px] font-military-display text-center tabular-nums ${
                    contract.contractEfficiency > 1 ? 'text-blue-400' : 
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
    </div>
  )
}

