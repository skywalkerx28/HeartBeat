'use client'

import * as Headless from '@headlessui/react'
import clsx from 'clsx'
import { motion, AnimatePresence } from 'framer-motion'
import React, { forwardRef } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  ChartBarIcon, 
  UserGroupIcon, 
  TrophyIcon,
  ClockIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  HomeIcon,
  DocumentTextIcon,
  BeakerIcon
} from '@heroicons/react/24/outline'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  userInfo?: {
    username: string
    name: string
    role: string
    email: string
    team_access: string[]
  }
  onLogout?: () => void
}

export function MilitarySidebar({ isOpen, onToggle, userInfo, onLogout }: SidebarProps) {
  const pathname = usePathname()
  return (
    <>
      {/* Mobile backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            onClick={onToggle}
          />
        )}
      </AnimatePresence>

      {/* Unified sidebar that expands/collapses */}
      <motion.aside
        initial={false}
        animate={{ width: isOpen ? 280 : 64 }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
        className="fixed left-0 top-0 bottom-0 bg-gray-950 border-r border-red-600/10 z-50 flex flex-col overflow-hidden"
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-red-600/10">
          <AnimatePresence mode="wait">
            {isOpen ? (
              <motion.div
                key="expanded-header"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-center space-x-2 flex-1"
              >
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
                <h2 className="text-base font-military-display text-white whitespace-nowrap tracking-wider">HeartBeat</h2>
              </motion.div>
            ) : (
              <motion.div
                key="collapsed-header"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="w-full flex justify-center"
              >
                <button
                  onClick={onToggle}
                  className="p-2 rounded-md text-gray-600 hover:text-red-400 hover:bg-red-600/10 transition-colors"
                >
                  <ChevronRightIcon className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          
          {isOpen && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="p-1.5 rounded-md text-gray-600 hover:text-red-400 hover:bg-red-600/10 transition-colors ml-auto"
            >
              <ChevronLeftIcon className="w-4 h-4" />
            </motion.button>
          )}
        </div>

        {/* Sidebar navigation */}
        <nav className="flex-1 overflow-y-auto py-6">
          {/* Main section */}
          <div className={clsx("mb-6", isOpen ? "px-3" : "px-2")}>
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.h3
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-3 px-3 text-xs font-military-display text-gray-600 overflow-hidden tracking-wider"
                >
                  MAIN
                </motion.h3>
              )}
            </AnimatePresence>
            <div className="space-y-1">
              <UnifiedSidebarItem href="/analytics" icon={ChartBarIcon} current={pathname === '/analytics'} isOpen={isOpen}>
                Analytics
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/scores" icon={UserGroupIcon} current={pathname === '/scores'} isOpen={isOpen}>
                Scores
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/pulse" icon={TrophyIcon} current={pathname === '/pulse'} isOpen={isOpen}>
                Pulse
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/chat" icon={HomeIcon} current={pathname === '/chat'} isOpen={isOpen}>
                Stanley
              </UnifiedSidebarItem>
            </div>
          </div>

          {/* Divider */}
          <div className={clsx("my-4 border-t border-red-600/10", isOpen ? "mx-3" : "mx-2")} />

          {/* Advanced section */}
          <div className={clsx("mb-6", isOpen ? "px-3" : "px-2")}>
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.h3
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-3 px-3 text-xs font-military-display text-gray-600 overflow-hidden tracking-wider"
                >
                  ADVANCED
                </motion.h3>
              )}
            </AnimatePresence>
            <div className="space-y-1">
              <UnifiedSidebarItem href="/predictions" icon={ClockIcon} current={pathname === '/predictions'} isOpen={isOpen}>
                Predictions
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/reports" icon={DocumentTextIcon} current={pathname === '/reports'} isOpen={isOpen}>
                Reports
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/lab" icon={BeakerIcon} current={pathname === '/lab'} isOpen={isOpen}>
                Engine
              </UnifiedSidebarItem>
            </div>
          </div>

          {/* Divider */}
          <div className={clsx("my-4 border-t border-red-600/10", isOpen ? "mx-3" : "mx-2")} />

          {/* System section */}
          <div className={clsx(isOpen ? "px-3" : "px-2")}>
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.h3
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-3 px-3 text-xs font-military-display text-gray-600 overflow-hidden tracking-wider"
                >
                  SYSTEM
                </motion.h3>
              )}
            </AnimatePresence>
            <div className="space-y-1">
              <UnifiedSidebarItem href="/settings" icon={CogIcon} current={pathname === '/settings'} isOpen={isOpen}>
                Settings
              </UnifiedSidebarItem>
              <button
                onClick={onLogout}
                className={clsx(
                  "group relative flex items-center w-full rounded-md transition-all h-10",
                  isOpen 
                    ? "gap-3 px-3 text-sm font-military-chat text-gray-400 hover:text-white hover:bg-red-600/10 text-left"
                    : "justify-center text-gray-600 hover:text-red-400 hover:bg-red-600/10"
                )}
              >
                <ArrowRightOnRectangleIcon className={clsx(
                  "flex-shrink-0 w-5 h-5",
                  isOpen ? "text-gray-600 group-hover:text-red-400" : ""
                )} />
                {isOpen && <span>Logout</span>}
                {!isOpen && (
                  <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-red-600/20">
                    Logout
                  </span>
                )}
              </button>
            </div>
          </div>
        </nav>

        {/* User info section */}
        {userInfo && (
          <div className={clsx(
            "py-4 border-t border-red-600/10 transition-all",
            isOpen ? "px-4" : "px-2"
          )}>
            <AnimatePresence mode="wait">
              {isOpen ? (
                <motion.div
                  key="expanded-user"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-8 h-8 rounded-full bg-red-600/20 border border-red-600/30 text-red-400 flex items-center justify-center text-xs font-military-display">
                      {userInfo.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-military-chat text-white truncate">
                        {userInfo.name}
                      </p>
                      <p className="text-xs font-military-display text-red-400 uppercase tracking-wider">
                        {userInfo.role}
                      </p>
                    </div>
                  </div>
                  
                  {/* System info */}
                  <div className="flex items-center justify-between text-xs text-gray-600 pt-3 border-t border-red-600/10">
                    <span className="font-military-display tracking-wider">HEARTBEAT</span>
                    <span className="font-military-display">V2.1</span>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="collapsed-user"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="w-full flex justify-center"
                >
                  <div className="w-8 h-8 rounded-full bg-red-600/20 border border-red-600/30 text-red-400 flex items-center justify-center text-xs font-military-display">
                    {userInfo.name.split(' ').map(n => n[0]).join('')}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </motion.aside>
    </>
  )
}

interface UnifiedSidebarItemProps {
  href: string
  icon: React.ComponentType<{ className?: string }>
  current?: boolean
  isOpen: boolean
  children: React.ReactNode
}

const UnifiedSidebarItem = forwardRef<HTMLAnchorElement, UnifiedSidebarItemProps>(
  function UnifiedSidebarItem({ href, icon: Icon, current = false, isOpen, children }, ref) {
    return (
      <Link
        href={href}
        className={clsx(
          'group relative flex items-center rounded-md transition-all h-10',
          isOpen
            ? clsx(
                'gap-3 px-3 text-sm font-military-chat',
                current
                  ? 'text-white'
                  : 'text-gray-400 hover:text-white hover:bg-red-600/10'
              )
            : clsx(
                'justify-center',
                current
                  ? 'text-red-400'
                  : 'text-gray-600 hover:text-red-400 hover:bg-red-600/10'
              )
        )}
      >
        <Icon className={clsx(
          'flex-shrink-0 w-5 h-5',
          current 
            ? 'text-red-400' 
            : (isOpen ? 'text-gray-600 group-hover:text-red-400' : '')
        )} />
        
        {isOpen ? (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.2 }}
            className="whitespace-nowrap overflow-hidden"
          >
            {children}
          </motion.span>
        ) : (
          <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-red-600/20">
            {children}
          </span>
        )}
      </Link>
    )
  }
)