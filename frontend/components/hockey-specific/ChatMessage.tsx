'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { AnalyticsPanel } from './AnalyticsPanel'

interface Message {
  id: string
  role: 'user' | 'stanley'
  content: string
  timestamp: Date
  analytics?: AnalyticsData[]
}

interface AnalyticsData {
  type: 'stat' | 'chart' | 'table' | 'clips'
  title: string
  data: any
  clips?: {
    clip_id: string
    title: string
    player_name: string
    game_info: string
    event_type: string
    description: string
    file_url: string
    thumbnail_url: string
    duration: number
    relevance_score?: number
  }[]
}

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isStanley = message.role === 'stanley'
  
  if (isStanley) {
    // Stanley's messages: Plain text with military styling
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-6 w-full"
      >
        {/* Stanley indicator with accent line */}
        <div className="flex items-center space-x-2 mb-2">
          <div className="w-0.5 h-3 bg-gradient-to-b from-red-600 to-transparent"></div>
          <span className="text-[10px] font-military-display text-red-400 uppercase tracking-widest">STANLEY</span>
        </div>
        
        {/* Plain text response - clean military style */}
        <div className="text-white text-sm leading-relaxed font-military-chat whitespace-pre-wrap break-words">
          {message.content.split('\n').map((line, index) => (
            <p key={index} className={index > 0 ? 'mt-3' : ''}>
              {line}
            </p>
          ))}
        </div>
        
        {/* Analytics panel if present */}
        {message.analytics && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.3 }}
            className="mt-4"
          >
            <AnalyticsPanel analytics={message.analytics} />
          </motion.div>
        )}
      </motion.div>
    )
  }

  // User messages: Glassy bubble aligned to the right
  return (
    <div className="mb-4 w-full flex justify-end">
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.2 }}
        className="relative max-w-2xl"
      >
        {/* Glassy message bubble */}
        <div className="px-4 py-2 rounded-lg bg-black/40 backdrop-blur-xl border border-white/10 shadow-lg shadow-white/5">
          <div className="text-sm leading-relaxed font-military-chat text-white">
            {message.content}
          </div>
        </div>
        
        {/* Corner accent */}
        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-red-600/10 to-transparent pointer-events-none rounded-lg" />
      </motion.div>
    </div>
  )
}
