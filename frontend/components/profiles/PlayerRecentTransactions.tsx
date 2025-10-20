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

interface PlayerRecentTransactionsProps {
  playerId: string
  playerName?: string
  limit?: number
}

export function PlayerRecentTransactions({ playerId, playerName, limit = 5 }: PlayerRecentTransactionsProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [playerId, playerName])

  const fetchTransactions = async () => {
    try {
      // Try by ID first (career history - up to 2 years)
      let url = `/api/v1/news/player/${playerId}/transactions?days=730`
      const response = await fetch(url)
      let data = await response.json()
      
      // Handle different response formats
      if (!Array.isArray(data)) {
        data = []
      }
      
      // Fallback to name-based search if ID doesn't work
      if (data.length === 0 && playerName) {
        const nameUrl = `/api/v1/news/player/?player_name=${encodeURIComponent(playerName)}&days=365`
        const nameResponse = await fetch(nameUrl)
        const nameData = await nameResponse.json()
        
        // Handle array response
        if (Array.isArray(nameData)) {
          data = nameData.filter((item: any) => item.transaction_type)
        }
      }
      
      setTransactions(Array.isArray(data) ? data.slice(0, limit) : [])
    } catch (error) {
      console.error('Error fetching player transactions:', error)
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
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
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
            LOADING TRANSACTION HISTORY...
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
            No transaction history
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
              Transaction History
            </h4>
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
              {/* Transaction Type + Date */}
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2 flex-1">
                  <div className="text-red-400">
                    {getTransactionIcon(transaction.transaction_type)}
                  </div>
                  <span className="text-sm font-military-display text-white uppercase tracking-wider">
                    {transaction.transaction_type}
                  </span>
                </div>
                <div className="text-[9px] text-gray-600 uppercase tracking-wider">
                  {formatDate(transaction.date)}
                </div>
              </div>

              {/* Teams */}
              {(transaction.team_from || transaction.team_to) && (
                <div className="ml-7 flex items-center space-x-1.5 text-[11px] font-military-display text-gray-500">
                  {transaction.team_from && (
                    <>
                      <span>{transaction.team_from}</span>
                      <span>→</span>
                    </>
                  )}
                  {transaction.team_to && (
                    <span className="text-gray-400">{transaction.team_to}</span>
                  )}
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center">
            Career Moves
          </div>
        </div>
      </div>
    </div>
  )
}

