'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ClockIcon, SparklesIcon } from '@heroicons/react/24/outline'

interface NewsArticleCardProps {
  title: string
  summary: string
  category: string
  date: string
  sourceCount?: number
  imageUrl?: string
  tags?: string[]
  onClick?: () => void
}

export function NewsArticleCard({
  title,
  category,
  date,
  sourceCount = 0,
  imageUrl,
  onClick
}: NewsArticleCardProps) {
  
  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'transactions':
        return 'text-red-400'
      case 'injuries':
        return 'text-red-500'
      case 'rumors':
        return 'text-gray-400'
      case 'atlantic':
      case 'division':
        return 'text-white'
      default:
        return 'text-gray-400'
    }
  }

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays === 1) return '1 day ago'
    return `${diffDays} days ago`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className="relative group cursor-pointer overflow-hidden rounded-lg h-full"
    >
      {/* Subtle glow effect */}
      <div className="absolute inset-0 bg-white/[0.02] rounded-lg blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      {/* Glass panel */}
      <div className="absolute inset-0 bg-black/20 backdrop-blur-xl border border-white/5 group-hover:border-white/10 group-hover:bg-black/25 transition-all duration-300 shadow-lg shadow-black/50" />
      
      <div className="relative h-full flex flex-col">
        {/* Image */}
        <div className="relative w-full h-44 overflow-hidden">
          <img 
            src={imageUrl || 'https://assets.nhle.com/logos/nhl/svg/NHL_light.svg'} 
            alt={title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = 'https://assets.nhle.com/logos/nhl/svg/NHL_light.svg'
            }}
          />
          
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
          
          {/* Category badge */}
          <div className="absolute top-2 left-2">
            <div className="px-2 py-1 rounded bg-black/60 backdrop-blur-sm border border-white/10">
              <span className={`text-[9px] font-military-display uppercase tracking-wider ${getCategoryColor(category)}`}>
                {category}
              </span>
            </div>
          </div>
          
          {/* AI badge */}
          {sourceCount > 0 && (
            <div className="absolute top-2 right-2">
              <div className="flex items-center space-x-1 px-2 py-1 rounded bg-black/60 backdrop-blur-sm border border-white/10">
                <SparklesIcon className="w-3 h-3 text-red-400" />
                <span className="text-[9px] font-military-display text-gray-300">{sourceCount}</span>
              </div>
            </div>
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 p-3 flex flex-col">
          {/* Title */}
          <h3 className="text-sm font-military-display text-white leading-snug group-hover:text-red-400 transition-colors line-clamp-3">
            {title}
          </h3>
          
          {/* Footer */}
          <div className="flex items-center justify-between pt-2 mt-auto">
            <div className="flex items-center space-x-1 text-[9px] text-gray-600">
              <ClockIcon className="w-3 h-3" />
              <span>{formatRelativeTime(date)}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
