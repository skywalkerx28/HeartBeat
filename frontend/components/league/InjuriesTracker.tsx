'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { HeartIcon, ClockIcon } from '@heroicons/react/24/outline'

interface Injury {
  id: number
  player_name: string
  team_code: string
  injury_status: string
  injury_description: string
  return_estimate?: string
  source_url?: string
  date: string  // Actual injury date
  created_at: string  // When we scraped it
}

interface InjuriesTrackerProps {
  limit?: number
}

export function InjuriesTracker({ limit = 10 }: InjuriesTrackerProps) {
  const [injuries, setInjuries] = useState<Injury[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchInjuries()
  }, [])

  const fetchInjuries = async () => {
    try {
      // Fetch from dedicated injuries API endpoint
      const response = await fetch(`/api/v1/news/injuries?active_only=true`)
      const data = await response.json()
      
      if (!data.success || !data.injuries) {
        console.error('Invalid response from injuries API')
        setInjuries([])
        return
      }
      
      // Map injury reports to component format
      const injuryData = data.injuries
        .slice(0, limit)
        .map((injury: any) => ({
          id: injury.id,
          player_name: injury.player_name,
          team_code: injury.team_code || 'NHL',
          injury_status: normalizeInjuryStatus(injury.injury_status),
          injury_description: injury.injury_description || injury.injury_type || 'Injury',
          return_estimate: injury.return_estimate || extractReturnEstimate(injury.injury_description || ''),
          source_url: injury.source_url,
          date: injury.placed_on_ir_date || injury.created_at,
          created_at: injury.created_at
        }))
      
      setInjuries(injuryData)
    } catch (error) {
      console.error('Error fetching injuries:', error)
    } finally {
      setLoading(false)
    }
  }

  const normalizeInjuryStatus = (status: string): string => {
    if (!status) return 'OUT'
    
    const statusLower = status.toLowerCase()
    
    if (statusLower.includes('ltir') || statusLower.includes('long-term')) return 'LTIR'
    if (statusLower.includes('ir') && !statusLower.includes('ltir')) return 'IR'
    if (statusLower.includes('day-to-day')) return 'DAY-TO-DAY'
    if (statusLower.includes('week-to-week')) return 'WEEK-TO-WEEK'
    if (statusLower.includes('questionable')) return 'QUESTIONABLE'
    if (statusLower.includes('out')) return 'OUT'
    
    return 'OUT'
  }

  const extractReturnEstimate = (text: string): string | undefined => {
    // Look for patterns like "2-3 weeks", "4-6 weeks", "indefinitely", etc.
    const weekMatch = text.match(/(\d+[-–]\d+|\d+)\s*weeks?/i)
    if (weekMatch) return weekMatch[0]
    
    const monthMatch = text.match(/(\d+[-–]\d+|\d+)\s*months?/i)
    if (monthMatch) return monthMatch[0]
    
    if (text.toLowerCase().includes('indefinite')) return 'Indefinite'
    if (text.toLowerCase().includes('day-to-day')) return 'Day-to-Day'
    
    return undefined
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OUT':
      case 'IR':
      case 'LTIR':
        return 'text-red-400'
      case 'DAY-TO-DAY':
      case 'QUESTIONABLE':
        return 'text-yellow-400'
      default:
        return 'text-gray-400'
    }
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

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-xs font-military-display text-gray-500">
          LOADING INJURIES...
        </div>
      </div>
    )
  }

  if (injuries.length === 0) {
    return (
      <div className="text-center py-8">
        <HeartIcon className="w-8 h-8 text-gray-600 mx-auto mb-2" />
        <div className="text-xs font-military-display text-gray-500">
          NO INJURIES REPORTED
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {injuries.map((injury, index) => (
        <motion.div
          key={injury.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.03 }}
          className="relative group"
        >
          <a
            href={injury.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block py-3 px-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors duration-200"
          >
            <div className="flex items-start justify-between mb-1">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-military-display text-white truncate">
                    {injury.player_name}
                  </span>
                  <span className="text-[10px] font-military-display text-gray-500">
                    {injury.team_code}
                  </span>
                </div>
              </div>
              <div className={`text-[9px] font-military-display font-bold ${getStatusColor(injury.injury_status)} uppercase tracking-wider ml-2`}>
                {injury.injury_status}
              </div>
            </div>
            
            <div className="text-[11px] text-gray-400 leading-tight mb-1.5 line-clamp-2">
              {injury.injury_description}
            </div>
            
            <div className="flex items-center justify-between">
              {injury.return_estimate && (
                <div className="flex items-center space-x-1 text-[10px] text-gray-500">
                  <ClockIcon className="w-3 h-3" />
                  <span>{injury.return_estimate}</span>
                </div>
              )}
              <div className="text-[9px] font-military-display text-gray-600 ml-auto uppercase tracking-wider">
                {formatDate(injury.date)}
              </div>
            </div>
          </a>
        </motion.div>
      ))}
    </div>
  )
}

