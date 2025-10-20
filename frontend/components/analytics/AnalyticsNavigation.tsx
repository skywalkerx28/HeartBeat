'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter, usePathname } from 'next/navigation'
import { 
  ChartBarIcon, 
  TrophyIcon, 
  UserGroupIcon, 
  GlobeAltIcon,
  MagnifyingGlassIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

interface SearchResult {
  type: 'player' | 'team'
  id: string | number
  name: string
  team?: string
  teamName?: string
  position?: string
  sweaterNumber?: string
  headshot?: string
  code?: string
  relevance?: number
}

interface NavItem {
  id: string
  label: string
  path: string
  icon: React.ReactNode
}

export function AnalyticsNavigation() {
  const router = useRouter()
  const pathname = usePathname()
  const [isSearchActive, setIsSearchActive] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const navItems: NavItem[] = [
    {
      id: 'analytics',
      label: 'Analytics',
      path: '/analytics',
      icon: <TrophyIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'prospect',
      label: 'Prospect',
      path: '/analytics/prospect',
      icon: <UserGroupIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'market',
      label: 'Market',
      path: '/analytics/market',
      icon: <ChartBarIcon className="w-3.5 h-3.5" />
    },
    {
      id: 'league',
      label: 'League',
      path: '/analytics/league',
      icon: <GlobeAltIcon className="w-3.5 h-3.5" />
    }
  ]

  useEffect(() => {
    if (isSearchActive && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [isSearchActive])

  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setIsSearching(true)
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=20`)
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
      } else {
        console.error(`Search API returned ${response.status}: ${response.statusText}`)
        setSearchResults([])
      }
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }, [])

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchQuery) {
        performSearch(searchQuery)
      } else {
        setSearchResults([])
      }
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [searchQuery, performSearch])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        if (searchInputRef.current && !searchInputRef.current.contains(event.target as Node)) {
          setSearchResults([])
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const isActive = (path: string) => {
    if (path === '/analytics') {
      return pathname === '/analytics'
    }
    return pathname?.startsWith(path)
  }

  const handleNavigation = (path: string) => {
    router.push(path)
  }

  const handleSearch = () => {
    setIsSearchActive(!isSearchActive)
    if (isSearchActive) {
      setSearchQuery('')
      setSearchResults([])
    }
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchResults.length > 0) {
      handleSelectResult(searchResults[0])
    }
  }

  const handleSelectResult = (result: SearchResult) => {
    // Clear search state immediately
    setIsSearchActive(false)
    setSearchQuery('')
    setSearchResults([])
    
    // Navigate immediately without delay
    if (result.type === 'player') {
      router.push(`/player/${result.id}`)
    } else if (result.type === 'team') {
      router.push(`/team/${result.id}`)
    }
  }

  const handleResultHover = (result: SearchResult) => {
    // Prefetch the route on hover for instant navigation
    if (result.type === 'player') {
      router.prefetch(`/player/${result.id}`)
    } else if (result.type === 'team') {
      router.prefetch(`/team/${result.id}`)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const newIndex = Math.min(selectedIndex + 1, searchResults.length - 1)
      setSelectedIndex(newIndex)
      // Prefetch on keyboard navigation
      if (newIndex >= 0 && searchResults[newIndex]) {
        handleResultHover(searchResults[newIndex])
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const newIndex = Math.max(selectedIndex - 1, -1)
      setSelectedIndex(newIndex)
      // Prefetch on keyboard navigation
      if (newIndex >= 0 && searchResults[newIndex]) {
        handleResultHover(searchResults[newIndex])
      }
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSelectResult(searchResults[selectedIndex])
    } else if (e.key === 'Escape') {
      setIsSearchActive(false)
      setSearchQuery('')
      setSearchResults([])
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="mb-10"
    >
      <div className="flex items-center justify-center">
        <div className="relative">
          <div className="relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg shadow-lg shadow-white/5 overflow-hidden" style={{ width: '520px', height: '40px' }}>
          {/* Navigation Items - slide out to left when search is active */}
          <motion.div
            animate={{ 
              x: isSearchActive ? -600 : 0,
              opacity: isSearchActive ? 0 : 1
            }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute left-0 top-0 flex items-center space-x-1.5 p-1.5 h-full"
            style={{ pointerEvents: isSearchActive ? 'none' : 'auto' }}
          >
            {navItems.map((item, index) => {
              const active = isActive(item.path)
              
              return (
                <motion.button
                  key={item.id}
                  onClick={() => handleNavigation(item.path)}
                  className={`
                    relative flex items-center space-x-2 px-3.5 py-1.5 rounded-md
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

            {/* Separator */}
            <div className="w-px h-5 bg-white/10" />
          </motion.div>

          {/* Single Search Icon - animates position from right to left */}
          <motion.div
            animate={{ 
              left: isSearchActive ? '8px' : '470px'
            }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute top-1/2 -translate-y-1/2 z-10"
          >
            <motion.button
              onClick={handleSearch}
              className="flex items-center justify-center px-2.5 py-1.5 rounded-md transition-colors duration-200"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              title="Search"
            >
              <MagnifyingGlassIcon className={`w-4 h-4 ${isSearchActive ? 'text-white' : 'text-gray-400'}`} />
            </motion.button>
          </motion.div>

          {/* Search Input - slides in from right */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: isSearchActive ? 1 : 0
            }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute left-14 top-1/2 -translate-y-1/2 flex items-center h-[28px]"
            style={{ pointerEvents: isSearchActive ? 'auto' : 'none' }}
          >
            <form onSubmit={handleSearchSubmit} className="flex items-center h-full">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setSelectedIndex(-1)
                }}
                onKeyDown={handleKeyDown}
                placeholder="SEARCH PLAYERS & TEAMS..."
                className="bg-transparent border-none outline-none text-white placeholder-gray-500 font-military-display text-xs uppercase tracking-wider w-[430px] px-2 h-full"
                autoComplete="off"
              />
            </form>
          </motion.div>

          {/* Close Button - appears on the right when search is active */}
          <AnimatePresence>
            {isSearchActive && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                onClick={handleSearch}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center justify-center h-[28px] px-2.5 rounded-md text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-200 z-20"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                title="Close"
              >
                <XMarkIcon className="w-4 h-4" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* Search Results Dropdown */}
        <AnimatePresence>
          {isSearchActive && searchResults.length > 0 && (
            <motion.div
              ref={dropdownRef}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.1 }}
              className="absolute top-full mt-2 w-[520px] bg-black/95 backdrop-blur-xl border border-white/20 rounded-lg shadow-2xl shadow-white/10 overflow-hidden z-50"
            >
              <div className="max-h-96 overflow-y-auto">
                {searchResults.map((result, index) => (
                  <motion.button
                    key={`${result.type}-${result.id}`}
                    onClick={() => handleSelectResult(result)}
                    onMouseEnter={() => handleResultHover(result)}
                    className={`
                      w-full px-4 py-3 flex items-center space-x-3 transition-all duration-150
                      ${index === selectedIndex 
                        ? 'bg-red-600/20 border-l-2 border-red-600' 
                        : 'hover:bg-white/5 border-l-2 border-transparent'
                      }
                      ${index !== searchResults.length - 1 ? 'border-b border-white/5' : ''}
                    `}
                    whileHover={{ x: 4 }}
                  >
                    {result.type === 'player' ? (
                      <>
                        <div className="flex-1 text-left">
                          <div className="flex items-center gap-3">
                            <div className="text-white font-military-display text-sm">
                              {result.name}
                            </div>
                            <div className="text-gray-400 font-mono text-xs tabular-nums">
                              {result.id}
                            </div>
                          </div>
                          <div className="text-gray-400 text-xs font-military-display">
                            {result.position && `${result.position} `}
                            {result.sweaterNumber && `#${result.sweaterNumber} `}
                            | {result.teamName}
                          </div>
                        </div>
                        
                        <div className="text-xs text-gray-500 font-military-display">
                          PLAYER
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="w-10 h-10 flex items-center justify-center">
                          <img 
                            src={`https://assets.nhle.com/logos/nhl/svg/${result.code}_light.svg`}
                            alt={result.code}
                            className="w-10 h-10 object-contain grayscale opacity-60"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none'
                            }}
                          />
                        </div>
                        
                        <div className="flex-1 text-left">
                          <div className="text-white font-military-display text-sm">
                            {result.name}
                          </div>
                          <div className="text-gray-400 text-xs font-military-display">
                            {result.code}
                          </div>
                        </div>
                        
                        <div className="text-xs text-gray-500 font-military-display">
                          TEAM
                        </div>
                      </>
                    )}
                  </motion.button>
                ))}
              </div>
              
              {isSearching && (
                <div className="px-4 py-3 text-center text-gray-400 text-xs font-military-display border-t border-white/5">
                  SEARCHING...
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}

