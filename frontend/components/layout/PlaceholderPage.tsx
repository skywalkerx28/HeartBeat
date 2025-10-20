'use client'

import { motion } from 'framer-motion'
import { CogIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline'

interface PlaceholderPageProps {
  title: string
  description: string
  icon?: React.ComponentType<{ className?: string }>
}

export function PlaceholderPage({ title, description, icon: Icon = CogIcon }: PlaceholderPageProps) {
  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto"
      >
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <div className="w-3 h-3 bg-gray-500 rounded-full animate-pulse" />
            <h1 className="text-2xl font-military-display text-white">
              {title}
            </h1>
            <div className="px-3 py-1 rounded-full text-xs font-military-display bg-gray-600/20 text-gray-400 border border-gray-600/30">
              IN DEVELOPMENT
            </div>
          </div>
        </div>

        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-900/50 border border-gray-800 rounded-lg backdrop-blur-sm p-12 text-center"
        >
          <div className="mb-8">
            <Icon className="w-24 h-24 text-gray-600 mx-auto mb-6" />
            <h2 className="text-xl font-military-display text-gray-300 mb-4">
              MODULE UNDER CONSTRUCTION
            </h2>
            <p className="text-gray-400 font-military-chat max-w-md mx-auto">
              {description}
            </p>
          </div>

          {/* Status Indicators */}
          <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto">
            <div className="bg-gray-800/50 border border-gray-700 rounded p-3">
              <div className="text-xs font-military-display text-gray-500 mb-1">STATUS</div>
              <div className="text-sm font-military-chat text-gray-300">DEVELOPMENT</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded p-3">
              <div className="text-xs font-military-display text-gray-500 mb-1">PRIORITY</div>
              <div className="text-sm font-military-chat text-gray-300">MEDIUM</div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 rounded p-3">
              <div className="text-xs font-military-display text-gray-500 mb-1">ETA</div>
              <div className="text-sm font-military-chat text-gray-300">Q1 2024</div>
            </div>
          </div>

          {/* Additional Info */}
          <div className="mt-8 pt-8 border-t border-gray-800">
            <div className="flex items-center justify-center space-x-2 text-gray-500">
              <WrenchScrewdriverIcon className="w-4 h-4" />
              <span className="text-xs font-military-display">
                HEARTBEAT ENGINE DEVELOPMENT TEAM
              </span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
