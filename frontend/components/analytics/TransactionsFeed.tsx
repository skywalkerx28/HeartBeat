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
        <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 shadow-sm dark:bg-black/20 dark:border-white/5" />
        <div className="relative p-6 text-center">
          <div className="text-xs font-military-display text-gray-600 dark:text-gray-400">
            LOADING TRANSACTIONS...
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-lg group">
      {/* Subtle glow effect */}
      <div className="absolute inset-0 bg-gray-100/20 rounded-lg blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 dark:bg-white/[0.02]" />
      
      {/* Glass panel */}
      <div className="absolute inset-0 bg-gray-100/60 backdrop-blur-xl border border-gray-200/60 group-hover:border-gray-300/80 group-hover:bg-gray-100/80 transition-all duration-300 shadow-sm dark:bg-black/20 dark:border-white/5 dark:group-hover:border-white/10 dark:group-hover:bg-black/25 dark:shadow-black/50" />
      
      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
            <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
              Transactions
            </h4>
          </div>
          {transactions.length > 0 && (
            <div className="flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
              <span className="text-[10px] font-military-display text-red-500 uppercase tracking-wider dark:text-red-400">
                Live
              </span>
            </div>
          )}
        </div>

        {/* Transactions List */}
        {transactions.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">
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
                className="relative py-3 border-b border-gray-200 last:border-0 hover:bg-gray-50 hover:backdrop-blur-sm transition-all duration-200 rounded-sm px-1 -mx-1 dark:border-white/5 dark:hover:bg-white/[0.03]"
              >
                {/* Transaction Header - Type and Time */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-military-display text-gray-600 uppercase tracking-widest dark:text-gray-500">
                    {transaction.transaction_type}
                  </span>
                  <span className="text-[9px] font-military-display text-gray-500 uppercase dark:text-gray-600">
                    {formatTime(transaction.created_at)}
                  </span>
                </div>

                {/* Player Name - Prominent */}
                <div className="text-sm font-military-display text-gray-900 mb-1 dark:text-white">
                  {transaction.player_name}
                </div>

                {/* Teams - Simple text */}
                {(transaction.team_from || transaction.team_to) && (
                  <div className="text-[10px] font-military-display text-gray-600 mb-1.5 dark:text-gray-400">
                    {transaction.team_from && <span>{transaction.team_from}</span>}
                    {transaction.team_from && transaction.team_to && <span className="mx-1.5">→</span>}
                    {transaction.team_to && <span>{transaction.team_to}</span>}
                  </div>
                )}

                {/* Description - Clean text */}
                <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed dark:text-gray-500">
                  {transaction.description}
                </p>
              </motion.div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-gray-200 space-y-2 dark:border-white/5">
          <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider text-center dark:text-gray-600">
            Last {hours}H Activity
          </div>
          
          {/* Source Citations */}
          <div className="flex items-center justify-center space-x-1.5 text-[9px] font-military-display text-gray-500 dark:text-gray-700">
            <span className="text-gray-500 dark:text-gray-600">via</span>
            <a 
              href="https://capwages.com/moves" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-700 transition-colors duration-200 dark:hover:text-gray-500"
            >
              CapWages
            </a>
            <span>•</span>
            <a 
              href="https://www.tsn.ca/nhl/tradecentre/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-700 transition-colors duration-200 dark:hover:text-gray-500"
            >
              TSN
            </a>
            <span>•</span>
            <a 
              href="https://www.sportsnet.ca/hockey/nhl/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-700 transition-colors duration-200 dark:hover:text-gray-500"
            >
              Sportsnet
            </a>
            <span>•</span>
            <a 
              href="https://www.nhl.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-700 transition-colors duration-200 dark:hover:text-gray-500"
            >
              NHL
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
