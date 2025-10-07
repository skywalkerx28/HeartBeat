'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { CpuChipIcon, CircleStackIcon, MagnifyingGlassIcon, ChartBarIcon } from '@heroicons/react/24/outline'

interface TypingIndicatorProps {
  status?: string
  currentTool?: string
}

const TOOL_ICONS: Record<string, typeof CpuChipIcon> = {
  'parquet_query': CircleStackIcon,
  'vector_search': MagnifyingGlassIcon,
  'analyzing': ChartBarIcon,
  'reasoning': CpuChipIcon,
}

const TOOL_LABELS: Record<string, string> = {
  'parquet_query': 'QUERYING ADVANCED STATS DATABASE',
  'vector_search': 'RETRIEVING EXPERT HOCKEY CONTEXT',
  'analyzing': 'ANALYZING DATA',
  'reasoning': 'AI REASONING',
  'synthesizing': 'SYNTHESIZING ANALYSIS',
}

export function TypingIndicator({ status, currentTool }: TypingIndicatorProps = {}) {
  const Icon = (currentTool && TOOL_ICONS[currentTool]) || CpuChipIcon
  const label = (currentTool && TOOL_LABELS[currentTool]) || status || 'STANLEY AI PROCESSING'
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-8 w-full"
    >
      {/* Stanley indicator with accent line */}
      <div className="flex items-center space-x-2 mb-3">
        <div className="w-0.5 h-4 bg-gradient-to-b from-red-600 to-transparent"></div>
        <span className="text-xs font-military-display text-red-400 uppercase tracking-widest">STANLEY</span>
      </div>
      
      {/* Thinking indicator with dynamic tool status */}
      <div className="flex items-center space-x-3">
        {/* Tool Icon (animated) */}
        <motion.div
          animate={{ 
            rotate: currentTool === 'parquet_query' || currentTool === 'analyzing' ? 360 : 0,
            scale: [1, 1.1, 1]
          }}
          transition={{ 
            rotate: { duration: 2, repeat: Infinity, ease: "linear" },
            scale: { duration: 1.5, repeat: Infinity }
          }}
          className="text-red-400"
        >
          <Icon className="w-4 h-4" />
        </motion.div>

        <span className="text-sm text-gray-400 font-military-chat">{label}</span>
        
        <div className="flex space-x-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 bg-red-600 rounded-full"
              animate={{
                scale: [1, 1.4, 1],
                opacity: [0.3, 1, 0.3],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                delay: i * 0.2,
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  )
}
