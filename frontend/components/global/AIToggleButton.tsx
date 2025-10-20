'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface AIToggleButtonProps {
  onClick: () => void
  isOpen: boolean
}

export function AIToggleButton({ onClick, isOpen }: AIToggleButtonProps) {
  // Hide button when sidebar is open - it merges with the sidebar header
  if (isOpen) return null

  return (
    <AnimatePresence>
      <motion.button
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 20 }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onClick}
        className="fixed top-4 right-6 z-30 group"
        title="Open STANLEY AI Assistant"
      >
        <div className={`
          relative flex items-center gap-2 px-2.5 py-2
          bg-black/30 backdrop-blur-sm
          border border-white/10 rounded-lg
          hover:border-red-500/30 hover:shadow-[0_0_10px_rgba(239,68,68,0.15)]
          transition-all duration-300
        `}>
          {/* Status indicator dot - matches sidebar header */}
          <div className="w-1.5 h-1.5 rounded-full bg-gray-500 group-hover:bg-red-500 transition-colors" />

          {/* Label - matches sidebar header font */}
          <span className="text-sm font-military-display tracking-wider text-gray-400 group-hover:text-gray-300 transition-colors">
            STANLEY
          </span>
        </div>
      </motion.button>
    </AnimatePresence>
  )
}

