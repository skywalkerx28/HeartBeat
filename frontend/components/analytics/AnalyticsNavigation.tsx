'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { useRouter, usePathname } from 'next/navigation'
import { 
  ChartBarIcon, 
  TrophyIcon, 
  UserGroupIcon, 
  GlobeAltIcon 
} from '@heroicons/react/24/outline'

interface NavItem {
  id: string
  label: string
  path: string
  icon: React.ReactNode
}

export function AnalyticsNavigation() {
  const router = useRouter()
  const pathname = usePathname()

  const navItems: NavItem[] = [
    {
      id: 'market',
      label: 'Market',
      path: '/analytics/market',
      icon: <ChartBarIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'draft',
      label: 'Draft',
      path: '/analytics/draft',
      icon: <UserGroupIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'analytics',
      label: 'Analytics',
      path: '/analytics',
      icon: <TrophyIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'league',
      label: 'League',
      path: '/analytics/league',
      icon: <GlobeAltIcon className="w-3.5 h-3.5" />
    }
  ]

  const isActive = (path: string) => {
    if (path === '/analytics') {
      return pathname === '/analytics'
    }
    return pathname?.startsWith(path)
  }

  const handleNavigation = (path: string) => {
    router.push(path)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="mb-10"
    >
      <div className="flex items-center justify-center">
        <div className="inline-flex items-center space-x-2 bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg p-1.5 shadow-lg shadow-white/5">
          {navItems.map((item, index) => {
            const active = isActive(item.path)
            
            return (
              <motion.button
                key={item.id}
                onClick={() => handleNavigation(item.path)}
                className={`
                  relative flex items-center space-x-2 px-4 py-2 rounded-md
                  font-military-display text-xs uppercase tracking-wider
                  transition-all duration-200
                  ${active 
                    ? 'bg-red-600/10 text-white border border-red-600/30' 
                    : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
                  }
                `}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {/* Active indicator */}
                {active && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute inset-0 bg-red-600/10 rounded-md border border-red-600/30"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
                
                <div className={`relative flex items-center space-x-2 ${active ? 'text-white' : ''}`}>
                  {item.icon}
                  <span>{item.label}</span>
                </div>
              </motion.button>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}

