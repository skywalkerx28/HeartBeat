'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline'

interface TickerItem {
  playerName: string
  capHit: number
  status: 'overperforming' | 'fair' | 'underperforming'
  position: string
  yearsRemaining: number
}

interface ContractTickerProps {
  items: TickerItem[]
}

export function ContractTicker({ items }: ContractTickerProps) {
  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  // Duplicate items to create seamless loop
  const duplicatedItems = [...items, ...items, ...items]

  return (
    <div className="relative w-full overflow-hidden border-y border-white/5 bg-black/20">
      <div className="relative h-16 flex items-center">
        {/* Scrolling container */}
        <motion.div
          className="flex items-center space-x-8 whitespace-nowrap"
          animate={{
            x: [0, -33.33 * items.length * 8], // Adjust based on item width
          }}
          transition={{
            x: {
              repeat: Infinity,
              repeatType: "loop",
              duration: items.length * 12, // Slowed down significantly
              ease: "linear",
            },
          }}
        >
          {duplicatedItems.map((item, index) => (
            <div
              key={`ticker-${index}`}
              className="flex items-center space-x-3 px-4"
            >
              {/* Player Name & Position */}
              <div className="flex items-center space-x-2">
                <span className="text-sm font-military-display text-white uppercase tracking-wider">
                  {item.playerName}
                </span>
                <span className="text-xs font-military-display text-gray-600 uppercase">
                  {item.position}
                </span>
              </div>

              {/* Cap Hit */}
              <div className="flex items-center space-x-1">
                <span className="text-sm font-military-display text-gray-400 tabular-nums">
                  {formatCurrency(item.capHit)}
                </span>
              </div>

              {/* Status Indicator */}
              <div className="flex items-center">
                {item.status === 'overperforming' ? (
                  <ArrowTrendingUpIcon className="w-4 h-4 text-white" />
                ) : item.status === 'underperforming' ? (
                  <ArrowTrendingDownIcon className="w-4 h-4 text-red-400" />
                ) : (
                  <div className="w-4 h-0.5 bg-gray-500" />
                )}
              </div>

              {/* Years Remaining */}
              <div className="text-xs font-military-display text-gray-600 tabular-nums">
                {item.yearsRemaining}Y
              </div>

              {/* Separator */}
              <div className="w-px h-6 bg-white/10" />
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  )
}

