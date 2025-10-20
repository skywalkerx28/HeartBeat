'use client'

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  PlayIcon,
  PauseIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ClockIcon,
  UserGroupIcon,
  BoltIcon
} from '@heroicons/react/24/outline'

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
    shift_game_length_s?: number
    shift_real_length_s?: number
  }
}

interface EnhancedVideoClipCardProps {
  clip: ClipData
  index?: number
}

export function EnhancedVideoClipCard({ clip, index = 0 }: EnhancedVideoClipCardProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(true)
  const [currentTime, setCurrentTime] = useState(0)
  const [isHovered, setIsHovered] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const isShiftMode = clip.metadata?.mode === 'shift'

  // Prefer HLS if backend provided a playlist in metadata.extra (served via index extra_metadata)
  // Fallback to MP4
  const [sourceUrl, setSourceUrl] = useState<string>(clip.file_url)
  const [isHls, setIsHls] = useState<boolean>(false)

  useEffect(() => {
    // If the MP4 URL ends with .m3u8 we handle via hls.js; otherwise use native
    const isM3U8 = typeof clip.file_url === 'string' && clip.file_url.endsWith('.m3u8')
    if (isM3U8) {
      setIsHls(true)
      setSourceUrl(clip.file_url)
      return
    }
    // If metadata contains an alternate HLS URL, prefer it
    const metaAny: any = clip.metadata as any
    if (metaAny && typeof metaAny.hls_playlist_url === 'string') {
      setIsHls(true)
      setSourceUrl(metaAny.hls_playlist_url)
    } else {
      setIsHls(false)
      setSourceUrl(clip.file_url)
    }
  }, [clip.file_url, clip.metadata])

  // Attach hls.js dynamically when needed for non-native HLS browsers
  useEffect(() => {
    if (!isHls) return
    const video = videoRef.current
    if (!video) return
    const canPlayNative = video.canPlayType('application/vnd.apple.mpegurl') !== ''
    if (canPlayNative) return // Safari/iOS play natively
    let hls: any
    let cancelled = false
    ;(async () => {
      try {
        const mod = await import('hls.js')
        if (cancelled) return
        const Hls = (mod as any).default || (mod as any)
        if (Hls.isSupported()) {
          hls = new Hls({
            maxBufferLength: 10,
            startLevel: -1,
            enableWorker: true,
            lowLatencyMode: true,
          })
          hls.attachMedia(video)
          hls.on((Hls as any).Events.MEDIA_ATTACHED, () => {
            hls.loadSource(sourceUrl)
          })
        }
      } catch {}
    })()
    return () => {
      cancelled = true
      try { hls && hls.destroy && hls.destroy() } catch {}
    }
  }, [isHls, sourceUrl])

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleMuteToggle = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="relative bg-black/40 border border-red-900/20 rounded-lg overflow-hidden backdrop-blur-sm group hover:border-red-600/40 hover:shadow-xl hover:shadow-red-900/10 transition-all duration-300"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Video Container */}
      <div className="relative aspect-video bg-black">
        {/* Video Element */}
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          poster={clip.thumbnail_url}
          muted={isMuted}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          onLoadedData={() => setIsLoaded(true)}
          preload="metadata"
          crossOrigin="anonymous"
          playsInline
          controlsList="nodownload"
        >
          {/* If HLS is preferred, let hls.js attach later; provide fallback MP4 for browsers that support it natively */}
          {isHls ? (
            <>
              {/* hls.js will handle MSE; keep a minimal fallback for Safari which supports HLS natively */}
              <source src={sourceUrl} type="application/vnd.apple.mpegurl" />
            </>
          ) : (
            <source src={sourceUrl} type="video/mp4" />
          )}
          Your browser does not support the video tag.
        </video>

        {/* Loading State */}
        {!isLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
            <div className="flex flex-col items-center space-y-2">
              <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs font-military-display text-gray-400 tracking-wider">LOADING</span>
            </div>
          </div>
        )}

        {/* Video Overlay Controls */}
        <AnimatePresence>
          {isHovered && isLoaded && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"
            >
              {/* Center Play Button */}
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handlePlayPause}
                  className="bg-red-600/90 border border-red-500/50 rounded-lg p-3 hover:bg-red-600 transition-colors backdrop-blur-md"
                >
                  {isPlaying ? (
                    <PauseIcon className="w-6 h-6 text-white" />
                  ) : (
                    <PlayIcon className="w-6 h-6 text-white ml-0.5" />
                  )}
                </motion.button>
              </div>

              {/* Top Bar */}
              <div className="absolute top-0 left-0 right-0 p-3 flex items-center justify-between">
                {/* Mode Badge */}
                <div className="flex items-center space-x-2">
                  {isShiftMode ? (
                    <div className="flex items-center space-x-1.5 bg-red-600/90 backdrop-blur-md px-2.5 py-1 rounded-md border border-red-500/30">
                      <ClockIcon className="w-3.5 h-3.5 text-white" />
                      <span className="text-xs font-military-display text-white tracking-wider">SHIFT</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1.5 bg-cyan-600/90 backdrop-blur-md px-2.5 py-1 rounded-md border border-cyan-500/30">
                      <BoltIcon className="w-3.5 h-3.5 text-white" />
                      <span className="text-xs font-military-display text-white tracking-wider">EVENT</span>
                    </div>
                  )}
                  
                  {/* Duration */}
                  <div className="bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-md border border-white/10">
                    <span className="text-xs font-mono text-gray-300">
                      {isShiftMode && (clip.metadata?.shift_game_length_s || clip.metadata?.shift_real_length_s) ? (
                        <>Shift length: {formatDuration(clip.metadata?.shift_game_length_s || clip.duration)} (real-time {formatDuration(clip.metadata?.shift_real_length_s || clip.duration)})</>
                      ) : (
                        <>{formatDuration(clip.duration)}</>
                      )}
                    </span>
                  </div>

                  {/* Strength Badge (for shifts) */}
                  {isShiftMode && clip.metadata?.strength && (
                    <div className="bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-md border border-white/10">
                      <span className="text-xs font-mono text-white">
                        {clip.metadata.strength}
                      </span>
                    </div>
                  )}
                </div>
                
                {/* Mute Toggle */}
                <button
                  onClick={handleMuteToggle}
                  className="bg-black/70 backdrop-blur-md p-2 rounded-md hover:bg-black/90 transition-colors border border-white/10"
                >
                  {isMuted ? (
                    <SpeakerXMarkIcon className="w-4 h-4 text-gray-300" />
                  ) : (
                    <SpeakerWaveIcon className="w-4 h-4 text-white" />
                  )}
                </button>
              </div>

              {/* Bottom Progress Bar */}
              <div className="absolute bottom-0 left-0 right-0 p-3">
                {/* Progress Bar */}
                <div className="bg-white/10 h-1 rounded-full overflow-hidden mb-2 backdrop-blur-sm">
                  <div 
                    className="bg-red-500 h-full transition-all duration-100"
                    style={{ 
                      width: clip.duration > 0 ? `${(currentTime / clip.duration) * 100}%` : '0%' 
                    }}
                  />
                </div>
                
                {/* Time Display */}
                <div className="flex items-center justify-between text-xs text-gray-300 font-mono">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(clip.duration)}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Static Overlay (when not hovered) */}
        <AnimatePresence>
          {!isHovered && !isPlaying && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-military-display text-white leading-tight mb-1 truncate">
                    {clip.player_name}
                  </h3>
                  <p className="text-xs text-gray-400 font-military-chat truncate">
                    {clip.description}
                  </p>
                </div>
                
                {/* Quick Stats Badge */}
                <div className="flex-shrink-0 ml-2">
                  {isShiftMode ? (
                    <div className="bg-red-600/20 border border-red-600/30 px-2 py-0.5 rounded">
                      <span className="text-xs font-mono text-red-400">
                        {clip.metadata?.shift_game_length_s ? `${formatDuration(clip.metadata.shift_game_length_s)} (rt ${formatDuration(clip.metadata?.shift_real_length_s || clip.duration)})` : formatDuration(clip.duration)}
                      </span>
                    </div>
                  ) : (
                    <div className="bg-cyan-600/20 border border-cyan-600/30 px-2 py-0.5 rounded">
                      <span className="text-xs font-mono text-cyan-400">
                        P{clip.metadata?.period || '?'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom Info Bar */}
      <div className="p-3 bg-black/60 border-t border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-mono text-gray-400 truncate">
                {clip.game_info}
              </span>
            </div>
            
            {/* Event Type */}
            <div className="flex items-center space-x-2">
              <div className="w-1 h-1 bg-red-500 rounded-full"></div>
              <span className="text-xs font-military-display text-white tracking-wider truncate">
                {clip.event_type}
              </span>
            </div>
          </div>
          
          {/* Play Count / Stats (optional) */}
          {clip.relevance_score && (
            <div className="flex-shrink-0 ml-2">
              <div className="text-right">
                <div className="text-xs font-mono text-gray-500">
                  Score: {(clip.relevance_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

