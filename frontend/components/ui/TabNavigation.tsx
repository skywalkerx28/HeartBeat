'use client'

import { motion } from 'framer-motion'

interface Tab {
  id: string
  label: string
}

interface TabNavigationProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
  variant?: 'default' | 'compact'
}

export function TabNavigation({ 
  tabs, 
  activeTab, 
  onTabChange, 
  variant = 'default' 
}: TabNavigationProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative"
    >
        {/* Individual Floating Buttons */}
        <div className="flex space-x-6">
          {tabs.map((tab, index) => {
            const isActive = activeTab === tab.id
            
            return (
              <motion.button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  relative px-6 py-3 font-military-display text-sm uppercase tracking-wider transition-all group
                  ${isActive 
                    ? 'bg-black/40 backdrop-blur-xl border border-red-600/50 shadow-lg shadow-red-600/10' 
                    : 'bg-black/20 backdrop-blur-sm border border-white/10 hover:bg-black/30 hover:border-white/20'
                  }
                  rounded-lg
                `}
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                {/* Main Label */}
                <span className={`
                  transition-colors
                  ${isActive 
                    ? 'text-white' 
                    : 'text-gray-400 group-hover:text-white'
                  }
                `}>
                  {tab.label}
                </span>

                {/* Active State Accent Line */}
                {isActive && (
                  <motion.div
                    layoutId="activeTabAccent"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-red-400 to-transparent"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}


                {/* Tactical Grid Overlay */}
                <div className="absolute inset-0 opacity-10 pointer-events-none rounded-lg overflow-hidden">
                  <div 
                    className="absolute inset-0"
                    style={{
                      backgroundImage: `
                        linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)
                      `,
                      backgroundSize: '6px 6px'
                    }}
                  />
                </div>
              </motion.button>
            )
          })}
        </div>

    </motion.div>
  )
}

// Specialized Military Tab Variant
export function MilitaryTabNavigation({ 
  tabs, 
  activeTab, 
  onTabChange 
}: Omit<TabNavigationProps, 'variant'>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative"
    >
      {/* Command Panel Frame */}
      <div className="relative overflow-hidden rounded-lg border border-red-600/20">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-xl" />
        
        {/* Tactical Header */}
        <div className="relative border-b border-white/10 px-4 py-2">
          <div className="flex items-center space-x-2">
            <div className="w-1 h-1 bg-red-600 rounded-full animate-pulse" />
            <span className="text-xs font-military-display text-gray-400 uppercase tracking-widest">
              Command Interface
            </span>
          </div>
        </div>

        {/* Navigation Grid */}
        <div className="relative p-2">
          <div className="grid grid-cols-4 gap-1">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id
              
              return (
                <motion.button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className="relative group"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className={`
                    relative p-4 rounded-md border transition-all duration-200
                    ${isActive 
                      ? 'bg-red-600/20 border-red-600/50 shadow-red-500/20 shadow-lg' 
                      : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                    }
                  `}>
                    {/* Icon Placeholder */}
                    <div className={`
                      w-8 h-8 mx-auto mb-2 rounded-sm flex items-center justify-center
                      ${isActive 
                        ? 'bg-red-600/30 border border-red-600/50' 
                        : 'bg-white/10 border border-white/20'
                      }
                    `}>
                      <div className={`
                        w-3 h-3 rounded-full
                        ${isActive ? 'bg-red-400' : 'bg-gray-500'}
                      `} />
                    </div>

                    {/* Label */}
                    <div className={`
                      text-xs font-military-display uppercase tracking-widest text-center
                      ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-gray-300'}
                    `}>
                      {tab.label}
                    </div>

                    {/* Active State Indicators */}
                    {isActive && (
                      <>
                        <motion.div
                          className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-400 rounded-full"
                          animate={{ opacity: [1, 0.3, 1] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        />
                        <motion.div
                          className="absolute bottom-1 left-1 w-8 h-0.5 bg-gradient-to-r from-red-600 to-transparent"
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: 1 }}
                          transition={{ delay: 0.1 }}
                        />
                      </>
                    )}
                  </div>
                </motion.button>
              )
            })}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
