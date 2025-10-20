'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BellAlertIcon, ArrowsRightLeftIcon, PlusCircleIcon, MinusCircleIcon } from '@heroicons/react/24/outline'

interface Transaction {
  id: string
  type: 'trade' | 'signing' | 'waiver' | 'injury' | 'recall' | 'reassignment'
  timestamp: string
  description: string
  team?: string
  player?: string
}

interface TransactionFeedProps {
  teamAbbrev: string
}

// Mock transaction data (used until real API is implemented)
const getMockTransactions = (): Transaction[] => [
  {
    id: '1',
    type: 'recall',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    description: 'Recalled F Joshua Roy from Laval (AHL)',
    team: 'MTL',
    player: 'Joshua Roy'
  },
  {
    id: '2',
    type: 'injury',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    description: 'D Mike Matheson placed on IR (upper body)',
    team: 'MTL',
    player: 'Mike Matheson'
  },
  {
    id: '3',
    type: 'reassignment',
    timestamp: new Date(Date.now() - 10800000).toISOString(),
    description: 'Assigned G Cayden Primeau to Laval (AHL)',
    team: 'MTL',
    player: 'Cayden Primeau'
  },
  {
    id: '4',
    type: 'signing',
    timestamp: new Date(Date.now() - 86400000).toISOString(),
    description: 'Signed D Logan Mailloux to 3-year ELC',
    team: 'MTL',
    player: 'Logan Mailloux'
  },
  {
    id: '5',
    type: 'trade',
    timestamp: new Date(Date.now() - 172800000).toISOString(),
    description: 'Acquired D from TOR for 2025 4th round pick',
    team: 'MTL'
  }
]

export function TransactionFeed({ teamAbbrev }: TransactionFeedProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        // Note: NHL API doesn't provide transactions endpoint yet
        // Using mock data until backend implements transactions API
        setTransactions(getMockTransactions())
        setLoading(false)
      } catch (error) {
        console.error('Failed to fetch transactions:', error)
        setTransactions(getMockTransactions())
        setLoading(false)
      }
    }
    fetchTransactions()

    // Auto-refresh every 60 seconds (currently just resets with mock data)
    const interval = setInterval(fetchTransactions, 60000)
    return () => clearInterval(interval)
  }, [teamAbbrev])

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'trade':
        return <ArrowsRightLeftIcon className="w-3 h-3" />
      case 'signing':
        return <PlusCircleIcon className="w-3 h-3" />
      case 'waiver':
        return <MinusCircleIcon className="w-3 h-3" />
      case 'recall':
        return <PlusCircleIcon className="w-3 h-3" />
      default:
        return <BellAlertIcon className="w-3 h-3" />
    }
  }

  const getTransactionColor = (type: string) => {
    switch (type) {
      case 'trade':
        return 'text-white'
      case 'signing':
        return 'text-white'
      case 'injury':
        return 'text-red-400'
      case 'recall':
        return 'text-white'
      default:
        return 'text-gray-400'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  return (
    <div className="relative overflow-hidden rounded-lg h-full flex flex-col">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      
      <div className="relative flex-1 flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 px-4 py-3 border-b border-white/5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
              LIVE ACTIVITY
            </h4>
            <div className="flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
              <span className="text-[8px] font-military-display text-gray-500 uppercase tracking-wider">
                LIVE
              </span>
            </div>
          </div>
        </div>

        {/* Transaction Feed */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="popLayout">
            {transactions.map((transaction, index) => (
              <motion.div
                key={transaction.id}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ delay: index * 0.05 }}
                className="border-b border-white/5 px-4 py-2 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-start space-x-2">
                  <div className={`flex-shrink-0 mt-0.5 ${getTransactionColor(transaction.type)}`}>
                    {getTransactionIcon(transaction.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-military-display text-white leading-relaxed">
                      {transaction.description}
                    </div>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-[8px] font-military-display text-gray-600 uppercase tracking-wider">
                        {transaction.type}
                      </span>
                      <span className="text-[8px] font-military-display text-gray-600">
                        •
                      </span>
                      <span className="text-[8px] font-military-display text-gray-600 tabular-nums">
                        {formatTimestamp(transaction.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
