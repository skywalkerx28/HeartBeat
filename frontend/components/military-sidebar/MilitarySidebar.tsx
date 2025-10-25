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
  BeakerIcon,
  BanknotesIcon,
  SunIcon,
  MoonIcon
} from '@heroicons/react/24/outline'
import { ChevronDownIcon } from '@heroicons/react/24/solid'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useTheme } from '@/components/global/ThemeProvider'

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
  const { theme, toggleTheme } = useTheme()
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
        className="fixed left-0 top-0 bottom-0 bg-gray-50/95 backdrop-blur-xl border-r border-gray-200/60 shadow-sm dark:bg-gray-950 dark:border-white/5 z-50 flex flex-col overflow-hidden"
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200/60 dark:border-white/5">
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
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse dark:bg-white" />
                <h2 className="text-base font-military-display text-gray-900 whitespace-nowrap tracking-wider dark:text-white">HeartBeat</h2>
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
                  className="p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3"
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
              className="p-1.5 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors ml-auto dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3"
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
                  className="mb-3 px-3 text-xs font-military-display text-gray-500 overflow-hidden tracking-wider dark:text-gray-600"
                >
                  MAIN
                </motion.h3>
              )}
            </AnimatePresence>
            <div className="space-y-1">
              <UnifiedSidebarItem href="/analytics" icon={ChartBarIcon} current={pathname === '/analytics'} isOpen={isOpen}>
                Analytics
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/contracts" icon={BanknotesIcon} current={pathname === '/contracts'} isOpen={isOpen}>
                Contracts
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/scores" icon={UserGroupIcon} current={pathname === '/scores'} isOpen={isOpen}>
                Scores
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/pulse" icon={TrophyIcon} current={pathname === '/pulse'} isOpen={isOpen}>
                Pulse
              </UnifiedSidebarItem>
              <StanleyItemWithConversations isOpen={isOpen} current={pathname === '/chat'} />
            </div>
          </div>

          {/* Divider */}
          <div className={clsx("my-4 border-t border-gray-200/60 dark:border-white/5", isOpen ? "mx-3" : "mx-2")} />

          {/* Advanced section */}
          <div className={clsx("mb-6", isOpen ? "px-3" : "px-2")}>
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.h3
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-3 px-3 text-xs font-military-display text-gray-500 overflow-hidden tracking-wider dark:text-gray-600"
                >
                  ADVANCED
                </motion.h3>
              )}
            </AnimatePresence>
            <div className="space-y-1">
              <UnifiedSidebarItem href="/predictions" icon={ClockIcon} current={pathname === '/predictions'} isOpen={isOpen}>
                Predictions
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/league" icon={DocumentTextIcon} current={pathname === '/league'} isOpen={isOpen}>
                League
              </UnifiedSidebarItem>
              <UnifiedSidebarItem href="/lab" icon={BeakerIcon} current={pathname === '/lab'} isOpen={isOpen}>
                Engine
              </UnifiedSidebarItem>
            </div>
          </div>

          {/* Divider */}
          <div className={clsx("my-4 border-t border-gray-200/60 dark:border-white/5", isOpen ? "mx-3" : "mx-2")} />

          {/* System section */}
          <div className={clsx(isOpen ? "px-3" : "px-2")}>
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.h3
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mb-3 px-3 text-xs font-military-display text-gray-500 overflow-hidden tracking-wider dark:text-gray-600"
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
                    ? "gap-3 px-3 text-sm font-military-chat text-gray-600 hover:text-gray-900 hover:bg-gray-100 text-left dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/3"
                    : "justify-center text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3"
                )}
              >
                <ArrowRightOnRectangleIcon className={clsx(
                  "flex-shrink-0 w-5 h-5",
                  isOpen ? "text-gray-500 group-hover:text-gray-900 dark:text-gray-600 dark:group-hover:text-white" : ""
                )} />
                {isOpen && <span>Logout</span>}
                {!isOpen && (
                  <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-white/5">
                    Logout
                  </span>
                )}
              </button>
            </div>
          </div>
        </nav>

        {/* Theme toggle section */}
        <div className={clsx(
          "py-3 border-t border-gray-200 transition-all dark:border-white/5",
          isOpen ? "px-4" : "px-2"
        )}>
          <AnimatePresence mode="wait">
            {isOpen ? (
              <motion.button
                key="expanded-theme"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={toggleTheme}
                className="w-full flex items-center justify-between gap-3 p-2.5 rounded-md text-sm font-military-chat text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/3"
              >
                <div className="flex items-center gap-3">
                  {theme === 'dark' ? (
                    <SunIcon className="w-5 h-5 text-gray-500 dark:text-gray-600" />
                  ) : (
                    <MoonIcon className="w-5 h-5 text-gray-500 dark:text-gray-600" />
                  )}
                  <span className="uppercase tracking-wider text-xs">
                    {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-600">
                  <div className={clsx(
                    "w-9 h-5 rounded-full transition-colors relative",
                    theme === 'dark' ? 'bg-white/10' : 'bg-red-600/20'
                  )}>
                    <div className={clsx(
                      "absolute top-0.5 w-4 h-4 rounded-full transition-all",
                      theme === 'dark' 
                        ? 'left-0.5 bg-gray-600' 
                        : 'left-4 bg-red-600'
                    )} />
                  </div>
                </div>
              </motion.button>
            ) : (
              <motion.button
                key="collapsed-theme"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={toggleTheme}
                className="group relative w-full flex justify-center p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3"
                title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              >
                {theme === 'dark' ? (
                  <SunIcon className="w-5 h-5" />
                ) : (
                  <MoonIcon className="w-5 h-5" />
                )}
                <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-white/5">
                  {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                </span>
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* User info section */}
        {userInfo && (
          <div className={clsx(
            "py-4 border-t border-gray-200 transition-all dark:border-white/5",
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
                    <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 text-gray-900 flex items-center justify-center text-xs font-military-display dark:bg-white/5 dark:border-white/5 dark:text-white">
                      {userInfo.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-military-chat text-gray-900 truncate dark:text-white">
                        {userInfo.name}
                      </p>
                      <p className="text-xs font-military-display text-gray-600 uppercase tracking-wider dark:text-gray-400">
                        {userInfo.role}
                      </p>
                    </div>
                  </div>
                  
                  {/* System info */}
                  <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-gray-200 dark:text-gray-600 dark:border-white/5">
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
                  <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 text-gray-900 flex items-center justify-center text-xs font-military-display dark:bg-white/5 dark:border-white/5 dark:text-white">
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
                  ? 'text-gray-900 dark:text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/3'
              )
            : clsx(
                'justify-center',
                current
                  ? 'text-gray-900 dark:text-white'
                  : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3'
              )
        )}
      >
        <Icon className={clsx(
          'flex-shrink-0 w-5 h-5',
          current 
            ? 'text-gray-900 dark:text-white' 
            : (isOpen ? 'text-gray-500 group-hover:text-gray-900 dark:text-gray-600 dark:group-hover:text-white' : '')
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
          <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-white/5">
            {children}
          </span>
        )}
      </Link>
    )
  }
)

// Stanley item with conversation list
function StanleyItemWithConversations({ isOpen, current }: { isOpen: boolean; current?: boolean }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [conversations, setConversations] = useState<Array<{ conversation_id: string; title: string; updated_at?: string; message_count: number }>>([])
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const res = await api.listConversations()
      setConversations(res.conversations || [])
    } catch (e) {
      console.error('Failed to load conversations', e)
    } finally {
      setLoading(false)
    }
  }

  const handleRename = async (conversationId: string) => {
    if (!renameValue.trim()) {
      setRenamingId(null)
      return
    }
    try {
      await api.renameConversation(conversationId, renameValue.trim())
      setConversations(prev => prev.map(c => 
        c.conversation_id === conversationId ? { ...c, title: renameValue.trim() } : c
      ))
      setRenamingId(null)
      setRenameValue('')
    } catch (e) {
      console.error('Failed to rename conversation', e)
    }
  }

  const handleDelete = async (conversationId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this conversation?')) return
    try {
      await api.deleteConversation(conversationId)
      setConversations(prev => prev.filter(c => c.conversation_id !== conversationId))
    } catch (err) {
      console.error('Failed to delete conversation', err)
    }
  }

  useEffect(() => {
    if (open) fetchConversations()
  }, [open])

  return (
    <>
      {/* Stanley main button */}
      <div
        className={clsx(
          'group relative flex items-center rounded-md transition-all h-10 cursor-pointer',
          isOpen
            ? clsx(
                'gap-3 px-3 text-sm font-military-chat',
                current ? 'text-gray-900 dark:text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/3'
              )
            : clsx('justify-center', current ? 'text-gray-900 dark:text-white' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-600 dark:hover:text-white dark:hover:bg-white/3')
        )}
        onClick={() => setOpen((v) => !v)}
        title={isOpen ? undefined : 'Stanley'}
      >
        <HomeIcon className={clsx('flex-shrink-0 w-5 h-5', current ? 'text-gray-900 dark:text-white' : (isOpen ? 'text-gray-500 group-hover:text-gray-900 dark:text-gray-600 dark:group-hover:text-white' : ''))} />
        {isOpen ? (
          <>
            <span className="whitespace-nowrap overflow-hidden">Stanley</span>
            <ChevronDownIcon className={clsx('w-3 h-3 ml-auto transition-transform text-gray-500 dark:text-gray-600', open ? 'rotate-180' : '')} />
          </>
        ) : (
          <span className="absolute left-full ml-2 px-2 py-1 text-xs bg-black/80 backdrop-blur-sm text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 border border-white/5">
            Stanley
          </span>
        )}
      </div>
      
      {/* Conversation list - shown when expanded */}
      <AnimatePresence>
        {isOpen && open && (
          <motion.div 
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            exit={{ opacity: 0, scaleY: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="space-y-1 mb-2 origin-top"
          >
            {/* New conversation */}
            <Link 
              href="/chat" 
              className="group relative flex items-center rounded-md transition-all h-9 gap-2 pl-8 pr-3 text-xs font-military-chat text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:text-white dark:hover:bg-white/3"
            >
              <span className="text-sm">+</span>
              <span className="truncate">New chat</span>
            </Link>
            
            {/* Loading */}
            {loading && (
              <div className="pl-8 pr-3 h-9 flex items-center text-xs text-gray-500 font-military-chat dark:text-gray-600">
                Loading...
              </div>
            )}
            
            {/* Conversations */}
            {!loading && conversations.length === 0 && (
              <div className="pl-8 pr-3 h-9 flex items-center text-xs text-gray-500 font-military-chat dark:text-gray-600">
                No conversations yet
              </div>
            )}
            {!loading && conversations.slice(0, 10).map((c) => (
              <div key={c.conversation_id} className="group/item relative">
                {renamingId === c.conversation_id ? (
                  <div className="flex items-center rounded-md h-9 pl-8 pr-3 bg-gray-100 dark:bg-white/3">
                    <input
                      type="text"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename(c.conversation_id)
                        if (e.key === 'Escape') { setRenamingId(null); setRenameValue('') }
                      }}
                      onBlur={() => handleRename(c.conversation_id)}
                      autoFocus
                      className="flex-1 bg-transparent text-xs text-gray-900 font-military-chat focus:outline-none placeholder-gray-500 dark:text-white"
                      placeholder="Enter name..."
                    />
                  </div>
                ) : (
                  <Link 
                    href={`/chat?conversation_id=${c.conversation_id}`}
                    className="flex items-center rounded-md transition-all h-9 gap-2 pl-8 pr-12 text-xs font-military-chat text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:text-white dark:hover:bg-white/3"
                    title={c.title}
                  >
                    <span className="truncate flex-1 min-w-0">{c.title}</span>
                    <div className="absolute right-3 flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          setRenamingId(c.conversation_id)
                          setRenameValue(c.title)
                        }}
                        className="p-0.5 text-gray-500 hover:text-gray-900 transition-colors dark:text-gray-600 dark:hover:text-white"
                        title="Rename"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => handleDelete(c.conversation_id, e)}
                        className="p-0.5 text-gray-500 hover:text-red-600 transition-colors dark:text-gray-600 dark:hover:text-red-500"
                        title="Delete"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </Link>
                )}
              </div>
            ))}
            
            {/* Show more if needed */}
            {!loading && conversations.length > 10 && (
              <Link 
                href="/chat" 
                className="group relative flex items-center rounded-md transition-all h-9 gap-2 pl-8 pr-3 text-xs font-military-chat text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:text-white dark:hover:bg-white/3"
              >
                <span className="truncate">+{conversations.length - 10} more...</span>
              </Link>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
