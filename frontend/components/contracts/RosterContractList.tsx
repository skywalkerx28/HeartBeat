'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { PlayerLink } from '../navigation/PlayerLink'

interface PlayerContract {
  playerId: string
  playerName: string
  position: string
  age: number
  capHit: number
  yearsRemaining: number
  contractType?: string
  rosterStatus?: string
  contractStatus?: string
  deadCap?: boolean
  capHitPercentage?: number
  noTradeClause?: boolean
  noMovementClause?: boolean
  baseSalary?: number
  signingBonus?: number
  birthDate?: string
  birthCountry?: string
  heightInches?: number
  weightPounds?: number
  shootsCatches?: string
  headshot?: string
  jerseyNumber?: number
}

interface RosterContractListProps {
  contracts: PlayerContract[]
  compact?: boolean
}

export function RosterContractList({ contracts, compact = false }: RosterContractListProps) {
  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  const abbreviateName = (full: string): string => {
    if (!full) return ''
    const s = full.trim()
    let first = ''
    let last = ''
    if (s.includes(',')) {
      const [l, r] = s.split(',')
      last = (l || '').trim()
      // take first token of the right side as first name
      first = (r || '').trim().split(/\s+/)[0] || ''
    } else {
      const parts = s.split(/\s+/)
      first = parts[0] || ''
      last = parts.slice(1).join(' ')
    }
    const firstInitial = first ? `${first[0].toUpperCase()}.` : ''
    const titleCase = (name: string) =>
      name
        .toLowerCase()
        .replace(/(^|[\s-])([a-z])/g, (m, p1, p2) => `${p1}${p2.toUpperCase()}`)
    const lastTitle = last ? titleCase(last) : ''
    return [firstInitial, lastTitle].filter(Boolean).join(' ')
  }

  const getContractStatusColor = (years: number) => {
    if (years <= 1) return 'text-red-400'
    if (years <= 2) return 'text-yellow-400'
    return 'text-white'
  }

  const calculateAge = (birthDate: string | undefined): number => {
    if (!birthDate) return 0
    try {
      const birth = new Date(birthDate)
      const today = new Date()
      let age = today.getFullYear() - birth.getFullYear()
      const monthDiff = today.getMonth() - birth.getMonth()
      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
        age--
      }
      return age
    } catch {
      return 0
    }
  }

  if (contracts.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="text-xs font-military-display text-gray-500 uppercase tracking-wider">
          NO CONTRACTS
        </div>
      </div>
    )
  }

  return (
    <div className="text-[9px] font-military-display overflow-x-auto">
      <div className="min-w-[500px]">
        {/* Table Header */}
        <div className="sticky top-0 bg-black/60 backdrop-blur-sm border-b border-white/10 px-3 py-2 grid grid-cols-[1fr_45px_35px_75px_55px_35px_45px] gap-2 text-gray-500 uppercase tracking-wider whitespace-nowrap">
          <div>PLAYER</div>
          <div className="text-center">POS</div>
          <div className="text-center">AGE</div>
          <div className="text-right">CAP HIT</div>
          <div className="text-right">CAP %</div>
          <div className="text-center">YRS</div>
          <div className="text-center">CLS</div>
        </div>

        {/* Table Rows */}
        <div>
          {contracts.map((contract, index) => {
          const status = (contract.contractStatus || '').toLowerCase()
          const isDead = Boolean(contract.deadCap) || status === 'buyout' || status === 'dead_cap' || status === 'retained' || status === 'buried'
          const badge = status === 'buyout' ? 'BO' : 'DC'
          const age = calculateAge(contract.birthDate)
          return (
          <motion.div
            key={`${contract.playerId}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.01 }}
            className={`grid grid-cols-[1fr_45px_35px_75px_55px_35px_45px] gap-2 px-3 py-2.5 border-b items-center transition-colors whitespace-nowrap ${
              isDead ? 'bg-red-500/5 hover:bg-red-500/10 border-red-500/20' : 'hover:bg-white/5 border-white/5'
            }`}
          >
            {/* Player Name */}
            <PlayerLink 
              playerId={contract.playerId}
              className={`${isDead ? 'text-red-300' : 'text-white hover:text-gray-300'} truncate text-[10px]`}
            >
              {abbreviateName(contract.playerName)}
            </PlayerLink>

            {/* Position */}
            <div className="text-center text-gray-400 uppercase">
              {contract.position}
            </div>

            {/* Age */}
            <div className="text-center text-gray-300 tabular-nums">
              {age > 0 ? age : '-'}
            </div>

            {/* Cap Hit */}
            <div className="text-right text-gray-300 tabular-nums">
              {formatCurrency(contract.capHit)}
            </div>

            {/* Cap % */}
            <div className="text-right text-gray-500 tabular-nums">
              {contract.capHitPercentage && contract.capHitPercentage > 0 
                ? `${contract.capHitPercentage.toFixed(1)}%` 
                : '-'}
            </div>

            {/* Years Remaining */}
            <div className={`text-center tabular-nums ${getContractStatusColor(contract.yearsRemaining)}`}>
              {contract.yearsRemaining}
            </div>

            {/* Clauses / Status */}
            <div className="flex items-center justify-center gap-0.5">
              {isDead ? (
                <span className="text-[7px] text-red-400 bg-red-500/10 px-1 rounded uppercase tracking-wider">
                  {badge}
                </span>
              ) : (
                <>
                  {contract.noMovementClause && (
                    <span className="text-[7px] text-yellow-400 bg-yellow-400/10 px-0.5 rounded">
                      NM
                    </span>
                  )}
                  {contract.noTradeClause && (
                    <span className="text-[7px] text-blue-400 bg-blue-400/10 px-0.5 rounded">
                      NT
                    </span>
                  )}
                  {!contract.noMovementClause && !contract.noTradeClause && (
                    <span className="text-gray-600">-</span>
                  )}
                </>
              )}
            </div>
          </motion.div>
          )})}
        </div>
      </div>
    </div>
  )
}
