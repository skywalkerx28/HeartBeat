'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '../../lib/api'

interface Transaction {
  id: number
  date: string
  player_name: string
  player_id?: string
  team_from?: string
  team_to?: string
  transaction_type: string
  description: string
  source_url?: string
  created_at: string
}

interface TransactionsFeedProps {
  hours?: number
  isLoading?: boolean
}

export function TransactionsFeed({ hours = 72, isLoading }: TransactionsFeedProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [hours])

  const fetchTransactions = async () => {
    setLoading(true)
    try {
      const data = await api.getTransactions(hours)
      setTransactions(data.slice(0, 8))
    } catch (error) {
      console.error('Error fetching transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 5) return 'NOW'
    if (diffMins < 60) return `${diffMins}M`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}H`
    return `${Math.floor(diffMins / 1440)}D`
  }

  if (loading || isLoading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
        <div className="relative p-6 text-center">
          <div className="text-xs font-military-display text-gray-400">
            LOADING TRANSACTIONS...
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
              Transactions
            </h4>
          </div>
          {transactions.length > 0 && (
            <div className="flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
              <span className="text-[10px] font-military-display text-red-400 uppercase tracking-wider">
                Live
              </span>
            </div>
          )}
        </div>

        {/* Transactions List */}
        {transactions.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-xs font-military-display text-gray-500">
              NO TRANSACTIONS IN LAST {hours}H
            </div>
          </div>
        ) : (
          <div className="space-y-0">
            {transactions.map((transaction, index) => (
              <motion.div
                key={transaction.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
                className="relative py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.03] hover:backdrop-blur-sm transition-all duration-200 rounded-sm px-1 -mx-1"
              >
                {/* Transaction Header - Type and Time */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-widest">
                    {transaction.transaction_type}
                  </span>
                  <span className="text-[9px] font-military-display text-gray-600 uppercase">
                    {formatTime(transaction.created_at)}
                  </span>
                </div>

                {/* Player Name - Prominent */}
                <div className="text-sm font-military-display text-white mb-1">
                  {transaction.player_name}
                </div>

                {/* Teams - Simple text */}
                {(transaction.team_from || transaction.team_to) && (
                  <div className="text-[10px] font-military-display text-gray-400 mb-1.5">
                    {transaction.team_from && <span>{transaction.team_from}</span>}
                    {transaction.team_from && transaction.team_to && <span className="mx-1.5">→</span>}
                    {transaction.team_to && <span>{transaction.team_to}</span>}
                  </div>
                )}

                {/* Description - Clean text */}
                <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                  {transaction.description}
                </p>
              </motion.div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-white/5 space-y-2">
          <div className="text-[10px] font-military-display text-gray-600 uppercase tracking-wider text-center">
            Last {hours}H Activity
          </div>
          
          {/* Source Citations */}
          <div className="flex items-center justify-center space-x-1.5 text-[9px] font-military-display text-gray-700">
            <span className="text-gray-600">via</span>
            <a 
              href="https://capwages.com/moves" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-500 transition-colors duration-200"
            >
              CapWages
            </a>
            <span>•</span>
            <a 
              href="https://www.tsn.ca/nhl/tradecentre/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-500 transition-colors duration-200"
            >
              TSN
            </a>
            <span>•</span>
            <a 
              href="https://www.sportsnet.ca/hockey/nhl/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-500 transition-colors duration-200"
            >
              Sportsnet
            </a>
            <span>•</span>
            <a 
              href="https://www.nhl.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-500 transition-colors duration-200"
            >
              NHL
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
