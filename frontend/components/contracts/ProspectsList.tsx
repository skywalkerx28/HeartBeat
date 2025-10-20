'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { PlayerLink } from '../navigation/PlayerLink'

interface Prospect {
  playerId: string
  name: string
  position: string
  age: number
  league: string
  draftYear?: string
}

interface ProspectsListProps {
  teamAbbrev: string
}

export function ProspectsList({ teamAbbrev }: ProspectsListProps) {
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProspects = async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
        const response = await fetch(`${API_BASE}/api/prospects/team/${teamAbbrev}?season=20252026`)
        if (response.ok) {
          const data = await response.json()
          if (data.prospects && Array.isArray(data.prospects)) {
            const transformed = data.prospects.slice(0, 5).map((p: any) => ({
              playerId: p.nhl_id?.toString() || '0',
              name: p.name || 'Unknown',
              position: p.position || 'N/A',
              age: p.age || 0,
              league: 'PROSPECT',
              draftYear: p.draft_year?.toString()
            }))
            setProspects(transformed)
          } else {
            setProspects(mockProspects)
          }
        } else {
          setProspects(mockProspects)
        }
      } catch (error) {
        console.error('Failed to fetch prospects, using mock data:', error)
        setProspects(mockProspects)
      } finally {
        setLoading(false)
      }
    }
    fetchProspects()
  }, [teamAbbrev])

  const mockProspects: Prospect[] = [
    { playerId: '1', name: 'Ivan Demidov', position: 'RW', age: 18, league: 'KHL', draftYear: '2024' },
    { playerId: '2', name: 'Lane Hutson', position: 'D', age: 20, league: 'NCAA', draftYear: '2022' },
    { playerId: '3', name: 'Michael Hage', position: 'C', age: 18, league: 'NCAA', draftYear: '2024' },
    { playerId: '4', name: 'David Reinbacher', position: 'D', age: 19, league: 'AHL', draftYear: '2023' },
    { playerId: '5', name: 'Joshua Roy', position: 'LW', age: 21, league: 'NHL', draftYear: '2021' }
  ]

  const displayProspects = prospects.length > 0 ? prospects : mockProspects

  return (
    <div className="relative overflow-hidden rounded-lg h-full flex flex-col">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      
      <div className="relative flex-1 flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 px-4 py-3 border-b border-white/5">
          <h4 className="text-xs font-military-display text-white uppercase tracking-widest">
            TOP PROSPECTS
          </h4>
        </div>

        {/* Prospects List */}
        <div className="flex-1 overflow-y-auto">
          <div className="divide-y divide-white/5">
            {displayProspects.map((prospect, index) => (
              <motion.div
                key={`${prospect.playerId}-${index}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="px-4 py-2 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-military-display text-white truncate">
                      {prospect.name}
                    </div>
                    <div className="flex items-center space-x-2 text-[9px] font-military-display text-gray-500 mt-0.5">
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
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
