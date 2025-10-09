'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ClockIcon } from '@heroicons/react/24/outline'

interface LeagueEvent {
  id: string
  title: string
  summary: string
  timestamp: string
  category?: 'trade' | 'injury' | 'performance' | 'standings' | 'general'
  relevance: 'high' | 'medium' | 'low'
}

interface LeagueSummaryProps {
  events?: LeagueEvent[]
  isLoading?: boolean
}

export function LeagueSummary({ events = [], isLoading }: LeagueSummaryProps) {
  const mockEvents: LeagueEvent[] = events.length > 0 ? events : [
    {
      id: '1',
      title: 'Atlantic Division Tightens After Weekend Series',
      summary: 'The Montreal Canadiens pulled within 3 points of the third playoff spot following a decisive 4-1 victory over the Buffalo Sabres. Key performances from Cole Caufield (2G, 1A) and Sam Montembeault (32 saves) highlighted the team\'s improved form over the past 10 games. Toronto and Tampa Bay remain locked in a tight race for division supremacy, with both teams registering identical 8-2-0 records in their last 10 contests.',
      timestamp: '2 hours ago',
      relevance: 'high'
    },
    {
      id: '2',
      title: 'Caufield Extends Point Streak to Career-High 12 Games',
      summary: 'Montreal forward Cole Caufield continues his exceptional play, recording at least one point in 12 consecutive games. During this stretch, Caufield has tallied 9 goals and 8 assists for 17 points, elevating his season totals to 28 goals and 45 points in 58 games. His recent surge places him among the league\'s top-10 goal scorers and demonstrates the offensive potential that made him a first-round selection.',
      timestamp: '4 hours ago',
      relevance: 'high'
    },
    {
      id: '3',
      title: 'Montembeault Posts League-Leading Third Shutout',
      summary: 'Goaltender Sam Montembeault recorded his third shutout of the season in Montreal\'s 3-0 victory over Detroit, matching the league lead. The 27-year-old netminder has posted a .923 save percentage over his last 15 starts, establishing himself as a reliable presence between the pipes. His improved consistency has been a critical factor in the team\'s recent playoff push.',
      timestamp: '1 day ago',
      relevance: 'high'
    },
    {
      id: '4',
      title: 'Eastern Conference Playoff Race Intensifies',
      summary: 'With 24 games remaining in the regular season, the Eastern Conference playoff picture remains highly competitive. Five teams are separated by just 6 points in the race for the final wild card position. Montreal\'s remaining schedule includes 8 games against direct playoff competitors, making each contest critical to their postseason aspirations. Advanced metrics suggest the Canadiens maintain a 42% probability of securing a playoff berth based on current trajectories.',
      timestamp: '1 day ago',
      relevance: 'medium'
    }
  ]


  if (isLoading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-400">
            LOADING LEAGUE INTELLIGENCE...
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            League Intelligence
          </h3>
        </div>
        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
          Updated 5 minutes ago
        </div>
      </div>

      <div className="space-y-4">
        {mockEvents.map((event, index) => (
          <motion.article
            key={event.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="relative group"
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="text-base font-military-display text-white mb-2 leading-snug tracking-wide">
                    {event.title}
                  </h4>
                  <p className="text-sm text-gray-400 leading-relaxed">
                    {event.summary}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-3 text-xs">
                <div className="flex items-center space-x-1.5">
                  <ClockIcon className="w-3 h-3 text-gray-500" />
                  <span className="font-military-display text-gray-500 uppercase tracking-wider">
                    {event.timestamp}
                  </span>
                </div>
              </div>
            </div>
            
            {index < mockEvents.length - 1 && (
              <div className="mt-4 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            )}
          </motion.article>
        ))}
      </div>
    </div>
  )
}
