'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowsRightLeftIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline'

interface Transaction {
  id: number
  player_name: string
  team_from?: string
  team_to?: string
  transaction_type: string
  description: string
  source_url?: string
  date: string  // Actual transaction date
  created_at: string  // When we scraped it
}

interface TransactionsQuickFeedProps {
  limit?: number
}

export function TransactionsQuickFeed({ limit = 15 }: TransactionsQuickFeedProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [])

  const fetchTransactions = async () => {
    try {
      const response = await fetch(`/api/v1/news/transactions?hours=168`) // Last week
      const data = await response.json()
      
      // Filter OUT injury transactions (they go to the Injuries Tracker)
      const nonInjuryTransactions = data.filter((trans: any) => {
        const type = trans.transaction_type?.toLowerCase() || ''
        const desc = trans.description?.toLowerCase() || ''
        
        // Exclude if it's an injury-related transaction
        return !(type.includes('injury') || 
                 type.includes('ir') || 
                 type.includes('ltir') ||
                 desc.includes('injured reserve') ||
                 desc.includes('injury'))
      })
      
      setTransactions(nonInjuryTransactions.slice(0, limit))
    } catch (error) {
      console.error('Error fetching transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTransactionIcon = (type: string) => {
    const lowerType = type.toLowerCase()
    if (lowerType.includes('trade') || lowerType.includes('acquire')) {
      return <ArrowsRightLeftIcon className="w-3 h-3" />
    }
    if (lowerType.includes('recall') || lowerType.includes('call-up') || lowerType.includes('signing')) {
      return <ArrowTrendingUpIcon className="w-3 h-3" />
    }
    if (lowerType.includes('assign') || lowerType.includes('waiver') || lowerType.includes('loan')) {
      return <ArrowTrendingDownIcon className="w-3 h-3" />
    }
    return <ArrowsRightLeftIcon className="w-3 h-3" />
  }

  const getTransactionColor = (type: string) => {
    const lowerType = type.toLowerCase()
    if (lowerType.includes('trade')) return 'text-red-400'
    if (lowerType.includes('signing')) return 'text-green-400'
    if (lowerType.includes('waiver')) return 'text-yellow-400'
    if (lowerType.includes('recall') || lowerType.includes('call-up')) return 'text-blue-400'
    if (lowerType.includes('assign') || lowerType.includes('loan')) return 'text-orange-400'
    return 'text-gray-400'
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    // Show relative date for recent events
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    
    // Show actual date for older events
    const month = date.toLocaleDateString('en-US', { month: 'short' })
    const day = date.getDate()
    return `${month} ${day}`
  }

  const formatTeamMove = (transaction: Transaction) => {
    if (transaction.team_from && transaction.team_to) {
      return `${transaction.team_from} → ${transaction.team_to}`
    }
    if (transaction.team_to) {
      return transaction.team_to
    }
    if (transaction.team_from) {
      return transaction.team_from
    }
    return 'NHL'
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-xs font-military-display text-gray-500">
          LOADING TRANSACTIONS...
        </div>
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="text-center py-8">
        <ArrowsRightLeftIcon className="w-8 h-8 text-gray-600 mx-auto mb-2" />
        <div className="text-xs font-military-display text-gray-500">
          NO RECENT TRANSACTIONS
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {transactions.map((transaction, index) => (
        <motion.div
          key={transaction.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.02 }}
          className="relative group"
        >
          <a
            href={transaction.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block py-2.5 px-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors duration-200"
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                <div className={`${getTransactionColor(transaction.transaction_type)}`}>
                  {getTransactionIcon(transaction.transaction_type)}
                </div>
                <span className="text-sm font-military-display text-white truncate">
                  {transaction.player_name}
                </span>
              </div>
              <div className="text-[9px] font-military-display text-gray-600 ml-2 uppercase tracking-wider">
                {formatDate(transaction.date)}
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
                {formatTeamMove(transaction)}
              </div>
              <div className={`text-[9px] font-military-display ${getTransactionColor(transaction.transaction_type)} uppercase ml-2`}>
                {transaction.transaction_type}
              </div>
            </div>
          </a>
        </motion.div>
      ))}
    </div>
  )
}

