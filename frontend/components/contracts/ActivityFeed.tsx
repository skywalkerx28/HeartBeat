'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  BellAlertIcon, 
  ArrowsRightLeftIcon, 
  PlusCircleIcon, 
  TrophyIcon,
  UserGroupIcon
} from '@heroicons/react/24/outline'

interface Transaction {
  id: string
  type: 'trade' | 'signing' | 'waiver' | 'injury' | 'recall' | 'reassignment'
  timestamp: string
  description: string
  category: 'transaction'
}

interface Prospect {
  id: string
  name: string
  position: string
  age: number
  league: string
  draftYear?: string
  category: 'prospect'
}

type ActivityItem = Transaction | Prospect

interface ActivityFeedProps {
  teamAbbrev: string
}

// Mock data generators
const getMockTransactions = (): Transaction[] => [
  {
    id: 't1',
    type: 'recall',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    description: 'Recalled F Joshua Roy from Laval (AHL)',
    category: 'transaction'
  },
  {
    id: 't2',
    type: 'injury',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    description: 'D Mike Matheson placed on IR (upper body)',
    category: 'transaction'
  },
  {
    id: 't3',
    type: 'reassignment',
    timestamp: new Date(Date.now() - 10800000).toISOString(),
    description: 'Assigned G Cayden Primeau to Laval (AHL)',
    category: 'transaction'
  },
  {
    id: 't4',
    type: 'signing',
    timestamp: new Date(Date.now() - 86400000).toISOString(),
    description: 'Signed D Logan Mailloux to 3-year ELC',
    category: 'transaction'
  }
]

const getMockProspects = (): Prospect[] => [
  { id: 'p1', name: 'Ivan Demidov', position: 'RW', age: 18, league: 'KHL', draftYear: '2024', category: 'prospect' },
  { id: 'p2', name: 'Lane Hutson', position: 'D', age: 20, league: 'NCAA', draftYear: '2022', category: 'prospect' },
  { id: 'p3', name: 'Michael Hage', position: 'C', age: 18, league: 'NCAA', draftYear: '2024', category: 'prospect' },
  { id: 'p4', name: 'David Reinbacher', position: 'D', age: 19, league: 'AHL', draftYear: '2023', category: 'prospect' },
  { id: 'p5', name: 'Joshua Roy', position: 'LW', age: 21, league: 'NHL', draftYear: '2021', category: 'prospect' }
]

export function ActivityFeed({ teamAbbrev }: ActivityFeedProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [activeTab, setActiveTab] = useState<'transactions' | 'prospects'>('transactions')

  useEffect(() => {
    // Fetch transactions
    setTransactions(getMockTransactions())
    
    // Fetch prospects
    const fetchProspects = async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
        const response = await fetch(`${API_BASE}/api/prospects/team/${teamAbbrev}?season=20252026`)
        if (response.ok) {
          const data = await response.json()
          if (data.prospects && Array.isArray(data.prospects)) {
            const transformed: Prospect[] = data.prospects.slice(0, 5).map((p: any) => ({
              id: p.nhl_id?.toString() || Math.random().toString(),
              name: p.name || 'Unknown',
              position: p.position || 'N/A',
              age: p.age || 0,
              league: 'PROSPECT',
              draftYear: p.draft_year?.toString(),
              category: 'prospect' as const
            }))
            setProspects(transformed)
          } else {
            setProspects(getMockProspects())
          }
        } else {
          setProspects(getMockProspects())
        }
      } catch (error) {
        console.error('Failed to fetch prospects:', error)
        setProspects(getMockProspects())
      }
    }
    
    fetchProspects()
  }, [teamAbbrev])

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

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'trade':
        return <ArrowsRightLeftIcon className="w-3 h-3" />
      case 'signing':
      case 'recall':
        return <PlusCircleIcon className="w-3 h-3" />
      default:
        return <BellAlertIcon className="w-3 h-3" />
    }
  }

  return (
    <div className="space-y-3">
      {/* Tab Header */}
      <div className="flex items-center space-x-6">
        <button
          onClick={() => setActiveTab('transactions')}
          className={`flex items-center transition-colors ${
            activeTab === 'transactions' ? 'text-white' : 'text-gray-600 hover:text-gray-400'
          }`}
        >
          <span className="text-xs font-military-display uppercase tracking-widest">
            Live Activity
          </span>
          {activeTab === 'transactions' && (
            <div className="flex items-center space-x-1">
              <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
            </div>
          )}
        </button>

        <button
          onClick={() => setActiveTab('prospects')}
          className={`flex items-center transition-colors ${
            activeTab === 'prospects' ? 'text-white' : 'text-gray-600 hover:text-gray-400'
          }`}
        >
          <span className="text-xs font-military-display uppercase tracking-widest">
            Top Prospects
          </span>
        </button>
      </div>

      {/* Transactions List */}
      {activeTab === 'transactions' && (
        <div className="space-y-2">
          {transactions.map((transaction, index) => (
            <motion.div
              key={transaction.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-start space-x-2 py-2 border-b border-white/5"
            >
              <div className="flex-shrink-0 mt-0.5 text-gray-500">
                {getTransactionIcon(transaction.type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-military-display text-white leading-relaxed">
                  {transaction.description}
                </div>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="text-[9px] font-military-display text-gray-600 uppercase tracking-wider">
                    {transaction.type}
                  </span>
                  <span className="text-[9px] font-military-display text-gray-600">
                    •
                  </span>
                  <span className="text-[9px] font-military-display text-gray-600 tabular-nums">
                    {formatTimestamp(transaction.timestamp)}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Prospects List */}
      {activeTab === 'prospects' && (
        <div className="space-y-2">
          {prospects.map((prospect, index) => (
            <motion.div
              key={prospect.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-center justify-between py-2 border-b border-white/5"
            >
              <div className="flex-1 min-w-0">
                <div className="text-xs font-military-display text-white">
                  {prospect.name}
                </div>
                <div className="flex items-center space-x-2 text-[9px] font-military-display text-gray-600 mt-0.5">
                  <span className="uppercase">{prospect.position}</span>
                  <span>•</span>
                  <span>AGE {prospect.age}</span>
                  <span>•</span>
                  <span className="uppercase">{prospect.league}</span>
                </div>
              </div>
              {prospect.draftYear && (
                <div className="text-[9px] font-military-display text-gray-600">
                  '{prospect.draftYear.slice(-2)}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
