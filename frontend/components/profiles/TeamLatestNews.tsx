'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { NewspaperIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

interface NewsArticle {
  id: number
  title: string
  summary?: string
  date: string
  image_url?: string
  created_at: string
}

interface TeamLatestNewsProps {
  teamCode: string
  limit?: number
}

export function TeamLatestNews({ teamCode, limit = 5 }: TeamLatestNewsProps) {
  const router = useRouter()
  const [news, setNews] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchNews()
  }, [teamCode])

  const fetchNews = async () => {
    try {
      const response = await fetch(`/api/v1/news/team/${teamCode.toUpperCase()}/tags/news?days=14`)
      const data = await response.json()
      
      // Handle different response formats
      if (!Array.isArray(data)) {
        setNews([])
        return
      }
      
      setNews(data.slice(0, limit))
    } catch (error) {
      console.error('Error fetching team news:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  if (loading) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
        <div className="relative p-5 text-center">
          <div className="text-xs font-military-display text-gray-400">
            LOADING NEWS...
          </div>
        </div>
      </div>
    )
  }

  if (news.length === 0) {
    return (
      <div className="relative overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5" />
        <div className="relative p-5 text-center">
          <div className="text-xs font-military-display text-gray-500">
            No recent news
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
              Latest News
            </h4>
          </div>
          <div className="flex items-center space-x-1.5">
            <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
            <span className="text-[9px] font-military-display text-red-400 uppercase tracking-wider">
              Live
            </span>
          </div>
        </div>

        {/* News Items */}
        <div className="space-y-0">
          {news.map((article, index) => (
            <motion.button
              key={article.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => router.push(`/league/article/${article.id}`)}
              className="w-full text-left py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.03] hover:backdrop-blur-sm transition-all duration-200 group/item"
            >
              {/* Title */}
              <div className="flex items-start justify-between mb-1.5">
                <h5 className="text-sm font-military-display text-white leading-tight group-hover/item:text-red-400 transition-colors line-clamp-2 pr-2">
                  {article.title}
                </h5>
                <ChevronRightIcon className="w-3.5 h-3.5 text-gray-600 group-hover/item:text-red-400 transition-colors flex-shrink-0 mt-0.5" />
              </div>

              {/* Summary */}
              {article.summary && (
                <p className="text-xs text-gray-500 leading-relaxed mb-2 line-clamp-2">
                  {article.summary}
                </p>
              )}

              {/* Date */}
              <div className="text-[10px] text-gray-600 uppercase tracking-wider">
                {formatDate(article.created_at)}
              </div>
            </motion.button>
          ))}
        </div>

        {/* Footer */}
        {news.length >= limit && (
          <div className="mt-4 pt-3 border-t border-white/5">
            <button
              onClick={() => router.push('/league')}
              className="w-full text-[10px] font-military-display text-gray-500 hover:text-red-400 uppercase tracking-wider text-center transition-colors duration-200"
            >
              View All League News →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

