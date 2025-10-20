'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowsRightLeftIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, PlusIcon, MinusIcon } from '@heroicons/react/24/outline'

interface Transaction {
  id: number
  player_name: string
  team_from?: string
  team_to?: string
  transaction_type: string
  description: string
  date: string
  created_at: string
}

interface TeamRecentTransactionsProps {
  teamCode: string
  limit?: number
}

export function TeamRecentTransactions({ teamCode, limit = 8 }: TeamRecentTransactionsProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [teamCode])

  const fetchTransactions = async () => {
    try {
      const response = await fetch(`/api/v1/news/team/${teamCode.toUpperCase()}/transactions?days=30`)
      const data = await response.json()
      
      // Handle different response formats
      if (!Array.isArray(data)) {
        setTransactions([])
        return
      }
      
      // Filter out injuries (they have their own section elsewhere)
      const nonInjuryTransactions = data.filter((trans: any) => {
        const type = trans.transaction_type?.toLowerCase() || ''
        return !['injury', 'ir', 'ltir'].includes(type)
      })
      
      setTransactions(nonInjuryTransactions.slice(0, limit))
    } catch (error) {
      console.error('Error fetching team transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getTransactionIcon = (type: string) => {
    const typeLower = type.toLowerCase()
    
    if (typeLower.includes('trade')) {
      return <ArrowsRightLeftIcon className="w-3.5 h-3.5" />
    }
    if (typeLower.includes('sign')) {
      return <PlusIcon className="w-3.5 h-3.5" />
    }
    if (typeLower.includes('recall') || typeLower.includes('call')) {
      return <ArrowTrendingUpIcon className="w-3.5 h-3.5" />
    }
    if (typeLower.includes('assign') || typeLower.includes('loan')) {
      return <ArrowTrendingDownIcon className="w-3.5 h-3.5" />
    }
    if (typeLower.includes('waiver')) {
      return <MinusIcon className="w-3.5 h-3.5" />
    }
    
    return <ArrowsRightLeftIcon className="w-3.5 h-3.5" />
  }

  if (loading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
        <div className="relative p-5 text-center">
          <div className="text-xs font-military-display text-gray-400">
            LOADING TRANSACTIONS...
          </div>
        </div>
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
        <div className="relative p-5 text-center">
          <div className="text-xs font-military-display text-gray-500">
            No recent transactions
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-lg group">
      {/* Subtle glow effect */}
      <div className="absolute inset-0 bg-white/[0.02] rounded-lg blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Glass panel */}
      <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5 group-hover:border-white/10 group-hover:bg-black/25 transition-all duration-300 shadow-lg shadow-black/50" />
      
      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
              Recent Moves
            </h4>
          </div>
          <div className="text-[9px] font-military-display text-gray-600 uppercase tracking-wider">
            Last 30D
          </div>
        </div>

        {/* Transaction Items */}
        <div className="space-y-0">
          {transactions.map((transaction, index) => (
            <motion.div
              key={transaction.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.03 }}
              className="relative py-2.5 border-b border-white/5 last:border-0 hover:bg-white/[0.03] hover:backdrop-blur-sm transition-all duration-200"
            >
              {/* Player Name + Type */}
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <div className="text-red-400">
                    {getTransactionIcon(transaction.transaction_type)}
                  </div>
                  <span className="text-sm font-military-display text-white truncate">
                    {transaction.player_name}
                  </span>
                </div>
                <div className="text-[9px] text-gray-600 uppercase tracking-wider ml-2">
                  {formatDate(transaction.date)}
                </div>
              </div>

              {/* Transaction Type */}
              <div className="ml-5">
                <span className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                  {transaction.transaction_type}
                </span>
              </div>

              {/* Teams */}
              {(transaction.team_from || transaction.team_to) && (
                <div className="ml-5 mt-0.5 flex items-center space-x-1.5 text-[10px] text-gray-600">
                  {transaction.team_from && (
                    <>
                      <span>{transaction.team_from}</span>
                      <span>→</span>
                    </>
                  )}
                  {transaction.team_to && (
                    <span className="text-gray-500">{transaction.team_to}</span>
                  )}
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center">
            Roster Activity
          </div>
        </div>
      </div>
    </div>
  )
}

