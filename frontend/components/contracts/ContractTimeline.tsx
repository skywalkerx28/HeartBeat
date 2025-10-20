'use client'

import React, { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { ChevronDownIcon } from '@heroicons/react/24/outline'

interface PlayerContract {
  playerId: string
  playerName: string
  position: string
  capHit: number
  yearsRemaining: number
}

interface ContractTimelineProps {
  contracts: PlayerContract[]
  capCeiling: number
  totalCapHit: number
}

type MetricType = 'capCommitments' | 'contractExpirations' | 'positionBreakdown' | 'ageDistribution'

export function ContractTimeline({ contracts, capCeiling, totalCapHit }: ContractTimelineProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('capCommitments')
  const [metricDropdownOpen, setMetricDropdownOpen] = useState(false)
  
  const currentYear = 2025
  const years = [2025, 2026, 2027, 2028, 2029, 2030]

  const metrics = [
    { id: 'capCommitments' as MetricType, label: 'Cap Commitments', shortLabel: 'CAP' },
    { id: 'contractExpirations' as MetricType, label: 'Contract Expirations', shortLabel: 'EXP' },
    { id: 'positionBreakdown' as MetricType, label: 'Position Breakdown', shortLabel: 'POS' },
    { id: 'ageDistribution' as MetricType, label: 'Age Distribution', shortLabel: 'AGE' },
  ]

  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  // Cap commitments data by year
  const capCommitmentsData = useMemo(() => {
    return years.map(year => {
      const yearOffset = year - currentYear
      const activeContracts = contracts.filter(c => c.yearsRemaining > yearOffset)
      const totalCap = activeContracts.reduce((sum, c) => sum + c.capHit, 0)
      
      return {
        year: year.toString(),
        yearLabel: `${year}`,
        capHit: totalCap,
        capSpace: capCeiling - totalCap,
        playerCount: activeContracts.length,
        capCeiling: capCeiling,
      }
    })
  }, [contracts, capCeiling])

  // Contract expirations data
  const expirationsData = useMemo(() => {
    return years.map(year => {
      const yearOffset = year - currentYear
      const expiring = contracts.filter(c => c.yearsRemaining === yearOffset + 1)
      const totalExpiring = expiring.reduce((sum, c) => sum + c.capHit, 0)
      
      return {
        year: year.toString(),
        yearLabel: `${year}`,
        expiringContracts: expiring.length,
        expiringCapHit: totalExpiring,
      }
    })
  }, [contracts])

  // Position breakdown data
  const positionData = useMemo(() => {
    const positions: { [key: string]: { count: number; capHit: number } } = {
      'C': { count: 0, capHit: 0 },
      'LW': { count: 0, capHit: 0 },
      'RW': { count: 0, capHit: 0 },
      'D': { count: 0, capHit: 0 },
      'G': { count: 0, capHit: 0 },
    }
    
    contracts.forEach(c => {
      const pos = c.position || 'Unknown'
      if (positions[pos]) {
        positions[pos].count++
        positions[pos].capHit += c.capHit
      }
    })
    
    return Object.entries(positions).map(([position, data]) => ({
      position,
      count: data.count,
      capHit: data.capHit,
    }))
  }, [contracts])

  const getCurrentMetricLabel = () => {
    return metrics.find(m => m.id === selectedMetric)?.label || 'Select Metric'
  }

  return (
    <div className="space-y-4">
      {/* Header with Metric Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            CONTRACT ANALYTICS
          </h3>
        </div>
        
        {/* Metric Selector */}
        <div className="relative">
          <button
            onClick={() => setMetricDropdownOpen(!metricDropdownOpen)}
            className="flex items-center space-x-2 px-3 py-1.5 rounded border border-white/10 bg-black/40 hover:bg-white/5 transition-colors"
          >
            <span className="text-xs font-military-display text-white">
              {getCurrentMetricLabel()}
            </span>
            <ChevronDownIcon className={`w-3 h-3 text-gray-400 transition-transform ${metricDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          
          {/* Dropdown */}
          {metricDropdownOpen && (
            <div className="absolute right-0 top-full mt-1 w-56 bg-black/90 backdrop-blur-xl border border-white/10 rounded shadow-lg z-50">
              {metrics.map((metric) => (
                <button
                  key={metric.id}
                  onClick={() => {
                    setSelectedMetric(metric.id)
                    setMetricDropdownOpen(false)
                  }}
                  className={`w-full text-left px-3 py-2 text-xs font-military-display transition-colors ${
                    selectedMetric === metric.id
                      ? 'bg-white/10 text-white'
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  {metric.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chart Display */}
      <div className="relative" style={{ height: '480px' }}>
        <div className="relative h-full flex flex-col">
          
          {/* Cap Commitments Chart */}
          {selectedMetric === 'capCommitments' && (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={capCommitmentsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis 
                    dataKey="year" 
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-military-display)'
                    }}
                    formatter={(value: any) => [formatCurrency(value), '']}
                  />
                  <Bar dataKey="capHit" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.3)" name="Cap Hit" />
                  <Bar dataKey="capSpace" fill="rgba(239,68,68,0.2)" stroke="rgba(239,68,68,0.4)" name="Cap Space" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Contract Expirations Chart */}
          {selectedMetric === 'contractExpirations' && (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={expirationsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis 
                    dataKey="year" 
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-military-display)'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="expiringContracts" 
                    stroke="rgba(255,255,255,0.6)" 
                    strokeWidth={2}
                    dot={{ fill: 'rgba(255,255,255,0.8)', r: 4 }}
                    name="Expiring Contracts"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Position Breakdown Chart */}
          {selectedMetric === 'positionBreakdown' && (
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={positionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis 
                    type="number"
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <YAxis 
                    type="category"
                    dataKey="position" 
                    stroke="rgba(255,255,255,0.3)"
                    style={{ fontSize: '10px', fontFamily: 'var(--font-military-display)' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-military-display)'
                    }}
                    formatter={(value: any, name: string) => {
                      if (name === 'capHit') return [formatCurrency(value), 'Cap Hit']
                      return [value, 'Players']
                    }}
                  />
                  <Bar dataKey="capHit" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.3)" name="Cap Hit" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Age Distribution - Placeholder */}
          {selectedMetric === 'ageDistribution' && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-sm font-military-display text-gray-400 mb-2">
                  AGE DISTRIBUTION
                </div>
                <div className="text-xs font-military-display text-gray-600">
                  Coming soon - requires player age data
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

