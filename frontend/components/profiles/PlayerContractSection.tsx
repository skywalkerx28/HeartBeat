'use client'

import { motion } from 'framer-motion'
import { BanknotesIcon, DocumentTextIcon, CalendarIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { PlayerContract } from '../../lib/marketApi'

interface PlayerContractSectionProps {
  contract: PlayerContract | null
  loading?: boolean
}

export function PlayerContractSection({ contract, loading }: PlayerContractSectionProps) {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Contract Details
            </h3>
          </div>
          <div className="text-center py-8">
            <div className="text-sm font-military-display text-gray-400">
              Loading contract data...
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  if (!contract) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-lg"
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Contract Details
            </h3>
          </div>
          <div className="text-center py-4">
            <div className="text-sm font-military-display text-gray-500">
              Contract data not available
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  const getStatusColor = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'text-green-400'
      case 'injured reserve':
      case 'ir':
        return 'text-red-400'
      case 'minor':
        return 'text-gray-400'
      default:
        return 'text-white'
    }
  }

  const getContractTypeColor = (type: string): string => {
    switch (type.toLowerCase()) {
      case 'ufa':
        return 'text-white'
      case 'rfa':
        return 'text-gray-400'
      case 'elc':
        return 'text-gray-300'
      default:
        return 'text-white'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Main Contract Terms */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-6">
            <BanknotesIcon className="w-4 h-4 text-gray-500" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Contract Terms
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Average Annual Value
              </div>
              <div className="text-2xl font-military-display text-white tabular-nums">
                {formatCurrency(contract.cap_hit)}
              </div>
            </div>

            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Years Remaining
              </div>
              <div className="text-2xl font-military-display text-white tabular-nums">
                {contract.years_remaining}
              </div>
            </div>

            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Contract Type
              </div>
              <div className={`text-base font-military-display uppercase tracking-wider ${getContractTypeColor(contract.contract_type)}`}>
                {contract.contract_type}
              </div>
            </div>

            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Cap Hit %
              </div>
              <div className="text-base font-military-display text-white tabular-nums">
                {contract.cap_hit_percentage.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Current Season Cap Hit if different from AAV */}
          {contract.cap_hit_2025_26 && contract.cap_hit_2025_26 !== contract.cap_hit && (
            <div className="pt-4 border-t border-white/10">
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                2025-26 Cap Hit
              </div>
              <div className="text-xl font-military-display text-yellow-400 tabular-nums">
                {formatCurrency(contract.cap_hit_2025_26)}
              </div>
              <div className="text-xs font-military-display text-gray-400 mt-1">
                Adjusted for bonuses/structure
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status & Clauses */}
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-6">
          <div className="flex items-center space-x-2 mb-4">
            <DocumentTextIcon className="w-4 h-4 text-gray-500" />
            <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
              Status & Clauses
            </h4>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Contract Status
              </div>
              <div className={`text-sm font-military-display uppercase tracking-wider ${getStatusColor(contract.contract_status)}`}>
                {contract.contract_status}
              </div>
            </div>

            <div>
              <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                Roster Status
              </div>
              <div className={`text-sm font-military-display uppercase tracking-wider ${getStatusColor(contract.roster_status)}`}>
                {contract.roster_status}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                No-Trade Clause
              </span>
              <span className={`text-sm font-military-display ${contract.no_trade_clause ? 'text-red-400' : 'text-green-400'}`}>
                {contract.no_trade_clause ? 'YES' : 'NO'}
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
                No-Movement Clause
              </span>
              <span className={`text-sm font-military-display ${contract.no_movement_clause ? 'text-red-400' : 'text-green-400'}`}>
                {contract.no_movement_clause ? 'YES' : 'NO'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Analytics */}
      {(contract.performance_index || contract.contract_efficiency || contract.market_value || contract.surplus_value) && (
        <div className="relative overflow-hidden rounded-lg">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
          <div className="relative p-6">
            <div className="flex items-center space-x-2 mb-4">
              <ChartBarIcon className="w-4 h-4 text-gray-500" />
              <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                Performance Analytics
              </h4>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {contract.performance_index && (
                <div>
                  <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                    Performance Index
                  </div>
                  <div className="text-lg font-military-display text-white tabular-nums">
                    {contract.performance_index.toFixed(2)}
                  </div>
                </div>
              )}

              {contract.contract_efficiency && (
                <div>
                  <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                    Contract Efficiency
                  </div>
                  <div className={`text-lg font-military-display tabular-nums ${
                    contract.contract_efficiency > 1 ? 'text-green-400' : 
                    contract.contract_efficiency > 0.8 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {contract.contract_efficiency.toFixed(2)}
                  </div>
                </div>
              )}

              {contract.market_value && (
                <div>
                  <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                    Market Value
                  </div>
                  <div className="text-lg font-military-display text-white tabular-nums">
                    {formatCurrency(contract.market_value)}
                  </div>
                </div>
              )}

              {contract.surplus_value && (
                <div>
                  <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider mb-1">
                    Surplus Value
                  </div>
                  <div className={`text-lg font-military-display tabular-nums ${
                    contract.surplus_value > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {contract.surplus_value > 0 ? '+' : ''}{formatCurrency(contract.surplus_value)}
                  </div>
                  <div className="text-xs font-military-display text-gray-400 mt-0.5">
                    {contract.surplus_value > 0 ? 'Team-friendly' : 'Above market'}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Year-by-Year Breakdown */}
      {contract.contract_details && contract.contract_details.length > 0 && (
        <div className="relative overflow-hidden rounded-lg">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
          <div className="relative p-6">
            <div className="flex items-center space-x-2 mb-6">
              <CalendarIcon className="w-4 h-4 text-gray-500" />
              <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
                Year-by-Year Breakdown
              </h4>
            </div>

            {/* Table Header */}
            <div className="grid grid-cols-7 gap-2 pb-3 border-b border-white/10 mb-2">
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Season</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Cap Hit</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Cap %</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Base</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Bonus</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-right">Total</div>
              <div className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider text-center">Clause</div>
            </div>

            {/* Table Rows */}
            <div className="space-y-1">
              {contract.contract_details.map((detail: any, index: number) => {
                const season = detail.season || ''
                const isCurrent = season.startsWith('2025-26')
                const isFuture = season.startsWith('202') && parseInt(season.split('-')[0]) > 2025
                
                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className={`
                      grid grid-cols-7 gap-2 py-2 rounded transition-colors
                      ${isCurrent ? 'bg-red-600/10 border border-red-600/20' : 'hover:bg-white/5'}
                    `}
                  >
                    <div className={`text-[10px] font-military-display tabular-nums ${isCurrent ? 'text-red-400' : isFuture ? 'text-white' : 'text-gray-500'}`}>
                      {season}
                    </div>
                    <div className={`text-[10px] font-military-display tabular-nums text-right ${isCurrent ? 'text-white' : 'text-gray-400'}`}>
                      {detail.cap_hit || '-'}
                    </div>
                    <div className={`text-[10px] font-military-display tabular-nums text-right ${isCurrent ? 'text-white' : 'text-gray-400'}`}>
                      {detail.cap_percentage || '-'}
                    </div>
                    <div className="text-[10px] font-military-display tabular-nums text-right text-gray-400">
                      {detail.base_salary || '-'}
                    </div>
                    <div className="text-[10px] font-military-display tabular-nums text-right text-gray-400">
                      {detail.signing_bonuses || '-'}
                    </div>
                    <div className="text-[10px] font-military-display tabular-nums text-right text-gray-400">
                      {detail.total_salary || '-'}
                    </div>
                    <div className={`text-[9px] font-military-display text-center ${
                      detail.clause && detail.clause !== '-' 
                        ? detail.clause.includes('NMC') ? 'text-red-400' : 'text-yellow-400'
                        : 'text-gray-600'
                    }`}>
                      {detail.clause === '-' ? '' : detail.clause || ''}
                    </div>
                  </motion.div>
                )
              })}
            </div>

            {/* Legend */}
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="flex items-center justify-between text-[9px] font-military-display text-gray-500">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-red-600/50 rounded-sm" />
                    <span>Current Season</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span className="text-red-400">NMC</span>
                    <span>= No Movement</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span className="text-yellow-400">NTC</span>
                    <span>= No Trade</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}
