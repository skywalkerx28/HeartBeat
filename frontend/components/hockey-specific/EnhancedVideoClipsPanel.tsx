'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  VideoCameraIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon
} from '@heroicons/react/24/outline'
import { EnhancedVideoClipCard } from './EnhancedVideoClipCard'
import { API_BASE_URL, api } from '../../lib/api'

interface ClipData {
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
  metadata?: {
    mode?: string
    period?: number
    strength?: string
    team?: string
    opponent?: string
    season?: string
    game_id?: string
  }
}

interface EnhancedVideoClipsPanelProps {
  clips: ClipData[]
  title?: string
}

type ViewMode = 'grid' | 'list'
type FilterMode = 'all' | 'shifts' | 'events'

export function EnhancedVideoClipsPanel({ clips, title = "Video Highlights" }: EnhancedVideoClipsPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
  const [sortBy, setSortBy] = useState<'chronological' | 'duration' | 'period'>('chronological')

  // Build absolute URLs with token
  const token = api.getAccessToken()
  const toAbsolute = (path: string) => {
    if (!path) return path
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
    if (path.startsWith('/api/v1/clips/')) {
      return `${API_BASE_URL}${path}${tokenParam}`
    }
    return `${API_BASE_URL}${path}`
  }

  const normalizedClips = (clips || []).map((c) => ({
    ...c,
    file_url: toAbsolute(c.file_url),
    thumbnail_url: toAbsolute(c.thumbnail_url),
  }))

  // Prewarm thumbnails for perceived performance
  useEffect(() => {
    const controllers: AbortController[] = []
    normalizedClips.forEach((c) => {
      if (!c?.thumbnail_url) return
      const ctrl = new AbortController()
      controllers.push(ctrl)
      try {
        fetch(c.thumbnail_url, { method: 'GET', cache: 'force-cache', signal: ctrl.signal }).catch(() => {})
      } catch {}
    })
    return () => controllers.forEach((c) => c.abort())
  }, [normalizedClips.map(c => c.thumbnail_url).join('|')])

  // Filter clips
  const filteredClips = normalizedClips.filter(clip => {
    if (filterMode === 'all') return true
    if (filterMode === 'shifts') return clip.metadata?.mode === 'shift'
    if (filterMode === 'events') return clip.metadata?.mode !== 'shift'
    return true
  })

  // Sort clips
  const sortedClips = [...filteredClips].sort((a, b) => {
    if (sortBy === 'duration') return b.duration - a.duration
    if (sortBy === 'period') return (a.metadata?.period || 0) - (b.metadata?.period || 0)
    return 0 // chronological (preserve order)
  })

  // Count shifts vs events
  const shiftCount = normalizedClips.filter(c => c.metadata?.mode === 'shift').length
  const eventCount = normalizedClips.length - shiftCount

  // Empty state
  if (normalizedClips.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-black/40 border border-red-900/20 rounded-lg p-8 backdrop-blur-sm text-center"
      >
        <div className="flex flex-col items-center space-y-3">
          <div className="w-16 h-16 bg-red-600/10 rounded-lg flex items-center justify-center">
            <VideoCameraIcon className="w-8 h-8 text-red-600/50" />
          </div>
          <div>
            <h3 className="text-base font-military-display text-white tracking-wider mb-1">
              NO CLIPS AVAILABLE
            </h3>
            <p className="text-sm text-gray-400 font-military-chat">
              No video clips were found for your query.
            </p>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Title */}
          <div>
            <h3 className="text-sm font-military-display text-white tracking-wider">
              {title.toUpperCase()}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-xs font-mono text-gray-400">
                {sortedClips.length} clip{sortedClips.length !== 1 ? 's' : ''}
              </span>
              {shiftCount > 0 && (
                <>
                  <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                  <span className="text-xs font-mono text-red-400">
                    {shiftCount} shift{shiftCount !== 1 ? 's' : ''}
                  </span>
                </>
              )}
              {eventCount > 0 && (
                <>
                  <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                  <span className="text-xs font-mono text-cyan-400">
                    {eventCount} event{eventCount !== 1 ? 's' : ''}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          {/* Filter Buttons */}
          {(shiftCount > 0 && eventCount > 0) && (
            <div className="flex items-center bg-black/40 border border-white/10 rounded-lg p-0.5">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1.5 rounded-md text-xs font-military-display tracking-wider transition-all duration-200 ${
                  filterMode === 'all'
                    ? 'bg-white/10 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                ALL
              </button>
              <button
                onClick={() => setFilterMode('shifts')}
                className={`px-3 py-1.5 rounded-md text-xs font-military-display tracking-wider transition-all duration-200 ${
                  filterMode === 'shifts'
                    ? 'bg-red-600/20 text-red-400 border border-red-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                SHIFTS
              </button>
              <button
                onClick={() => setFilterMode('events')}
                className={`px-3 py-1.5 rounded-md text-xs font-military-display tracking-wider transition-all duration-200 ${
                  filterMode === 'events'
                    ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                EVENTS
              </button>
            </div>
          )}

          {/* View Mode Toggle */}
          <div className="flex items-center bg-black/40 border border-white/10 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md transition-all duration-200 ${
                viewMode === 'grid'
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
              title="Grid View"
            >
              <Squares2X2Icon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-md transition-all duration-200 ${
                viewMode === 'list'
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
              title="List View"
            >
              <ListBulletIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Clips Grid/List */}
      <AnimatePresence mode="wait">
        {sortedClips.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-8"
          >
            <FunnelIcon className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400 font-military-chat">
              No clips match your filter
            </p>
          </motion.div>
        ) : (
          <motion.div
            key={viewMode}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
                : 'space-y-4'
            }
          >
            {sortedClips.map((clip, index) => (
              <EnhancedVideoClipCard
                key={clip.clip_id}
                clip={clip}
                index={index}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

