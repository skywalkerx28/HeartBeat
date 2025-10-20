'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ClockIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { api } from '../../lib/api'

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
  const [article, setArticle] = useState<any>(null)
  const [games, setGames] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchNewsContent = async () => {
      setLoading(true)
      try {
        // Fetch AI-generated daily article and recent games
        const [articleData, gamesData] = await Promise.all([
          api.getDailyArticle(),
          api.getRecentGames(1)
        ])

        setArticle(articleData)
        setGames(gamesData)
      } catch (error) {
        console.error('Error fetching news content:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchNewsContent()
  }, [])

  // Fallback mock events if no real data
  const mockEvents: LeagueEvent[] = [
    {
      id: '1',
      title: 'Atlantic Division Tightens After Weekend Series',
      summary: 'The Montreal Canadiens pulled within 3 points of the third playoff spot following a decisive 4-1 victory over the Buffalo Sabres.',
      timestamp: '2 hours ago',
      relevance: 'high'
    }
  ]


  if (loading || isLoading) {
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

  // Format relative time
  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours} hours ago`
    return `${Math.floor(diffHours / 24)} days ago`
  }

  // Split article content into paragraphs for display
  const renderArticleContent = () => {
    if (!article || !article.content) return null

    const paragraphs = article.content.split('\n\n').filter((p: string) => p.trim())
    
    return paragraphs.map((paragraph: string, index: number) => (
      <motion.div
        key={index}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.1 }}
        className="space-y-3"
      >
        <p className="text-sm text-gray-300 leading-relaxed">
          {paragraph}
        </p>
        {index < paragraphs.length - 1 && (
          <div className="my-4 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        )}
      </motion.div>
    ))
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
        <div className="flex items-center space-x-2">
          {article && (
            <div className="flex items-center space-x-1.5">
              <SparklesIcon className="w-3 h-3 text-red-400" />
              <span className="text-[10px] font-military-display text-red-400 uppercase tracking-wider">
                AI Generated
              </span>
            </div>
          )}
          {article && (
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider">
              {getRelativeTime(article.created_at)}
            </div>
          )}
        </div>
      </div>

      {article ? (
        <motion.article
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative group space-y-4"
        >
          <div className="space-y-3">
            <h4 className="text-xl font-military-display text-white leading-snug tracking-wide">
              {article.title}
            </h4>
            <div className="space-y-4">
              {renderArticleContent()}
            </div>
          </div>
          
          {games && games.length > 0 && (
            <>
              <div className="mt-6 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              <div className="space-y-2">
                <h5 className="text-xs font-military-display text-gray-400 uppercase tracking-widest">
                  Recent Games ({games.length})
                </h5>
                <div className="grid grid-cols-2 gap-2">
                  {games.slice(0, 6).map((game: any) => (
                    <div 
                      key={game.game_id}
                      className="text-xs font-military-display text-gray-400 bg-white/5 px-2 py-1.5 rounded border border-white/10"
                    >
                      {game.away_team} @ {game.home_team}: {game.away_score}-{game.home_score}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
          
          {/* Source Citations */}
          <div className="mt-6 pt-4 border-t border-white/5">
            <div className="flex items-center space-x-2 text-[10px] font-military-display text-gray-600">
              <span className="uppercase tracking-wider">Sources:</span>
              <div className="flex items-center space-x-2">
                <a 
                  href="https://www.nhl.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  NHL.com
                </a>
                <span className="text-gray-700">•</span>
                <a 
                  href="https://www.tsn.ca/nhl/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  TSN
                </a>
                <span className="text-gray-700">•</span>
                <a 
                  href="https://www.sportsnet.ca/hockey/nhl/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  Sportsnet
                </a>
                <span className="text-gray-700">•</span>
                <a 
                  href="https://capwages.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  CapWages
                </a>
                <span className="text-gray-700">•</span>
                <a 
                  href="https://www.dailyfaceoff.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  DailyFaceoff
                </a>
                <span className="text-gray-700">•</span>
                <a 
                  href="https://www.espn.com/nhl/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-gray-400 transition-colors duration-200"
                >
                  ESPN
                </a>
                <span className="text-gray-700">•</span>
                <span className="text-gray-600">32 Team Sites</span>
              </div>
            </div>
          </div>
        </motion.article>
      ) : (
        <div className="text-center py-8">
          <div className="text-sm font-military-display text-gray-500">
            No league intelligence available
          </div>
        </div>
      )}
    </div>
  )
}
