'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { FaceSmileIcon, FaceFrownIcon, MinusCircleIcon } from '@heroicons/react/24/outline'

interface SentimentData {
  fsp_score: number
  sentiment: string
  sentiment_description: string
  factors: {
    xgf_impact: number
    special_teams_impact: number
    pdo_impact: number
    star_player_impact: number
  }
  note?: string
}

interface SentimentDialProps {
  sentiment: SentimentData
  isLoading?: boolean
}

export function SentimentDial({ sentiment, isLoading }: SentimentDialProps) {
  if (isLoading) {
    return (
      <div className="relative group overflow-hidden rounded-lg">
        <div className="absolute inset-0 bg-white/90 backdrop-blur-xl border border-gray-200 dark:bg-black/40 dark:border-white/10" />
        <div className="relative p-8 text-center">
          <div className="text-sm font-military-display text-gray-500 dark:text-gray-400">
            CALCULATING FAN SENTIMENT...
          </div>
        </div>
      </div>
    )
  }

  const getSentimentColor = (score: number) => {
    if (score >= 70) return 'text-green-400'
    if (score >= 55) return 'text-white'
    if (score >= 45) return 'text-yellow-400'
    if (score >= 30) return 'text-orange-400'
    return 'text-red-400'
  }

  const getSentimentIcon = (score: number) => {
    if (score >= 55) return <FaceSmileIcon className="w-8 h-8" />
    if (score >= 45) return <MinusCircleIcon className="w-8 h-8" />
    return <FaceFrownIcon className="w-8 h-8" />
  }

  const getArcPath = (percentage: number) => {
    const angle = (percentage / 100) * 180
    const radians = (angle - 90) * (Math.PI / 180)
    const x = 50 + 40 * Math.cos(radians)
    const y = 50 + 40 * Math.sin(radians)
    const largeArc = angle > 180 ? 1 : 0
    
    return `M 10 50 A 40 40 0 ${largeArc} 1 ${x} ${y}`
  }

  return (
    <div className="relative group overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-white/90 backdrop-blur-xl border border-gray-200 dark:bg-black/40 dark:border-white/10" />
      
      <div className="relative p-6">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
          <h4 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
            Fan Sentiment Proxy
          </h4>
        </div>

        <div className="flex flex-col items-center justify-center py-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="relative w-32 h-16 mb-4"
          >
            <svg viewBox="0 0 100 50" className="w-full h-full">
              <defs>
                <linearGradient id="dialGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#EF4444" />
                  <stop offset="50%" stopColor="#FBBF24" />
                  <stop offset="100%" stopColor="#10B981" />
                </linearGradient>
              </defs>
              
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                fill="none"
                stroke="rgba(156, 163, 175, 0.3)"
                className="dark:stroke-white/10"
                strokeWidth="8"
                strokeLinecap="round"
              />
              
              <motion.path
                d={getArcPath(sentiment.fsp_score)}
                fill="none"
                stroke="url(#dialGradient)"
                strokeWidth="8"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.5, ease: "easeOut" }}
              />
            </svg>
            
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.5, duration: 0.3 }}
                className={`${getSentimentColor(sentiment.fsp_score)}`}
              >
                {getSentimentIcon(sentiment.fsp_score)}
              </motion.div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="text-center"
          >
            <div className={`text-3xl font-military-display ${getSentimentColor(sentiment.fsp_score)} mb-1`}>
              {sentiment.fsp_score.toFixed(1)}
            </div>
            <div className="text-sm font-military-display text-gray-900 uppercase tracking-wider mb-1 dark:text-white">
              {sentiment.sentiment}
            </div>
            <div className="text-xs font-military-display text-gray-600 dark:text-gray-500">
              {sentiment.sentiment_description}
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="grid grid-cols-2 gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-white/5"
        >
          <div className="text-center p-2 bg-gray-100 rounded dark:bg-white/5">
            <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">xGF IMPACT</div>
            <div className={`text-sm font-military-display ${sentiment.factors.xgf_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {sentiment.factors.xgf_impact > 0 ? '+' : ''}{sentiment.factors.xgf_impact.toFixed(1)}
            </div>
          </div>
          
          <div className="text-center p-2 bg-gray-100 rounded dark:bg-white/5">
            <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">ST IMPACT</div>
            <div className={`text-sm font-military-display ${sentiment.factors.special_teams_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {sentiment.factors.special_teams_impact > 0 ? '+' : ''}{sentiment.factors.special_teams_impact.toFixed(1)}
            </div>
          </div>
          
          <div className="text-center p-2 bg-gray-100 rounded dark:bg-white/5">
            <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">PDO IMPACT</div>
            <div className={`text-sm font-military-display ${sentiment.factors.pdo_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {sentiment.factors.pdo_impact > 0 ? '+' : ''}{sentiment.factors.pdo_impact.toFixed(1)}
            </div>
          </div>
          
          <div className="text-center p-2 bg-gray-100 rounded dark:bg-white/5">
            <div className="text-xs font-military-display text-gray-600 mb-1 dark:text-gray-500">STAR IMPACT</div>
            <div className={`text-sm font-military-display ${sentiment.factors.star_player_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {sentiment.factors.star_player_impact > 0 ? '+' : ''}{sentiment.factors.star_player_impact.toFixed(1)}
            </div>
          </div>
        </motion.div>

        {sentiment.note && (
          <div className="mt-4 pt-3 border-t border-gray-200 dark:border-white/5">
            <p className="text-xs font-military-display text-gray-600 text-center dark:text-gray-500">
              {sentiment.note}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

